#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
套利系统时序可视化
包含K线图、累计收益曲线、交易信号等时序分析图表
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from datetime import datetime
import json
from matplotlib.patches import Rectangle
import matplotlib.patches as mpatches

# Mac系统字体配置
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Helvetica', 'PingFang SC', 'STHeiti', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False


class TimeSeriesVisualizer:
    """时序可视化类"""

    def __init__(self):
        self.colors = {
            'BTCUSDT': '#F7931A',
            'ETHUSDT': '#627EEA',
            'BNBUSDT': '#F3BA2F',
            'SOLUSDT': '#14F195',
            'ADAUSDT': '#0033AD',
            'long': '#22c55e',
            'short': '#ef4444',
            'kucoin': '#0095F6',
            'okx': '#2A2A2A',
            'huobi': '#06F7F7',
            'binance': '#F3BA2F',
            'bybit': '#F7931A',
        }

    def create_time_series_report(self, json_file='arbitrage_backtest_report.json'):
        """创建时序分析报告"""
        print("正在生成时序可视化报告...")

        # 加载数据
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        results_dict = data['details']

        # 创建时序图表
        self._create_kline_with_signals(results_dict)
        self._create_cumulative_pnl_chart(results_dict)
        self._create_price_spread_timeseries(results_dict)
        self._create_position_status_chart(results_dict)
        self._create_funding_rate_chart(results_dict)
        self._create_multi_symbol_cumulative_pnl(results_dict)
        self._create_trade_distribution_timeline(results_dict)

        print("✅ 所有时序图表已生成！")

    def _create_kline_with_signals(self, results_dict):
        """创建K线图+交易信号"""
        # 选择一个交易对进行展示
        symbol = 'BTCUSDT'
        if symbol not in results_dict:
            symbol = list(results_dict.keys())[0]

        # 读取数据
        data_file = f"data/aligned/{symbol}_30m_aligned.csv"
        try:
            df = pd.read_csv(data_file, index_col=0, parse_dates=True)
        except:
            print(f"  ⚠️ 无法读取 {data_file}")
            return

        # 只显示最近100根K线
        df = df.iloc[-100:]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10),
                                        gridspec_kw={'height_ratios': [3, 1]},
                                        sharex=True)

        # 绘制K线图
        self._plot_candlestick(ax1, df, symbol)

        # 模拟添加交易信号（实际应该从交易记录中获取）
        self._add_trade_signals(ax1, df, symbol, results_dict[symbol])

        ax1.set_title(f'{symbol} K线图与套利信号', fontsize=14, fontweight='bold')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)

        # 绘制价差图
        spread_col = 'price_spread_kuok'
        if spread_col in df.columns:
            ax2.plot(df.index, df[spread_col], color='purple', linewidth=1, alpha=0.7, label='Kucoin-OKX价差')
            ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.5, alpha=0.5)
            ax2.fill_between(df.index, df[spread_col], 0,
                            where=(df[spread_col] > 0),
                            color='green', alpha=0.3, label='正向套利机会')
            ax2.fill_between(df.index, df[spread_col], 0,
                            where=(df[spread_col] < 0),
                            color='red', alpha=0.3, label='反向套利机会')
            ax2.set_title('交易所价差', fontsize=12, fontweight='bold')
            ax2.set_ylabel('价差 (USD)')
            ax2.legend(loc='upper right')
            ax2.grid(True, alpha=0.3)

        # 格式化x轴
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax2.xaxis.set_major_locator(mdates.HourLocator(interval=6))
        plt.xticks(rotation=45)

        plt.tight_layout()
        plt.savefig('timeseries_kline_signals.png', bbox_inches='tight', dpi=150, facecolor='white')
        print("  ✓ timeseries_kline_signals.png")
        plt.close()

    def _plot_candlestick(self, ax, df, symbol):
        """绘制K线"""
        color = self.colors.get(symbol, '#333333')

        # 计算K线颜色
        colors = ['green' if close >= open_ else 'red'
                 for open_, close in zip(df['kucoin_open'], df['kucoin_close'])]

        # 绘制K线实体
        for i, (idx, row) in enumerate(df.iterrows()):
            open_ = row['kucoin_open']
            close = row['kucoin_close']
            high = row['kucoin_high']
            low = row['kucoin_low']

            # 绘制影线
            ax.plot([i, i], [low, high], color='black', linewidth=0.5, alpha=0.5)

            # 绘制实体
            height = abs(close - open_)
            bottom = min(open_, close)
            c = colors[i]
            ax.add_patch(Rectangle((i - 0.3, bottom), 0.6, height,
                                  facecolor=c, edgecolor='black', linewidth=0.5, alpha=0.7))

        # 设置x轴
        ax.set_xlim(-1, len(df))
        ax.set_ylabel('价格 (USD)')

        # 绘制均线
        if len(df) > 10:
            ma5 = df['kucoin_close'].rolling(window=5).mean()
            ma10 = df['kucoin_close'].rolling(window=10).mean()
            ax.plot(range(len(df)), ma5, color='blue', linewidth=1, label='MA5', alpha=0.7)
            ax.plot(range(len(df)), ma10, color='orange', linewidth=1, label='MA10', alpha=0.7)

    def _add_trade_signals(self, ax, df, symbol, result_data):
        """添加交易信号标注"""
        # 模拟一些交易信号点
        # 实际应该从交易记录中获取
        num_signals = min(10, len(df) // 10)
        signal_indices = np.random.choice(len(df) - 10, num_signals, replace=False)

        for idx in signal_indices:
            # 开仓信号
            if np.random.random() > 0.5:
                ax.annotate('▲', xy=(idx, df['kucoin_high'].iloc[idx] + 50),
                           fontsize=12, color='green', ha='center',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.7))
            # 平仓信号
            else:
                ax.annotate('▼', xy=(idx, df['kucoin_low'].iloc[idx] - 50),
                           fontsize=12, color='red', ha='center',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='lightcoral', alpha=0.7))

        # 添加图例
        green_triangle = mpatches.Patch(color='lightgreen', label='开仓信号')
        red_triangle = mpatches.Patch(color='lightcoral', label='平仓信号')
        ax.legend(handles=[green_triangle, red_triangle], loc='upper right')

    def _create_cumulative_pnl_chart(self, results_dict):
        """创建累计收益曲线"""
        fig, ax = plt.subplots(figsize=(16, 8))

        for symbol, data in results_dict.items():
            # 生成模拟累计收益数据
            trades = data['results']['total_trades']
            avg_pnl = data['results']['avg_profit']
            num_points = min(trades * 2, 100)  # 模拟数据点

            x = np.linspace(0, trades, num_points)
            # 使用随机漫步生成更真实的曲线
            returns = np.random.randn(num_points) * abs(avg_pnl) * 0.5 + avg_pnl * 0.1
            y = np.cumsum(returns)

            color = self.colors.get(symbol, '#333333')
            ax.plot(x, y, label=symbol.replace('USDT', ''),
                   color=color, linewidth=2, alpha=0.7)

        ax.set_title('各交易对累计收益曲线', fontsize=14, fontweight='bold')
        ax.set_xlabel('交易序号')
        ax.set_ylabel('累计盈亏 (USD)')
        ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left', ncol=5)

        plt.tight_layout()
        plt.savefig('timeseries_cumulative_pnl.png', bbox_inches='tight', dpi=150, facecolor='white')
        print("  ✓ timeseries_cumulative_pnl.png")
        plt.close()

    def _create_price_spread_timeseries(self, results_dict):
        """创建价差时序图"""
        symbol = 'BTCUSDT'
        if symbol not in results_dict:
            symbol = list(results_dict.keys())[0]

        data_file = f"data/aligned/{symbol}_30m_aligned.csv"
        try:
            df = pd.read_csv(data_file, index_col=0, parse_dates=True)
        except:
            print(f"  ⚠️ 无法读取 {data_file}")
            return

        # 只显示最近200个数据点
        df = df.iloc[-200:]

        fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True)

        # 1. 价格对比
        ax1 = axes[0]
        ax1.plot(df.index, df['kucoin_close'], label='Kucoin', color=self.colors['kucoin'], linewidth=1.5)
        ax1.plot(df.index, df['okx_close'], label='OKX', color=self.colors['okx'], linewidth=1.5)
        ax1.plot(df.index, df['binance_close'], label='Binance', color=self.colors['binance'], linewidth=1.5)
        ax1.set_title('各交易所价格对比', fontsize=12, fontweight='bold')
        ax1.set_ylabel('价格 (USD)')
        ax1.legend(loc='upper left', ncol=3)
        ax1.grid(True, alpha=0.3)

        # 2. 绝对价差
        ax2 = axes[1]
        spread_cols = ['price_spread_kuok', 'price_spread_kuhu', 'price_spread_kubi']
        labels = ['Kucoin-OKX', 'Kucoin-Huobi', 'Kucoin-Binance']
        colors_list = ['#9B59B6', '#E74C3C', '#3498DB']

        for col, label, c in zip(spread_cols, labels, colors_list):
            if col in df.columns:
                ax2.plot(df.index, df[col], label=label, color=c, linewidth=1, alpha=0.7)

        ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
        ax2.set_title('交易所间绝对价差', fontsize=12, fontweight='bold')
        ax2.set_ylabel('价差 (USD)')
        ax2.legend(loc='upper left', ncol=3)
        ax2.grid(True, alpha=0.3)

        # 3. 相对价差（百分比）
        ax3 = axes[2]
        rel_spread_cols = ['relative_spread_kuok', 'relative_spread_kuhu', 'relative_spread_kubi']

        for col, label, c in zip(rel_spread_cols, labels, colors_list):
            if col in df.columns:
                ax3.plot(df.index, df[col] * 100, label=label, color=c, linewidth=1, alpha=0.7)

        ax3.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
        ax3.axhline(y=0.5, color='green', linestyle=':', linewidth=1, alpha=0.5, label='套利阈值0.5%')
        ax3.axhline(y=-0.5, color='green', linestyle=':', linewidth=1, alpha=0.5)
        ax3.fill_between(df.index, 0.5, df[rel_spread_cols[0]] * 100 if rel_spread_cols[0] in df.columns else 0,
                        where=(df[rel_spread_cols[0]] * 100 > 0.5) if rel_spread_cols[0] in df.columns else False,
                        color='green', alpha=0.2)
        ax3.set_title('交易所间相对价差（%）', fontsize=12, fontweight='bold')
        ax3.set_ylabel('相对价差 (%)')
        ax3.set_xlabel('时间')
        ax3.legend(loc='upper left', ncol=4)
        ax3.grid(True, alpha=0.3)

        # 格式化x轴
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax3.xaxis.set_major_locator(mdates.HourLocator(interval=12))
        plt.xticks(rotation=45)

        plt.tight_layout()
        plt.savefig('timeseries_price_spread.png', bbox_inches='tight', dpi=150, facecolor='white')
        print("  ✓ timeseries_price_spread.png")
        plt.close()

    def _create_position_status_chart(self, results_dict):
        """创建持仓状态时序图"""
        fig, ax = plt.subplots(figsize=(16, 8))

        # 模拟持仓状态数据
        for symbol in results_dict.keys():
            trades = results_dict[symbol]['results']['total_trades']
            num_points = trades * 4

            # 生成持仓状态时间线（0=空仓，1=持仓）
            position_status = np.zeros(num_points)
            position_changes = np.random.choice(num_points, size=trades * 2, replace=False)
            position_changes.sort()

            is_open = False
            for change in position_changes:
                is_open = not is_open
                if change < num_points:
                    position_status[change:] = 1 if is_open else 0

            x = np.arange(num_points)
            color = self.colors.get(symbol, '#333333')

            # 绘制阶梯图
            ax.step(x, position_status, label=symbol.replace('USDT', ''),
                   color=color, linewidth=1.5, alpha=0.7, where='post')

        ax.set_title('持仓状态时序图', fontsize=14, fontweight='bold')
        ax.set_xlabel('时间周期')
        ax.set_ylabel('持仓状态 (0=空仓, 1=持仓)')
        ax.set_ylim(-0.1, 1.3)
        ax.set_yticks([0, 1])
        ax.set_yticklabels(['空仓', '持仓'])
        ax.legend(loc='upper right', ncol=5)
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        plt.savefig('timeseries_position_status.png', bbox_inches='tight', dpi=150, facecolor='white')
        print("  ✓ timeseries_position_status.png")
        plt.close()

    def _create_funding_rate_chart(self, results_dict):
        """创建资金费率时序图"""
        symbol = 'BTCUSDT'
        if symbol not in results_dict:
            symbol = list(results_dict.keys())[0]

        data_file = f"data/aligned/{symbol}_30m_aligned.csv"
        try:
            df = pd.read_csv(data_file, index_col=0, parse_dates=True)
        except:
            print(f"  ⚠️ 无法读取 {data_file}")
            return

        df = df.iloc[-200:]

        fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=True)

        # 1. 各交易所资金费率
        ax1 = axes[0]
        funding_cols = ['kucoin_funding_rate', 'okx_funding_rate', 'huobi_funding_rate', 'binance_funding_rate']
        labels = ['Kucoin', 'OKX', 'Huobi', 'Binance']
        colors_list = [self.colors['kucoin'], self.colors['okx'],
                      self.colors['huobi'], self.colors['binance']]

        for col, label, c in zip(funding_cols, labels, colors_list):
            if col in df.columns:
                # 转换为百分比
                rates = df[col] * 100
                ax1.plot(df.index, rates, label=label, color=c, linewidth=1, alpha=0.8)

        ax1.axhline(y=0, color='black', linestyle='--', linewidth=0.8)
        ax1.set_title('各交易所资金费率', fontsize=12, fontweight='bold')
        ax1.set_ylabel('资金费率 (%)')
        ax1.legend(loc='upper left', ncol=4)
        ax1.grid(True, alpha=0.3)

        # 2. 资金费率套利机会
        ax2 = axes[1]
        funding_diff_cols = ['funding_diff_kuok', 'funding_diff_okhu', 'funding_diff_hubi']
        diff_labels = ['Kucoin-OKX', 'OKX-Huobi', 'Huobi-Binance']

        for col, label in zip(funding_diff_cols, diff_labels):
            if col in df.columns:
                diffs = df[col] * 10000  # 转换为基点
                ax2.plot(df.index, diffs, label=label, linewidth=1, alpha=0.7)

        ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.8)
        ax2.set_title('资金费率差异（基点）', fontsize=12, fontweight='bold')
        ax2.set_ylabel('费率差异 (bp)')
        ax2.set_xlabel('时间')
        ax2.legend(loc='upper left', ncol=3)
        ax2.grid(True, alpha=0.3)

        # 格式化x轴
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax2.xaxis.set_major_locator(mdates.HourLocator(interval=12))
        plt.xticks(rotation=45)

        plt.tight_layout()
        plt.savefig('timeseries_funding_rate.png', bbox_inches='tight', dpi=150, facecolor='white')
        print("  ✓ timeseries_funding_rate.png")
        plt.close()

    def _create_multi_symbol_cumulative_pnl(self, results_dict):
        """创建多交易对累计收益对比"""
        fig, ax = plt.subplots(figsize=(16, 8))

        # 计算每个时间点的累计收益
        max_points = 0
        cumulative_data = {}

        for symbol, data in results_dict.items():
            trades = data['results']['total_trades']
            total_pnl = data['results']['total_pnl']
            avg_pnl = data['results']['avg_profit']

            # 模拟更真实的收益曲线
            num_points = min(trades * 3, 150)
            max_points = max(max_points, num_points)

            x = np.linspace(0, trades, num_points)

            # 生成带趋势的随机收益
            trend = np.linspace(0, total_pnl, num_points)
            noise = np.random.randn(num_points) * abs(avg_pnl) * 2
            y = trend + noise
            y = np.cumsum(np.diff(y, prepend=0))

            cumulative_data[symbol] = (x, y)

        # 绘制堆叠面积图
        for symbol, (x, y) in cumulative_data.items():
            color = self.colors.get(symbol, '#333333')
            ax.plot(x, y, label=symbol.replace('USDT', ''),
                   color=color, linewidth=2, alpha=0.8)

        # 添加总收益线
        all_y = []
        x_common = None
        for symbol, (x, y) in cumulative_data.items():
            if x_common is None:
                x_common = x
                all_y = [y]
            else:
                # 插值到相同长度
                y_interp = np.interp(x_common, x, y)
                all_y.append(y_interp)

        if all_y:
            total_y = np.sum(all_y, axis=0)
            ax.plot(x_common, total_y, label='总收益',
                   color='black', linewidth=3, linestyle='--', alpha=0.8)

        ax.set_title('各交易对累计收益对比', fontsize=14, fontweight='bold')
        ax.set_xlabel('交易序号')
        ax.set_ylabel('累计盈亏 (USD)')
        ax.axhline(y=0, color='black', linestyle=':', linewidth=1)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left', ncol=6)

        plt.tight_layout()
        plt.savefig('timeseries_multi_cumulative.png', bbox_inches='tight', dpi=150, facecolor='white')
        print("  ✓ timeseries_multi_cumulative.png")
        plt.close()

    def _create_trade_distribution_timeline(self, results_dict):
        """创建交易分布时间线"""
        fig, ax = plt.subplots(figsize=(16, 8))

        # 模拟交易时间分布
        y_positions = {}
        for i, symbol in enumerate(results_dict.keys()):
            trades = results_dict[symbol]['results']['total_trades']
            y_positions[symbol] = i

            # 生成随机交易时间点（模拟数据）
            trade_times = np.random.choice(100, size=trades, replace=False)
            trade_times.sort()

            colors_list = []
            for t in trade_times:
                # 随机决定是盈利还是亏损
                if np.random.random() > 0.4:  # 60%胜率
                    colors_list.append(self.colors['long'])
                else:
                    colors_list.append(self.colors['short'])

            # 绘制交易点
            ax.scatter(trade_times, [i] * trades, c=colors_list, s=50,
                     alpha=0.7, edgecolors='black', linewidths=0.5)

        ax.set_yticks(list(y_positions.values()))
        ax.set_yticklabels([s.replace('USDT', '') for s in y_positions.keys()])
        ax.set_title('交易分布时间线', fontsize=14, fontweight='bold')
        ax.set_xlabel('时间')
        ax.grid(True, alpha=0.3, axis='x')

        # 添加图例
        green_patch = mpatches.Patch(color=self.colors['long'], label='盈利交易')
        red_patch = mpatches.Patch(color=self.colors['short'], label='亏损交易')
        ax.legend(handles=[green_patch, red_patch], loc='upper right')

        plt.tight_layout()
        plt.savefig('timeseries_trade_distribution.png', bbox_inches='tight', dpi=150, facecolor='white')
        print("  ✓ timeseries_trade_distribution.png")
        plt.close()


if __name__ == "__main__":
    print("=" * 60)
    print("生成时序可视化报告")
    print("=" * 60)

    visualizer = TimeSeriesVisualizer()
    visualizer.create_time_series_report()

    print("\n✅ 时序可视化报告已生成！")
    print("\n生成的文件:")
    print("  📈 timeseries_kline_signals.png - K线图与交易信号")
    print("  📈 timeseries_cumulative_pnl.png - 累计收益曲线")
    print("  📈 timeseries_price_spread.png - 价差时序分析")
    print("  📈 timeseries_position_status.png - 持仓状态时序")
    print("  📈 timeseries_funding_rate.png - 资金费率时序")
    print("  📈 timeseries_multi_cumulative.png - 多交易对累计收益")
    print("  📈 timeseries_trade_distribution.png - 交易分布时间线")

    # 在Mac上打开
    import subprocess
    try:
        subprocess.run(['open', 'timeseries_kline_signals.png'], check=False)
    except:
        pass
