import time

class DualMartingaleStrategy:
    def __init__(self, 
                 base_size=0.01, 
                 grid_step=10, 
                 multiplier=1.6, 
                 max_levels=10, 
                 martingale_start_level=1, 
                 target_profit=5.0,
                 max_floating_loss=100.0):
        """
        初始化策略参数 
        :param base_size: 初始手数 
        :param grid_step: 网格间距 (假设为绝对价格距离) 
        :param multiplier: 马丁倍数 
        :param max_levels: 最大层数限制 [cite: 9]
        :param martingale_start_level: 第几层开始加倍 (普通层 vs 马丁层) 
        :param target_profit: 目标止盈金额 (统一回本止盈) [cite: 12]
        :param max_floating_loss: 最大浮亏保护线 
        """
        self.base_size = base_size
        self.grid_step = grid_step
        self.multiplier = multiplier
        self.max_levels = max_levels
        self.martingale_start_level = martingale_start_level
        self.target_profit = target_profit
        self.max_floating_loss = max_floating_loss

        # 状态变量
        self.baseline_price = None  # 基准价格 
        self.positions = {'long': [], 'short': []} # 存储买单和卖单列表
        self.current_levels = {'long': 0, 'short': 0} # 当前层级计数 
        self.total_pnl = 0.0

    def start(self, current_price):
        """策略启动 [cite: 2]"""
        self.baseline_price = current_price
        print(f"策略启动，基准价格设定为: {self.baseline_price}")

    def get_lot_size(self, direction):
        """
        计算下单手数 [cite: 29-32]
        普通层(1~N): base_size
        马丁层(N+1): 上层手数 * multiplier
        """
        level = self.current_levels[direction]
        
        # 如果是第一单，或者还在普通层范围内
        if level < self.martingale_start_level:
            return self.base_size
        else:
            # 获取上一单的手数进行倍投
            last_order_size = self.positions[direction][-1]['size']
            return round(last_order_size * self.multiplier, 4)

    def open_order(self, direction, price):
        """开仓逻辑 """
        if self.current_levels[direction] >= self.max_levels:
            print(f"{direction} 方向已达最大层数，停止加仓。")
            return

        size = self.get_lot_size(direction)
        
        # 模拟下单记录 
        order = {
            'price': price,
            'size': size,
            'direction': direction,
            'time': time.time()
        }
        self.positions[direction].append(order)
        self.current_levels[direction] += 1  # 层级+1 
        
        print(f"开仓 {direction.upper()} | 价格: {price} | 手数: {size} | 当前层级: {self.current_levels[direction]}")

    def calculate_pnl(self, current_price):
        """计算总浮动盈亏"""
        pnl = 0.0
        # 计算多单盈亏
        for order in self.positions['long']:
            pnl += (current_price - order['price']) * order['size']
        # 计算空单盈亏
        for order in self.positions['short']:
            pnl += (order['price'] - current_price) * order['size']
        return pnl

    def close_all(self, current_price, reason=""):
        """平仓并重置 [cite: 40, 45, 46]"""
        realized_pnl = self.calculate_pnl(current_price)
        print(f"触发平仓: {reason} | 最终盈亏: {realized_pnl:.2f}")
        
        # 重置数据
        self.positions = {'long': [], 'short': []}
        self.current_levels = {'long': 0, 'short': 0}
        
        # 重设基准价 (动态基准模式) 
        self.baseline_price = current_price 
        print(f"系统重置，新基准价: {self.baseline_price}")
        print("-" * 30)

    def on_tick(self, current_price):
        """
        主循环: 模拟接收实时价格 
        """
        if self.baseline_price is None:
            self.start(current_price)
            return

        # 1. 计算盈亏与风控检查 [cite: 38, 44]
        current_pnl = self.calculate_pnl(current_price)
        
        # 检查止损 (保护机制)
        if current_pnl <= -self.max_floating_loss:
            self.close_all(current_price, reason="触发最大浮亏保护 ")
            return

        # 检查止盈 (统一回本止盈) 
        if current_pnl >= self.target_profit and (self.current_levels['long'] > 0 or self.current_levels['short'] > 0):
            self.close_all(current_price, reason="触发总目标止盈 [cite: 41]")
            return

        # 2. 检查网格触发条件 [cite: 18-27]
        # 计算当前价格相对于基准价的距离层级
        price_diff = current_price - self.baseline_price
        
        # 上涨区间处理 (高于基准+间距) [cite: 21]
        if price_diff > 0:
            # 计算理论应该所在的网格线索引 (向下取整)
            grid_index = int(price_diff / self.grid_step)
            # 如果当前层级小于网格索引，说明价格突破了新的网格线，需要开多单 [cite: 23, 26, 28]
            # 注意：这里假设是一个顺势/或逆势补单逻辑，严格按照流程图“到达买单线 -> 开买单”
            if grid_index > self.current_levels['long']:
                self.open_order('long', current_price)

        # 下跌区间处理 (低于基准-间距) [cite: 22]
        elif price_diff < 0:
            grid_index = int(abs(price_diff) / self.grid_step)
            # 检查下方网格线 
            if grid_index > self.current_levels['short']:
                self.open_order('short', current_price)

# --- 模拟运行测试 ---
if __name__ == "__main__":
    # 初始化策略
    strategy = DualMartingaleStrategy(
        base_size=1, 
        grid_step=10,    # 每10块钱波动开一单
        multiplier=2.0,  # 倍投
        target_profit=20 # 赚20块就跑
    )

    # 模拟一段价格走势: 震荡后单边突破
    # 假设初始价 100
    prices = [
        100, 105, 112, # 触发多单 (100+10)
        108, 122,      # 触发多单 (100+20)
        115, 95,       # 价格回调
        135,           # 价格大涨，触发止盈
        136
    ]

    print("--- 开始模拟回测 ---")
    for p in prices:
        print(f"\n当前市价: {p}")
        strategy.on_tick(p)