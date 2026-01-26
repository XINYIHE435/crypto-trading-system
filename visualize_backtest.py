#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测结果可视化
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Helvetica', 'PingFang SC', 'STHeiti', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

def load_backtest_results():
    """加载最新的回测结果"""
    results_dir = Path("data/backtest_results")
    json_files = sorted(results_dir.glob("all_symbols_test_*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not json_files:
        print("❌ 未找到回测结果文件")
        return None
    
    latest_file = json_files[0]
    print(f"📁 加载回测结果: {latest_file}")
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data

def create_comprehensive_visualization(results):
    """创建综合可视化图表"""
    
    # 筛选成功的测试结果
    successful = {k: v for k, v in results.items() if v.get('status') == 'success'}
    
    if not successful:
        print("❌ 没有成功的回测结果")
        return
    
    symbols = list(successful.keys())
    
    # 提取数据
    trades = [successful[s]['total_trades'] for s in symbols]
    returns = [successful[s]['return_rate'] * 100 for s in symbols]
    win_rates = [successful[s]['win_rate'] for s in symbols]
    pnls = [successful[s]['total_pnl'] for s in symbols]
    max_profits = [successful[s]['max_profit'] for s in symbols]
    max_losses = [successful[s]['max_loss'] for s in symbols]
    
    # 创建图表
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    # 颜色配置
    colors = ['#F7931A', '#627EEA', '#F3BA2F', '#14F195', '#0033AD']
    
    # 1. 收益率对比
    ax1 = fig.add_subplot(gs[0, 0])
    bars = ax1.bar(symbols, returns, color=colors[:len(symbols)])
    ax1.set_title('各货币收益率对比', fontsize=14, fontweight='bold')
    ax1.set_ylabel('收益率 (%)', fontsize=12)
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    for bar, val in zip(bars, returns):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.2f}%', ha='center', va='bottom' if height > 0 else 'top', fontsize=10)
    
    # 2. 交易数量对比
    ax2 = fig.add_subplot(gs[0, 1])
    bars2 = ax2.bar(symbols, trades, color=colors[:len(symbols)], alpha=0.8)
    ax2.set_title('各货币交易数量', fontsize=14, fontweight='bold')
    ax2.set_ylabel('交易次数', fontsize=12)
    ax2.grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars2, trades):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{val}', ha='center', va='bottom', fontsize=10)
    
    # 3. 胜率对比
    ax3 = fig.add_subplot(gs[0, 2])
    bars3 = ax3.bar(symbols, win_rates, color=colors[:len(symbols)], alpha=0.8)
    ax3.set_title('各货币胜率对比', fontsize=14, fontweight='bold')
    ax3.set_ylabel('胜率 (%)', fontsize=12)
    ax3.set_ylim([0, 100])
    ax3.grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars3, win_rates):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.2f}%', ha='center', va='bottom', fontsize=10)
    
    # 4. 总盈亏对比
    ax4 = fig.add_subplot(gs[1, 0])
    bars4 = ax4.bar(symbols, pnls, color=colors[:len(symbols)], alpha=0.8)
    ax4.set_title('各货币总盈亏', fontsize=14, fontweight='bold')
    ax4.set_ylabel('盈亏 ($)', fontsize=12)
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    for bar, val in zip(bars4, pnls):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'${val:.2f}', ha='center', va='bottom' if height > 0 else 'top', fontsize=10)
    
    # 5. 最大盈利/亏损对比
    ax5 = fig.add_subplot(gs[1, 1])
    x = np.arange(len(symbols))
    width = 0.35
    bars5a = ax5.bar(x - width/2, max_profits, width, label='最大盈利', color='green', alpha=0.7)
    bars5b = ax5.bar(x + width/2, max_losses, width, label='最大亏损', color='red', alpha=0.7)
    ax5.set_title('最大盈利/亏损对比', fontsize=14, fontweight='bold')
    ax5.set_ylabel('金额 ($)', fontsize=12)
    ax5.set_xticks(x)
    ax5.set_xticklabels(symbols)
    ax5.legend()
    ax5.grid(True, alpha=0.3, axis='y')
    ax5.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
    
    # 6. 收益率 vs 胜率散点图
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.scatter(win_rates, returns, s=200, c=colors[:len(symbols)], alpha=0.6, edgecolors='black', linewidths=2)
    for i, symbol in enumerate(symbols):
        ax6.annotate(symbol, (win_rates[i], returns[i]), 
                    xytext=(5, 5), textcoords='offset points', fontsize=10, fontweight='bold')
    ax6.set_title('收益率 vs 胜率', fontsize=14, fontweight='bold')
    ax6.set_xlabel('胜率 (%)', fontsize=12)
    ax6.set_ylabel('收益率 (%)', fontsize=12)
    ax6.grid(True, alpha=0.3)
    
    # 7. 综合评分雷达图
    ax7 = fig.add_subplot(gs[2, :], projection='polar')
    
    def normalize(data, min_val=None, max_val=None):
        if min_val is None:
            min_val = min(data)
        if max_val is None:
            max_val = max(data)
        if max_val == min_val:
            return [50] * len(data)
        return [(x - min_val) / (max_val - min_val) * 100 for x in data]
    
    categories = ['收益率', '交易数', '胜率', '总盈亏', '风险控制']
    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    angles += angles[:1]
    
    for i, symbol in enumerate(symbols):
        values = [
            normalize([returns[i]], min(returns), max(returns))[0],
            normalize([trades[i]], min(trades), max(trades))[0],
            win_rates[i],
            normalize([pnls[i]], min(pnls), max(pnls))[0],
            normalize([abs(max_losses[i])], min([abs(x) for x in max_losses]), max([abs(x) for x in max_losses]))[0]
        ]
        values += values[:1]
        
        ax7.plot(angles, values, 'o-', linewidth=2, label=symbol, color=colors[i])
        ax7.fill(angles, values, alpha=0.15, color=colors[i])
    
    ax7.set_xticks(angles[:-1])
    ax7.set_xticklabels(categories, fontsize=11)
    ax7.set_ylim(0, 100)
    ax7.set_title('综合评分雷达图', fontsize=14, fontweight='bold', pad=20)
    ax7.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    ax7.grid(True)
    
    # 添加总标题
    total_pnl = sum(pnls)
    total_trades = sum(trades)
    avg_return = np.mean(returns)
    avg_win_rate = np.mean(win_rates)
    
    fig.suptitle(f'套利系统回测结果汇总\n总交易: {total_trades} 笔 | 总盈亏: ${total_pnl:.2f} | 平均收益率: {avg_return:.2f}% | 平均胜率: {avg_win_rate:.2f}%',
                fontsize=16, fontweight='bold', y=0.995)
    
    # 保存图表
    output_file = 'data/results/backtest_comprehensive_analysis.png'
    Path("data/results").mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"✅ 综合图表已保存: {output_file}")
    plt.close()

def create_performance_comparison(results):
    """创建性能对比表格"""
    successful = {k: v for k, v in results.items() if v.get('status') == 'success'}
    symbols = list(successful.keys())
    
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.axis('tight')
    ax.axis('off')
    
    table_data = []
    headers = ['交易对', '交易数', '收益率', '胜率', '总盈亏', '最大盈利', '最大亏损']
    
    for symbol in symbols:
        r = successful[symbol]
        table_data.append([
            symbol,
            r['total_trades'],
            f"{r['return_rate']*100:.2f}%",
            f"{r['win_rate']:.2f}%",
            f"${r['total_pnl']:.2f}",
            f"${r['max_profit']:.2f}",
            f"${r['max_loss']:.2f}"
        ])
    
    total_trades = sum([successful[s]['total_trades'] for s in symbols])
    total_pnl = sum([successful[s]['total_pnl'] for s in symbols])
    avg_return = np.mean([successful[s]['return_rate']*100 for s in symbols])
    avg_win_rate = np.mean([successful[s]['win_rate'] for s in symbols])
    
    table_data.append([
        '总计/平均',
        total_trades,
        f"{avg_return:.2f}%",
        f"{avg_win_rate:.2f}%",
        f"${total_pnl:.2f}",
        '-',
        '-'
    ])
    
    table = ax.table(cellText=table_data, colLabels=headers,
                    cellLoc='center', loc='center')
    
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 2)
    
    for i in range(len(headers)):
        table[(0, i)].set_facecolor('#4CAF50')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    for i in range(len(headers)):
        table[(len(table_data), i)].set_facecolor('#E8F5E9')
        table[(len(table_data), i)].set_text_props(weight='bold')
    
    plt.title('套利系统回测结果详细对比表', fontsize=16, fontweight='bold', pad=20)
    
    output_file = 'data/results/backtest_comparison_table.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"✅ 对比表格已保存: {output_file}")
    plt.close()

if __name__ == '__main__':
    print("=" * 60)
    print("生成回测结果可视化")
    print("=" * 60)
    
    results = load_backtest_results()
    
    if results:
        print("\n📊 生成综合可视化图表...")
        create_comprehensive_visualization(results)
        
        print("\n📋 生成对比表格...")
        create_performance_comparison(results)
        
        print("\n✅ 所有可视化图表生成完成！")
        print(f"\n生成的文件:")
        print(f"  📊 data/results/backtest_comprehensive_analysis.png")
        print(f"  📋 data/results/backtest_comparison_table.png")
