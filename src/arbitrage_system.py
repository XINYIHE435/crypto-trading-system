"""
跨交易所套利系统核心模块
实现开平仓逻辑、风险管理和利润计算

主要功能：
1. 价格监控和套利机会识别
2. 开仓逻辑执行
3. 平仓逻辑执行
4. 风险控制
5. 利润计算和统计
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
from src.data.funding_rate_loader import FundingRateLoader

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PositionType(Enum):
    """持仓类型枚举"""
    LONG = "long"      # 做多
    SHORT = "short"    # 做空
    FLAT = "flat"      # 空仓

class ActionType(Enum):
    """交易动作类型枚举"""
    OPEN_LONG = "open_long"     # 开多
    OPEN_SHORT = "open_short"   # 开空
    CLOSE_LONG = "close_long"   # 平多
    CLOSE_SHORT = "close_short" # 平空

@dataclass
class Position:
    """持仓信息数据类"""
    symbol: str
    exchange: str
    position_type: PositionType
    size: float
    entry_price: float
    entry_time: datetime
    current_price: float = 0.0
    unrealized_pnl: float = 0.0

    def update_price(self, new_price: float):
        """更新当前价格和未实现盈亏"""
        self.current_price = new_price
        if self.position_type == PositionType.LONG:
            self.unrealized_pnl = (new_price - self.entry_price) * self.size
        elif self.position_type == PositionType.SHORT:
            self.unrealized_pnl = (self.entry_price - new_price) * self.size

@dataclass
class ArbitrageOpportunity:
    """套利机会数据类"""
    symbol: str
    exchange_high: str     # 价格较高的交易所
    exchange_low: str      # 价格较低的交易所
    price_high: float      # 高价
    price_low: float       # 低价
    price_diff: float      # 价差
    price_diff_pct: float  # 价差百分比
    timestamp: datetime
    # 预期利润计算相关
    trading_fee_rate: float = 0.001  # 手续费率（默认0.1%）
    min_profit_threshold: float = 0.002  # 最小利润阈值（默认0.2%）
    # 资金费率相关
    funding_rate_high: float = 0.0     # 高价交易所资金费率
    funding_rate_low: float = 0.0      # 低价交易所资金费率
    expected_holding_hours: float = 8.0  # 预期持仓时间（小时）

    @property
    def expected_profit_pct(self) -> float:
        """计算预期利润百分比（考虑手续费和资金费率）"""
        gross_profit_pct = self.price_diff_pct

        # 交易手续费成本（双边）
        trading_cost_pct = 2 * self.trading_fee_rate

        # 资金费率成本/收益
        # 套利策略：做空高价交易所，做多低价交易所
        # 做空交易所：资金费率为正时需要支付，为负时获得收益
        # 做多交易所：资金费率为正时获得收益，为负时需要支付
        # 资金费率净成本 = 做空交易所费率 - 做多交易所费率
        funding_cost_pct = (self.funding_rate_high - self.funding_rate_low) * (self.expected_holding_hours / 24)

        net_profit_pct = gross_profit_pct - trading_cost_pct - funding_cost_pct
        return net_profit_pct

    @property
    def is_profitable(self) -> bool:
        """判断是否有利可图"""
        return self.expected_profit_pct >= self.min_profit_threshold

    @property
    def funding_arbitrage_pct(self) -> float:
        """计算纯资金费率套利收益百分比（正数表示成本，负数表示收益）"""
        return (self.funding_rate_high - self.funding_rate_low) * (self.expected_holding_hours / 24)

class ArbitrageSystem:
    """跨交易所套利系统主类"""

    def __init__(self, config: Dict = None, initial_balance: float = 10000, transaction_fee: float = 0.001,
                 enable_funding_rate: bool = True):
        """
        初始化套利系统

        Args:
            config: 配置字典，包含参数设置
            initial_balance: 初始资金余额
            transaction_fee: 交易手续费率
            enable_funding_rate: 是否启用资金费率计算
        """
        # 默认配置
        self.default_config = {
            'min_profit_threshold': 0.002,      # 最小利润阈值 0.2%（用于开仓判断）
            'max_position_size': 10000,         # 最大持仓大小
            'risk_max_drawdown': 0.05,          # 最大回撤限制 5%
            'stop_loss_pct': 0.05,             # 止损阈值 5%
            'take_profit_pct': 0.015,          # 止盈阈值 1.5%（风险收益比 1:3）
            'price_update_interval': 30,        # 价格更新间隔（秒）
            'position_timeout': 7200,           # 持仓超时时间（秒，2小时）
            'trading_fee_rate': transaction_fee, # 交易手续费率
            'min_price_diff': 0.001,            # 最小价差要求 0.1%
            'max_positions': 5,                 # 最大同时持仓数量
            'initial_balance': initial_balance,   # 初始资金余额
            'enable_funding_rate': enable_funding_rate,  # 是否启用资金费率
            'expected_holding_hours': 8.0,      # 预期持仓时间（小时）
        }

        # 合并配置
        self.config = self.default_config.copy()
        if config:
            self.config.update(config)

        # 系统状态
        self.positions: Dict[str, Position] = {}  # 持仓字典 {position_id: Position}
        self.open_opportunities: List[ArbitrageOpportunity] = []  # 当前套利机会
        self.closed_trades: List[Dict] = []      # 已完成交易记录
        self.total_pnl = 0.0                     # 总盈亏
        self.max_drawdown = 0.0                  # 最大回撤
        self.running = False                     # 系统运行状态

        # 初始化资金费率加载器
        self.funding_loader = None
        if self.config['enable_funding_rate']:
            try:
                self.funding_loader = FundingRateLoader()
                logger.info("资金费率加载器初始化成功")
            except Exception as e:
                logger.warning(f"资金费率加载器初始化失败: {e}")
                self.config['enable_funding_rate'] = False

        logger.info("套利系统初始化完成")

    def load_data(self, file_path: str, symbol: str) -> pd.DataFrame:
        """
        加载对齐后的价格数据
        自动适配不同的数据格式（单交易所或多交易所）

        Args:
            file_path: 数据文件路径
            symbol: 交易对符号

        Returns:
            处理后的DataFrame
        """
        try:
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)

            # 数据质量检查
            if df.empty:
                raise ValueError(f"数据文件为空: {file_path}")

            # 自动检测数据格式并标准化列名
            df = self._standardize_data_format(df)

            # 填充缺失值
            df = df.ffill().bfill()

            logger.info(f"成功加载数据: {symbol}, 数据量: {len(df)} 条")
            return df

        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            raise

    def _standardize_data_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化数据格式，处理不同的列名格式
        支持多交易所对齐数据格式

        Args:
            df: 原始DataFrame

        Returns:
            标准化后的DataFrame
        """
        # 检测数据来源（单交易所或多交易所）
        exchange_columns = {}

        # 方法1: 检测对齐数据集格式 (exchange_type_column) - 这是我们对齐数据集使用的格式
        for exchange in ['binance', 'bybit', 'kucoin']:
            price_col = f'{exchange}_close'
            if price_col in df.columns:
                exchange_columns[exchange] = {
                    'close': price_col,
                    'high': f'{exchange}_high',
                    'low': f'{exchange}_low',
                    'volume': f'{exchange}_volume'
                }

        # 方法2: 检测反向格式列名 (close_exchange)
        if not exchange_columns:
            for exchange in ['binance', 'bybit', 'kucoin']:
                price_col = f'close_{exchange}'
                if price_col in df.columns:
                    exchange_columns[exchange] = {
                        'close': price_col,
                        'high': f'high_{exchange}',
                        'low': f'low_{exchange}',
                        'volume': f'volume_{exchange}'
                    }

        # 方法3: 如果没有找到标准格式，检查是否为单交易所数据
        if not exchange_columns:
            # 检查是否有binance数据（最常见的格式）
            if 'close_binance' in df.columns:
                exchange_columns['binance'] = {
                    'close': 'close_binance',
                    'high': 'high_binance',
                    'low': 'low_binance',
                    'volume': 'volume_binance'
                }
            # 如果是简化格式（没有交易所前缀），假设为单一交易所
            elif 'close' in df.columns:
                exchange_columns['default'] = {
                    'close': 'close',
                    'high': 'high',
                    'low': 'low',
                    'volume': 'volume'
                }

        # 如果找到了单交易所数据，为其他交易所复制数据（用于测试）
        if len(exchange_columns) == 1:
            source_exchange = list(exchange_columns.keys())[0]
            source_cols = exchange_columns[source_exchange]

            # 添加微小噪声模拟其他交易所的价格差异
            noise_factor = 0.001  # 0.1%的噪声

            for target_exchange in ['binance', 'bybit', 'kucoin']:
                if target_exchange not in exchange_columns:
                    # 为目标交易所创建带噪声的价格数据
                    for col_type in ['close', 'high', 'low']:
                        source_col = source_cols[col_type]
                        target_col = f'{col_type}_{target_exchange}'
                        df[target_col] = df[source_col] * (1 + np.random.normal(0, noise_factor, len(df)))

                    # 交易量也添加噪声
                    source_volume = source_cols['volume']
                    target_volume = f'volume_{target_exchange}'
                    df[target_volume] = df[source_volume] * (1 + np.random.normal(0, noise_factor * 2, len(df)))
                    df[target_volume] = df[target_volume].abs()  # 确保交易量为正数

            logger.info(f"检测到单交易所数据，已模拟生成多交易所数据用于测试")
        else:
            logger.info(f"检测到多交易所数据，支持的交易所: {list(exchange_columns.keys())}")

        return df

    def identify_arbitrage_opportunities(self, df: pd.DataFrame, current_time: datetime) -> List[ArbitrageOpportunity]:
        """
        识别套利机会

        Args:
            df: 价格数据DataFrame
            current_time: 当前时间点

        Returns:
            套利机会列表
        """
        opportunities = []

        # 简化时间处理，统一转换为pandas Timestamp
        current_time = pd.Timestamp(current_time)

        # 获取当前时间点的价格数据
        try:
            current_data = df.loc[df.index <= current_time].iloc[-1]
        except IndexError:
            return opportunities

        # 获取交易对符号
        symbol = 'UNKNOWN'
        if 'symbol' in df.columns and not df['symbol'].empty:
            symbol = df['symbol'].iloc[0]

        # 检查所有交易所组合 - 使用有序组合避免重复
        exchanges = ['binance', 'bybit', 'kucoin']

        for i, exchange1 in enumerate(exchanges):
            for j in range(i + 1, len(exchanges)):  # 只比较 i < j，避免重复
                exchange2 = exchanges[j]

                # 获取价格列 - 统一列名检测
                price1 = self._get_exchange_price(current_data, exchange1)
                price2 = self._get_exchange_price(current_data, exchange2)

                # 检查价格有效性
                if price1 is None or price2 is None or price1 <= 0 or price2 <= 0:
                    continue

                # 计算价差（确保唯一性：exchange1 vs exchange2）
                if price1 > price2:
                    price_high, price_low = price1, price2
                    exchange_high, exchange_low = exchange1, exchange2
                else:
                    price_high, price_low = price2, price1
                    exchange_high, exchange_low = exchange2, exchange1

                price_diff = price_high - price_low
                price_diff_pct = price_diff / price_low if price_low > 0 else 0

                # 检查价差是否合理（避免异常值）
                if price_diff_pct > 0.1:  # 如果价差超过10%，可能是数据错误
                    logger.warning(f"检测到异常价差: {exchange_high}({price_high:.2f}) vs {exchange_low}({price_low:.2f}), "
                                  f"价差百分比: {price_diff_pct:.4f}, 跳过此机会")
                    continue

                # 检查最小价差阈值
                if price_diff_pct < self.config['min_price_diff']:
                    continue

                # 限制最大价差为5%（避免极端情况）
                if price_diff_pct >= 0.05:
                    continue

                # 获取资金费率数据
                funding_rate_high = 0.0
                funding_rate_low = 0.0

                if self.config['enable_funding_rate'] and self.funding_loader:
                    funding_rate_high = self._get_funding_rate(current_data, exchange_high, df, current_time)
                    funding_rate_low = self._get_funding_rate(current_data, exchange_low, df, current_time)

                # 创建套利机会对象
                opportunity = ArbitrageOpportunity(
                    symbol=symbol,
                    exchange_high=exchange_high,
                    exchange_low=exchange_low,
                    price_high=price_high,
                    price_low=price_low,
                    price_diff=price_diff,
                    price_diff_pct=price_diff_pct,
                    timestamp=current_time,
                    trading_fee_rate=self.config['trading_fee_rate'],
                    min_profit_threshold=self.config['min_profit_threshold'],
                    funding_rate_high=funding_rate_high,
                    funding_rate_low=funding_rate_low,
                    expected_holding_hours=self.config['expected_holding_hours']
                )

                # 判断是否满足套利条件
                if opportunity.is_profitable:
                    opportunities.append(opportunity)

                    # 记录详细的套利机会信息
                    funding_info = ""
                    if self.config['enable_funding_rate']:
                        funding_info = f", 资金费率成本: {opportunity.funding_arbitrage_pct:.6f}"

                    logger.info(f"发现套利机会: {exchange_high}({price_high:.2f}) vs {exchange_low}({price_low:.2f}), "
                              f"价差: {price_diff_pct:.4f}, 预期利润: {opportunity.expected_profit_pct:.4f}{funding_info}")

        return opportunities

    def _get_exchange_price(self, data_row: pd.Series, exchange: str) -> Optional[float]:
        """获取指定交易所的价格，支持多种列名格式"""
        # 尝试两种列名格式
        if f'{exchange}_close' in data_row:
            price = data_row[f'{exchange}_close']
        elif f'close_{exchange}' in data_row:
            price = data_row[f'close_{exchange}']
        else:
            return None
        return price if pd.notna(price) and price > 0 else None

    def _get_funding_rate(self, data_row: pd.Series, exchange: str, df: pd.DataFrame, current_time: datetime) -> float:
        """获取指定交易所的资金费率"""
        funding_rate_col = f'{exchange}_funding_rate'

        # 优先从数据行获取
        if funding_rate_col in data_row.index and not pd.isna(data_row[funding_rate_col]):
            return float(data_row[funding_rate_col])

        # 从资金费率加载器获取
        if self.funding_loader:
            # 尝试从 df 的属性中获取 symbol（标量值）
            symbol = 'UNKNOWN'
            if hasattr(df, 'attrs') and 'symbol' in df.attrs:
                symbol = df.attrs['symbol']
            elif isinstance(df, pd.DataFrame) and 'symbol' in df.columns:
                # 获取第一行的 symbol 值（假设整个 df 是同一个 symbol）
                symbol = df['symbol'].iloc[0] if not df['symbol'].empty else 'UNKNOWN'

            rate = self.funding_loader.get_funding_rate(
                exchange.lower(),
                symbol,
                current_time
            )
            return rate if rate is not None else 0.0

        return 0.0

    def calculate_position_size(self, opportunity: ArbitrageOpportunity, account_balance: float) -> float:
        """
        计算合适的持仓大小

        Args:
            opportunity: 套利机会
            account_balance: 账户余额

        Returns:
            建议的持仓大小
        """
        # 基于风险管理计算持仓大小
        max_risk_per_trade = account_balance * 0.02  # 单笔交易最大风险2%
        risk_per_unit = opportunity.price_low * (1 + self.config['trading_fee_rate'])

        # 基于风险和流动性计算持仓大小
        position_size = min(
            max_risk_per_trade / risk_per_unit,
            self.config['max_position_size'],
            account_balance * 0.3  # 单笔最大占用30%资金
        )

        return max(0, position_size)

    def open_positions(self, opportunity: ArbitrageOpportunity, position_size: float) -> bool:
        """
        开仓操作

        Args:
            opportunity: 套利机会
            position_size: 持仓大小

        Returns:
            开仓是否成功
        """
        try:
            # 检查持仓数量限制
            if len(self.positions) >= self.config['max_positions']:
                logger.warning("已达到最大持仓数量限制")
                return False

            # 生成持仓ID
            position_id = f"{opportunity.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # 创建两个持仓：高价交易所做空，低价交易所做多
            # 高价交易所做空
            short_position = Position(
                symbol=opportunity.symbol,
                exchange=opportunity.exchange_high,
                position_type=PositionType.SHORT,
                size=position_size,
                entry_price=opportunity.price_high,
                entry_time=opportunity.timestamp
            )

            # 低价交易所做多
            long_position = Position(
                symbol=opportunity.symbol,
                exchange=opportunity.exchange_low,
                position_type=PositionType.LONG,
                size=position_size,
                entry_price=opportunity.price_low,
                entry_time=opportunity.timestamp
            )

            # 保存持仓
            self.positions[f"{position_id}_short"] = short_position
            self.positions[f"{position_id}_long"] = long_position

            logger.info(f"开仓成功 - 套利对: {position_id}, "
                       f"做空: {opportunity.exchange_high}@{opportunity.price_high:.2f}, "
                       f"做多: {opportunity.exchange_low}@{opportunity.price_low:.2f}, "
                       f"数量: {position_size:.6f}")

            return True

        except Exception as e:
            logger.error(f"开仓失败: {e}")
            return False

    def update_positions(self, df: pd.DataFrame, current_time: datetime):
        """
        更新持仓状态和盈亏

        Args:
            df: 价格数据
            current_time: 当前时间
        """
        # 简化时间处理，统一转换为pandas Timestamp
        current_time = pd.Timestamp(current_time)

        try:
            current_data = df.loc[df.index <= current_time].iloc[-1]
        except IndexError:
            return

        positions_to_close = []

        for position_id, position in self.positions.items():
            # 获取当前价格 - 尝试两种列名格式
            current_price = None
            if f'{position.exchange}_close' in current_data.index:
                current_price = current_data[f'{position.exchange}_close']
            elif f'close_{position.exchange}' in current_data.index:
                current_price = current_data[f'close_{position.exchange}']
            
            if current_price is not None:
                position.update_price(current_price)
            else:
                logger.warning(f"无法获取 {position.exchange} 的价格数据")
                continue

            # 检查平仓条件
            should_close = False
            close_reason = ""

            # 1. 时间超限
            if (current_time - position.entry_time).total_seconds() > self.config['position_timeout']:
                should_close = True
                close_reason = "持仓超时"

            # 2. 达到目标利润（使用独立的止盈参数）
            if position.unrealized_pnl > 0:
                profit_pct = position.unrealized_pnl / (position.entry_price * position.size)
                take_profit = self.config.get('take_profit_pct', 0.015)  # 默认1.5%
                if profit_pct >= take_profit:
                    should_close = True
                    close_reason = f"达到目标利润 ({profit_pct:.2%})"

            # 3. 亏损扩大（使用独立的止损参数）
            if position.unrealized_pnl < 0:
                loss_pct = abs(position.unrealized_pnl) / (position.entry_price * position.size)
                stop_loss = self.config.get('stop_loss_pct', self.config.get('risk_max_drawdown', 0.05))
                if loss_pct >= stop_loss:
                    should_close = True
                    close_reason = f"止损平仓 ({loss_pct:.2%})"

            if should_close:
                positions_to_close.append((position_id, close_reason))

        # 平仓处理
        for position_id, reason in positions_to_close:
            self.close_position(position_id, reason)

    def close_position(self, position_id: str, current_price: float = None,
                    current_time: datetime = None, reason: str = ""):
        """
        平仓操作

        Args:
            position_id: 持仓ID
            current_price: 当前价格（可选，如果未提供则使用持仓价格）
            current_time: 当前时间（可选，如果未提供则使用持仓时间）
            reason: 平仓原因
        """
        if position_id not in self.positions:
            logger.warning(f"持仓不存在: {position_id}")
            return

        position = self.positions[position_id]

        # 使用提供的价格或当前持仓价格
        exit_price = current_price if current_price is not None else position.current_price
        exit_time = current_time if current_time is not None else datetime.now()

        # 计算已实现盈亏
        if current_price is not None:
            # 如果提供了新价格，重新计算盈亏
            if position.position_type == PositionType.LONG:
                realized_pnl = (exit_price - position.entry_price) * position.size
            elif position.position_type == PositionType.SHORT:
                realized_pnl = (position.entry_price - exit_price) * position.size
            else:
                realized_pnl = 0
        else:
            realized_pnl = position.unrealized_pnl

        # 计算交易手续费
        trading_fee = position.entry_price * position.size * self.config['trading_fee_rate']
        
        # 计算资金费率成本/收益
        funding_cost = 0.0
        if self.config['enable_funding_rate'] and self.funding_loader:
            funding_cost = self.funding_loader.calculate_funding_cost(
                position.exchange.lower(),
                position.symbol,
                position.size,
                position.entry_time,
                exit_time
            )
        
        # 净盈亏 = 已实现盈亏 - 交易手续费 + 资金费率收益/成本
        net_pnl = realized_pnl - trading_fee + funding_cost

        # 更新总盈亏
        self.total_pnl += net_pnl

        # 记录交易
        trade_record = {
            'position_id': position_id,
            'symbol': position.symbol,
            'exchange': position.exchange,
            'position_type': position.position_type.value,
            'entry_price': position.entry_price,
            'exit_price': exit_price,
            'size': position.size,
            'entry_time': position.entry_time,
            'exit_time': exit_time,
            'realized_pnl': realized_pnl,
            'trading_fee': trading_fee,
            'funding_cost': funding_cost,
            'net_pnl': net_pnl,
            'close_reason': reason,
            'holding_hours': (exit_time - position.entry_time).total_seconds() / 3600
        }

        self.closed_trades.append(trade_record)

        # 移除持仓
        del self.positions[position_id]

        logger.info(f"平仓完成 - {position_id}, "
                   f"盈亏: {net_pnl:.2f}, 原因: {reason}")

    def _update_positions_prices(self, row, current_time):
        """更新所有持仓的当前价格"""
        for position in self.positions.values():
            try:
                # 尝试两种列名格式
                current_price = None

                # 方法1: exchange_close 格式
                col1 = f'{position.exchange}_close'
                if col1 in row.index:
                    current_price = row[col1]
                # 方法2: close_exchange 格式
                elif f'close_{position.exchange}' in row.index:
                    current_price = row[f'close_{position.exchange}']

                if current_price is not None and pd.notna(current_price):
                    position.update_price(current_price)
                else:
                    logger.debug(f"无法获取 {position.exchange} 的价格数据")
            except Exception as e:
                logger.debug(f"更新 {position.exchange} 价格时出错: {e}")
                continue

    def _should_open_position(self, opportunity: ArbitrageOpportunity, account_balance: float) -> bool:
        """判断是否应该开仓"""
        if not opportunity.is_profitable:
            return False

        if len(self.positions) >= self.config['max_positions']:
            return False

        position_size = min(
            self.config['max_position_size'],
            account_balance * self.config['risk_max_drawdown']
        )

        return position_size > 100  # 最小交易金额

    def _open_arbitrage_position(self, opportunity: ArbitrageOpportunity, account_balance: float):
        """开套利仓位"""
        position_id = f"arb_{opportunity.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 计算合理的持仓数量（基于资金和价格）
        # 单笔交易最大占用10%资金，分别在两个交易所建仓
        max_position_value = account_balance * 0.1
        # 基于低价计算持仓数量，确保两边资金占用相近
        position_size = min(max_position_value / opportunity.price_low, self.config['max_position_size'])

        # 套利对必须使用相同的持仓数量（金额相同）
        # 在高价交易所做空，低价交易所做多
        short_pos = Position(
            symbol=opportunity.symbol,
            exchange=opportunity.exchange_high,
            position_type=PositionType.SHORT,
            size=position_size,
            entry_price=opportunity.price_high,
            entry_time=opportunity.timestamp
        )

        long_pos = Position(
            symbol=opportunity.symbol,
            exchange=opportunity.exchange_low,
            position_type=PositionType.LONG,
            size=position_size,
            entry_price=opportunity.price_low,
            entry_time=opportunity.timestamp
        )

        self.positions[f"{position_id}_short"] = short_pos
        self.positions[f"{position_id}_long"] = long_pos

        logger.info(f"开仓成功 - {position_id}, 数量: {position_size:.6f}, 预期利润: {opportunity.expected_profit_pct:.3%}")

    def _check_position_exit_conditions(self, row, current_time):
        """检查持仓平仓条件"""
        positions_to_close = []

        for pos_id, position in self.positions.items():
            # 检查持仓时间
            position_age = (current_time - position.entry_time).total_seconds()
            if position_age > self.config['position_timeout']:
                positions_to_close.append((pos_id, "持仓超时"))
                continue

            # 检查盈亏（基于持仓金额计算百分比）
            position_value = position.entry_price * position.size
            if position_value > 0:
                pnl_pct = abs(position.unrealized_pnl) / position_value
                # 使用配置的止盈止损参数
                if position.unrealized_pnl > 0:
                    # 止盈检查
                    take_profit = self.config.get('take_profit_pct', 0.015)  # 默认1.5%
                    if pnl_pct >= take_profit:
                        reason = f"止盈 ({pnl_pct:.2%})"
                        positions_to_close.append((pos_id, reason))
                else:
                    # 止损检查
                    stop_loss = self.config.get('stop_loss_pct', self.config.get('risk_max_drawdown', 0.05))
                    if pnl_pct >= stop_loss:
                        reason = f"止损 ({pnl_pct:.2%})"
                        positions_to_close.append((pos_id, reason))

        # 执行平仓
        for pos_id, reason in positions_to_close:
            if pos_id in self.positions:
                exchange = self.positions[pos_id].exchange
                current_price = None

                # 尝试两种列名格式
                col1 = f'{exchange}_close'
                if col1 in row.index:
                    current_price = row[col1]
                elif f'close_{exchange}' in row.index:
                    current_price = row[f'close_{exchange}']

                if current_price is None:
                    current_price = self.positions[pos_id].current_price
                self.close_position(pos_id, current_price, current_time, reason)

    def _close_all_positions(self, last_row, last_time, reason):
        """平仓所有持仓"""
        for pos_id in list(self.positions.keys()):
            if pos_id in self.positions:
                # 尝试两种列名格式
                current_price = None
                exchange = self.positions[pos_id].exchange

                col1 = f'{exchange}_close'
                if col1 in last_row.index:
                    current_price = last_row[col1]
                elif f'close_{exchange}' in last_row.index:
                    current_price = last_row[f'close_{exchange}']

                if current_price is None:
                    current_price = self.positions[pos_id].current_price
                self.close_position(pos_id, current_price, last_time, reason)

    def _calculate_backtest_results(self, account_balance: float) -> Dict:
        """计算回测结果"""
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'total_pnl': 0.0,
                'return_rate': 0.0,
                'win_rate': 0.0,
                'max_profit': 0.0,
                'max_loss': 0.0,
                'avg_profit': 0.0
            }

        profits = [t['net_pnl'] for t in self.closed_trades]
        profitable_trades = [t for t in self.closed_trades if t['net_pnl'] > 0]

        return {
            'total_trades': len(self.closed_trades),
            'total_pnl': sum(profits),
            'return_rate': sum(profits) / account_balance,
            'win_rate': len(profitable_trades) / len(self.closed_trades),
            'max_profit': max(profits),
            'max_loss': min(profits),
            'avg_profit': np.mean(profits)
        }

    def calculate_portfolio_stats(self) -> Dict:
        """
        计算投资组合统计信息

        Returns:
            统计信息字典
        """
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0,
                'avg_profit': 0.0,
                'max_profit': 0.0,
                'max_loss': 0.0,
                'current_positions': len(self.positions)
            }

        # 提取盈利交易
        profitable_trades = [t for t in self.closed_trades if t['net_pnl'] > 0]

        profits = [t['net_pnl'] for t in self.closed_trades]

        stats = {
            'total_trades': len(self.closed_trades),
            'total_pnl': sum(profits),
            'win_rate': len(profitable_trades) / len(self.closed_trades),
            'avg_profit': np.mean(profits) if profits else 0,
            'max_profit': max(profits) if profits else 0,
            'max_loss': min(profits) if profits else 0,
            'current_positions': len(self.positions),
            'unrealized_pnl': sum(p.unrealized_pnl for p in self.positions.values())
        }

        return stats

    def run_backtest(self, df: pd.DataFrame = None, symbol: str = "UNKNOWN", data_file: str = None,
                    start_date: datetime = None, end_date: datetime = None,
                    account_balance: float = 100000, enable_visualization: bool = False) -> Dict:
        """
        运行回测（整合后的统一接口）

        Args:
            df: 价格数据DataFrame（优先使用）
            symbol: 交易对符号
            data_file: 数据文件路径（如果未提供df）
            start_date: 开始日期
            end_date: 结束日期
            account_balance: 初始账户余额
            enable_visualization: 是否启用可视化

        Returns:
            回测结果统计
        """
        # 如果提供了文件路径，加载数据
        if data_file and df is None:
            logger.info(f"从文件加载数据: {data_file}")
            df = self.load_data(data_file, symbol)
            df['symbol'] = symbol

            # 移除时区信息以避免比较问题
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)

            # 设置日期范围
            if start_date:
                df = df[df.index >= pd.Timestamp(start_date)]
            if end_date:
                df = df[df.index <= pd.Timestamp(end_date)]

        if df is None or df.empty:
            raise ValueError("无效的数据：请提供有效的DataFrame或数据文件路径")

        logger.info(f"开始回测: {symbol}")
        logger.info(f"数据范围: {df.index[0]} 至 {df.index[-1]}")
        logger.info(f"数据点数: {len(df)}")

        # 重置系统状态
        self.positions.clear()
        self.closed_trades.clear()
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.running = True

        # 标准化数据格式
        df_processed = self._standardize_data_format(df.copy())
        df_processed['symbol'] = symbol

        # 逐个时间点处理
        for i, (current_time, row) in enumerate(df_processed.iterrows()):
            try:
                # 更新所有持仓的当前价格
                self._update_positions_prices(row, current_time)

                # 检查套利机会
                opportunities = self.identify_arbitrage_opportunities(df_processed.iloc[:i+1], current_time)

                # 评估并执行套利机会
                if opportunities:
                    for opportunity in opportunities[:2]:  # 限制同时开仓数量
                        if self._should_open_position(opportunity, account_balance):
                            self._open_arbitrage_position(opportunity, account_balance)

                # 检查持仓平仓条件
                self._check_position_exit_conditions(row, current_time)

                # 定期输出进度
                if i % 1000 == 0:
                    logger.info(f"处理进度: {i}/{len(df_processed)} - 当前盈亏: ${self.total_pnl:.2f}")

            except Exception as e:
                logger.error(f"处理时间点 {current_time} 时出错: {e}")
                continue

        # 平仓所有剩余持仓
        self._close_all_positions(df_processed.iloc[-1], df_processed.index[-1], "回测结束")

        # 计算回测结果
        results = self._calculate_backtest_results(account_balance)

        logger.info(f"回测完成 - 总交易: {results['total_trades']}, 总盈亏: ${results['total_pnl']:.2f}, "
                   f"胜率: {results['win_rate']:.2%}, 收益率: {results['return_rate']:.2%}")

        # 可选的可视化
        if enable_visualization:
            self._visualize_results(results)

        return results

    def _visualize_results(self, results: Dict):
        """
        可视化回测结果

        Args:
            results: 回测结果字典
        """
        try:
            # 尝试导入可视化模块
            import importlib
            spec = importlib.util.find_spec("src.visualization")
            if spec is None:
                logger.warning("可视化模块不存在，跳过图表生成")
                return

            from src.visualization import ArbitrageVisualizer
            visualizer = ArbitrageVisualizer()

            # 生成综合仪表板
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            dashboard_path = f"dashboard_{timestamp}.html"
            visualizer.create_dashboard(
                results,
                self.closed_trades,
                save_path=dashboard_path
            )

            # 导出完整报告
            report_path = f"arbitrage_report_{timestamp}.html"
            visualizer.export_report(
                results,
                self.closed_trades,
                save_path=report_path
            )

            logger.info(f"可视化报告已生成: {dashboard_path}")
            logger.info(f"HTML报告已导出: {report_path}")

        except ImportError:
            logger.warning("可视化模块不可用，跳过图表生成")
        except Exception as e:
            logger.error(f"生成可视化图表失败: {e}")

def main():
    """主函数 - 演示套利系统使用"""
    # 初始化套利系统
    arbitrage_system = ArbitrageSystem()

    # 设置回测参数
    symbol = "BTCUSDT"
    data_file = "/Users/jhjh/Documents/2025/Project/data project/data/aligned/aligned_BTCUSDT_30m_start_end.csv"

    # 运行回测
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)

    try:
        results = arbitrage_system.run_backtest(
            symbol=symbol,
            data_file=data_file,
            start_date=start_date,
            end_date=end_date,
            account_balance=100000,
            enable_visualization=False  # 设置为True以启用可视化
        )

        print("\n=== 回测结果 ===")
        for key, value in results.items():
            if isinstance(value, float):
                print(f"{key}: {value:.4f}")
            else:
                print(f"{key}: {value}")

    except Exception as e:
        logger.error(f"回测执行失败: {e}")

if __name__ == "__main__":
    main()