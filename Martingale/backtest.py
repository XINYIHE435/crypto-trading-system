"""
Martingale 策略回测脚本
使用真实历史数据测试策略表现
"""
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from main import DualMartingaleStrategy
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti', 'PingFang SC']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

class BacktestEngine:
    def __init__(self, strategy_params, data_path):
        """
        初始化回测引擎
        :param strategy_params: 策略参数字典
        :param data_path: 数据文件路径
        """
        self.strategy = DualMartingaleStrategy(**strategy_params)
        self.data_path = data_path
        self.trades = []
        self.equity_curve = []
        self.price_history = []

    def load_data(self):
        """加载历史数据"""
        print(f"正在加载数据: {self.data_path}")
        df = pd.read_csv(self.data_path)

        # 数据预处理
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        print(f"数据加载完成:")
        print(f"  时间范围: {df['timestamp'].iloc[0]} 至 {df['timestamp'].iloc[-1]}")
        print(f"  数据点数: {len(df)}")
        print(f"  价格区间: {df['close'].min():.2f} - {df['close'].max():.2f}")
        print(f"  平均价格: {df['close'].mean():.2f}")

        return df

    def run(self, use_close=True):
        """
        执行回测
        :param use_close: True使用收盘价, False使用收盘价作为代表价格
        """
        df = self.load_data()
        prices = df['close'].values if use_close else df[['open', 'high', 'low', 'close']].values.mean(axis=1)
        timestamps = df['timestamp'].values

        print(f"\n{'='*50}")
        print("开始回测...")
        print(f"{'='*50}\n")

        for i, (price, timestamp) in enumerate(zip(prices, timestamps)):
            # 记录状态
            current_pnl = self.strategy.calculate_pnl(price)
            self.equity_curve.append({
                'timestamp': timestamp,
                'price': price,
                'pnl': current_pnl,
                'long_positions': len(self.strategy.positions['long']),
                'short_positions': len(self.strategy.positions['short'])
            })

            # 执行策略逻辑
            prev_long_count = len(self.strategy.positions['long'])
            prev_short_count = len(self.strategy.positions['short'])

            self.strategy.on_tick(price)

            # 记录交易
            if len(self.strategy.positions['long']) > prev_long_count:
                new_order = self.strategy.positions['long'][-1]
                self.trades.append({
                    'timestamp': timestamp,
                    'type': 'LONG',
                    'price': new_order['price'],
                    'size': new_order['size'],
                    'level': self.strategy.current_levels['long']
                })

            if len(self.strategy.positions['short']) > prev_short_count:
                new_order = self.strategy.positions['short'][-1]
                self.trades.append({
                    'timestamp': timestamp,
                    'type': 'SHORT',
                    'price': new_order['price'],
                    'size': new_order['size'],
                    'level': self.strategy.current_levels['short']
                })

        # 最终统计
        final_price = prices[-1]
        final_pnl = self.strategy.calculate_pnl(final_price)

        print(f"\n{'='*50}")
        print("回测完成!")
        print(f"{'='*50}")
        print(f"最终价格: {final_price:.2f}")
        print(f"最终浮动盈亏: {final_pnl:.2f}")
        print(f"总交易次数: {len(self.trades)}")
        print(f"多单次数: {sum(1 for t in self.trades if t['type'] == 'LONG')}")
        print(f"空单次数: {sum(1 for t in self.trades if t['type'] == 'SHORT')}")

        return self.equity_curve, self.trades

    def plot_results(self, save_path=None):
        """绘制回测结果图表"""
        if not self.equity_curve:
            print("没有可绘制的数据")
            return

        df = pd.DataFrame(self.equity_curve)

        fig, axes = plt.subplots(3, 1, figsize=(15, 12))

        # 1. 价格曲线
        axes[0].plot(df['timestamp'], df['price'], label='价格', linewidth=1)
        axes[0].set_ylabel('价格 (USDT)', fontsize=10)
        axes[0].set_title('BTC/USDT 价格走势', fontsize=12, fontweight='bold')
        axes[0].grid(True, alpha=0.3)
        axes[0].legend()

        # 标记基准价
        if self.strategy.baseline_price:
            axes[0].axhline(y=self.strategy.baseline_price, color='red',
                           linestyle='--', label=f'基准价: {self.strategy.baseline_price:.2f}')
            axes[0].legend()

        # 2. 盈亏曲线
        axes[1].plot(df['timestamp'], df['pnl'], label='浮动盈亏', linewidth=1, color='green')
        axes[1].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        axes[1].axhline(y=self.strategy.target_profit, color='green',
                       linestyle='--', label=f'止盈线: {self.strategy.target_profit}')
        axes[1].axhline(y=-self.strategy.max_floating_loss, color='red',
                       linestyle='--', label=f'止损线: {-self.strategy.max_floating_loss}')
        axes[1].set_ylabel('盈亏 (USDT)', fontsize=10)
        axes[1].set_title('策略浮动盈亏', fontsize=12, fontweight='bold')
        axes[1].grid(True, alpha=0.3)
        axes[1].legend()

        # 3. 持仓数量
        axes[2].plot(df['timestamp'], df['long_positions'], label='多单数量', linewidth=1, color='blue')
        axes[2].plot(df['timestamp'], df['short_positions'], label='空单数量', linewidth=1, color='orange')
        axes[2].set_ylabel('持仓数量', fontsize=10)
        axes[2].set_xlabel('时间', fontsize=10)
        axes[2].set_title('持仓变化', fontsize=12, fontweight='bold')
        axes[2].grid(True, alpha=0.3)
        axes[2].legend()

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"\n图表已保存至: {save_path}")
        else:
            plt.savefig('backtest_results.png', dpi=150, bbox_inches='tight')
            print(f"\n图表已保存至: backtest_results.png")

        plt.show()

    def print_trade_log(self, limit=20):
        """打印交易日志"""
        if not self.trades:
            print("没有交易记录")
            return

        print(f"\n{'='*80}")
        print(f"交易日志 (显示最近 {min(limit, len(self.trades))} 笔)")
        print(f"{'='*80}")
        print(f"{'时间':<20} {'类型':<8} {'价格':<12} {'手数':<10} {'层级':<6}")
        print(f"{'-'*80}")

        for trade in self.trades[-limit:]:
            timestamp = pd.Timestamp(trade['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"{timestamp:<20} {trade['type']:<8} {trade['price']:<12.2f} "
                  f"{trade['size']:<10.4f} {trade['level']:<6}")


def main():
    """主函数"""
    # 数据文件路径
    data_file = "../data/raw/klines/binance_BTCUSDT_30m.csv"

    # 检查文件是否存在
    if not os.path.exists(data_file):
        print(f"错误: 数据文件不存在: {data_file}")
        return

    # 策略参数 - 可以根据需要调整
    strategy_params = {
        'base_size': 0.001,          # 初始手数 (BTC)
        'grid_step': 200,            # 网格间距 (USDT) - 根据BTC波动性调整
        'multiplier': 1.5,           # 马丁倍数
        'max_levels': 8,             # 最大层数
        'martingale_start_level': 2, # 从第3层开始倍投
        'target_profit': 10,         # 目标止盈 (USDT)
        'max_floating_loss': 100     # 最大浮亏止损 (USDT)
    }

    print("Martingale 策略回测")
    print("="*50)
    print("策略参数:")
    for key, value in strategy_params.items():
        print(f"  {key}: {value}")
    print("="*50)

    # 创建回测引擎
    engine = BacktestEngine(strategy_params, data_file)

    # 运行回测
    equity_curve, trades = engine.run()

    # 打印交易日志
    engine.print_trade_log(limit=30)

    # 绘制结果
    results_dir = "../data/backtest_results"
    os.makedirs(results_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plot_path = f"{results_dir}/martingale_backtest_{timestamp}.png"
    engine.plot_results(save_path=plot_path)

    # 保存交易记录到CSV
    if trades:
        trades_df = pd.DataFrame(trades)
        csv_path = f"{results_dir}/martingale_trades_{timestamp}.csv"
        trades_df.to_csv(csv_path, index=False)
        print(f"\n交易记录已保存至: {csv_path}")

    # 保存盈亏曲线到CSV
    if equity_curve:
        equity_df = pd.DataFrame(equity_curve)
        equity_path = f"{results_dir}/martingale_equity_{timestamp}.csv"
        equity_df.to_csv(equity_path, index=False)
        print(f"盈亏曲线已保存至: {equity_path}")


if __name__ == "__main__":
    main()
