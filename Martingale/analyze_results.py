"""
Martingale 回测结果分析工具
"""
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti', 'PingFang SC']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

def analyze_backtest_results(trades_csv, equity_csv):
    """分析回测结果"""

    # 读取数据
    trades_df = pd.read_csv(trades_csv)
    equity_df = pd.read_csv(equity_csv)

    trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
    equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])

    print("="*80)
    print("Martingale 策略回测分析报告")
    print("="*80)

    # 基本统计
    total_trades = len(trades_df)
    long_trades = len(trades_df[trades_df['type'] == 'LONG'])
    short_trades = len(trades_df[trades_df['type'] == 'SHORT'])

    print(f"\n【交易统计】")
    print(f"  总交易次数: {total_trades}")
    print(f"  多单次数: {long_trades} ({long_trades/total_trades*100:.1f}%)")
    print(f"  空单次数: {short_trades} ({short_trades/total_trades*100:.1f}%)")

    # 层级统计
    level_stats = trades_df.groupby('level').agg({
        'type': 'count',
        'size': ['mean', 'sum']
    }).round(4)
    level_stats.columns = ['交易次数', '平均手数', '总手数']

    print(f"\n【层级统计】")
    print(level_stats)

    # 盈亏分析
    final_pnl = equity_df['pnl'].iloc[-1]
    max_pnl = equity_df['pnl'].max()
    min_pnl = equity_df['pnl'].min()

    print(f"\n【盈亏分析】")
    print(f"  最终盈亏: {final_pnl:.2f} USDT")
    print(f"  最大盈利: {max_pnl:.2f} USDT")
    print(f"  最大亏损: {min_pnl:.2f} USDT")
    print(f"  盈亏比: {abs(max_pnl/min_pnl) if min_pnl != 0 else 0:.2f}")

    # 识别交易周期 (从开仓到平仓)
    # 通过寻找连续的策略重置来识别完整交易
    equity_df['pnl_change'] = equity_df['pnl'].diff()
    resets = equity_df[equity_df['pnl_change'] > 50].index  # 假设重置时盈亏会大幅变化

    print(f"\n【交易周期】")
    print(f"  完成交易周期: {len(resets)}")

    if len(resets) > 0:
        # 计算每个周期的盈亏
        period_pnls = []
        prev_idx = 0
        for reset_idx in resets:
            if reset_idx > 0:
                period_pnl = equity_df.iloc[reset_idx]['pnl'] - equity_df.iloc[prev_idx]['pnl']
                period_pnls.append(period_pnl)
                prev_idx = reset_idx

        if period_pnls:
            print(f"  平均周期盈亏: {sum(period_pnls)/len(period_pnls):.2f} USDT")
            print(f"  最佳周期: {max(period_pnls):.2f} USDT")
            print(f"  最差周期: {min(period_pnls):.2f} USDT")

    # 持仓分析
    max_long_positions = equity_df['long_positions'].max()
    max_short_positions = equity_df['short_positions'].max()

    print(f"\n【持仓分析】")
    print(f"  最大多单持仓: {max_long_positions} 层")
    print(f"  最大空单持仓: {max_short_positions} 层")

    # 时间跨度
    time_span = equity_df['timestamp'].iloc[-1] - equity_df['timestamp'].iloc[0]
    print(f"\n【时间跨度】")
    print(f"  回测时长: {time_span.days} 天")
    print(f"  数据点数: {len(equity_df)}")

    # 绘制详细图表
    fig, axes = plt.subplots(4, 1, figsize=(16, 14))

    # 1. 价格与交易点位
    ax1 = axes[0]
    ax1.plot(equity_df['timestamp'], equity_df['price'],
             label='价格', linewidth=1, color='gray', alpha=0.7)

    # 标记多单
    long_trades_data = trades_df[trades_df['type'] == 'LONG']
    ax1.scatter(long_trades_data['timestamp'], long_trades_data['price'],
               marker='^', color='green', s=50, label=f'多单 ({len(long_trades_data)})',
               alpha=0.6, zorder=5)

    # 标记空单
    short_trades_data = trades_df[trades_df['type'] == 'SHORT']
    ax1.scatter(short_trades_data['timestamp'], short_trades_data['price'],
               marker='v', color='red', s=50, label=f'空单 ({len(short_trades_data)})',
               alpha=0.6, zorder=5)

    ax1.set_ylabel('价格 (USDT)', fontsize=11)
    ax1.set_title('价格走势与交易点位', fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='best')

    # 2. 盈亏曲线
    ax2 = axes[1]
    ax2.plot(equity_df['timestamp'], equity_df['pnl'],
             label='浮动盈亏', linewidth=1.5, color='blue')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.8, alpha=0.5)
    ax2.axhline(y=10, color='green', linestyle='--',
               linewidth=1, label='止盈线 (+10)', alpha=0.7)
    ax2.axhline(y=-100, color='red', linestyle='--',
               linewidth=1, label='止损线 (-100)', alpha=0.7)

    # 填充正负区域
    ax2.fill_between(equity_df['timestamp'], equity_df['pnl'], 0,
                     where=(equity_df['pnl'] >= 0), color='green', alpha=0.2)
    ax2.fill_between(equity_df['timestamp'], equity_df['pnl'], 0,
                     where=(equity_df['pnl'] < 0), color='red', alpha=0.2)

    ax2.set_ylabel('盈亏 (USDT)', fontsize=11)
    ax2.set_title('策略浮动盈亏曲线', fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='best')

    # 3. 持仓数量
    ax3 = axes[2]
    ax3.plot(equity_df['timestamp'], equity_df['long_positions'],
             label='多单持仓', linewidth=1.5, color='green')
    ax3.plot(equity_df['timestamp'], equity_df['short_positions'],
             label='空单持仓', linewidth=1.5, color='red')
    ax3.fill_between(equity_df['timestamp'], equity_df['long_positions'],
                     0, color='green', alpha=0.15)
    ax3.fill_between(equity_df['timestamp'], equity_df['short_positions'],
                     0, color='red', alpha=0.15)
    ax3.set_ylabel('持仓层数', fontsize=11)
    ax3.set_title('持仓数量变化', fontsize=13, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc='best')

    # 4. 累计交易次数
    ax4 = axes[3]
    trades_df_sorted = trades_df.sort_values('timestamp')
    trades_df_sorted['cumulative_count'] = range(1, len(trades_df_sorted) + 1)

    # 分开多空
    long_cumsum = trades_df_sorted[trades_df_sorted['type'] == 'LONG'].copy()
    short_cumsum = trades_df_sorted[trades_df_sorted['type'] == 'SHORT'].copy()

    long_cumsum['cumcount'] = range(1, len(long_cumsum) + 1)
    short_cumsum['cumcount'] = range(1, len(short_cumsum) + 1)

    if not long_cumsum.empty:
        ax4.plot(long_cumsum['timestamp'], long_cumsum['cumcount'],
                label='累计多单', linewidth=1.5, color='green')
    if not short_cumsum.empty:
        ax4.plot(short_cumsum['timestamp'], short_cumsum['cumcount'],
                label='累计空单', linewidth=1.5, color='red')

    ax4.set_ylabel('累计交易次数', fontsize=11)
    ax4.set_xlabel('时间', fontsize=11)
    ax4.set_title('累计交易频率', fontsize=13, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.legend(loc='best')

    plt.tight_layout()

    # 保存图表
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"../data/backtest_results/detailed_analysis_{timestamp}.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n详细分析图表已保存: {output_path}")

    plt.show()

    return {
        'total_trades': total_trades,
        'final_pnl': final_pnl,
        'max_pnl': max_pnl,
        'min_pnl': min_pnl,
        'max_positions': max(max_long_positions, max_short_positions)
    }


if __name__ == "__main__":
    # 使用最新生成的结果文件
    trades_file = "../data/backtest_results/martingale_trades_20260118_124118.csv"
    equity_file = "../data/backtest_results/martingale_equity_20260118_124118.csv"

    results = analyze_backtest_results(trades_file, equity_file)

    print(f"\n{'='*80}")
    print("分析完成!")
    print(f"{'='*80}")
