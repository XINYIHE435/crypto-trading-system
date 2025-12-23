#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级套利系统可视化
包含实际交易数据的详细图表
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
from datetime import datetime
import json

# Mac系统字体配置
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Helvetica', 'PingFang SC', 'STHeiti', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False


class AdvancedArbitrageVisualizer:
    """高级套利系统可视化类"""

    def __init__(self):
        self.colors = {
            'BTCUSDT': '#F7931A',
            'ETHUSDT': '#627EEA',
            'BNBUSDT': '#F3BA2F',
            'SOLUSDT': '#14F195',
            'ADAUSDT': '#0033AD',
            'long': '#22c55e',
            'short': '#ef4444',
        }

    def create_full_report(self, json_file='arbitrage_backtest_report.json'):
        """创建完整的可视化报告"""
        print("正在生成高级可视化报告...")

        # 加载数据
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        results_dict = data['details']

        # 创建多页面报告
        self._create_dashboard_page1(results_dict)
        self._create_dashboard_page2(results_dict)
        self._create_trade_analysis(results_dict)
        self._create_performance_summary(results_dict)

        print("✅ 所有可视化图表已生成！")

    def _create_dashboard_page1(self, results_dict):
        """第一页：主要指标对比"""
        fig = plt.figure(figsize=(16, 10))
        gs = gridspec.GridSpec(2, 3, hspace=0.3, wspace=0.3)

        # 1. 总盈亏对比
        ax1 = fig.add_subplot(gs[0, 0])
        symbols = list(results_dict.keys())
        pnls = [results_dict[s]['results']['total_pnl'] for s in symbols]
        colors = [self.colors.get(s, '#666') for s in symbols]

        bars = ax1.bar(range(len(symbols)), pnls, color=colors, alpha=0.7, edgecolor='black')
        ax1.set_xticks(range(len(symbols)))
        ax1.set_xticklabels([s.replace('USDT', '') for s in symbols])
        ax1.set_title('总盈亏对比', fontsize=12, fontweight='bold')
        ax1.set_ylabel('盈亏 (USD)')
        ax1.axhline(y=0, color='black', linewidth=1)
        ax1.grid(axis='y', alpha=0.3)

        for bar, pnl in zip(bars, pnls):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'${pnl:.0f}', ha='center', va='bottom' if height > 0 else 'top',
                    fontsize=9, fontweight='bold')

        # 2. 收益率对比
        ax2 = fig.add_subplot(gs[0, 1])
        returns = [results_dict[s]['results']['return_rate'] * 100 for s in symbols]

        bars = ax2.bar(range(len(symbols)), returns, color=colors, alpha=0.7, edgecolor='black')
        ax2.set_xticks(range(len(symbols)))
        ax2.set_xticklabels([s.replace('USDT', '') for s in symbols])
        ax2.set_title('收益率对比', fontsize=12, fontweight='bold')
        ax2.set_ylabel('收益率 (%)')
        ax2.axhline(y=0, color='black', linewidth=1)
        ax2.grid(axis='y', alpha=0.3)

        for bar, ret in zip(bars, returns):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{ret:.2f}%', ha='center', va='bottom' if height > 0 else 'top',
                    fontsize=9, fontweight='bold')

        # 3. 胜率对比
        ax3 = fig.add_subplot(gs[0, 2])
        win_rates = [results_dict[s]['results']['win_rate'] * 100 for s in symbols]

        bars = ax3.bar(range(len(symbols)), win_rates, color=colors, alpha=0.7, edgecolor='black')
        ax3.set_xticks(range(len(symbols)))
        ax3.set_xticklabels([s.replace('USDT', '') for s in symbols])
        ax3.set_title('胜率对比', fontsize=12, fontweight='bold')
        ax3.set_ylabel('胜率 (%)')
        ax3.set_ylim(45, 75)
        ax3.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
        ax3.grid(axis='y', alpha=0.3)

        for bar, wr in zip(bars, win_rates):
            height = bar.get_height()
            c = self.colors['long'] if wr > 50 else self.colors['short']
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{wr:.1f}%', ha='center', va='bottom',
                    fontsize=9, fontweight='bold', color=c)

        # 4. 交易次数
        ax4 = fig.add_subplot(gs[1, 0])
        trades = [results_dict[s]['results']['total_trades'] for s in symbols]

        bars = ax4.bar(range(len(symbols)), trades, color=colors, alpha=0.7, edgecolor='black')
        ax4.set_xticks(range(len(symbols)))
        ax4.set_xticklabels([s.replace('USDT', '') for s in symbols])
        ax4.set_title('交易次数', fontsize=12, fontweight='bold')
        ax4.set_ylabel('次数')
        ax4.grid(axis='y', alpha=0.3)

        for bar, t in zip(bars, trades):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{t}', ha='center', va='bottom',
                    fontsize=10, fontweight='bold')

        # 5. 风险收益散点图
        ax5 = fig.add_subplot(gs[1, 1])
        max_losses = [abs(results_dict[s]['results']['max_loss']) for s in symbols]
        returns_pct = [results_dict[s]['results']['return_rate'] * 100 for s in symbols]

        scatter = ax5.scatter(max_losses, returns_pct, s=200, c=colors,
                            alpha=0.6, edgecolors='black', linewidths=1.5)

        for i, s in enumerate(symbols):
            ax5.annotate(s.replace('USDT', ''), (max_losses[i], returns_pct[i]),
                        xytext=(5, 5), textcoords='offset points',
                        fontsize=9, fontweight='bold')

        ax5.set_title('风险-收益关系', fontsize=12, fontweight='bold')
        ax5.set_xlabel('最大风险 (USD)')
        ax5.set_ylabel('收益率 (%)')
        ax5.grid(True, alpha=0.3)
        ax5.axhline(y=0, color='black', linewidth=1)
        ax5.axvline(x=0, color='black', linewidth=1)

        # 6. 盈亏比
        ax6 = fig.add_subplot(gs[1, 2])
        avg_profits = [results_dict[s]['results']['max_profit'] for s in symbols]
        max_losses = [abs(results_dict[s]['results']['max_loss']) for s in symbols]

        x = np.arange(len(symbols))
        width = 0.35

        bars1 = ax6.bar(x - width/2, avg_profits, width, label='最大盈利',
                       color=self.colors['long'], alpha=0.7, edgecolor='black')
        bars2 = ax6.bar(x + width/2, max_losses, width, label='最大亏损',
                       color=self.colors['short'], alpha=0.7, edgecolor='black')

        ax6.set_xticks(x)
        ax6.set_xticklabels([s.replace('USDT', '') for s in symbols])
        ax6.set_title('最大盈利 vs 最大亏损', fontsize=12, fontweight='bold')
        ax6.set_ylabel('金额 (USD)')
        ax6.legend(loc='upper right')
        ax6.grid(axis='y', alpha=0.3)

        fig.suptitle('套利系统回测报告 - 主要指标', fontsize=16, fontweight='bold')
        plt.savefig('arbitrage_report_page1.png', bbox_inches='tight', dpi=150, facecolor='white')
        print("  ✓ arbitrage_report_page1.png")
        plt.close()

    def _create_dashboard_page2(self, results_dict):
        """第二页：详细分析"""
        fig = plt.figure(figsize=(16, 10))
        gs = gridspec.GridSpec(2, 2, hspace=0.3, wspace=0.3)

        # 1. 做多vs做空统计
        ax1 = fig.add_subplot(gs[0, 0])

        long_pnls = [results_dict[s].get('long_pnl', 0) for s in results_dict]
        short_pnls = [results_dict[s].get('short_pnl', 0) for s in results_dict]
        symbols_short = [s.replace('USDT', '') for s in results_dict]

        x = np.arange(len(symbols_short))
        width = 0.35

        bars1 = ax1.bar(x - width/2, long_pnls, width, label='做多盈亏',
                       color=self.colors['long'], alpha=0.7, edgecolor='black')
        bars2 = ax1.bar(x + width/2, short_pnls, width, label='做空盈亏',
                       color=self.colors['short'], alpha=0.7, edgecolor='black')

        ax1.set_xticks(x)
        ax1.set_xticklabels(symbols_short)
        ax1.set_title('做多 vs 做空盈亏', fontsize=12, fontweight='bold')
        ax1.set_ylabel('盈亏 (USD)')
        ax1.axhline(y=0, color='black', linewidth=1)
        ax1.legend()
        ax1.grid(axis='y', alpha=0.3)

        # 2. 平仓原因分布
        ax2 = fig.add_subplot(gs[0, 1])

        reasons_data = {}
        for s in results_dict:
            for reason, count in results_dict[s].get('close_reasons', {}).items():
                if reason not in reasons_data:
                    reasons_data[reason] = []
                reasons_data[reason].append(count)

        if reasons_data:
            x = np.arange(len(reasons_data))
            reasons_list = list(reasons_data.keys())
            counts = [sum(reasons_data[r]) for r in reasons_list]

            ax2.bar(x, counts, color='steelblue', alpha=0.7, edgecolor='black')
            ax2.set_xticks(x)
            ax2.set_xticklabels(reasons_list, rotation=15, ha='right')
            ax2.set_title('平仓原因分布', fontsize=12, fontweight='bold')
            ax2.set_ylabel('次数')

            for i, v in enumerate(counts):
                ax2.text(i, v, f'{v}', ha='center', va='bottom', fontweight='bold')

            ax2.grid(axis='y', alpha=0.3)

        # 3. 盈利能力对比
        ax3 = fig.add_subplot(gs[1, 0])

        profitable_counts = [results_dict[s].get('profitable_trades', 0) for s in results_dict]
        losing_counts = [results_dict[s].get('losing_trades', 0) for s in results_dict]

        x = np.arange(len(symbols_short))
        width = 0.35

        bars1 = ax3.bar(x - width/2, profitable_counts, width, label='盈利交易',
                       color=self.colors['long'], alpha=0.7, edgecolor='black')
        bars2 = ax3.bar(x + width/2, losing_counts, width, label='亏损交易',
                       color=self.colors['short'], alpha=0.7, edgecolor='black')

        ax3.set_xticks(x)
        ax3.set_xticklabels(symbols_short)
        ax3.set_title('盈利 vs 亏损交易数', fontsize=12, fontweight='bold')
        ax3.set_ylabel('交易次数')
        ax3.legend()
        ax3.grid(axis='y', alpha=0.3)

        # 4. 平均盈亏对比
        ax4 = fig.add_subplot(gs[1, 1])

        avg_profits = [results_dict[s].get('avg_profit', 0) for s in results_dict]
        avg_losses = [results_dict[s].get('avg_loss', 0) for s in results_dict]

        x = np.arange(len(symbols_short))
        width = 0.35

        bars1 = ax4.bar(x - width/2, avg_profits, width, label='平均盈利',
                       color=self.colors['long'], alpha=0.7, edgecolor='black')
        bars2 = ax4.bar(x + width/2, [abs(x) for x in avg_losses], width, label='平均亏损',
                       color=self.colors['short'], alpha=0.7, edgecolor='black')

        ax4.set_xticks(x)
        ax4.set_xticklabels(symbols_short)
        ax4.set_title('平均盈利 vs 平均亏损', fontsize=12, fontweight='bold')
        ax4.set_ylabel('金额 (USD)')
        ax4.legend()
        ax4.grid(axis='y', alpha=0.3)

        fig.suptitle('套利系统回测报告 - 详细分析', fontsize=16, fontweight='bold')
        plt.savefig('arbitrage_report_page2.png', bbox_inches='tight', dpi=150, facecolor='white')
        print("  ✓ arbitrage_report_page2.png")
        plt.close()

    def _create_trade_analysis(self, results_dict):
        """创建交易分析图表"""
        fig = plt.figure(figsize=(16, 8))
        gs = gridspec.GridSpec(2, 2, hspace=0.3, wspace=0.3)

        # 准备数据
        all_trades_info = []
        for s in results_dict:
            all_trades_info.append({
                'symbol': s,
                'total': results_dict[s]['results']['total_trades'],
                'win_rate': results_dict[s]['results']['win_rate'] * 100,
                'avg_pnl': results_dict[s]['results']['avg_profit']
            })

        # 1. 综合评分雷达图
        ax1 = fig.add_subplot(gs[:, 0], projection='polar')

        categories = ['收益率', '胜率', '交易频率', '稳定性']
        N = len(categories)

        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]

        # 为每个交易对绘制雷达图
        for i, info in enumerate(all_trades_info):
            values = [
                info['win_rate'] / 70 * 100,  # 归一化
                info['win_rate'],
                min(info['total'] / 50 * 100, 100),  # 交易频率
                100 - abs(info['avg_pnl']) / 2  # 稳定性
            ]
            values += values[:1]

            ax1.plot(angles, values, 'o-', linewidth=2,
                    label=info['symbol'].replace('USDT', ''),
                    color=self.colors.get(info['symbol'], '#666'))
            ax1.fill(angles, values, alpha=0.15,
                    color=self.colors.get(info['symbol'], '#666'))

        ax1.set_xticks(angles[:-1])
        ax1.set_xticklabels(categories)
        ax1.set_ylim(0, 100)
        ax1.set_title('综合评分雷达图', fontsize=12, fontweight='bold', pad=20)
        ax1.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
        ax1.grid(True)

        # 2. 收益率排名
        ax2 = fig.add_subplot(gs[0, 1])
        sorted_results = sorted(all_trades_info, key=lambda x: x['avg_pnl'], reverse=True)

        symbols_sorted = [x['symbol'].replace('USDT', '') for x in sorted_results]
        pnls_sorted = [x['avg_pnl'] for x in sorted_results]
        colors_sorted = [self.colors.get(x['symbol'], '#666') for x in sorted_results]

        bars = ax2.barh(range(len(symbols_sorted)), pnls_sorted, color=colors_sorted, alpha=0.7, edgecolor='black')
        ax2.set_yticks(range(len(symbols_sorted)))
        ax2.set_yticklabels(symbols_sorted)
        ax2.set_title('平均盈亏排名', fontsize=12, fontweight='bold')
        ax2.set_xlabel('平均盈亏 (USD)')
        ax2.axvline(x=0, color='black', linewidth=1)
        ax2.grid(axis='x', alpha=0.3)

        for bar, pnl in zip(bars, pnls_sorted):
            width = bar.get_width()
            ax2.text(width + (1 if width > 0 else -3), bar.get_y() + bar.get_height()/2,
                    f'${pnl:.1f}', ha='left' if width > 0 else 'right',
                    va='center', fontsize=9, fontweight='bold')

        # 3. 胜率排名
        ax3 = fig.add_subplot(gs[1, 1])
        sorted_results = sorted(all_trades_info, key=lambda x: x['win_rate'], reverse=True)

        symbols_sorted = [x['symbol'].replace('USDT', '') for x in sorted_results]
        win_rates_sorted = [x['win_rate'] for x in sorted_results]
        colors_sorted = [self.colors.get(x['symbol'], '#666') for x in sorted_results]

        bars = ax3.barh(range(len(symbols_sorted)), win_rates_sorted, color=colors_sorted, alpha=0.7, edgecolor='black')
        ax3.set_yticks(range(len(symbols_sorted)))
        ax3.set_yticklabels(symbols_sorted)
        ax3.set_title('胜率排名', fontsize=12, fontweight='bold')
        ax3.set_xlabel('胜率 (%)')
        ax3.set_xlim(45, 75)
        ax3.axvline(x=50, color='gray', linestyle='--', alpha=0.5)
        ax3.grid(axis='x', alpha=0.3)

        for bar, wr in zip(bars, win_rates_sorted):
            width = bar.get_width()
            ax3.text(width, bar.get_y() + bar.get_height()/2,
                    f'{wr:.1f}%', ha='left', va='center',
                    fontsize=9, fontweight='bold')

        fig.suptitle('交易分析', fontsize=16, fontweight='bold')
        plt.savefig('arbitrage_trade_analysis.png', bbox_inches='tight', dpi=150, facecolor='white')
        print("  ✓ arbitrage_trade_analysis.png")
        plt.close()

    def _create_performance_summary(self, results_dict):
        """创建性能总结图表"""
        fig, axes = plt.subplots(1, 1, figsize=(14, 6))
        ax = axes

        # 准备表格数据
        symbols = list(results_dict.keys())

        cell_text = []
        for s in symbols:
            r = results_dict[s]['results']
            row = [
                s.replace('USDT', ''),
                f"${r['total_pnl']:.2f}",
                f"{r['return_rate']:.2%}",
                f"{r['win_rate']:.1%}",
                r['total_trades'],
                f"${r['max_profit']:.2f}",
                f"${abs(r['max_loss']):.2f}",
                f"${r['avg_profit']:.2f}"
            ]
            cell_text.append(row)

        # 添加总计行
        total_pnl = sum(results_dict[s]['results']['total_pnl'] for s in symbols)
        avg_return = np.mean([results_dict[s]['results']['return_rate'] for s in symbols])
        total_trades = sum(results_dict[s]['results']['total_trades'] for s in symbols)
        avg_winrate = np.mean([results_dict[s]['results']['win_rate'] for s in symbols])
        max_profit = max(results_dict[s]['results']['max_profit'] for s in symbols)
        max_loss = max(abs(results_dict[s]['results']['max_loss']) for s in symbols)

        cell_text.append([
            '总计/平均',
            f"${total_pnl:.2f}",
            f"{avg_return:.2%}",
            f"{avg_winrate:.1%}",
            total_trades,
            f"${max_profit:.2f}",
            f"${max_loss:.2f}",
            "-"
        ])

        # 绘制表格
        table = ax.table(cellText=cell_text,
                        cellLoc='center',
                        bbox=[0, 0, 1, 1],
                        colLabels=['交易对', '总盈亏', '收益率', '胜率', '交易次数', '最大盈利', '最大亏损', '平均盈亏'])

        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1, 2.2)

        # 设置颜色
        for i in range(len(symbols) + 1):
            for j in range(8):
                cell = table[(i, j)]
                if i == len(symbols):
                    cell.set_facecolor('#4CAF50')
                    cell.set_text_props(weight='bold', color='white')
                elif i % 2 == 0:
                    cell.set_facecolor('#F5F5F5')
                else:
                    cell.set_facecolor('#FFFFFF')

                if j == 0:
                    cell.set_text_props(weight='bold')

        ax.axis('off')
        ax.set_title('套利系统性能总结', fontsize=14, fontweight='bold', pad=20)

        plt.savefig('arbitrage_performance_summary.png', bbox_inches='tight', dpi=150, facecolor='white')
        print("  ✓ arbitrage_performance_summary.png")
        plt.close()


if __name__ == "__main__":
    print("=" * 60)
    print("生成高级可视化报告")
    print("=" * 60)

    visualizer = AdvancedArbitrageVisualizer()
    visualizer.create_full_report()

    print("\n✅ 可视化报告已生成！")
    print("\n生成的文件:")
    print("  📊 arbitrage_report_page1.png - 主要指标对比")
    print("  📊 arbitrage_report_page2.png - 详细分析")
    print("  📊 arbitrage_trade_analysis.png - 交易分析")
    print("  📊 arbitrage_performance_summary.png - 性能总结")

    # 在Mac上打开
    import subprocess
    try:
        subprocess.run(['open', 'arbitrage_report_page1.png'], check=False)
    except:
        pass
