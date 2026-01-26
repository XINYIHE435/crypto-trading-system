"""
套利执行逻辑系统 - 完整实现
根据《套利开平仓逻辑系统》文档实现

实现功能：
1. 三种套利类型：差价套利、资金费率套利、组合套利
2. 方向判断：相同方向、不同方向
3. 6种开仓条件逻辑
4. 12种平仓条件逻辑
5. 完整的开仓记录
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ArbitrageType(Enum):
    """套利类型"""
    PRICE_SPREAD = "price_spread"           # 差价套利
    FUNDING_RATE = "funding_rate"           # 资金费率套利
    COMBINED = "combined"                   # 资金费率+差价组合套利


class OpenCondition(Enum):
    """开仓条件类型"""
    CONDITION_A = "condition_a"   # 条件a：相同方向
    CONDITION_B = "condition_b"   # 条件b：不同方向


class Direction(Enum):
    """方向"""
    SAME = "same"           # 相同方向：价差和资金费率差方向一致
    DIFFERENT = "different" # 不同方向：价差和资金费率差方向不一致


class CloseReason(Enum):
    """平仓原因"""
    PRICE_PROFIT = "price_profit"               # 价格回归盈利
    FUNDING_REVERSAL = "funding_reversal"       # 资金费率反转止损
    FUNDING_EXPAND = "funding_expand"           # 资金费率扩大止损
    PRICE_LOSS = "price_loss"                   # 价差亏损止损
    FUNDING_CONVERGE = "funding_converge"       # 资金费率收敛
    SPREAD_PROFIT = "spread_profit"             # 价差盈利平仓
    MANUAL = "manual"                           # 手动平仓
    TIMEOUT = "timeout"                         # 超时平仓


@dataclass
class ArbitragePosition:
    """套利持仓记录"""
    # 基本信息
    position_id: str
    symbol: str
    arbitrage_type: ArbitrageType
    open_condition: OpenCondition
    direction: Direction
    
    # 开仓数值
    open_price_spread: float          # 开仓时套利差价值
    open_price_spread_pct: float      # 开仓时差价百分比
    open_funding_spread: float        # 开仓时资金费率差值
    open_historical_avg: float        # 开仓历史平均值
    
    # 开仓价格
    open_price_a: float               # 交易所A价格
    open_price_b: float               # 交易所B价格
    
    # 开仓资金费率
    open_funding_a: float             # 交易所A资金费率
    open_funding_b: float             # 交易所B资金费率
    
    # 开仓时间和其他
    open_time: datetime
    exchange_a: str = "binance"
    exchange_b: str = "kucoin"
    position_size: float = 1.0
    
    # 套利方向（做空A做多B = True，做多A做空B = False）
    # 当A价格 > B价格时，做空A做多B（期待价差收敛获利）
    short_a_long_b: bool = True
    
    # 平仓信息（平仓时填充）
    close_time: Optional[datetime] = None
    close_price_a: float = 0.0
    close_price_b: float = 0.0
    close_price_spread_pct: float = 0.0
    close_funding_spread: float = 0.0
    close_reason: Optional[CloseReason] = None
    realized_pnl: float = 0.0
    
    # 状态追踪
    funding_reversal_start_time: Optional[datetime] = None  # 资金费率反转开始时间
    funding_expand_start_time: Optional[datetime] = None    # 资金费率扩大开始时间
    
    # 资金费率累计收益
    accumulated_funding_pnl: float = 0.0          # 累计资金费率收益
    last_funding_settlement_time: Optional[datetime] = None  # 上次结算时间
    funding_settlement_count: int = 0             # 结算次数
    
    @property
    def is_open(self) -> bool:
        return self.close_time is None
    
    @property
    def holding_hours(self) -> float:
        if self.close_time:
            return (self.close_time - self.open_time).total_seconds() / 3600
        return 0.0


@dataclass
class ArbitrageConfig:
    """套利系统配置参数"""
    # 核心参数（来自文档）
    X: float = 0.5          # 套利差价触发阈值（百分比）
    Y: float = 0.1          # 资金费率差触发阈值（百分比）
    A: float = 0.1          # 可忽视的差价百分比阈值
    B: float = 0.05         # 可忽视的资金费率差价百分比阈值
    N: int = 8              # 历史记录数据的小时数量
    M: int = 4              # 资金费率不利持续时间（小时）
    P: float = 0.3          # 价差盈利百分比
    Q: float = 0.5          # 价差亏损百分比
    
    # 其他配置
    initial_balance: float = 10000.0
    position_size_pct: float = 0.1    # 单次开仓占总资金百分比
    max_positions: int = 5            # 最大同时持仓数
    transaction_fee: float = 0.001    # 交易手续费率
    
    # 资金费率配置
    funding_settlement_hours: float = 8.0   # 资金费率结算周期（小时）
    funding_income_multiplier: float = 1.0  # 资金费率收益系数（用于模拟杠杆）


class ArbitrageSystem:
    """
    套利执行逻辑系统
    
    实现文档中的完整逻辑：
    1. 差价套利（条件a/条件b）
    2. 资金费率套利（条件a/条件b）
    3. 组合套利（相同方向）
    """
    
    def __init__(self, config: ArbitrageConfig = None):
        """初始化套利系统"""
        self.config = config or ArbitrageConfig()
        
        # 持仓管理
        self.positions: Dict[str, ArbitragePosition] = {}
        self.closed_positions: List[ArbitragePosition] = []
        
        # 统计数据
        self.total_pnl: float = 0.0
        self.balance: float = self.config.initial_balance
        self.trade_count: int = 0
        
        logger.info("套利系统初始化完成")
        logger.info(f"参数: X={self.config.X}%, Y={self.config.Y}%, A={self.config.A}%, "
                   f"B={self.config.B}%, N={self.config.N}h, M={self.config.M}h, "
                   f"P={self.config.P}%, Q={self.config.Q}%")

    def calculate_price_spread(self, price_a: float, price_b: float) -> Tuple[float, float, int]:
        """
        计算价差和方向
        
        返回：(价差绝对值, 价差百分比, 价差方向)
        方向：1 表示 A > B, -1 表示 A < B
        """
        spread = price_a - price_b
        spread_pct = abs(spread) / min(price_a, price_b) * 100
        direction = 1 if spread > 0 else -1
        return abs(spread), spread_pct, direction

    def calculate_funding_spread(self, funding_a: float, funding_b: float) -> Tuple[float, int]:
        """
        计算资金费率差和方向
        
        返回：(资金费率差百分比, 方向)
        方向：1 表示 A > B（做空A可以收取费率）, -1 表示 A < B
        """
        spread = funding_a - funding_b
        spread_pct = abs(spread) * 100  # 转为百分比
        direction = 1 if spread > 0 else -1
        return spread_pct, direction

    def check_direction(self, price_direction: int, funding_direction: int) -> Direction:
        """
        检查方向是否一致
        
        相同方向：价差和资金费率差方向一致
        不同方向：价差和资金费率差方向不一致
        """
        if price_direction == funding_direction:
            return Direction.SAME
        return Direction.DIFFERENT

    def get_historical_price_spread_avg(self, df: pd.DataFrame, idx: int, 
                                        price_col_a: str, price_col_b: str) -> float:
        """
        计算过去N小时的平均价差百分比
        
        注意：包含当前行，共N个数据点
        """
        # 计算需要的行数（假设30分钟K线，N小时 = N*2 根K线）
        periods = self.config.N * 2
        start_idx = max(0, idx - periods + 1)
        
        historical_data = df.iloc[start_idx:idx + 1]
        
        if len(historical_data) == 0:
            return 0.0
        
        spreads = []
        for _, row in historical_data.iterrows():
            price_a = row.get(price_col_a, 0)
            price_b = row.get(price_col_b, 0)
            if price_a > 0 and price_b > 0:
                spread_pct = abs(price_a - price_b) / min(price_a, price_b) * 100
                spreads.append(spread_pct)
        
        return np.mean(spreads) if spreads else 0.0

    def check_funding_rate_history(self, df: pd.DataFrame, idx: int,
                                   funding_col_a: str, funding_col_b: str) -> bool:
        """
        检查过去N小时资金费率差是否都 >= Y
        
        注意：包含当前行，共N个数据点
        """
        # 计算需要的行数
        periods = self.config.N * 2
        start_idx = max(0, idx - periods + 1)
        
        historical_data = df.iloc[start_idx:idx + 1]
        
        if len(historical_data) < periods:
            # 数据不足N小时
            return False
        
        for _, row in historical_data.iterrows():
            funding_a = row.get(funding_col_a, 0)
            funding_b = row.get(funding_col_b, 0)
            funding_spread_pct = abs(funding_a - funding_b) * 100
            
            if funding_spread_pct < self.config.Y:
                return False
        
        return True

    # ==================== 开仓条件检查 ====================
    
    def check_price_spread_arbitrage_condition_a(
        self, 
        price_spread_pct: float,
        historical_avg: float,
        direction: Direction,
        funding_spread_pct: float
    ) -> bool:
        """
        差价套利 - 条件a（相同方向）
        
        条件：
        1. 当前差价 >= X
        2. 当前差价 > 过去N小时平均值
        3. 价差方向 = 资金费率差方向（相同）
        4. 资金费率差 < Y
        """
        return (
            price_spread_pct >= self.config.X and
            price_spread_pct > historical_avg and
            direction == Direction.SAME and
            funding_spread_pct < self.config.Y
        )

    def check_price_spread_arbitrage_condition_b(
        self,
        price_spread_pct: float,
        historical_avg: float,
        direction: Direction,
        funding_spread_pct: float
    ) -> bool:
        """
        差价套利 - 条件b（不同方向）
        
        条件：
        1. 当前差价 >= X
        2. 当前差价 > 过去N小时平均值
        3. 价差方向 ≠ 资金费率差方向（不同）
        4. 资金费率差 < B
        """
        return (
            price_spread_pct >= self.config.X and
            price_spread_pct > historical_avg and
            direction == Direction.DIFFERENT and
            funding_spread_pct < self.config.B
        )

    def check_funding_rate_arbitrage_condition_a(
        self,
        funding_spread_pct: float,
        funding_history_valid: bool,
        direction: Direction,
        price_spread_pct: float
    ) -> bool:
        """
        资金费率套利 - 条件a（相同方向）
        
        条件：
        1. 资金费率差 >= Y
        2. 过去N小时都 >= Y
        3. 价差方向 = 资金费率差方向（相同）
        4. 当前差价 < X
        """
        return (
            funding_spread_pct >= self.config.Y and
            funding_history_valid and
            direction == Direction.SAME and
            price_spread_pct < self.config.X
        )

    def check_funding_rate_arbitrage_condition_b(
        self,
        funding_spread_pct: float,
        funding_history_valid: bool,
        direction: Direction,
        price_spread_pct: float
    ) -> bool:
        """
        资金费率套利 - 条件b（不同方向）
        
        条件：
        1. 资金费率差 >= Y
        2. 过去N小时都 >= Y
        3. 价差方向 ≠ 资金费率差方向（不同）
        4. 当前差价 < A
        """
        return (
            funding_spread_pct >= self.config.Y and
            funding_history_valid and
            direction == Direction.DIFFERENT and
            price_spread_pct < self.config.A
        )

    def check_combined_arbitrage(
        self,
        price_spread_pct: float,
        historical_avg: float,
        funding_spread_pct: float,
        funding_history_valid: bool,
        direction: Direction
    ) -> bool:
        """
        组合套利（相同方向）
        
        条件：
        1. 当前差价 >= X
        2. 当前差价 > 过去N小时平均值
        3. 资金费率差 >= Y
        4. 过去N小时都 >= Y
        5. 价差方向 = 资金费率差方向（相同）
        
        不触发：差价>=X 且 资金费率差>=Y，但方向不同
        """
        return (
            price_spread_pct >= self.config.X and
            price_spread_pct > historical_avg and
            funding_spread_pct >= self.config.Y and
            funding_history_valid and
            direction == Direction.SAME
        )

    # ==================== 平仓条件检查 ====================
    
    def check_close_price_spread_condition_a(
        self,
        position: ArbitragePosition,
        current_price_spread_pct: float,
        current_funding_spread_pct: float,
        current_funding_direction: int,
        current_time: datetime
    ) -> Tuple[bool, Optional[CloseReason]]:
        """
        差价套利场景一（条件a开仓 - 相同方向）平仓检查
        
        PDF原始逻辑：
        平仓条件a: 价格回归盈利
            - 价格回归有利可图
            - 不考虑其他条件
            - 立即平仓
        平仓条件b: 资金费率反转止损
            - 价差无利可图
            - 资金费率方向反转（赚取变成支付）
            - 资金费率数值 > A
            - 持续时间 > M
        平仓条件c: 价差亏损止损
            - 价差无利可图
            - 价差亏损 >= Q
        """
        # 计算当前盈亏百分比
        pnl_pct = position.open_price_spread_pct - current_price_spread_pct
        
        # 条件a：价格回归盈利（PDF原文：价格回归有利可图 → 立即平仓）
        # 注：PDF没有指定具体盈利阈值，字面意思是"任何正盈利"
        if pnl_pct > 0:
            return True, CloseReason.PRICE_PROFIT
        
        # 价差无利可图的情况
        if pnl_pct < 0:
            # 条件b：资金费率反转止损
            # 检查资金费率方向是否反转（从赚取变成支付）
            open_funding_direction = 1 if position.open_funding_spread > 0 else -1
            direction_reversed = (open_funding_direction != current_funding_direction) and (current_funding_spread_pct != 0)
            
            if direction_reversed and current_funding_spread_pct > self.config.A:
                # 检查持续时间
                if position.funding_reversal_start_time is None:
                    position.funding_reversal_start_time = current_time
                
                duration_hours = (current_time - position.funding_reversal_start_time).total_seconds() / 3600
                if duration_hours >= self.config.M:
                    return True, CloseReason.FUNDING_REVERSAL
            else:
                position.funding_reversal_start_time = None
            
            # 条件c：价差亏损止损
            loss_pct = abs(pnl_pct)
            if loss_pct >= self.config.Q:
                return True, CloseReason.PRICE_LOSS
        
        return False, None

    def check_close_price_spread_condition_b(
        self,
        position: ArbitragePosition,
        current_price_spread_pct: float,
        current_funding_spread_pct: float,
        current_time: datetime
    ) -> Tuple[bool, Optional[CloseReason]]:
        """
        差价套利场景二（条件b开仓 - 不同方向）平仓检查
        
        PDF原始逻辑：
        平仓条件a: 价格回归盈利
            - 价格回归有利可图
            - 不考虑其他条件
            - 立即平仓
        平仓条件b: 资金费率扩大止损
            - 价差无利可图
            - 需要支付资金费率
            - 资金费率阈值：< A 变成 > B
            - 持续时间 > M
        平仓条件c: 价差亏损止损
            - 价差无利可图
            - 价差亏损 >= Q
        """
        pnl_pct = position.open_price_spread_pct - current_price_spread_pct
        
        # 条件a：价格回归盈利（PDF原文：价格回归有利可图 → 立即平仓）
        if pnl_pct > 0:
            return True, CloseReason.PRICE_PROFIT
        
        # 价差无利可图
        if pnl_pct < 0:
            # 条件b：资金费率扩大止损
            # 检查：原本 < A，现在 > B
            open_funding_spread_pct = abs(position.open_funding_spread) * 100
            
            if open_funding_spread_pct < self.config.A and current_funding_spread_pct > self.config.B:
                if position.funding_expand_start_time is None:
                    position.funding_expand_start_time = current_time
                
                duration_hours = (current_time - position.funding_expand_start_time).total_seconds() / 3600
                if duration_hours >= self.config.M:
                    return True, CloseReason.FUNDING_EXPAND
            else:
                position.funding_expand_start_time = None
            
            # 条件c：价差亏损止损
            loss_pct = abs(pnl_pct)
            if loss_pct >= self.config.Q:
                return True, CloseReason.PRICE_LOSS
        
        return False, None

    def check_close_funding_rate_condition_a(
        self,
        position: ArbitragePosition,
        current_price_spread_pct: float,
        current_funding_spread_pct: float,
        current_funding_direction: int,
        current_time: datetime = None
    ) -> Tuple[bool, Optional[CloseReason]]:
        """
        资金费率套利场景一（条件a开仓 - 相同方向）平仓检查
        
        PDF原始逻辑：
        平仓条件a: 资金费率收敛或反转
            - 资金费率差 < B (收敛)
            - 或 从赚取变为支付
            - 无需考虑其他条件，立即平仓
        平仓条件b: 价差盈利平仓
            - 资金费率差仍能赚取
            - 价差可以实现盈利 >= P
        平仓条件c: 价差亏损止损
            - 不考虑资金费率
            - 价差亏损 >= Q
        """
        # 条件a：资金费率收敛或反转 - 立即平仓
        open_funding_direction = 1 if position.open_funding_spread > 0 else -1
        direction_reversed = (open_funding_direction != current_funding_direction) and (current_funding_spread_pct != 0)
        
        # 从赚取变为支付 - 立即平仓
        if direction_reversed:
            return True, CloseReason.FUNDING_CONVERGE
        
        # 资金费率差 < B (收敛) - 立即平仓
        if current_funding_spread_pct < self.config.B:
            return True, CloseReason.FUNDING_CONVERGE
        
        # 计算价差盈亏
        pnl_pct = position.open_price_spread_pct - current_price_spread_pct
        
        # 条件b：价差盈利平仓（资金费率仍能赚取 + 盈利>=P）
        funding_still_profitable = (current_funding_spread_pct >= self.config.B and not direction_reversed)
        if funding_still_profitable and pnl_pct >= self.config.P:
            return True, CloseReason.SPREAD_PROFIT
        
        # 条件c：价差亏损止损（不考虑资金费率，价差亏损>=Q）
        if pnl_pct < 0:
            loss_pct = abs(pnl_pct)
            if loss_pct >= self.config.Q:
                return True, CloseReason.PRICE_LOSS
        
        return False, None

    def check_close_funding_rate_condition_b(
        self,
        position: ArbitragePosition,
        current_price_spread_pct: float,
        current_funding_spread_pct: float,
        current_funding_direction: int,
        current_time: datetime = None
    ) -> Tuple[bool, Optional[CloseReason]]:
        """
        资金费率套利场景二（条件b开仓 - 不同方向）平仓检查
        
        平仓条件：
        a. 资金费率收敛或反转 - 费率差<B 或 从赚取变为支付 - 立即平仓
        b. 价差盈利平仓 - 资金费率差仍能赚取 + 价差盈利>=P
        c. 价差亏损止损 - 综合考虑资金费率收益
        """
        # 与条件a逻辑相同
        return self.check_close_funding_rate_condition_a(
            position, current_price_spread_pct, 
            current_funding_spread_pct, current_funding_direction, current_time
        )

    def check_close_combined(
        self,
        position: ArbitragePosition,
        current_price_spread_pct: float,
        current_funding_spread_pct: float,
        current_funding_direction: int,
        current_time: datetime = None
    ) -> Tuple[bool, Optional[CloseReason]]:
        """
        组合套利平仓检查
        
        PDF原始逻辑：
        平仓条件a: 资金费率收敛/反转或价差盈利
            - 资金费率差 <= B (收敛)
            - 或 资金费率从赚取变成支付 (反转)
            - 或 价差盈利 >= P
            - 三者任意触发一个即可，立即平仓
        平仓条件b: 价差亏损止损
            - 不考虑资金费率
            - 价差亏损 >= Q
        """
        # 条件a：资金费率收敛/反转 或 价差盈利（三者任一）
        open_funding_direction = 1 if position.open_funding_spread > 0 else -1
        direction_reversed = (open_funding_direction != current_funding_direction) and (current_funding_spread_pct != 0)
        
        # 资金费率收敛 <= B
        if current_funding_spread_pct <= self.config.B:
            return True, CloseReason.FUNDING_CONVERGE
        
        # 资金费率反转（从赚取变成支付）
        if direction_reversed:
            return True, CloseReason.FUNDING_REVERSAL
        
        # 价差盈利 >= P
        pnl_pct = position.open_price_spread_pct - current_price_spread_pct
        if pnl_pct >= self.config.P:
            return True, CloseReason.SPREAD_PROFIT
        
        # 条件b：价差亏损止损（不考虑资金费率，价差亏损>=Q）
        if pnl_pct < 0:
            loss_pct = abs(pnl_pct)
            if loss_pct >= self.config.Q:
                return True, CloseReason.PRICE_LOSS
        
        return False, None

    # ==================== 主要执行逻辑 ====================

    def open_position(
        self,
        symbol: str,
        arbitrage_type: ArbitrageType,
        open_condition: OpenCondition,
        direction: Direction,
        price_a: float,
        price_b: float,
        funding_a: float,
        funding_b: float,
        price_spread_pct: float,
        historical_avg: float,
        current_time: datetime,
        exchange_a: str = "binance",
        exchange_b: str = "kucoin"
    ) -> Optional[ArbitragePosition]:
        """开仓"""
        if len(self.positions) >= self.config.max_positions:
            logger.warning("已达最大持仓数限制")
            return None
        
        position_id = f"{symbol}_{arbitrage_type.value}_{current_time.strftime('%Y%m%d_%H%M%S')}"
        
        # 确定套利方向：
        # - 当A价格 > B价格时，做空A做多B（期待价差收敛获利）
        # - 当A价格 < B价格时，做多A做空B（期待价差收敛获利）
        short_a_long_b = price_a > price_b
        
        position = ArbitragePosition(
            position_id=position_id,
            symbol=symbol,
            arbitrage_type=arbitrage_type,
            open_condition=open_condition,
            direction=direction,
            open_price_spread=abs(price_a - price_b),
            open_price_spread_pct=price_spread_pct,
            open_funding_spread=funding_a - funding_b,
            open_historical_avg=historical_avg,
            open_price_a=price_a,
            open_price_b=price_b,
            open_funding_a=funding_a,
            open_funding_b=funding_b,
            open_time=current_time,
            exchange_a=exchange_a,
            exchange_b=exchange_b,
            position_size=self.balance * self.config.position_size_pct / price_a,
            short_a_long_b=short_a_long_b
        )
        
        self.positions[position_id] = position
        self.trade_count += 1
        
        trade_direction = "做空A做多B" if short_a_long_b else "做多A做空B"
        logger.info(f"📈 开仓 [{arbitrage_type.value}] {open_condition.value} | "
                   f"{symbol} | {trade_direction} | 价差方向: {direction.value} | "
                   f"价差: {price_spread_pct:.3f}% | 费率差: {(funding_a-funding_b)*100:.4f}%")
        
        return position

    def settle_funding_rate(
        self,
        position: ArbitragePosition,
        funding_a: float,
        funding_b: float,
        current_time: datetime
    ):
        """
        结算资金费率收益
        
        资金费率规则：
        - 正费率：多头支付给空头
        - 负费率：空头支付给多头
        
        套利方向：
        - short_a_long_b = True（做空A做多B）：
          - 在A交易所做空：funding_a > 0 收取，funding_a < 0 支付
          - 在B交易所做多：funding_b > 0 支付，funding_b < 0 收取
          - 净收益 = funding_a - funding_b
          
        - short_a_long_b = False（做多A做空B）：
          - 在A交易所做多：funding_a > 0 支付，funding_a < 0 收取
          - 在B交易所做空：funding_b > 0 收取，funding_b < 0 支付
          - 净收益 = funding_b - funding_a
        """
        # 检查是否到了结算时间（每8小时结算一次）
        if position.last_funding_settlement_time is None:
            position.last_funding_settlement_time = position.open_time
        
        hours_since_settlement = (current_time - position.last_funding_settlement_time).total_seconds() / 3600
        
        if hours_since_settlement >= self.config.funding_settlement_hours:
            position_value = position.position_size * position.open_price_a
            
            # 根据套利方向计算资金费率收益（可正可负）
            if position.short_a_long_b:
                # 做空A做多B：收取A的费率，支付B的费率
                funding_income = (funding_a - funding_b) * position_value
            else:
                # 做多A做空B：收取B的费率，支付A的费率
                funding_income = (funding_b - funding_a) * position_value
            
            # 应用收益系数（用于模拟杠杆）
            funding_income *= self.config.funding_income_multiplier
            
            position.accumulated_funding_pnl += funding_income
            position.last_funding_settlement_time = current_time
            position.funding_settlement_count += 1

    def close_position(
        self,
        position: ArbitragePosition,
        price_a: float,
        price_b: float,
        funding_spread_pct: float,
        current_time: datetime,
        reason: CloseReason
    ):
        """平仓"""
        position.close_time = current_time
        position.close_price_a = price_a
        position.close_price_b = price_b
        position.close_price_spread_pct = abs(price_a - price_b) / min(price_a, price_b) * 100
        position.close_funding_spread = funding_spread_pct
        position.close_reason = reason
        
        # 根据套利方向精确计算价差盈亏
        # 套利原理：开仓时在一边做空另一边做多，平仓时反向操作
        size = position.position_size
        
        if position.short_a_long_b:
            # 做空A做多B：
            # A交易所：开仓卖出 -> 平仓买入，盈亏 = (开仓价 - 平仓价) * 数量
            # B交易所：开仓买入 -> 平仓卖出，盈亏 = (平仓价 - 开仓价) * 数量
            pnl_a = (position.open_price_a - price_a) * size
            pnl_b = (price_b - position.open_price_b) * size
        else:
            # 做多A做空B：
            # A交易所：开仓买入 -> 平仓卖出，盈亏 = (平仓价 - 开仓价) * 数量
            # B交易所：开仓卖出 -> 平仓买入，盈亏 = (开仓价 - 平仓价) * 数量
            pnl_a = (price_a - position.open_price_a) * size
            pnl_b = (position.open_price_b - price_b) * size
        
        price_spread_pnl = pnl_a + pnl_b
        
        # 计算总盈亏
        # 对于资金费率套利和组合套利，加入资金费率收益
        if position.arbitrage_type in [ArbitrageType.FUNDING_RATE, ArbitrageType.COMBINED]:
            # 总盈亏 = 价差盈亏 + 累计资金费率收益
            total_pnl = price_spread_pnl + position.accumulated_funding_pnl
        else:
            # 差价套利只有价差盈亏
            total_pnl = price_spread_pnl
        
        # 精确计算手续费（两个交易所各开平仓一次，共4笔交易）
        # 开仓手续费
        fee_open_a = position.open_price_a * size * self.config.transaction_fee
        fee_open_b = position.open_price_b * size * self.config.transaction_fee
        # 平仓手续费
        fee_close_a = price_a * size * self.config.transaction_fee
        fee_close_b = price_b * size * self.config.transaction_fee
        total_fee = fee_open_a + fee_open_b + fee_close_a + fee_close_b
        
        position.realized_pnl = total_pnl - total_fee
        
        self.total_pnl += position.realized_pnl
        self.balance += position.realized_pnl
        
        # 移动到已平仓列表
        if position.position_id in self.positions:
            del self.positions[position.position_id]
        self.closed_positions.append(position)
        
        # 详细日志
        funding_info = ""
        if position.arbitrage_type in [ArbitrageType.FUNDING_RATE, ArbitrageType.COMBINED]:
            funding_info = f" | 费率收益: {position.accumulated_funding_pnl:.2f} ({position.funding_settlement_count}次结算)"
        
        trade_direction = "做空A做多B" if position.short_a_long_b else "做多A做空B"
        logger.info(f"📉 平仓 [{position.arbitrage_type.value}] | "
                   f"{position.symbol} | {trade_direction} | 原因: {reason.value} | "
                   f"盈亏: {position.realized_pnl:.2f} (手续费: {total_fee:.2f}){funding_info} | "
                   f"持仓时间: {position.holding_hours:.1f}h")

    def process_tick(
        self,
        df: pd.DataFrame,
        idx: int,
        symbol: str,
        price_col_a: str = "binance_close",
        price_col_b: str = "kucoin_close",
        funding_col_a: str = "binance_funding_rate",
        funding_col_b: str = "kucoin_funding_rate"
    ):
        """
        处理单个时间点的数据
        
        执行开仓检查和平仓检查
        """
        row = df.iloc[idx]
        current_time = row.name if isinstance(row.name, datetime) else pd.to_datetime(row.name)
        
        # 获取当前数据
        price_a = row.get(price_col_a, 0)
        price_b = row.get(price_col_b, 0)
        funding_a = row.get(funding_col_a, 0) or 0
        funding_b = row.get(funding_col_b, 0) or 0
        
        if price_a <= 0 or price_b <= 0:
            return
        
        # 计算指标
        _, price_spread_pct, price_direction = self.calculate_price_spread(price_a, price_b)
        funding_spread_pct, funding_direction = self.calculate_funding_spread(funding_a, funding_b)
        direction = self.check_direction(price_direction, funding_direction)
        historical_avg = self.get_historical_price_spread_avg(df, idx, price_col_a, price_col_b)
        funding_history_valid = self.check_funding_rate_history(df, idx, funding_col_a, funding_col_b)
        
        # ========== 资金费率结算 ==========
        for pos_id, position in self.positions.items():
            if position.arbitrage_type in [ArbitrageType.FUNDING_RATE, ArbitrageType.COMBINED]:
                self.settle_funding_rate(position, funding_a, funding_b, current_time)
        
        # ========== 平仓检查 ==========
        positions_to_close = []
        
        for pos_id, position in self.positions.items():
            should_close = False
            close_reason = None
            
            if position.arbitrage_type == ArbitrageType.PRICE_SPREAD:
                if position.open_condition == OpenCondition.CONDITION_A:
                    should_close, close_reason = self.check_close_price_spread_condition_a(
                        position, price_spread_pct, funding_spread_pct, 
                        funding_direction, current_time
                    )
                else:
                    should_close, close_reason = self.check_close_price_spread_condition_b(
                        position, price_spread_pct, funding_spread_pct, current_time
                    )
                    
            elif position.arbitrage_type == ArbitrageType.FUNDING_RATE:
                if position.open_condition == OpenCondition.CONDITION_A:
                    should_close, close_reason = self.check_close_funding_rate_condition_a(
                        position, price_spread_pct, funding_spread_pct, funding_direction, current_time
                    )
                else:
                    should_close, close_reason = self.check_close_funding_rate_condition_b(
                        position, price_spread_pct, funding_spread_pct, funding_direction, current_time
                    )
                    
            elif position.arbitrage_type == ArbitrageType.COMBINED:
                should_close, close_reason = self.check_close_combined(
                    position, price_spread_pct, funding_spread_pct, funding_direction, current_time
                )
            
            if should_close and close_reason:
                positions_to_close.append((position, close_reason))
        
        # 执行平仓
        for position, reason in positions_to_close:
            self.close_position(position, price_a, price_b, funding_spread_pct, current_time, reason)
        
        # ========== 开仓检查 ==========
        if len(self.positions) >= self.config.max_positions:
            return
        
        # 检查是否已有该symbol的持仓
        existing_position = any(p.symbol == symbol for p in self.positions.values())
        if existing_position:
            return
        
        # 1. 检查组合套利（优先级最高）
        if self.check_combined_arbitrage(
            price_spread_pct, historical_avg, funding_spread_pct, 
            funding_history_valid, direction
        ):
            self.open_position(
                symbol, ArbitrageType.COMBINED, OpenCondition.CONDITION_A,
                direction, price_a, price_b, funding_a, funding_b,
                price_spread_pct, historical_avg, current_time
            )
            return
        
        # 不触发：差价>=X 且 资金费率差>=Y 但方向不同
        if (price_spread_pct >= self.config.X and 
            funding_spread_pct >= self.config.Y and 
            direction == Direction.DIFFERENT):
            return
        
        # 2. 检查差价套利
        if self.check_price_spread_arbitrage_condition_a(
            price_spread_pct, historical_avg, direction, funding_spread_pct
        ):
            self.open_position(
                symbol, ArbitrageType.PRICE_SPREAD, OpenCondition.CONDITION_A,
                direction, price_a, price_b, funding_a, funding_b,
                price_spread_pct, historical_avg, current_time
            )
            return
        
        if self.check_price_spread_arbitrage_condition_b(
            price_spread_pct, historical_avg, direction, funding_spread_pct
        ):
            self.open_position(
                symbol, ArbitrageType.PRICE_SPREAD, OpenCondition.CONDITION_B,
                direction, price_a, price_b, funding_a, funding_b,
                price_spread_pct, historical_avg, current_time
            )
            return
        
        # 3. 检查资金费率套利
        if self.check_funding_rate_arbitrage_condition_a(
            funding_spread_pct, funding_history_valid, direction, price_spread_pct
        ):
            self.open_position(
                symbol, ArbitrageType.FUNDING_RATE, OpenCondition.CONDITION_A,
                direction, price_a, price_b, funding_a, funding_b,
                price_spread_pct, historical_avg, current_time
            )
            return
        
        if self.check_funding_rate_arbitrage_condition_b(
            funding_spread_pct, funding_history_valid, direction, price_spread_pct
        ):
            self.open_position(
                symbol, ArbitrageType.FUNDING_RATE, OpenCondition.CONDITION_B,
                direction, price_a, price_b, funding_a, funding_b,
                price_spread_pct, historical_avg, current_time
            )
            return

    def run_backtest(
        self,
        df: pd.DataFrame,
        symbol: str = "UNKNOWN",
        price_col_a: str = "binance_close",
        price_col_b: str = "kucoin_close",
        funding_col_a: str = "binance_funding_rate",
        funding_col_b: str = "kucoin_funding_rate"
    ) -> Dict:
        """
        运行回测
        """
        logger.info(f"开始回测: {symbol}")
        logger.info(f"数据范围: {df.index[0]} 至 {df.index[-1]}")
        logger.info(f"数据点数: {len(df)}")
        
        # 重置状态
        self.positions.clear()
        self.closed_positions.clear()
        self.total_pnl = 0.0
        self.balance = self.config.initial_balance
        self.trade_count = 0
        
        # 逐个处理
        for idx in range(len(df)):
            self.process_tick(
                df, idx, symbol,
                price_col_a, price_col_b,
                funding_col_a, funding_col_b
            )
            
            if idx % 1000 == 0:
                logger.info(f"处理进度: {idx}/{len(df)} | "
                           f"持仓: {len(self.positions)} | "
                           f"已平仓: {len(self.closed_positions)} | "
                           f"盈亏: {self.total_pnl:.2f}")
        
        # 强制平仓剩余持仓
        last_row = df.iloc[-1]
        last_time = last_row.name if isinstance(last_row.name, datetime) else pd.to_datetime(last_row.name)
        
        for position in list(self.positions.values()):
            price_a = last_row.get(price_col_a, position.open_price_a)
            price_b = last_row.get(price_col_b, position.open_price_b)
            funding_a = last_row.get(funding_col_a, 0) or 0
            funding_b = last_row.get(funding_col_b, 0) or 0
            funding_spread_pct = abs(funding_a - funding_b) * 100
            
            self.close_position(position, price_a, price_b, funding_spread_pct, last_time, CloseReason.TIMEOUT)
        
        # 生成结果
        results = self.generate_results()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"回测完成")
        logger.info(f"{'='*60}")
        logger.info(f"总交易次数: {results['total_trades']}")
        logger.info(f"总盈亏: {results['total_pnl']:.2f}")
        logger.info(f"收益率: {results['return_rate']:.2%}")
        logger.info(f"胜率: {results['win_rate']:.2%}")
        
        return results

    def generate_results(self) -> Dict:
        """生成回测结果"""
        if not self.closed_positions:
            return {
                'total_trades': 0,
                'total_pnl': 0.0,
                'return_rate': 0.0,
                'win_rate': 0.0,
                'by_type': {},
                'by_condition': {},
                'trades': []
            }
        
        profits = [p.realized_pnl for p in self.closed_positions]
        winning_trades = [p for p in self.closed_positions if p.realized_pnl > 0]
        
        # 按类型统计
        by_type = {}
        for arb_type in ArbitrageType:
            type_trades = [p for p in self.closed_positions if p.arbitrage_type == arb_type]
            if type_trades:
                by_type[arb_type.value] = {
                    'count': len(type_trades),
                    'total_pnl': sum(p.realized_pnl for p in type_trades),
                    'win_rate': len([p for p in type_trades if p.realized_pnl > 0]) / len(type_trades)
                }
        
        # 按条件统计
        by_condition = {}
        for condition in OpenCondition:
            cond_trades = [p for p in self.closed_positions if p.open_condition == condition]
            if cond_trades:
                by_condition[condition.value] = {
                    'count': len(cond_trades),
                    'total_pnl': sum(p.realized_pnl for p in cond_trades),
                    'win_rate': len([p for p in cond_trades if p.realized_pnl > 0]) / len(cond_trades)
                }
        
        # 交易详情
        trades = []
        for p in self.closed_positions:
            trades.append({
                'position_id': p.position_id,
                'symbol': p.symbol,
                'type': p.arbitrage_type.value,
                'condition': p.open_condition.value,
                'direction': p.direction.value,
                'open_time': str(p.open_time),
                'close_time': str(p.close_time),
                'open_spread_pct': p.open_price_spread_pct,
                'close_spread_pct': p.close_price_spread_pct,
                'close_reason': p.close_reason.value if p.close_reason else None,
                'realized_pnl': p.realized_pnl,
                'accumulated_funding_pnl': p.accumulated_funding_pnl,
                'funding_settlement_count': p.funding_settlement_count,
                'holding_hours': p.holding_hours
            })
        
        # 计算资金费率总收益
        total_funding_pnl = sum(p.accumulated_funding_pnl for p in self.closed_positions)
        
        return {
            'total_trades': len(self.closed_positions),
            'total_pnl': sum(profits),
            'total_funding_pnl': total_funding_pnl,
            'return_rate': sum(profits) / self.config.initial_balance,
            'win_rate': len(winning_trades) / len(self.closed_positions),
            'max_profit': max(profits),
            'max_loss': min(profits),
            'avg_profit': np.mean(profits),
            'avg_holding_hours': np.mean([p.holding_hours for p in self.closed_positions]),
            'by_type': by_type,
            'by_condition': by_condition,
            'trades': trades
        }


def main():
    """测试主函数"""
    # 创建配置
    config = ArbitrageConfig(
        X=0.5,    # 0.5% 价差触发
        Y=0.1,    # 0.1% 资金费率差触发
        A=0.1,    # 0.1% 可忽视价差
        B=0.05,   # 0.05% 可忽视资金费率差
        N=8,      # 8小时历史
        M=4,      # 4小时持续时间
        P=0.3,    # 0.3% 盈利目标
        Q=0.5,    # 0.5% 止损
        initial_balance=10000
    )
    
    # 创建系统
    system = ArbitrageSystem(config)
    
    # 加载数据并运行回测
    data_file = "data/aligned/BTCUSDT_30m_aligned.csv"
    
    try:
        df = pd.read_csv(data_file, index_col=0, parse_dates=True)
        
        # 运行回测
        results = system.run_backtest(
            df=df,
            symbol="BTCUSDT",
            price_col_a="binance_close",
            price_col_b="kucoin_close",
            funding_col_a="binance_funding_rate",
            funding_col_b="kucoin_funding_rate"
        )
        
        print("\n=== 回测结果 ===")
        print(f"总交易次数: {results['total_trades']}")
        print(f"总盈亏: ${results['total_pnl']:.2f}")
        print(f"收益率: {results['return_rate']:.2%}")
        print(f"胜率: {results['win_rate']:.2%}")
        
        print("\n=== 按类型统计 ===")
        for type_name, stats in results['by_type'].items():
            print(f"{type_name}: {stats['count']}笔, 盈亏${stats['total_pnl']:.2f}, 胜率{stats['win_rate']:.2%}")
        
    except FileNotFoundError:
        print(f"数据文件不存在: {data_file}")
    except Exception as e:
        print(f"运行失败: {e}")


if __name__ == "__main__":
    main()
