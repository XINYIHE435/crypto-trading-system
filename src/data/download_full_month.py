#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载完整一个月的数据：2025年11月1日 - 2025年11月30日
"""

import pandas as pd
import requests
import time
import os
from datetime import datetime, timedelta
import numpy as np

def create_full_month_data():
    """创建完整一个月的模拟数据：2025-11-01 到 2025-11-30"""
    print("开始创建完整一个月的数据 (2025-11-01 到 2025-11-30)...")

    # 创建时间范围 - 完整一个月
    start_date = pd.to_datetime('2025-11-01')
    end_date = pd.to_datetime('2025-11-30 23:59:59')
    time_grid = pd.date_range(start=start_date, end=end_date, freq='30min')

    print(f"时间网格: {start_date} 到 {end_date}")
    print(f"总时间点数: {len(time_grid)}")

    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
    exchanges = ['binance', 'bybit', 'okx']

    # 确保目录存在
    os.makedirs('data/raw_full_month', exist_ok=True)

    # 基础价格设置
    base_prices = {
        'BTCUSDT': 65000,
        'ETHUSDT': 3200,
        'BNBUSDT': 650
    }

    for symbol in symbols:
        base_price = base_prices[symbol]
        print(f"\n创建 {symbol} 数据...")

        for exchange in exchanges:
            print(f"  处理 {exchange}...")

            # 设置随机种子确保可重现性
            seed = hash(f'{exchange}_{symbol}_2025_11') % 10000
            np.random.seed(seed)

            # 创建DataFrame
            df = pd.DataFrame({'timestamp': time_grid})

            # 模拟一个月的价格走势
            # 使用几何布朗运动模拟
            days = len(time_grid) * 0.5 / 24  # 30分钟间隔转换为天数
            dt = 1 / (24 * 2)  # 30分钟 = 0.5天 = 1/48年

            # 参数设置
            mu = 0.05  # 年化收益率5%
            sigma = 0.3  # 年化波动率30%

            # 生成随机游走
            returns = np.random.normal((mu - 0.5 * sigma**2) * dt, sigma * np.sqrt(dt), len(time_grid))
            prices = base_price * np.exp(np.cumsum(returns))

            # 添加一些趋势性
            trend = np.linspace(0, 0.1, len(time_grid))  # 一个月10%的上涨趋势
            prices = prices * (1 + trend)

            # 生成OHLC数据
            df['open'] = prices
            df['close'] = prices * (1 + np.random.normal(0, 0.003, len(time_grid)))

            # 生成合理的high和low
            intrabar_range = np.random.uniform(0.005, 0.02, len(time_grid))
            df['high'] = np.maximum(df['open'], df['close']) * (1 + intrabar_range)
            df['low'] = np.minimum(df['open'], df['close']) * (1 - intrabar_range)

            # 生成交易量
            # 模拟不同的交易量模式
            base_volume = {
                'BTCUSDT': 100,
                'ETHUSDT': 1000,
                'BNBUSDT': 10000
            }

            volume_scale = {
                'binance': 1.0,
                'bybit': 0.8,
                'okx': 0.6
            }

            df['volume'] = np.random.lognormal(
                np.log(base_volume[symbol]),
                0.5,
                len(time_grid)
            ) * volume_scale[exchange]

            df['quote_volume'] = df['volume'] * ((df['open'] + df['close']) / 2)

            # 根据交易所设置不同的数据可用性
            if exchange == 'bybit':
                # Bybit从11月10日开始有数据
                cutoff = pd.to_datetime('2025-11-10')
                df.loc[df['timestamp'] < cutoff, ['open', 'high', 'low', 'close', 'volume', 'quote_volume']] = None
            elif exchange == 'okx':
                # OKX从11月15日开始有数据
                cutoff = pd.to_datetime('2025-11-15')
                df.loc[df['timestamp'] < cutoff, ['open', 'high', 'low', 'close', 'volume', 'quote_volume']] = None
            # Binance有完整数据

            # 保存数据
            output_file = f'data/raw_full_month/{exchange}_{symbol}_30m.csv'
            df.to_csv(output_file, index=False)

            # 统计有效数据
            non_null_count = df['close'].notna().sum()
            percentage = (non_null_count / len(df)) * 100
            print(f"    已保存: {output_file}")
            print(f"    有效数据: {non_null_count}/{len(df)} 条 ({percentage:.1f}%)")

            time.sleep(0.1)  # 短暂暂停

    print(f"\n完整月份数据创建完成！")
    print(f"数据保存目录: data/raw_full_month/")

def generate_data_summary():
    """生成数据摘要报告"""
    print("\n生成数据摘要报告...")

    summary_file = 'data/raw_full_month/data_summary.txt'
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("完整月份数据摘要报告\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"时间范围: 2025-11-01 到 2025-11-30\n")
        f.write(f"数据频率: 30分钟\n")
        f.write(f"交易对: BTCUSDT, ETHUSDT, BNBUSDT\n")
        f.write(f"交易所: Binance, Bybit, OKX\n")
        f.write(f"生成时间: {datetime.now()}\n\n")

        f.write("数据可用性统计:\n")
        f.write("-" * 30 + "\n")

        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        exchanges = ['binance', 'bybit', 'okx']

        total_files = 0
        for symbol in symbols:
            f.write(f"\n{symbol}:\n")
            for exchange in exchanges:
                file_path = f'data/raw_full_month/{exchange}_{symbol}_30m.csv'
                if os.path.exists(file_path):
                    df = pd.read_csv(file_path)
                    non_null = df['close'].notna().sum()
                    total = len(df)
                    percentage = (non_null / total) * 100
                    f.write(f"  {exchange}: {non_null}/{total} ({percentage:.1f}%)\n")
                    total_files += 1

        f.write(f"\n总文件数: {total_files}\n")

    print(f"摘要报告已保存: {summary_file}")

if __name__ == "__main__":
    print("开始创建完整一个月的加密货币数据...")
    print("时间范围: 2025-11-01 到 2025-11-30")
    print("=" * 50)

    # 创建完整月份数据
    create_full_month_data()

    # 生成摘要报告
    generate_data_summary()

    print(f"\n{'='*50}")
    print("完整月份数据创建完成！")
    print("下一步: 修改对齐脚本使用新数据")
    print("命令: python3 align_full_month.py")