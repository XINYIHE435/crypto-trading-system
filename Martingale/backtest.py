"""
Martingale 策略回测脚本 - 完整版
支持所有策略功能的回测测试
"""
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from main import (
    DualMartingaleStrategy, 
    GridSpacingType, 
    TakeProfitMode, 
    BaselinePriceMode
)
import os
import json

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti', 'PingFang SC']
plt.rcParams['axes.unicode_minus'] = False


class BacktestEngine:
    """回测引擎 - 支持完整策略功能"""
    
    def __init__(self, strategy_params: dict, data_path: str):
        """
        初始化回测引擎
        
        参数：
        - strategy_params: 策略参数字典
        - data_path: 数据文件路径
        """
        self.strategy_params = strategy_params
        self.data_path = data_path
        self.strategy = None
        self.trades = []
        self.equity_curve = []
        self.close_events = []  # 平仓事件记录
        self.df = None
        
    def load_data(self) -> pd.DataFrame:
        """加载历史数据"""
        print(f"正在加载数据: {self.data_path}")
        df = pd.read_csv(self.data_path)

        # 数据预处理
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)

        print(f"数据加载完成:")
        print(f"  时间范围: {df['timestamp'].iloc[0]} 至 {df['timestamp'].iloc[-1]}")
        print(f"  数据点数: {len(df)}")
        print(f"  价格区间: {df['close'].min():.2f} - {df['close'].max():.2f}")
        print(f"  平均价格: {df['close'].mean():.2f}")

        self.df = df
        return df

    def run(self, use_ohlc: bool = True) -> tuple:
        """
        执行回测
        
        参数：
        - use_ohlc: 是否使用OHLC数据（用于ATR计算）
        """
        df = self.load_data()
        
        # 初始化策略
        self.strategy = DualMartingaleStrategy(**self.strategy_params)
        
        print(f"\n{'='*60}")
        print("开始回测...")
        print(f"{'='*60}")
        print(f"策略配置:")
        print(f"  网格类型: {self.strategy.grid_spacing_type.value}")
        print(f"  止盈模式: {self.strategy.take_profit_mode.value}")
        print(f"  基准模式: {self.strategy.baseline_mode.value}")
        print(f"{'='*60}\n")

        for i, row in df.iterrows():
            timestamp = row['timestamp']
            close_price = row['close']
            
            # 准备OHLC数据（用于ATR计算）
            price_data = None
            if use_ohlc and 'open' in df.columns:
                price_data = {
                    'open': row.get('open', close_price),
                    'high': row.get('high', close_price),
                    'low': row.get('low', close_price),
                    'close': close_price
                }
            
            # 记录执行前状态
            prev_long_count = self.strategy.long_state.current_level
            prev_short_count = self.strategy.short_state.current_level
            prev_realized_pnl = self.strategy.total_realized_pnl
            
            # 执行策略逻辑
            self.strategy.on_tick(close_price, price_data)
            
            # 记录当前状态
            status = self.strategy.get_status(close_price)
            self.equity_curve.append({
                'timestamp': timestamp,
                'price': close_price,
                'pnl': status['total_pnl'],
                'realized_pnl': status['total_realized_pnl'],
                'long_positions': status['long']['level'],
                'short_positions': status['short']['level'],
                'long_size': status['long']['total_size'],
                'short_size': status['short']['total_size'],
                'long_avg_price': status['long']['average_price'],
                'short_avg_price': status['short']['average_price'],
                'baseline_price': status['baseline_price'],
                'grid_spacing': status['grid_spacing'],
                'current_atr': status['current_atr']
            })
            
            # 记录新开仓
            if self.strategy.long_state.current_level > prev_long_count:
                new_order = self.strategy.long_state.positions[-1]
                self.trades.append({
                    'timestamp': timestamp,
                    'type': 'LONG',
                    'action': 'OPEN',
                    'price': new_order.price,
                    'size': new_order.size,
                    'level': new_order.level
                })
                
            if self.strategy.short_state.current_level > prev_short_count:
                new_order = self.strategy.short_state.positions[-1]
                self.trades.append({
                    'timestamp': timestamp,
                    'type': 'SHORT',
                    'action': 'OPEN',
                    'price': new_order.price,
                    'size': new_order.size,
                    'level': new_order.level
                })
            
            # 记录平仓事件
            if self.strategy.total_realized_pnl > prev_realized_pnl:
                realized_diff = self.strategy.total_realized_pnl - prev_realized_pnl
                self.close_events.append({
                    'timestamp': timestamp,
                    'price': close_price,
                    'realized_pnl': realized_diff,
                    'total_realized_pnl': self.strategy.total_realized_pnl
                })

        # 最终统计
        final_status = self.strategy.get_status(df['close'].iloc[-1])
        
        print(f"\n{'='*60}")
        print("回测完成!")
        print(f"{'='*60}")
        print(f"最终价格: {df['close'].iloc[-1]:.2f}")
        print(f"浮动盈亏: {final_status['total_pnl']:.2f}")
        print(f"已实现盈亏: {final_status['total_realized_pnl']:.2f}")
        print(f"总盈亏: {final_status['total_pnl'] + final_status['total_realized_pnl']:.2f}")
        print(f"总交易次数: {final_status['trade_count']}")
        print(f"平仓次数: {len(self.close_events)}")

        return self.equity_curve, self.trades

    def plot_results(self, save_path: str = None):
        """绘制回测结果图表"""
        if not self.equity_curve:
            print("没有可绘制的数据")
            return

        df = pd.DataFrame(self.equity_curve)

        fig, axes = plt.subplots(4, 1, figsize=(16, 14))

        # 1. 价格曲线 + 基准价 + 交易点
        ax1 = axes[0]
        ax1.plot(df['timestamp'], df['price'], label='价格', linewidth=1, color='blue', alpha=0.7)
        ax1.plot(df['timestamp'], df['baseline_price'], label='基准价', linewidth=1, 
                color='red', linestyle='--', alpha=0.5)
        
        # 标记开仓点
        trades_df = pd.DataFrame(self.trades)
        if not trades_df.empty:
            long_trades = trades_df[(trades_df['type'] == 'LONG') & (trades_df['action'] == 'OPEN')]
            short_trades = trades_df[(trades_df['type'] == 'SHORT') & (trades_df['action'] == 'OPEN')]
            
            if not long_trades.empty:
                ax1.scatter(long_trades['timestamp'], long_trades['price'], 
                           marker='^', color='green', s=50, label=f'多单开仓 ({len(long_trades)})',
                           alpha=0.7, zorder=5)
            if not short_trades.empty:
                ax1.scatter(short_trades['timestamp'], short_trades['price'], 
                           marker='v', color='red', s=50, label=f'空单开仓 ({len(short_trades)})',
                           alpha=0.7, zorder=5)
        
        # 标记平仓点
        if self.close_events:
            close_df = pd.DataFrame(self.close_events)
            ax1.scatter(close_df['timestamp'], close_df['price'], 
                       marker='x', color='purple', s=100, label=f'平仓 ({len(close_df)})',
                       linewidths=2, zorder=6)
        
        ax1.set_ylabel('价格 (USDT)', fontsize=10)
        ax1.set_title(f'价格走势与交易点位 | 网格类型: {self.strategy.grid_spacing_type.value}', 
                     fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='best', fontsize=8)

        # 2. 盈亏曲线
        ax2 = axes[1]
        ax2.plot(df['timestamp'], df['pnl'], label='浮动盈亏', linewidth=1.5, color='blue')
        ax2.plot(df['timestamp'], df['realized_pnl'], label='已实现盈亏', 
                linewidth=1.5, color='green', linestyle='--')
        total_pnl = df['pnl'] + df['realized_pnl']
        ax2.plot(df['timestamp'], total_pnl, label='总盈亏', linewidth=1, color='purple', alpha=0.7)
        
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax2.axhline(y=self.strategy.target_profit, color='green', linestyle='--', 
                   linewidth=1, label=f'止盈线: {self.strategy.target_profit}', alpha=0.7)
        ax2.axhline(y=-self.strategy.max_floating_loss, color='red', linestyle='--', 
                   linewidth=1, label=f'止损线: {-self.strategy.max_floating_loss}', alpha=0.7)
        
        # 填充区域
        ax2.fill_between(df['timestamp'], df['pnl'], 0,
                        where=(df['pnl'] >= 0), color='green', alpha=0.1)
        ax2.fill_between(df['timestamp'], df['pnl'], 0,
                        where=(df['pnl'] < 0), color='red', alpha=0.1)
        
        ax2.set_ylabel('盈亏 (USDT)', fontsize=10)
        ax2.set_title(f'策略盈亏曲线 | 止盈模式: {self.strategy.take_profit_mode.value}', 
                     fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc='best', fontsize=8)

        # 3. 持仓层数和仓位量
        ax3 = axes[2]
        ax3.plot(df['timestamp'], df['long_positions'], label='多单层数', 
                linewidth=1.5, color='green')
        ax3.plot(df['timestamp'], df['short_positions'], label='空单层数', 
                linewidth=1.5, color='red')
        
        ax3_twin = ax3.twinx()
        ax3_twin.plot(df['timestamp'], df['long_size'], label='多单仓位', 
                     linewidth=1, color='green', linestyle='--', alpha=0.5)
        ax3_twin.plot(df['timestamp'], df['short_size'], label='空单仓位', 
                     linewidth=1, color='red', linestyle='--', alpha=0.5)
        ax3_twin.set_ylabel('仓位量', fontsize=10, color='gray')
        
        ax3.set_ylabel('持仓层数', fontsize=10)
        ax3.set_title(f'持仓变化 | 基准模式: {self.strategy.baseline_mode.value}', 
                     fontsize=12, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        ax3.legend(loc='upper left', fontsize=8)
        ax3_twin.legend(loc='upper right', fontsize=8)

        # 4. 网格间距（ATR模式下会动态变化）
        ax4 = axes[3]
        ax4.plot(df['timestamp'], df['grid_spacing'], label='网格间距', 
                linewidth=1.5, color='orange')
        
        if self.strategy.grid_spacing_type == GridSpacingType.ATR:
            ax4.plot(df['timestamp'], df['current_atr'], label='ATR', 
                    linewidth=1, color='blue', linestyle='--', alpha=0.7)
        
        ax4.set_ylabel('间距 (USDT)', fontsize=10)
        ax4.set_xlabel('时间', fontsize=10)
        ax4.set_title('网格间距变化', fontsize=12, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        ax4.legend(loc='best', fontsize=8)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"\n图表已保存至: {save_path}")

        plt.show()

    def print_trade_log(self, limit: int = 30):
        """打印交易日志"""
        if not self.trades:
            print("没有交易记录")
            return

        print(f"\n{'='*90}")
        print(f"交易日志 (显示最近 {min(limit, len(self.trades))} 笔)")
        print(f"{'='*90}")
        print(f"{'时间':<20} {'类型':<8} {'操作':<8} {'价格':<12} {'手数':<12} {'层级':<6}")
        print(f"{'-'*90}")

        for trade in self.trades[-limit:]:
            timestamp = pd.Timestamp(trade['timestamp']).strftime('%Y-%m-%d %H:%M')
            print(f"{timestamp:<20} {trade['type']:<8} {trade['action']:<8} "
                  f"{trade['price']:<12.2f} {trade['size']:<12.6f} {trade['level']:<6}")
        
        # 打印平仓事件
        if self.close_events:
            print(f"\n{'='*90}")
            print(f"平仓事件 (共 {len(self.close_events)} 次)")
            print(f"{'='*90}")
            print(f"{'时间':<20} {'价格':<12} {'本次盈亏':<12} {'累计盈亏':<12}")
            print(f"{'-'*90}")
            
            for event in self.close_events[-limit:]:
                timestamp = pd.Timestamp(event['timestamp']).strftime('%Y-%m-%d %H:%M')
                print(f"{timestamp:<20} {event['price']:<12.2f} "
                      f"{event['realized_pnl']:<12.2f} {event['total_realized_pnl']:<12.2f}")

    def get_summary(self) -> dict:
        """获取回测摘要"""
        if not self.equity_curve:
            return {}
        
        df = pd.DataFrame(self.equity_curve)
        trades_df = pd.DataFrame(self.trades) if self.trades else pd.DataFrame()
        
        final_pnl = df['pnl'].iloc[-1]
        final_realized = df['realized_pnl'].iloc[-1]
        
        summary = {
            'strategy_config': {
                'grid_type': self.strategy.grid_spacing_type.value,
                'take_profit_mode': self.strategy.take_profit_mode.value,
                'baseline_mode': self.strategy.baseline_mode.value,
                'base_size': self.strategy.base_size,
                'multiplier': self.strategy.multiplier,
                'max_levels': self.strategy.max_levels,
                'target_profit': self.strategy.target_profit,
                'max_floating_loss': self.strategy.max_floating_loss
            },
            'performance': {
                'floating_pnl': float(final_pnl),
                'realized_pnl': float(final_realized),
                'total_pnl': float(final_pnl + final_realized),
                'max_pnl': float(df['pnl'].max()),
                'min_pnl': float(df['pnl'].min()),
                'max_drawdown': float(df['pnl'].min())
            },
            'trades': {
                'total_trades': len(trades_df) if not trades_df.empty else 0,
                'long_trades': len(trades_df[trades_df['type'] == 'LONG']) if not trades_df.empty else 0,
                'short_trades': len(trades_df[trades_df['type'] == 'SHORT']) if not trades_df.empty else 0,
                'close_events': len(self.close_events)
            },
            'positions': {
                'max_long_level': int(df['long_positions'].max()),
                'max_short_level': int(df['short_positions'].max()),
                'max_long_size': float(df['long_size'].max()),
                'max_short_size': float(df['short_size'].max())
            },
            'time_range': {
                'start': str(df['timestamp'].iloc[0]),
                'end': str(df['timestamp'].iloc[-1]),
                'data_points': len(df)
            }
        }
        
        return summary

    def save_results(self, output_dir: str):
        """保存所有回测结果"""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存图表
        plot_path = f"{output_dir}/martingale_backtest_{timestamp}.png"
        self.plot_results(save_path=plot_path)
        
        # 保存交易记录
        if self.trades:
            trades_df = pd.DataFrame(self.trades)
            csv_path = f"{output_dir}/martingale_trades_{timestamp}.csv"
            trades_df.to_csv(csv_path, index=False)
            print(f"交易记录已保存至: {csv_path}")
        
        # 保存盈亏曲线
        if self.equity_curve:
            equity_df = pd.DataFrame(self.equity_curve)
            equity_path = f"{output_dir}/martingale_equity_{timestamp}.csv"
            equity_df.to_csv(equity_path, index=False)
            print(f"盈亏曲线已保存至: {equity_path}")
        
        # 保存摘要
        summary = self.get_summary()
        summary_path = f"{output_dir}/martingale_summary_{timestamp}.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"回测摘要已保存至: {summary_path}")
        
        return timestamp


def run_backtest_comparison():
    """运行多种配置的回测对比"""
    data_file = "../data/raw/klines/binance_BTCUSDT_30m.csv"
    
    if not os.path.exists(data_file):
        print(f"错误: 数据文件不存在: {data_file}")
        return
    
    # 定义多种策略配置进行对比
    configs = [
        {
            'name': '固定网格 + 统一止盈',
            'params': {
                'base_size': 0.001,
                'grid_spacing_type': GridSpacingType.FIXED,
                'grid_step': 200,
                'multiplier': 1.5,
                'max_levels': 8,
                'martingale_start_level': 2,
                'take_profit_mode': TakeProfitMode.UNIFIED,
                'target_profit': 10,
                'max_floating_loss': 100,
                'baseline_mode': BaselinePriceMode.DYNAMIC,
                'verbose': False
            }
        },
        {
            'name': '百分比网格 + 逐笔止盈',
            'params': {
                'base_size': 0.001,
                'grid_spacing_type': GridSpacingType.PERCENTAGE,
                'grid_percentage': 0.5,
                'multiplier': 1.5,
                'max_levels': 8,
                'martingale_start_level': 2,
                'take_profit_mode': TakeProfitMode.PER_TRADE,
                'per_trade_profit': 5,
                'max_floating_loss': 100,
                'baseline_mode': BaselinePriceMode.DYNAMIC,
                'verbose': False
            }
        },
        {
            'name': '固定网格 + 分层止盈',
            'params': {
                'base_size': 0.001,
                'grid_spacing_type': GridSpacingType.FIXED,
                'grid_step': 200,
                'multiplier': 1.5,
                'max_levels': 8,
                'martingale_start_level': 2,
                'take_profit_mode': TakeProfitMode.TIERED,
                'target_profit': 10,
                'tiered_profit_ratios': {1: 0.3, 2: 0.5, 3: 0.7, 4: 1.0},
                'max_floating_loss': 100,
                'baseline_mode': BaselinePriceMode.FIXED,
                'verbose': False
            }
        }
    ]
    
    results = []
    
    for config in configs:
        print(f"\n{'='*60}")
        print(f"运行配置: {config['name']}")
        print(f"{'='*60}")
        
        engine = BacktestEngine(config['params'], data_file)
        engine.run()
        
        summary = engine.get_summary()
        summary['config_name'] = config['name']
        results.append(summary)
        
        print(f"\n结果摘要:")
        print(f"  总盈亏: {summary['performance']['total_pnl']:.2f}")
        print(f"  交易次数: {summary['trades']['total_trades']}")
        print(f"  平仓次数: {summary['trades']['close_events']}")
    
    # 打印对比结果
    print(f"\n{'='*60}")
    print("策略配置对比")
    print(f"{'='*60}")
    print(f"{'配置名称':<25} {'总盈亏':<12} {'交易次数':<10} {'平仓次数':<10}")
    print(f"{'-'*60}")
    
    for r in results:
        print(f"{r['config_name']:<25} {r['performance']['total_pnl']:<12.2f} "
              f"{r['trades']['total_trades']:<10} {r['trades']['close_events']:<10}")


def main():
    """主函数"""
    data_file = "../data/raw/klines/binance_BTCUSDT_30m.csv"

    if not os.path.exists(data_file):
        print(f"错误: 数据文件不存在: {data_file}")
        return

    # 策略参数
    strategy_params = {
        # 基础参数
        'base_size': 0.001,
        'multiplier': 1.5,
        'max_levels': 8,
        'martingale_start_level': 2,
        
        # 网格间距 - 可选: FIXED, PERCENTAGE, ATR
        'grid_spacing_type': GridSpacingType.FIXED,
        'grid_step': 200,
        # 'grid_spacing_type': GridSpacingType.PERCENTAGE,
        # 'grid_percentage': 0.5,
        
        # 仓位限制
        'max_position_value': 1000,  # 最大1000 USDT
        'total_capital': 10000,
        
        # 止盈模式 - 可选: UNIFIED, PER_TRADE, TIERED
        'take_profit_mode': TakeProfitMode.UNIFIED,
        'target_profit': 10,
        'per_trade_profit': 5,
        'hedge_profit_target': 3,
        
        # 止损
        'max_floating_loss': 100,
        
        # 基准价模式 - 可选: DYNAMIC, FIXED
        'baseline_mode': BaselinePriceMode.DYNAMIC,
        
        # 调试
        'verbose': False
    }

    print("=" * 60)
    print("Martingale 双向马丁策略回测 - 完整版")
    print("=" * 60)
    print("\n策略参数:")
    for key, value in strategy_params.items():
        if hasattr(value, 'value'):
            print(f"  {key}: {value.value}")
        else:
            print(f"  {key}: {value}")
    print("=" * 60)

    # 创建回测引擎
    engine = BacktestEngine(strategy_params, data_file)

    # 运行回测
    engine.run()

    # 打印交易日志
    engine.print_trade_log(limit=30)

    # 保存结果
    results_dir = "../data/backtest_results"
    engine.save_results(results_dir)


if __name__ == "__main__":
    # 运行单次回测
    main()
    
    # 或者运行多配置对比
    # run_backtest_comparison()
