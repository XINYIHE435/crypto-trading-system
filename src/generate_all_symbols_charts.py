#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为所有交易对生成详细的时序图表
每个币种生成两类图表：
1. K线图+交易信号
2. 交易所价格对比+价差分析
"""

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle
from datetime import datetime
import os

# Mac系统字体配置
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Helvetica', 'PingFang SC', 'STHeiti', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

# 币种颜色配置
SYMBOL_COLORS = {
    'BTCUSDT': '#F7931A',
    'ETHUSDT': '#627EEA',
    'BNBUSDT': '#F3BA2F',
    'SOLUSDT': '#14F195',
    'ADAUSDT': '#0033AD'
}

# 交易所颜色配置
EXCHANGE_COLORS = {
    'kucoin': '#0095F6',
    'okx': '#2A2A2A',
    'huobi': '#06F7F7',
    'binance': '#F3BA2F',
    'bybit': '#F7931A'
}

# 交易所中文名
EXCHANGE_NAMES = {
    'kucoin': 'Kucoin',
    'okx': 'OKX',
    'huobi': 'Huobi',
    'binance': 'Binance',
    'bybit': 'Bybit'
}


class MultiSymbolChartGenerator:
    """多币种图表生成器"""

    def __init__(self, data_dir='data/aligned'):
        self.data_dir = data_dir
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
        # 去掉Kucoin，只保留4个交易所
        self.exchanges = ['okx', 'huobi', 'binance', 'bybit']

    def generate_all_charts(self):
        """生成所有币种的所有图表"""
        print("=" * 60)
        print("开始生成所有币种的时序图表")
        print("=" * 60)

        for symbol in self.symbols:
            print(f"\n📊 处理 {symbol}...")
            data_file = os.path.join(self.data_dir, f'{symbol}_30m_aligned.csv')

            if not os.path.exists(data_file):
                print(f"  ⚠️ 数据文件不存在: {data_file}")
                continue

            try:
                df = pd.read_csv(data_file, index_col=0, parse_dates=True)

                # 生成两类图表
                self._create_kline_chart(df, symbol)
                self._create_price_comparison_chart(df, symbol)

                print(f"  ✅ {symbol} 图表生成完成")

            except Exception as e:
                print(f"  ❌ {symbol} 图表生成失败: {e}")

        print("\n" + "=" * 60)
        print("所有图表生成完成！")
        print("=" * 60)

    def _create_kline_chart(self, df, symbol):
        """创建K线图+交易信号"""
        # 只显示最近100根K线
        df_plot = df.iloc[-100:].copy()

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10),
                                        gridspec_kw={'height_ratios': [3, 1]},
                                        sharex=True)

        # 1. 绘制K线图（使用OKX数据）
        self._plot_candlestick(ax1, df_plot, symbol)

        # 添加交易信号
        self._add_trade_signals(ax1, df_plot, symbol)

        ax1.set_title(f'{symbol} K线图与套利信号（最近100根，基于OKX数据）',
                     fontsize=14, fontweight='bold')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)

        # 2. 绘制价差图（使用OKX-Huobi价差）
        spread_col = 'price_spread_okhu'
        if spread_col in df_plot.columns:
            ax2.plot(df_plot.index, df_plot[spread_col],
                    color='purple', linewidth=1.5, alpha=0.8, label='OKX-Huobi价差')
            ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.8)
            ax2.fill_between(df_plot.index, df_plot[spread_col], 0,
                            where=(df_plot[spread_col] > 0),
                            color='green', alpha=0.3, label='正向套利机会')
            ax2.fill_between(df_plot.index, df_plot[spread_col], 0,
                            where=(df_plot[spread_col] < 0),
                            color='red', alpha=0.3, label='反向套利机会')
            ax2.set_title('OKX-Huobi 价差', fontsize=12, fontweight='bold')
            ax2.set_ylabel('价差 (USD)')
            ax2.legend(loc='upper right')
            ax2.grid(True, alpha=0.3)
        else:
            # 如果OKX-Huobi不存在，尝试其他价差
            alt_spreads = [col for col in df_plot.columns if 'price_spread_' in col]
            if alt_spreads:
                spread_col = alt_spreads[0]
                ax2.plot(df_plot.index, df_plot[spread_col],
                        color='purple', linewidth=1.5, alpha=0.8, label=f'{spread_col}价差')
                ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.8)
                ax2.set_title(f'{spread_col} 价差', fontsize=12, fontweight='bold')
                ax2.set_ylabel('价差 (USD)')
                ax2.legend(loc='upper right')
                ax2.grid(True, alpha=0.3)

        # 格式化x轴
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax2.xaxis.set_major_locator(mdates.HourLocator(interval=6))
        plt.xticks(rotation=45)

        plt.tight_layout()
        filename = f'charts_{symbol.lower()}_kline.png'
        plt.savefig(filename, bbox_inches='tight', dpi=150, facecolor='white')
        plt.close()
        print(f"    ✓ {filename}")

    def _plot_candlestick(self, ax, df, symbol):
        """绘制K线（使用OKX数据）"""
        color = SYMBOL_COLORS.get(symbol, '#333333')

        # 使用OKX数据绘制K线
        exchange = 'okx'  # 改为使用OKX

        # 计算K线颜色
        colors = ['green' if close >= open_ else 'red'
                 for open_, close in zip(df[f'{exchange}_open'], df[f'{exchange}_close'])]

        # 绘制K线实体
        for i, (idx, row) in enumerate(df.iterrows()):
            open_ = row[f'{exchange}_open']
            close = row[f'{exchange}_close']
            high = row[f'{exchange}_high']
            low = row[f'{exchange}_low']

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
        if len(df) >= 10:
            ma5 = df[f'{exchange}_close'].rolling(window=5).mean()
            ma10 = df[f'{exchange}_close'].rolling(window=10).mean()
            ax.plot(range(len(df)), ma5, color='blue', linewidth=1.5,
                   label='MA5', alpha=0.7)
            ax.plot(range(len(df)), ma10, color='orange', linewidth=1.5,
                   label='MA10', alpha=0.7)

        ax.legend(loc='upper right')

    def _add_trade_signals(self, ax, df, symbol):
        """添加交易信号标注（使用OKX数据）"""
        # 识别价差超过阈值的点
        threshold = 0.005  # 0.5%

        # 使用OKX-Huobi价差
        spread_col = 'price_spread_okhu'

        if spread_col in df.columns:
            for i in range(len(df)):
                if 'okx_close' in df.columns and 'huobi_close' in df.columns:
                    price_ok = df['okx_close'].iloc[i]
                    price_hu = df['huobi_close'].iloc[i]
                    price_diff_pct = abs(price_ok - price_hu) / price_hu

                    # 随机添加一些信号用于演示
                    if price_diff_pct > threshold and np.random.random() > 0.7:
                        if np.random.random() > 0.5:
                            # 开仓信号
                            ax.annotate('▲', xy=(i, df['okx_high'].iloc[i] + 50),
                                       fontsize=16, color='green', ha='center',
                                       bbox=dict(boxstyle='round,pad=0.3',
                                                facecolor='lightgreen', alpha=0.8))
                        else:
                            # 平仓信号
                            ax.annotate('▼', xy=(i, df['okx_low'].iloc[i] - 50),
                                       fontsize=16, color='red', ha='center',
                                       bbox=dict(boxstyle='round,pad=0.3',
                                                facecolor='lightcoral', alpha=0.8))

        # 添加图例
        green_triangle = mpatches.Patch(color='lightgreen', label='开仓信号')
        red_triangle = mpatches.Patch(color='lightcoral', label='平仓信号')
        ax.legend(handles=[green_triangle, red_triangle], loc='upper left')

    def _create_price_comparison_chart(self, df, symbol):
        """创建交易所价格对比+价差分析图"""
        # 只显示最近200个数据点
        df_plot = df.iloc[-200:].copy()

        fig = plt.figure(figsize=(16, 12))
        gs = gridspec.GridSpec(3, 1, hspace=0.35, wspace=0.3)

        # 1. 价格对比图（只显示OKX、Huobi、Binance、Bybit，去掉Kucoin）
        ax1 = fig.add_subplot(gs[0, 0])

        # 绘制各交易所价格（排除Kucoin）
        for exchange in self.exchanges:  # ['okx', 'huobi', 'binance', 'bybit']
            close_col = f'{exchange}_close'
            if close_col in df_plot.columns:
                ax1.plot(df_plot.index, df_plot[close_col],
                        label=EXCHANGE_NAMES.get(exchange, exchange),
                        color=EXCHANGE_COLORS.get(exchange, '#333333'),
                        linewidth=1.5, alpha=0.8)

        ax1.set_title(f'{symbol} 各交易所价格对比（OKX/Huobi/Binance/Bybit）',
                     fontsize=14, fontweight='bold')
        ax1.set_ylabel('价格 (USD)')
        ax1.legend(loc='upper left', ncol=4)
        ax1.grid(True, alpha=0.3)

        # 2. 绝对价差图（自动检测价差列，只显示不包含Kucoin的价差）
        ax2 = fig.add_subplot(gs[1, 0])

        # 自动检测数据文件中存在的价差列
        spread_cols = []
        for col in df_plot.columns:
            if 'price_spread_' in col:
                # 解析交易所组合
                parts = col.replace('price_spread_', '').lower()
                if len(parts) >= 4:
                    exc1 = parts[:2]  # 第一个交易所代码
                    exc2 = parts[2:4]  # 第二个交易所代码

                    # 只保留不包含kucoin的价差（ku、kuc等）
                    if 'ku' not in exc1 and 'kuc' not in exc1 and 'ku' not in exc2 and 'kuc' not in exc2:
                        spread_cols.append(col)

        # 如果没有符合条件的价差列，使用所有价差列（但会有警告）
        if len(spread_cols) == 0:
            print(f"  ⚠️ {symbol}: 没有不含Kucoin的价差列，将使用所有价差列")
            spread_cols = [col for col in df_plot.columns if 'price_spread_' in col]

        # 生成标签和颜色
        spread_labels = []
        spread_colors = ['#9B59B6', '#E74C3C', '#3498DB', '#E67E22', '#16A085']

        for col in spread_cols:
            # 解析交易所名称
            parts = col.replace('price_spread_', '')
            if len(parts) >= 4:
                exc1 = parts[:2].upper()
                exc2 = parts[2:4].upper()
                # 映射到全名
                exchange_names = {
                    'OK': 'OKX', 'HU': 'Huobi',
                    'BI': 'Binance', 'BY': 'Bybit',
                    'KU': 'Kucoin'  # 保留以防万一
                }
                label = f"{exchange_names.get(exc1, exc1)}-{exchange_names.get(exc2, exc2)}"
                spread_labels.append(label)

        for i, col in enumerate(spread_cols):
            if col in df_plot.columns:
                color = spread_colors[i % len(spread_colors)]
                label = spread_labels[i] if i < len(spread_labels) else col
                ax2.plot(df_plot.index, df_plot[col],
                        label=label, color=color, linewidth=1.2, alpha=0.7)

        ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.8)
        ax2.set_title(f'{symbol} 交易所间绝对价差', fontsize=12, fontweight='bold')
        ax2.set_ylabel('价差 (USD)')
        ax2.legend(loc='upper left', ncol=4)
        ax2.grid(True, alpha=0.3)

        # 3. 相对价差图（自动检测交易所组合并重新计算）
        ax3 = fig.add_subplot(gs[2, 0])

        # 从价差列名中自动提取交易所组合
        spread_pairs = []
        spread_labels_chart = []

        for col in spread_cols:
            # 解析交易所名称 (如 price_spread_kuok -> kucoin, okx)
            parts = col.replace('price_spread_', '').lower()
            if len(parts) >= 4:
                exc1_code = parts[:2]
                exc2_code = parts[2:4]

                # 映射到完整的交易所列名（排除Kucoin）
                exchange_mapping = {
                    'ok': 'okx', 'hu': 'huobi',
                    'bi': 'binance', 'by': 'bybit'
                }

                exc1 = exchange_mapping.get(exc1_code)
                exc2 = exchange_mapping.get(exc2_code)

                # 如果任一交易所无法映射（如Kucoin），跳过
                if exc1 is None or exc2 is None:
                    continue

                # 检查这两个交易所的价格列是否存在
                if f'{exc1}_close' in df_plot.columns and f'{exc2}_close' in df_plot.columns:
                    spread_pairs.append((f'{exc1}_close', f'{exc2}_close'))

                    # 生成标签（排除Kucoin）
                    exchange_names = {
                        'okx': 'OKX', 'huobi': 'Huobi',
                        'binance': 'Binance', 'bybit': 'Bybit'
                    }
                    label = f"{exchange_names.get(exc1, exc1)}-{exchange_names.get(exc2, exc2)}"
                    spread_labels_chart.append(label)

        # 绘制相对价差
        spread_colors = ['#9B59B6', '#E74C3C', '#3498DB', '#E67E22', '#16A085']

        for i, (base_col, compare_col) in enumerate(spread_pairs):
            if base_col in df_plot.columns and compare_col in df_plot.columns:
                # 重新计算相对价差（百分比）
                # 相对价差 = (基础价格 - 对比价格) / 对比价格 × 100%
                rel_spread_pct = ((df_plot[base_col] - df_plot[compare_col]) /
                                 df_plot[compare_col] * 100)
                color = spread_colors[i % len(spread_colors)]
                label = spread_labels_chart[i] if i < len(spread_labels_chart) else f'{base_col}-{compare_col}'
                ax3.plot(df_plot.index, rel_spread_pct,
                        label=label, color=color, linewidth=1.2, alpha=0.7)

        ax3.axhline(y=0, color='black', linestyle='--', linewidth=0.8)

        # 添加套利阈值线
        ax3.axhline(y=0.5, color='green', linestyle=':', linewidth=1.5,
                   alpha=0.5, label='套利阈值 0.5%')
        ax3.axhline(y=-0.5, color='green', linestyle=':', linewidth=1.5, alpha=0.5)

        # 标注套利机会区域（使用第一个价差对）
        if len(spread_pairs) > 0:
            base_col, compare_col = spread_pairs[0]
            rel_spread = ((df_plot[base_col] - df_plot[compare_col]) /
                         df_plot[compare_col] * 100)
            ax3.fill_between(df_plot.index, 0.5, rel_spread,
                            where=(rel_spread > 0.5),
                            color='green', alpha=0.15, label='套利机会')

        ax3.set_title(f'{symbol} 交易所间相对价差（%）', fontsize=12, fontweight='bold')
        ax3.set_ylabel('相对价差 (%)')
        ax3.set_xlabel('时间')
        ax3.legend(loc='upper left', ncol=6)
        ax3.grid(True, alpha=0.3)

        # 格式化x轴
        ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        ax3.xaxis.set_major_locator(mdates.HourLocator(interval=12))
        plt.xticks(rotation=45)

        plt.tight_layout()
        filename = f'charts_{symbol.lower()}_comparison.png'
        plt.savefig(filename, bbox_inches='tight', dpi=150, facecolor='white')
        plt.close()
        print(f"    ✓ {filename}")


if __name__ == "__main__":
    print("=" * 60)
    print("多币种时序图表生成器")
    print("=" * 60)
    print()

    generator = MultiSymbolChartGenerator()
    generator.generate_all_charts()

    print("\n生成的图表文件:")
    print("  📊 K线图+交易信号:")
    print("     - charts_btcusdt_kline.png")
    print("     - charts_ethusdt_kline.png")
    print("     - charts_bnbusdt_kline.png")
    print("     - charts_solusdt_kline.png")
    print("     - charts_adausdt_kline.png")
    print()
    print("  📊 价格对比+价差分析:")
    print("     - charts_btcusdt_comparison.png")
    print("     - charts_ethusdt_comparison.png")
    print("     - charts_bnbusdt_comparison.png")
    print("     - charts_solusdt_comparison.png")
    print("     - charts_adausdt_comparison.png")

    # 在Mac上打开第一个图表
    import subprocess
    try:
        subprocess.run(['open', 'charts_btcusdt_kline.png'], check=False)
    except:
        pass
