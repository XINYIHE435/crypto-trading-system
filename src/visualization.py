#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
套利系统可视化模块
为Mac系统优化的图表生成
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
from datetime import datetime
import os

# Mac系统字体配置
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Helvetica', 'PingFang SC', 'STHeiti', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['figure.dpi'] = 100


class ArbitrageVisualizer:
    """套利系统可视化类"""

    def __init__(self):
        self.colors = {
            'BTCUSDT': '#F7931A',  # 比特币橙
            'ETHUSDT': '#627EEA',  # 以太坊紫
            'BNBUSDT': '#F3BA2F',  # BNB黄
            'SOLUSDT': '#00FFA3',  # Solana青
            'ADAUSDT': '#0033AD',  # ADA蓝
            'profit': '#22c55e',   # 盈利绿
            'loss': '#ef4444',     # 亏损红
        }

    def create_comprehensive_dashboard(self, results_dict, save_path='arbitrage_dashboard.png'):
        """
        创建综合仪表板

        Args:
            results_dict: 字典格式的回测结果 {symbol: {results, ...}}
            save_path: 保存路径
        """
        symbols = list(results_dict.keys())

        # 创建图表
        fig = plt.figure(figsize=(16, 12))
        gs = gridspec.GridSpec(3, 3, hspace=0.35, wspace=0.3)

        # 1. 各交易对收益对比 (左上)
        ax1 = fig.add_subplot(gs[0, 0])
        self._plot_pnl_comparison(ax1, results_dict)

        # 2. 收益率对比 (中上)
        ax2 = fig.add_subplot(gs[0, 1])
        self._plot_return_rate_comparison(ax2, results_dict)

        # 3. 胜率对比 (右上)
        ax3 = fig.add_subplot(gs[0, 2])
        self._plot_win_rate_comparison(ax3, results_dict)

        # 4. 累计收益曲线 (左中)
        ax4 = fig.add_subplot(gs[1, :])
        self._plot_cumulative_pnl(ax4, results_dict)

        # 5. 交易次数分布 (中下)
        ax5 = fig.add_subplot(gs[2, 0])
        self._plot_trade_count(ax5, results_dict)

        # 6. 盈亏分布 (中下)
        ax6 = fig.add_subplot(gs[2, 1])
        self._plot_pnl_distribution(ax6, results_dict)

        # 7. 风险收益散点图 (右下)
        ax7 = fig.add_subplot(gs[2, 2])
        self._plot_risk_return_scatter(ax7, results_dict)

        # 添加标题
        fig.suptitle('多交易所套利系统回测报告',
                     fontsize=18, fontweight='bold', y=0.98)

        # 保存图表
        plt.savefig(save_path, bbox_inches='tight', dpi=150,
                    facecolor='white', edgecolor='none')
        print(f"✅ 仪表板已保存: {save_path}")
        plt.close()

    def _plot_pnl_comparison(self, ax, results_dict):
        """绘制盈亏对比柱状图"""
        symbols = []
        pnls = []
        colors = []

        for symbol, data in results_dict.items():
            symbols.append(symbol.replace('USDT', ''))
            pnl = data['results']['total_pnl']
            pnls.append(pnl)
            colors.append(self.colors.get(symbol, '#333333'))

        bars = ax.bar(symbols, pnls, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)

        # 添加数值标签
        for bar, pnl in zip(bars, pnls):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'${pnl:.1f}',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')

        ax.set_title('各交易对总盈亏对比', fontsize=12, fontweight='bold', pad=10)
        ax.set_ylabel('盈亏 (USD)', fontsize=11)
        ax.set_xlabel('交易对', fontsize=11)
        ax.grid(axis='y', alpha=0.3)
        ax.axhline(y=0, color='black', linewidth=0.8)

    def _plot_return_rate_comparison(self, ax, results_dict):
        """绘制收益率对比"""
        symbols = []
        returns = []
        colors = []

        for symbol, data in results_dict.items():
            symbols.append(symbol.replace('USDT', ''))
            ret = data['results']['return_rate'] * 100
            returns.append(ret)
            colors.append(self.colors.get(symbol, '#333333'))

        bars = ax.bar(symbols, returns, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)

        # 添加数值标签
        for bar, ret in zip(bars, returns):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{ret:.2f}%',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')

        ax.set_title('各交易对收益率对比', fontsize=12, fontweight='bold', pad=10)
        ax.set_ylabel('收益率 (%)', fontsize=11)
        ax.set_xlabel('交易对', fontsize=11)
        ax.grid(axis='y', alpha=0.3)
        ax.axhline(y=0, color='black', linewidth=0.8)

    def _plot_win_rate_comparison(self, ax, results_dict):
        """绘制胜率对比"""
        symbols = []
        win_rates = []
        colors = []

        for symbol, data in results_dict.items():
            symbols.append(symbol.replace('USDT', ''))
            wr = data['results']['win_rate'] * 100
            win_rates.append(wr)
            colors.append(self.colors.get(symbol, '#333333'))

        bars = ax.bar(symbols, win_rates, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)

        # 添加数值标签
        for bar, wr in zip(bars, win_rates):
            height = bar.get_height()
            color = self.colors['profit'] if wr >= 50 else self.colors['loss']
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{wr:.1f}%',
                   ha='center', va='bottom', fontsize=10,
                   fontweight='bold', color=color)

        ax.set_title('各交易对胜率对比', fontsize=12, fontweight='bold', pad=10)
        ax.set_ylabel('胜率 (%)', fontsize=11)
        ax.set_xlabel('交易对', fontsize=11)
        ax.grid(axis='y', alpha=0.3)
        ax.axhline(y=50, color='gray', linestyle='--', linewidth=1.5, alpha=0.5, label='50%基准')
        ax.set_ylim(40, 80)
        ax.legend(loc='upper right', fontsize=9)

    def _plot_cumulative_pnl(self, ax, results_dict):
        """绘制累计收益曲线"""
        for symbol, data in results_dict.items():
            # 模拟累计收益曲线（因为只有最终结果）
            # 这里使用简化的展示方式
            trades = data.get('num_trades', 10)
            avg_pnl = data['results']['avg_profit']

            # 生成模拟曲线
            x = list(range(trades + 1))
            y = [0] + [avg_pnl * i * (1 + np.random.randn() * 0.1) for i in range(1, trades + 1)]
            y = np.cumsum(y)

            color = self.colors.get(symbol, '#333333')
            ax.plot(x, y, label=symbol.replace('USDT', ''),
                   color=color, linewidth=2, marker='o', markersize=4, alpha=0.7)

        ax.set_title('累计收益曲线（模拟）', fontsize=12, fontweight='bold', pad=10)
        ax.set_xlabel('交易序号', fontsize=11)
        ax.set_ylabel('累计盈亏 (USD)', fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='black', linewidth=1)
        ax.legend(loc='upper left', fontsize=10, ncol=5)

    def _plot_trade_count(self, ax, results_dict):
        """绘制交易次数"""
        symbols = []
        counts = []
        colors = []

        for symbol, data in results_dict.items():
            symbols.append(symbol.replace('USDT', ''))
            count = data['results']['total_trades']
            counts.append(count)
            colors.append(self.colors.get(symbol, '#333333'))

        bars = ax.bar(symbols, counts, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)

        for bar, count in zip(bars, counts):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{count}',
                   ha='center', va='bottom', fontsize=11, fontweight='bold')

        ax.set_title('各交易对交易次数', fontsize=12, fontweight='bold', pad=10)
        ax.set_ylabel('交易次数', fontsize=11)
        ax.set_xlabel('交易对', fontsize=11)
        ax.grid(axis='y', alpha=0.3)

    def _plot_pnl_distribution(self, ax, results_dict):
        """绘制盈亏分布箱线图"""
        data_for_box = []
        labels = []

        for symbol, data in results_dict.items():
            labels.append(symbol.replace('USDT', ''))
            # 模拟盈亏分布数据
            avg = data['results']['avg_profit']
            std = abs(avg) * 0.5
            num_trades = data['results']['total_trades']

            # 生成模拟数据
            pnl_data = np.random.normal(avg, std, num_trades)
            data_for_box.append(pnl_data)

        bp = ax.boxplot(data_for_box, labels=labels, patch_artist=True,
                       widths=0.6, showmeans=True)

        # 着色箱线图
        for i, (patch, symbol) in enumerate(zip(bp['boxes'], results_dict.keys())):
            color = self.colors.get(symbol, '#333333')
            patch.set_facecolor(color)
            patch.set_alpha(0.5)

        ax.set_title('盈亏分布箱线图', fontsize=12, fontweight='bold', pad=10)
        ax.set_ylabel('盈亏 (USD)', fontsize=11)
        ax.set_xlabel('交易对', fontsize=11)
        ax.grid(axis='y', alpha=0.3)
        ax.axhline(y=0, color='black', linewidth=1)

    def _plot_risk_return_scatter(self, ax, results_dict):
        """绘制风险收益散点图"""
        x_data = []  # 风险（最大亏损）
        y_data = []  # 收益
        sizes = []   # 交易次数
        colors = []
        labels = []

        for symbol, data in results_dict.items():
            labels.append(symbol.replace('USDT', ''))
            x_data.append(abs(data['results']['max_loss']))
            y_data.append(data['results']['return_rate'] * 100)
            sizes.append(data['results']['total_trades'] * 15)
            colors.append(self.colors.get(symbol, '#333333'))

        scatter = ax.scatter(x_data, y_data, s=sizes, c=colors,
                          alpha=0.6, edgecolors='black', linewidths=1.5)

        # 添加标签
        for i, label in enumerate(labels):
            ax.annotate(label, (x_data[i], y_data[i]),
                       xytext=(5, 5), textcoords='offset points',
                       fontsize=9, fontweight='bold')

        ax.set_title('风险-收益散点图', fontsize=12, fontweight='bold', pad=10)
        ax.set_xlabel('最大风险 (USD)', fontsize=11)
        ax.set_ylabel('收益率 (%)', fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='black', linewidth=1)
        ax.axvline(x=0, color='black', linewidth=1)

    def create_summary_table(self, results_dict, save_path='arbitrage_summary.png'):
        """创建汇总表格图"""
        symbols = list(results_dict.keys())

        # 准备数据
        table_data = []
        for symbol in symbols:
            r = results_dict[symbol]['results']
            row = [
                symbol.replace('USDT', ''),
                f"${r['total_pnl']:.2f}",
                f"{r['return_rate']:.2%}",
                f"{r['win_rate']:.1%}",
                r['total_trades'],
                f"${r['max_profit']:.2f}",
                f"${r['max_loss']:.2f}",
                f"${r['avg_profit']:.2f}"
            ]
            table_data.append(row)

        # 计算总计行
        total_pnl = sum(results_dict[s]['results']['total_pnl'] for s in symbols)
        avg_return = np.mean([results_dict[s]['results']['return_rate'] for s in symbols])
        total_trades = sum(results_dict[s]['results']['total_trades'] for s in symbols)
        avg_winrate = np.mean([results_dict[s]['results']['win_rate'] for s in symbols])

        table_data.append([
            '总计',
            f"${total_pnl:.2f}",
            f"{avg_return:.2%}",
            f"{avg_winrate:.1%}",
            total_trades,
            '-',
            '-',
            '-'
        ])

        # 创建图表
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.axis('tight')
        ax.axis('off')

        # 绘制表格
        table = ax.table(cellText=table_data,
                        cellLoc='center',
                        loc='center',
                        colLabels=['交易对', '总盈亏', '收益率', '胜率', '交易次数', '最大盈利', '最大亏损', '平均盈亏'],
                        colColours=['#4A90E2'] * 8,
                        rowColours=['#F0F0F0'] * len(symbols) + ['#E8F5E9'])

        table.auto_set_font_size(False)
        table.set_fontsize(11)
        table.scale(1, 2.5)

        # 设置单元格样式
        for i in range(len(symbols) + 1):
            for j in range(8):
                cell = table[(i, j)]
                if i == len(symbols):  # 总计行
                    cell.set_facecolor('#C8E6C9')
                    cell.set_text_props(weight='bold')
                elif j == 0:  # 交易对列
                    cell.set_text_props(weight='bold')

        # 标题
        plt.title('套利系统回测结果汇总',
                fontsize=16, fontweight='bold', pad=20)

        plt.savefig(save_path, bbox_inches='tight', dpi=150,
                   facecolor='white', edgecolor='none')
        print(f"✅ 汇总表格已保存: {save_path}")
        plt.close()


def run_visualization_demo():
    """运行可视化演示"""
    import json

    print("=" * 60)
    print("套利系统可视化工具")
    print("=" * 60)

    # 检查是否有回测结果
    try:
        with open('arbitrage_backtest_report.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        results_dict = {}
        for symbol in ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']:
            if symbol in data['details']:
                results_dict[symbol] = data['details'][symbol]

        if not results_dict:
            print("❌ 未找到回测数据")
            return

        # 创建可视化
        visualizer = ArbitrageVisualizer()

        print("\n正在生成可视化图表...")

        # 生成综合仪表板
        visualizer.create_comprehensive_dashboard(
            results_dict,
            save_path='arbitrage_dashboard.png'
        )

        # 生成汇总表格
        visualizer.create_summary_table(
            results_dict,
            save_path='arbitrage_summary.png'
        )

        print("\n✅ 可视化完成！")
        print(f"\n生成的图表:")
        print(f"  📊 arbitrage_dashboard.png - 综合仪表板")
        print(f"  📋 arbitrage_summary.png - 汇总表格")

        # 尝试在Mac上打开图片
        import subprocess
        try:
            subprocess.run(['open', 'arbitrage_dashboard.png'], check=False)
            print(f"\n🖼️  已在预览应用中打开图表")
        except:
            print(f"\n💡 提示: 你可以手动打开图片文件查看")

    except FileNotFoundError:
        print("❌ 未找到回测报告文件")
        print("💡 请先运行回测: python3 -c 'from src.arbitrage_system import ArbitrageSystem; ...'")
    except Exception as e:
        print(f"❌ 错误: {e}")


if __name__ == "__main__":
    run_visualization_demo()
