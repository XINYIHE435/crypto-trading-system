"""
双向马丁网格策略 - 完整实现
根据文档要求实现所有功能
"""
import time
from enum import Enum
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass, field


class GridSpacingType(Enum):
    """网格间距类型"""
    FIXED = "fixed"           # 固定点数
    PERCENTAGE = "percentage" # 百分比
    ATR = "atr"               # ATR 动态


class TakeProfitMode(Enum):
    """止盈方式"""
    UNIFIED = "unified"           # 1. 统一回本止盈（总盈亏≥0 + 小利润）
    PER_TRADE = "per_trade"       # 2. 逐笔小止盈（每组对冲完成后小额获利）
    TIERED = "tiered"             # 3. 分层止盈（不同层级不同止盈比例）


class BaselinePriceMode(Enum):
    """基准价模式"""
    DYNAMIC = "dynamic"   # 动态基准（基准价跟随当前价格重新设定）
    FIXED = "fixed"       # 固定区间（保持原基准）


@dataclass
class Order:
    """订单数据结构"""
    price: float
    size: float
    direction: str  # 'long' or 'short'
    level: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class DirectionState:
    """单方向持仓状态"""
    positions: List[Order] = field(default_factory=list)
    current_level: int = 0
    total_size: float = 0.0         # 累计仓位量
    average_price: float = 0.0      # 平均价格
    
    def reset(self):
        """重置状态"""
        self.positions = []
        self.current_level = 0
        self.total_size = 0.0
        self.average_price = 0.0
    
    def update_stats(self):
        """更新累计仓位量和平均价格"""
        if not self.positions:
            self.total_size = 0.0
            self.average_price = 0.0
            return
        
        self.total_size = sum(order.size for order in self.positions)
        total_value = sum(order.price * order.size for order in self.positions)
        self.average_price = total_value / self.total_size if self.total_size > 0 else 0.0


class DualMartingaleStrategy:
    """
    双向马丁网格策略 - 完整实现
    
    实现功能：
    1. 网格间距：固定点数 / 百分比 / ATR 动态
    2. 马丁倍投机制
    3. 总最大仓位限制（资金百分比或绝对值）
    4. 止盈方式：统一回本止盈 / 逐笔小止盈 / 分层止盈
    5. 平仓规则：总盈亏止盈 / 对冲回本 / 单边部分止盈 / 浮亏止损
    6. 基准价模式：动态基准 / 固定区间
    """
    
    def __init__(self, 
                 # 基础参数
                 base_size: float = 0.01,
                 multiplier: float = 1.6,
                 max_levels: int = 10,
                 martingale_start_level: int = 1,
                 
                 # 网格间距参数
                 grid_spacing_type: GridSpacingType = GridSpacingType.FIXED,
                 grid_step: float = 10.0,           # 固定点数时的间距
                 grid_percentage: float = 0.5,      # 百分比模式时的百分比（0.5 = 0.5%）
                 atr_multiplier: float = 1.0,       # ATR 动态模式的倍数
                 atr_period: int = 14,              # ATR 计算周期
                 
                 # 仓位限制参数
                 max_position_value: Optional[float] = None,  # 最大仓位绝对值（USDT）
                 max_position_percent: Optional[float] = None, # 最大仓位百分比（相对于总资金）
                 total_capital: float = 10000.0,              # 总资金（用于计算百分比限制）
                 
                 # 止盈参数
                 take_profit_mode: TakeProfitMode = TakeProfitMode.UNIFIED,
                 target_profit: float = 5.0,                  # 统一止盈目标
                 per_trade_profit: float = 1.0,               # 逐笔止盈金额
                 tiered_profit_ratios: Optional[Dict[int, float]] = None,  # 分层止盈比例 {层级: 止盈比例}
                 
                 # 对冲和部分止盈参数
                 hedge_profit_target: float = 2.0,            # 对冲回本后的小利目标
                 partial_profit_threshold: float = 5.0,       # 单边部分止盈触发阈值
                 partial_close_ratio: float = 0.5,            # 单边部分平仓比例
                 
                 # 止损参数
                 max_floating_loss: float = 100.0,
                 
                 # 基准价模式
                 baseline_mode: BaselinePriceMode = BaselinePriceMode.DYNAMIC,
                 
                 # 手续费参数
                 transaction_fee: float = 0.001,  # 交易手续费率 (0.1%)
                 
                 # 回调函数（用于获取外部数据）
                 atr_callback: Optional[Callable[[], float]] = None,
                 
                 # 调试模式
                 verbose: bool = True):
        """
        初始化策略参数
        
        参数说明：
        - base_size: 初始手数
        - multiplier: 马丁倍数（通常 1.6～3.0）
        - max_levels: 最大马丁层数（通常 4～10）
        - martingale_start_level: 第几层开始加倍（普通层 vs 马丁层）
        
        网格间距：
        - grid_spacing_type: 网格间距类型（固定/百分比/ATR）
        - grid_step: 固定点数间距
        - grid_percentage: 百分比间距
        - atr_multiplier: ATR 倍数
        
        仓位限制：
        - max_position_value: 最大仓位绝对值
        - max_position_percent: 最大仓位百分比
        - total_capital: 总资金
        
        止盈方式：
        - take_profit_mode: 止盈模式
        - target_profit: 统一止盈目标金额
        - per_trade_profit: 逐笔止盈金额
        - tiered_profit_ratios: 分层止盈比例字典
        
        止损：
        - max_floating_loss: 最大浮亏保护线
        
        基准价：
        - baseline_mode: 基准价模式（动态/固定）
        """
        # 基础参数
        self.base_size = base_size
        self.multiplier = multiplier
        self.max_levels = max_levels
        self.martingale_start_level = martingale_start_level
        
        # 网格间距参数
        self.grid_spacing_type = grid_spacing_type
        self.grid_step = grid_step
        self.grid_percentage = grid_percentage
        self.atr_multiplier = atr_multiplier
        self.atr_period = atr_period
        self.atr_callback = atr_callback
        
        # 仓位限制参数
        self.max_position_value = max_position_value
        self.max_position_percent = max_position_percent
        self.total_capital = total_capital
        
        # 止盈参数
        self.take_profit_mode = take_profit_mode
        self.target_profit = target_profit
        self.per_trade_profit = per_trade_profit
        self.tiered_profit_ratios = tiered_profit_ratios or {
            1: 0.3,   # 第1层止盈30%
            2: 0.5,   # 第2层止盈50%
            3: 0.7,   # 第3层止盈70%
            4: 1.0,   # 第4层及以上全部止盈
        }
        
        # 对冲和部分止盈参数
        self.hedge_profit_target = hedge_profit_target
        self.partial_profit_threshold = partial_profit_threshold
        self.partial_close_ratio = partial_close_ratio
        
        # 止损参数
        self.max_floating_loss = max_floating_loss
        
        # 基准价模式
        self.baseline_mode = baseline_mode
        
        # 手续费参数
        self.transaction_fee = transaction_fee
        
        # 调试模式
        self.verbose = verbose

        # 状态变量
        self.baseline_price: Optional[float] = None  # 基准价格
        self.initial_baseline_price: Optional[float] = None  # 初始基准价格（固定模式使用）
        self.long_state = DirectionState()
        self.short_state = DirectionState()
        
        # ATR 历史数据（用于计算 ATR）
        self.price_history: List[Dict] = []
        self.current_atr: float = 0.0
        
        # 统计数据
        self.total_realized_pnl: float = 0.0  # 当前轮次的已实现盈亏（平仓后清零）
        self.cumulative_pnl: float = 0.0  # 所有轮次的累计盈亏（不清零，用于回测统计）
        self.trade_count: int = 0  # 交易次数
        
    def log(self, message: str):
        """日志输出"""
        if self.verbose:
            print(message)

    def start(self, current_price: float):
        """策略启动"""
        self.baseline_price = current_price
        self.initial_baseline_price = current_price
        self.log(f"策略启动，基准价格设定为: {self.baseline_price:.2f}")

    def calculate_atr(self) -> float:
        """
        计算 ATR（平均真实波幅）
        如果提供了外部回调函数，则使用外部数据
        """
        if self.atr_callback:
            return self.atr_callback()
        
        if len(self.price_history) < self.atr_period:
            # 数据不足，返回默认值
            return self.grid_step
        
        # 使用最近 N 个周期的数据计算 ATR
        recent_data = self.price_history[-self.atr_period:]
        true_ranges = []
        
        for i in range(1, len(recent_data)):
            high = recent_data[i].get('high', recent_data[i]['close'])
            low = recent_data[i].get('low', recent_data[i]['close'])
            prev_close = recent_data[i-1]['close']
            
            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close)
            )
            true_ranges.append(tr)
        
        self.current_atr = sum(true_ranges) / len(true_ranges) if true_ranges else self.grid_step
        return self.current_atr

    def get_grid_spacing(self, current_price: float) -> float:
        """
        获取当前网格间距
        支持三种模式：固定点数 / 百分比 / ATR 动态
        """
        if self.grid_spacing_type == GridSpacingType.FIXED:
            return self.grid_step
        
        elif self.grid_spacing_type == GridSpacingType.PERCENTAGE:
            # 百分比模式：间距 = 当前价格 × 百分比
            return current_price * (self.grid_percentage / 100.0)
        
        elif self.grid_spacing_type == GridSpacingType.ATR:
            # ATR 动态模式：间距 = ATR × 倍数
            atr = self.calculate_atr()
            return atr * self.atr_multiplier
        
        return self.grid_step  # 默认

    def get_lot_size(self, direction: str) -> float:
        """
        计算下单手数
        普通层(1~N): base_size
        马丁层(N+1): 上层手数 × multiplier
        """
        state = self.long_state if direction == 'long' else self.short_state
        level = state.current_level
        
        # 如果是第一单，或者还在普通层范围内
        if level < self.martingale_start_level:
            return self.base_size
        else:
            # 获取上一单的手数进行倍投
            if state.positions:
                last_order_size = state.positions[-1].size
                return round(last_order_size * self.multiplier, 6)
            return self.base_size

    def check_position_limit(self, direction: str, new_size: float, current_price: float) -> bool:
        """
        检查是否超出仓位限制
        返回 True 表示允许开仓，False 表示已达到限制
        
        PDF原文："总最大仓位限制（资金百分比或绝对值）"
        要求：检查多空合计的总仓位，而非单方向仓位
        """
        # 计算新增仓位价值
        new_position_value = new_size * current_price
        
        # 计算多空双向的当前总仓位价值
        long_position_value = self.long_state.total_size * current_price
        short_position_value = self.short_state.total_size * current_price
        current_total_position_value = long_position_value + short_position_value
        
        # 加入新仓位后的总仓位价值
        total_position_value = current_total_position_value + new_position_value
        
        # 检查绝对值限制（总仓位限制）
        if self.max_position_value is not None:
            if total_position_value > self.max_position_value:
                self.log(f"⚠️ 总仓位已达最大值限制: {total_position_value:.2f} > {self.max_position_value:.2f} USDT "
                        f"(多:{long_position_value:.2f} + 空:{short_position_value:.2f} + 新:{new_position_value:.2f})")
                return False
        
        # 检查百分比限制（总仓位限制）
        if self.max_position_percent is not None:
            max_value = self.total_capital * (self.max_position_percent / 100.0)
            if total_position_value > max_value:
                self.log(f"⚠️ 总仓位已达百分比限制: {self.max_position_percent}% ({max_value:.2f} USDT) "
                        f"(当前总:{current_total_position_value:.2f} + 新:{new_position_value:.2f})")
                return False
        
        return True

    def open_order(self, direction: str, price: float) -> bool:
        """
        开仓逻辑
        返回 True 表示成功开仓
        """
        state = self.long_state if direction == 'long' else self.short_state
        
        # 检查是否达到最大层数
        if state.current_level >= self.max_levels:
            self.log(f"⚠️ {direction} 方向已达最大层数 {self.max_levels}，停止加仓。")
            return False

        # 计算手数
        size = self.get_lot_size(direction)
        
        # 检查仓位限制
        if not self.check_position_limit(direction, size, price):
            return False

        # 创建订单
        order = Order(
            price=price,
            size=size,
            direction=direction,
            level=state.current_level + 1
        )
        
        # 添加订单
        state.positions.append(order)
        state.current_level += 1
        
        # 更新累计仓位量和平均价格
        state.update_stats()
        
        self.trade_count += 1
        
        self.log(f"📈 开仓 {direction.upper()} | 价格: {price:.2f} | 手数: {size:.6f} | "
                f"层级: {state.current_level} | 累计仓位: {state.total_size:.6f} | "
                f"平均价: {state.average_price:.2f}")
        
        return True

    def calculate_direction_pnl(self, direction: str, current_price: float) -> float:
        """计算单方向浮动盈亏"""
        state = self.long_state if direction == 'long' else self.short_state
        pnl = 0.0
        
        for order in state.positions:
            if direction == 'long':
                pnl += (current_price - order.price) * order.size
            else:
                pnl += (order.price - current_price) * order.size
        
        return pnl

    def calculate_total_pnl(self, current_price: float, include_realized: bool = False) -> float:
        """
        计算总盈亏
        
        参数:
            include_realized: 是否包含已实现盈亏
                - False: 只返回当前浮动盈亏（用于显示当前持仓状态）
                - True: 返回总净盈亏 = 浮动盈亏 + 已实现盈亏（用于止盈判断）
        """
        long_pnl = self.calculate_direction_pnl('long', current_price)
        short_pnl = self.calculate_direction_pnl('short', current_price)
        floating_pnl = long_pnl + short_pnl
        
        if include_realized:
            return floating_pnl + self.total_realized_pnl
        return floating_pnl

    def close_direction(self, direction: str, current_price: float, ratio: float = 1.0, reason: str = ""):
        """
        平仓单个方向
        ratio: 平仓比例（0.0-1.0），用于部分平仓
        """
        state = self.long_state if direction == 'long' else self.short_state
        
        if not state.positions:
            return 0.0
        
        realized_pnl = 0.0
        total_fee = 0.0
        
        if ratio >= 1.0:
            # 全部平仓
            realized_pnl = self.calculate_direction_pnl(direction, current_price)
            
            # 计算手续费（开仓+平仓双向）
            for order in state.positions:
                # 开仓手续费
                total_fee += order.price * order.size * self.transaction_fee
                # 平仓手续费
                total_fee += current_price * order.size * self.transaction_fee
            
            realized_pnl -= total_fee
            self.log(f"📉 平仓 {direction.upper()} | {reason} | 盈亏: {realized_pnl:.2f} (手续费: {total_fee:.2f})")
            state.reset()
        else:
            # 部分平仓
            close_count = max(1, int(len(state.positions) * ratio))
            closed_positions = state.positions[:close_count]
            state.positions = state.positions[close_count:]
            
            for order in closed_positions:
                if direction == 'long':
                    realized_pnl += (current_price - order.price) * order.size
                else:
                    realized_pnl += (order.price - current_price) * order.size
                
                # 计算手续费（开仓+平仓双向）
                total_fee += order.price * order.size * self.transaction_fee
                total_fee += current_price * order.size * self.transaction_fee
            
            realized_pnl -= total_fee
            
            # 更新层级和统计
            state.current_level = len(state.positions)
            state.update_stats()
            
            self.log(f"📉 部分平仓 {direction.upper()} ({ratio*100:.0f}%) | {reason} | "
                    f"盈亏: {realized_pnl:.2f} (手续费: {total_fee:.2f}) | 剩余层级: {state.current_level}")
        
        self.total_realized_pnl += realized_pnl
        return realized_pnl

    def close_all(self, current_price: float, reason: str = ""):
        """平仓所有方向并重置"""
        realized_pnl = self.calculate_total_pnl(current_price)
        
        # 计算总手续费（开仓+平仓双向）
        total_fee = 0.0
        for order in self.long_state.positions:
            total_fee += order.price * order.size * self.transaction_fee  # 开仓
            total_fee += current_price * order.size * self.transaction_fee  # 平仓
        for order in self.short_state.positions:
            total_fee += order.price * order.size * self.transaction_fee  # 开仓
            total_fee += current_price * order.size * self.transaction_fee  # 平仓
        
        realized_pnl -= total_fee
        self.log(f"🔴 全部平仓: {reason} | 最终盈亏: {realized_pnl:.2f} (手续费: {total_fee:.2f})")
        
        # 重置两个方向
        self.long_state.reset()
        self.short_state.reset()
        
        # 本轮最终盈亏 = 当前浮动盈亏 + 本轮已实现盈亏（部分平仓）
        round_total_pnl = realized_pnl + self.total_realized_pnl
        
        # 更新累计盈亏（所有轮次，不清零）
        self.cumulative_pnl += round_total_pnl
        
        # 重置当前轮次的已实现盈亏（新一轮开始）
        # 修复GPT指出的问题：防止历史盈亏影响新一轮的统一止盈判断
        self.total_realized_pnl = 0.0
        
        self.log(f"📊 本轮盈亏: {round_total_pnl:.2f} | 累计盈亏: {self.cumulative_pnl:.2f}")
        
        # 根据基准价模式决定是否重设基准价
        if self.baseline_mode == BaselinePriceMode.DYNAMIC:
            self.baseline_price = current_price
            self.log(f"🔄 动态基准: 新基准价设定为 {self.baseline_price:.2f}")
        else:
            # 固定区间模式：保持原基准
            self.baseline_price = self.initial_baseline_price
            self.log(f"🔄 固定基准: 保持原基准价 {self.baseline_price:.2f}")
        
        self.log("-" * 50)

    def check_unified_take_profit(self, current_price: float) -> bool:
        """
        检查统一回本止盈
        条件：总净盈亏 ≥ 目标利润
        
        PDF原文："总净盈亏 ≥ 目标利润"
        总净盈亏 = 当前浮动盈亏 + 已实现盈亏（历史平仓收益）
        """
        # 计算总净盈亏（包含已实现盈亏）
        total_net_pnl = self.calculate_total_pnl(current_price, include_realized=True)
        has_positions = self.long_state.current_level > 0 or self.short_state.current_level > 0
        
        if total_net_pnl >= self.target_profit and has_positions:
            floating_pnl = self.calculate_total_pnl(current_price, include_realized=False)
            self.close_all(current_price, 
                          reason=f"统一止盈 (目标: {self.target_profit}, 净盈亏: {total_net_pnl:.2f}, "
                                f"浮动: {floating_pnl:.2f}, 已实现: {self.total_realized_pnl:.2f})")
            return True
        return False

    def check_per_trade_take_profit(self, current_price: float) -> bool:
        """
        检查逐笔小止盈
        条件：每组对冲完成后小额获利
        
        PDF原文："逐笔小止盈（每组对冲完成后小额获利）"
        要求：多空两边都已开仓（形成对冲），然后总盈亏达到目标时止盈
        """
        # 检查是否对冲完成：多空两边都有持仓
        has_long = self.long_state.current_level > 0
        has_short = self.short_state.current_level > 0
        
        if not (has_long and has_short):
            # 没有形成对冲，不触发逐笔止盈
            return False
        
        # 对冲完成，计算总浮动盈亏
        long_pnl = self.calculate_direction_pnl('long', current_price)
        short_pnl = self.calculate_direction_pnl('short', current_price)
        total_pnl = long_pnl + short_pnl
        
        if total_pnl >= self.per_trade_profit:
            # 对冲回本+小利，全部平仓
            self.close_all(current_price, reason=f"逐笔止盈 对冲完成 (目标: {self.per_trade_profit}, 盈亏: {total_pnl:.2f})")
            return True
        
        return False

    def check_tiered_take_profit(self, current_price: float) -> bool:
        """
        检查分层止盈
        条件：不同层级不同止盈比例
        """
        triggered = False
        
        for direction in ['long', 'short']:
            state = self.long_state if direction == 'long' else self.short_state
            
            if state.current_level == 0:
                continue
            
            direction_pnl = self.calculate_direction_pnl(direction, current_price)
            
            # 获取当前层级对应的止盈比例
            max_level_in_ratios = max(self.tiered_profit_ratios.keys())
            level_key = min(state.current_level, max_level_in_ratios)
            profit_ratio = self.tiered_profit_ratios.get(level_key, 1.0)
            
            # 计算该层级的止盈目标（基于层级的止盈目标）
            tier_target = self.target_profit * profit_ratio * state.current_level
            
            if direction_pnl >= tier_target:
                self.close_direction(direction, current_price, 
                                   reason=f"分层止盈 L{state.current_level} (比例: {profit_ratio*100:.0f}%, 目标: {tier_target:.2f})")
                triggered = True
        
        return triggered

    def check_hedge_take_profit(self, current_price: float) -> bool:
        """
        检查对冲回本+小利
        条件：多空两边都已开仓 → 对冲回本+小利
        """
        if self.long_state.current_level > 0 and self.short_state.current_level > 0:
            total_pnl = self.calculate_total_pnl(current_price)
            
            # 对冲后盈利达到目标
            if total_pnl >= self.hedge_profit_target:
                self.close_all(current_price, 
                             reason=f"对冲止盈 (多空对冲, 目标: {self.hedge_profit_target})")
                return True
        
        return False

    def check_partial_take_profit(self, current_price: float) -> bool:
        """
        检查单边部分止盈
        条件：单边达到一定盈利 → 部分止盈
        
        注意：此功能为可选扩展，不在标准止盈流程中自动调用。
        如需使用，可在自定义策略中手动调用，或修改 check_take_profit 添加调用。
        
        参数：
        - partial_profit_threshold: 单边部分止盈触发阈值
        - partial_close_ratio: 部分平仓比例 (0.0-1.0)
        """
        triggered = False
        
        for direction in ['long', 'short']:
            state = self.long_state if direction == 'long' else self.short_state
            
            if state.current_level == 0:
                continue
            
            direction_pnl = self.calculate_direction_pnl(direction, current_price)
            
            if direction_pnl >= self.partial_profit_threshold:
                self.close_direction(direction, current_price, 
                                   ratio=self.partial_close_ratio,
                                   reason=f"单边部分止盈 (阈值: {self.partial_profit_threshold})")
                triggered = True
        
        return triggered

    def check_stop_loss(self, current_price: float) -> bool:
        """
        检查止损
        条件：总浮亏达到预警线 → 强制全部止损
        """
        total_pnl = self.calculate_total_pnl(current_price)
        
        if total_pnl <= -self.max_floating_loss:
            self.close_all(current_price, reason=f"触发止损保护 (最大浮亏: {self.max_floating_loss})")
            return True
        
        return False

    def check_take_profit(self, current_price: float) -> bool:
        """
        根据当前止盈模式检查是否触发止盈
        """
        # 首先检查止损（最高优先级）
        if self.check_stop_loss(current_price):
            return True
        
        # 根据止盈模式执行
        if self.take_profit_mode == TakeProfitMode.UNIFIED:
            # 统一止盈模式：先检查对冲止盈，再检查统一止盈
            if self.check_hedge_take_profit(current_price):
                return True
            return self.check_unified_take_profit(current_price)
        
        elif self.take_profit_mode == TakeProfitMode.PER_TRADE:
            # 逐笔止盈模式：直接使用 per_trade_profit 作为目标
            # 不再调用 check_hedge_take_profit 避免重复
            return self.check_per_trade_take_profit(current_price)
        
        elif self.take_profit_mode == TakeProfitMode.TIERED:
            # 分层止盈模式：先检查对冲止盈，再检查分层止盈
            if self.check_hedge_take_profit(current_price):
                return True
            return self.check_tiered_take_profit(current_price)
        
        return False

    def update_price_history(self, price_data: Dict):
        """
        更新价格历史（用于 ATR 计算）
        price_data: {'open': x, 'high': y, 'low': z, 'close': w}
        """
        self.price_history.append(price_data)
        # 保留最近 N 个周期的数据
        max_history = self.atr_period * 2
        if len(self.price_history) > max_history:
            self.price_history = self.price_history[-max_history:]

    def on_tick(self, current_price: float, price_data: Optional[Dict] = None):
        """
        主循环: 处理实时价格
        
        参数：
        - current_price: 当前价格
        - price_data: 可选的OHLC数据，用于ATR计算 {'open': x, 'high': y, 'low': z, 'close': w}
        
        PDF原始逻辑：
        - 上涨区间 (高于基准+间距) → 检查上方网格线 → 开买单（多头）
        - 下跌区间 (低于基准-间距) → 检查下方网格线 → 开卖单（空头）
        """
        # 更新价格历史（用于ATR）
        if price_data:
            self.update_price_history(price_data)
        else:
            self.update_price_history({'close': current_price})
        
        # 初始化基准价
        if self.baseline_price is None:
            self.start(current_price)
            return

        # 1. 检查止盈止损
        if self.check_take_profit(current_price):
            return

        # 2. 计算网格间距
        grid_spacing = self.get_grid_spacing(current_price)
        
        # 3. 检查网格触发条件（严格按照PDF原始逻辑）
        price_diff = current_price - self.baseline_price
        
        # 上涨区间处理 (高于基准+间距) → 开买单（多头）
        # PDF原文：上涨区间 → 检查上方网格线 → 是否到达下一买单线？→ 开买单（多头）
        # 修复GPT指出的问题：如果价格跳过多层网格，需要补齐中间层级
        if price_diff > 0:
            grid_index = int(price_diff / grid_spacing)
            # 循环开仓，补齐所有跳过的层级
            while grid_index > self.long_state.current_level:
                if not self.open_order('long', current_price):
                    break  # 如果开仓失败（达到限制），停止循环

        # 下跌区间处理 (低于基准-间距) → 开卖单（空头）
        # PDF原文：下跌区间 → 检查下方网格线 → 是否到达下一卖单线？→ 开卖单（空头）
        elif price_diff < 0:
            grid_index = int(abs(price_diff) / grid_spacing)
            # 循环开仓，补齐所有跳过的层级
            while grid_index > self.short_state.current_level:
                if not self.open_order('short', current_price):
                    break  # 如果开仓失败（达到限制），停止循环

    def get_status(self, current_price: float) -> Dict:
        """获取当前策略状态"""
        return {
            'baseline_price': self.baseline_price,
            'current_price': current_price,
            'grid_spacing': self.get_grid_spacing(current_price),
            'grid_spacing_type': self.grid_spacing_type.value,
            'take_profit_mode': self.take_profit_mode.value,
            'baseline_mode': self.baseline_mode.value,
            'long': {
                'level': self.long_state.current_level,
                'total_size': self.long_state.total_size,
                'average_price': self.long_state.average_price,
                'pnl': self.calculate_direction_pnl('long', current_price)
            },
            'short': {
                'level': self.short_state.current_level,
                'total_size': self.short_state.total_size,
                'average_price': self.short_state.average_price,
                'pnl': self.calculate_direction_pnl('short', current_price)
            },
            'total_pnl': self.calculate_total_pnl(current_price),
            'total_realized_pnl': self.total_realized_pnl,  # 当前轮次已实现
            'cumulative_pnl': self.cumulative_pnl,  # 所有轮次累计
            'trade_count': self.trade_count,
            'current_atr': self.current_atr
        }


# --- 模拟运行测试 ---
if __name__ == "__main__":
    print("=" * 60)
    print("双向马丁网格策略 - 完整实现测试")
    print("=" * 60)
    
    # 测试1: 统一止盈模式（固定网格）
    print("\n【测试1】统一止盈模式 + 固定网格")
    print("-" * 40)
    
    strategy1 = DualMartingaleStrategy(
        base_size=1,
        grid_spacing_type=GridSpacingType.FIXED,
        grid_step=10,
        multiplier=2.0,
        max_levels=5,
        take_profit_mode=TakeProfitMode.UNIFIED,
        target_profit=20,
        max_floating_loss=50,
        baseline_mode=BaselinePriceMode.DYNAMIC
    )
    
    prices1 = [100, 105, 112, 108, 122, 115, 95, 135, 136]
    for p in prices1:
        print(f"\n当前市价: {p}")
        strategy1.on_tick(p)
    
    # 测试2: 逐笔止盈模式（百分比网格）
    print("\n" + "=" * 60)
    print("【测试2】逐笔止盈模式 + 百分比网格")
    print("-" * 40)
    
    strategy2 = DualMartingaleStrategy(
        base_size=1,
        grid_spacing_type=GridSpacingType.PERCENTAGE,
        grid_percentage=2.0,  # 2%
        multiplier=1.5,
        max_levels=5,
        take_profit_mode=TakeProfitMode.PER_TRADE,
        per_trade_profit=5,
        max_floating_loss=50,
        baseline_mode=BaselinePriceMode.FIXED
    )
    
    prices2 = [100, 103, 106, 104, 98, 95, 92, 100, 108]
    for p in prices2:
        print(f"\n当前市价: {p}")
        strategy2.on_tick(p)
    
    # 测试3: 分层止盈模式
    print("\n" + "=" * 60)
    print("【测试3】分层止盈模式")
    print("-" * 40)
    
    strategy3 = DualMartingaleStrategy(
        base_size=1,
        grid_spacing_type=GridSpacingType.FIXED,
        grid_step=5,
        multiplier=1.6,
        max_levels=6,
        take_profit_mode=TakeProfitMode.TIERED,
        target_profit=10,
        tiered_profit_ratios={1: 0.3, 2: 0.5, 3: 0.7, 4: 1.0},
        max_floating_loss=100,
        baseline_mode=BaselinePriceMode.DYNAMIC
    )
    
    prices3 = [100, 106, 112, 118, 115, 120, 125]
    for p in prices3:
        print(f"\n当前市价: {p}")
        strategy3.on_tick(p)
    
    # 测试4: 仓位限制测试
    print("\n" + "=" * 60)
    print("【测试4】仓位限制测试")
    print("-" * 40)
    
    strategy4 = DualMartingaleStrategy(
        base_size=0.01,
        grid_spacing_type=GridSpacingType.FIXED,
        grid_step=100,
        multiplier=2.0,
        max_levels=10,
        max_position_value=500,  # 最大仓位 500 USDT
        total_capital=10000,
        take_profit_mode=TakeProfitMode.UNIFIED,
        target_profit=50,
        max_floating_loss=200
    )
    
    # 模拟 BTC 价格
    prices4 = [50000, 50100, 50200, 50300, 50400, 50500, 50600, 50700]
    for p in prices4:
        print(f"\n当前市价: {p}")
        strategy4.on_tick(p)
    
    print("\n" + "=" * 60)
    print("所有测试完成!")
    print("=" * 60)
