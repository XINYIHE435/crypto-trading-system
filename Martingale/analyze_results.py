"""
Martingale 回测结果分析工具 - 完整版
支持分析所有策略功能的回测结果
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import json
import os
from glob import glob

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti', 'PingFang SC']
plt.rcParams['axes.unicode_minus'] = False


def load_latest_results(results_dir: str = "../data/backtest_results"):
    """加载最新的回测结果文件"""
    
    # 查找最新的文件
    trades_files = sorted(glob(f"{results_dir}/martingale_trades_*.csv"))
    equity_files = sorted(glob(f"{results_dir}/martingale_equity_*.csv"))
    summary_files = sorted(glob(f"{results_dir}/martingale_summary_*.json"))
    
    if not trades_files or not equity_files:
        print("未找到回测结果文件")
        return None, None, None
    
    latest_trades = trades_files[-1]
    latest_equity = equity_files[-1]
    latest_summary = summary_files[-1] if summary_files else None
    
    print(f"加载文件:")
    print(f"  交易记录: {latest_trades}")
    print(f"  盈亏曲线: {latest_equity}")
    if latest_summary:
        print(f"  回测摘要: {latest_summary}")
    
    return latest_trades, latest_equity, latest_summary


def analyze_backtest_results(trades_csv: str, equity_csv: str, summary_json: str = None):
    """分析回测结果"""

    # 读取数据
    trades_df = pd.read_csv(trades_csv)
    equity_df = pd.read_csv(equity_csv)

    trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
    equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])

    # 读取摘要（如果有）
    summary = None
    if summary_json and os.path.exists(summary_json):
        with open(summary_json, 'r', encoding='utf-8') as f:
            summary = json.load(f)

    print("=" * 80)
    print("Martingale 双向马丁策略 - 回测分析报告")
    print("=" * 80)

    # 策略配置信息
    if summary:
        config = summary.get('strategy_config', {})
        print(f"\n【策略配置】")
        print(f"  网格类型: {config.get('grid_type', 'N/A')}")
        print(f"  止盈模式: {config.get('take_profit_mode', 'N/A')}")
        print(f"  基准模式: {config.get('baseline_mode', 'N/A')}")
        print(f"  初始手数: {config.get('base_size', 'N/A')}")
        print(f"  马丁倍数: {config.get('multiplier', 'N/A')}")
        print(f"  最大层数: {config.get('max_levels', 'N/A')}")
        print(f"  止盈目标: {config.get('target_profit', 'N/A')}")
        print(f"  止损线: {config.get('max_floating_loss', 'N/A')}")

    # 基本统计
    total_trades = len(trades_df)
    long_trades = len(trades_df[trades_df['type'] == 'LONG']) if 'type' in trades_df.columns else 0
    short_trades = len(trades_df[trades_df['type'] == 'SHORT']) if 'type' in trades_df.columns else 0

    print(f"\n【交易统计】")
    print(f"  总交易次数: {total_trades}")
    print(f"  多单次数: {long_trades} ({long_trades/total_trades*100:.1f}%)" if total_trades > 0 else "  多单次数: 0")
    print(f"  空单次数: {short_trades} ({short_trades/total_trades*100:.1f}%)" if total_trades > 0 else "  空单次数: 0")

    # 层级统计
    if 'level' in trades_df.columns:
        level_stats = trades_df.groupby('level').agg({
            'type': 'count',
            'size': ['mean', 'sum']
        }).round(6)
        level_stats.columns = ['交易次数', '平均手数', '总手数']

        print(f"\n【层级统计】")
        print(level_stats.to_string())

    # 盈亏分析
    final_pnl = equity_df['pnl'].iloc[-1]
    final_realized = equity_df['realized_pnl'].iloc[-1] if 'realized_pnl' in equity_df.columns else 0
    max_pnl = equity_df['pnl'].max()
    min_pnl = equity_df['pnl'].min()
    total_final_pnl = final_pnl + final_realized

    print(f"\n【盈亏分析】")
    print(f"  最终浮动盈亏: {final_pnl:.2f} USDT")
    print(f"  已实现盈亏: {final_realized:.2f} USDT")
    print(f"  总盈亏: {total_final_pnl:.2f} USDT")
    print(f"  最大浮盈: {max_pnl:.2f} USDT")
    print(f"  最大浮亏: {min_pnl:.2f} USDT")
    print(f"  盈亏比: {abs(max_pnl/min_pnl) if min_pnl != 0 else 0:.2f}")

    # 回撤分析
    equity_df['cummax'] = equity_df['pnl'].cummax()
    equity_df['drawdown'] = equity_df['pnl'] - equity_df['cummax']
    max_drawdown = equity_df['drawdown'].min()
    
    print(f"\n【风险分析】")
    print(f"  最大回撤: {max_drawdown:.2f} USDT")
    print(f"  最大回撤比例: {abs(max_drawdown/max_pnl)*100 if max_pnl > 0 else 0:.2f}%")

    # 持仓分析
    max_long_positions = equity_df['long_positions'].max()
    max_short_positions = equity_df['short_positions'].max()
    
    if 'long_size' in equity_df.columns:
        max_long_size = equity_df['long_size'].max()
        max_short_size = equity_df['short_size'].max()
    else:
        max_long_size = max_short_size = 0

    print(f"\n【持仓分析】")
    print(f"  最大多单层数: {max_long_positions}")
    print(f"  最大空单层数: {max_short_positions}")
    print(f"  最大多单仓位: {max_long_size:.6f}")
    print(f"  最大空单仓位: {max_short_size:.6f}")

    # 时间跨度
    time_span = equity_df['timestamp'].iloc[-1] - equity_df['timestamp'].iloc[0]
    print(f"\n【时间跨度】")
    print(f"  回测时长: {time_span.days} 天")
    print(f"  数据点数: {len(equity_df)}")
    print(f"  日均交易: {total_trades / max(time_span.days, 1):.2f} 笔")

    # 绘制详细图表
    fig, axes = plt.subplots(5, 1, figsize=(16, 18))

    # 1. 价格与交易点位
    ax1 = axes[0]
    ax1.plot(equity_df['timestamp'], equity_df['price'],
             label='价格', linewidth=1, color='gray', alpha=0.7)
    
    if 'baseline_price' in equity_df.columns:
        ax1.plot(equity_df['timestamp'], equity_df['baseline_price'],
                label='基准价', linewidth=1, color='red', linestyle='--', alpha=0.5)

    # 标记多单
    if not trades_df.empty and 'type' in trades_df.columns:
        long_trades_data = trades_df[trades_df['type'] == 'LONG']
        if not long_trades_data.empty:
            ax1.scatter(long_trades_data['timestamp'], long_trades_data['price'],
                       marker='^', color='green', s=50, label=f'多单 ({len(long_trades_data)})',
                       alpha=0.6, zorder=5)

        # 标记空单
        short_trades_data = trades_df[trades_df['type'] == 'SHORT']
        if not short_trades_data.empty:
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
    
    if 'realized_pnl' in equity_df.columns:
        ax2.plot(equity_df['timestamp'], equity_df['realized_pnl'],
                label='已实现盈亏', linewidth=1.5, color='green', linestyle='--')
        total_pnl_series = equity_df['pnl'] + equity_df['realized_pnl']
        ax2.plot(equity_df['timestamp'], total_pnl_series,
                label='总盈亏', linewidth=1, color='purple', alpha=0.7)
    
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.8, alpha=0.5)

    # 填充正负区域
    ax2.fill_between(equity_df['timestamp'], equity_df['pnl'], 0,
                     where=(equity_df['pnl'] >= 0), color='green', alpha=0.2)
    ax2.fill_between(equity_df['timestamp'], equity_df['pnl'], 0,
                     where=(equity_df['pnl'] < 0), color='red', alpha=0.2)

    ax2.set_ylabel('盈亏 (USDT)', fontsize=11)
    ax2.set_title('策略盈亏曲线', fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='best')

    # 3. 回撤曲线
    ax3 = axes[2]
    ax3.fill_between(equity_df['timestamp'], equity_df['drawdown'], 0,
                     color='red', alpha=0.3)
    ax3.plot(equity_df['timestamp'], equity_df['drawdown'],
             label='回撤', linewidth=1, color='red')
    ax3.axhline(y=max_drawdown, color='darkred', linestyle='--',
               label=f'最大回撤: {max_drawdown:.2f}', alpha=0.7)
    
    ax3.set_ylabel('回撤 (USDT)', fontsize=11)
    ax3.set_title('回撤分析', fontsize=13, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc='best')

    # 4. 持仓数量
    ax4 = axes[3]
    ax4.plot(equity_df['timestamp'], equity_df['long_positions'],
             label='多单持仓', linewidth=1.5, color='green')
    ax4.plot(equity_df['timestamp'], equity_df['short_positions'],
             label='空单持仓', linewidth=1.5, color='red')
    ax4.fill_between(equity_df['timestamp'], equity_df['long_positions'],
                     0, color='green', alpha=0.15)
    ax4.fill_between(equity_df['timestamp'], equity_df['short_positions'],
                     0, color='red', alpha=0.15)
    ax4.set_ylabel('持仓层数', fontsize=11)
    ax4.set_title('持仓数量变化', fontsize=13, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.legend(loc='best')

    # 5. 网格间距变化（如果有）
    ax5 = axes[4]
    if 'grid_spacing' in equity_df.columns:
        ax5.plot(equity_df['timestamp'], equity_df['grid_spacing'],
                label='网格间距', linewidth=1.5, color='orange')
        if 'current_atr' in equity_df.columns:
            ax5.plot(equity_df['timestamp'], equity_df['current_atr'],
                    label='ATR', linewidth=1, color='blue', linestyle='--', alpha=0.7)
        ax5.set_ylabel('间距 (USDT)', fontsize=11)
        ax5.set_title('网格间距变化', fontsize=13, fontweight='bold')
    else:
        # 如果没有网格间距数据，显示累计交易
        trades_df_sorted = trades_df.sort_values('timestamp')
        trades_df_sorted['cumulative_count'] = range(1, len(trades_df_sorted) + 1)
        
        if 'type' in trades_df_sorted.columns:
            long_cumsum = trades_df_sorted[trades_df_sorted['type'] == 'LONG'].copy()
            short_cumsum = trades_df_sorted[trades_df_sorted['type'] == 'SHORT'].copy()
            
            if not long_cumsum.empty:
                long_cumsum['cumcount'] = range(1, len(long_cumsum) + 1)
                ax5.plot(long_cumsum['timestamp'], long_cumsum['cumcount'],
                        label='累计多单', linewidth=1.5, color='green')
            if not short_cumsum.empty:
                short_cumsum['cumcount'] = range(1, len(short_cumsum) + 1)
                ax5.plot(short_cumsum['timestamp'], short_cumsum['cumcount'],
                        label='累计空单', linewidth=1.5, color='red')
        
        ax5.set_ylabel('累计交易次数', fontsize=11)
        ax5.set_title('累计交易频率', fontsize=13, fontweight='bold')
    
    ax5.set_xlabel('时间', fontsize=11)
    ax5.grid(True, alpha=0.3)
    ax5.legend(loc='best')

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
        'realized_pnl': final_realized,
        'total_final_pnl': total_final_pnl,
        'max_pnl': max_pnl,
        'min_pnl': min_pnl,
        'max_drawdown': max_drawdown,
        'max_positions': max(max_long_positions, max_short_positions)
    }


def compare_results(results_dir: str = "../data/backtest_results"):
    """比较多次回测结果"""
    
    summary_files = sorted(glob(f"{results_dir}/martingale_summary_*.json"))
    
    if not summary_files:
        print("未找到回测摘要文件")
        return
    
    print("=" * 80)
    print("回测结果对比")
    print("=" * 80)
    
    results = []
    for f in summary_files[-10:]:  # 最多显示最近10次
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)
            # 提取时间戳
            timestamp = f.split('_')[-1].replace('.json', '')
            data['timestamp'] = timestamp
            results.append(data)
    
    print(f"\n{'时间戳':<16} {'网格类型':<12} {'止盈模式':<12} {'总盈亏':<12} {'交易数':<8} {'最大回撤':<10}")
    print("-" * 80)
    
    for r in results:
        config = r.get('strategy_config', {})
        perf = r.get('performance', {})
        trades = r.get('trades', {})
        
        print(f"{r.get('timestamp', 'N/A'):<16} "
              f"{config.get('grid_type', 'N/A'):<12} "
              f"{config.get('take_profit_mode', 'N/A'):<12} "
              f"{perf.get('total_pnl', 0):<12.2f} "
              f"{trades.get('total_trades', 0):<8} "
              f"{perf.get('max_drawdown', 0):<10.2f}")


if __name__ == "__main__":
    # 自动加载最新结果
    trades_file, equity_file, summary_file = load_latest_results()
    
    if trades_file and equity_file:
        results = analyze_backtest_results(trades_file, equity_file, summary_file)
        
        print(f"\n{'='*80}")
        print("分析完成!")
        print(f"{'='*80}")
        
        # 显示结果对比
        print("\n")
        compare_results()
