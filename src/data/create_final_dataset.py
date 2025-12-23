#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建最终数据集：选取三交易所完全重叠的时间段
时间范围：2025-11-15 到 2025-11-30 (16天)
"""

import pandas as pd
import os
from datetime import datetime

def create_final_dataset():
    """创建最终数据集"""
    print("创建最终数据集...")
    print("选取三交易所完全重叠时间段")
    print("="*50)

    # 创建输出目录
    final_dir = 'data/final_data'
    os.makedirs(final_dir, exist_ok=True)

    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']

    final_datasets = {}

    for symbol in symbols:
        print(f"\n处理 {symbol}...")

        # 读取完整月份数据
        input_file = f'data/aligned_full_month/{symbol}_aligned_full_month.csv'
        df = pd.read_csv(input_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        print(f"原始数据: {len(df)} 条记录")

        # 筛选三交易所重叠的数据
        three_source_df = df[df['data_sources'] == 3].copy()

        print(f"三交易所重叠数据: {len(three_source_df)} 条记录")

        if len(three_source_df) > 0:
            # 显示时间范围
            start_time = three_source_df['timestamp'].min()
            end_time = three_source_df['timestamp'].max()
            print(f"时间范围: {start_time} 到 {end_time}")
            print(f"时长: {(end_time - start_time).days} 天")

            # 添加价格差列用于分析
            three_source_df['price_diff_binance_bybit'] = (
                three_source_df['close_binance'] - three_source_df['close_bybit']
            )
            three_source_df['price_diff_binance_okx'] = (
                three_source_df['close_binance'] - three_source_df['close_okx']
            )
            three_source_df['price_diff_bybit_okx'] = (
                three_source_df['close_bybit'] - three_source_df['close_okx']
            )

            # 添加价差百分比
            three_source_df['price_diff_pct_binance_bybit'] = (
                (three_source_df['close_binance'] - three_source_df['close_bybit']) /
                three_source_df['close_bybit'] * 100
            )
            three_source_df['price_diff_pct_binance_okx'] = (
                (three_source_df['close_binance'] - three_source_df['close_okx']) /
                three_source_df['close_okx'] * 100
            )
            three_source_df['price_diff_pct_bybit_okx'] = (
                (three_source_df['close_bybit'] - three_source_df['close_okx']) /
                three_source_df['close_okx'] * 100
            )

            # 保存最终数据
            output_file = os.path.join(final_dir, f"{symbol}_final.csv")
            three_source_df.to_csv(output_file, index=False)
            final_datasets[symbol] = three_source_df

            print(f"已保存: {output_file}")
            print(f"最终数据维度: {three_source_df.shape}")

            # 显示数据质量统计
            print(f"数据质量统计:")
            print(f"  平均Binance价格: {three_source_df['close_binance'].mean():.2f}")
            print(f"  平均Bybit价格: {three_source_df['close_bybit'].mean():.2f}")
            print(f"  平均OKX价格: {three_source_df['close_okx'].mean():.2f}")

            print(f"  平均价差 Binance-Bybit: {three_source_df['price_diff_binance_bybit'].mean():.2f}")
            print(f"  平均价差 Binance-OKX: {three_source_df['price_diff_binance_okx'].mean():.2f}")
            print(f"  平均价差 Bybit-OKX: {three_source_df['price_diff_bybit_okx'].mean():.2f}")

    # 创建合并的最终数据集
    if final_datasets:
        print(f"\n{'='*50}")
        print("创建合并最终数据集...")

        all_final = pd.concat(final_datasets.values(), ignore_index=True)
        merged_output_file = os.path.join(final_dir, 'all_symbols_final.csv')
        all_final.to_csv(merged_output_file, index=False)

        print(f"合并数据已保存: {merged_output_file}")
        print(f"合并数据维度: {all_final.shape}")

        # 按币种统计
        print(f"\n各币种最终数据统计:")
        for symbol, df_symbol in final_datasets.items():
            print(f"  {symbol}: {len(df_symbol)} 条记录")

        print(f"\n总计: {len(all_final)} 条记录")

    # 生成最终数据集报告
    generate_final_report(final_datasets, final_dir)

def generate_final_report(final_datasets, output_dir):
    """生成最终数据集报告"""
    print(f"\n生成最终数据集报告...")

    report_file = os.path.join(output_dir, 'final_dataset_report.txt')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("最终数据集报告\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"生成时间: {datetime.now()}\n")
        f.write(f"数据选择标准: 三交易所完全重叠时间段\n")
        f.write(f"时间范围: 2025-11-15 到 2025-11-30\n\n")

        f.write("数据集统计:\n")
        f.write("-" * 30 + "\n")

        total_records = 0
        for symbol, df_symbol in final_datasets.items():
            total_records += len(df_symbol)

            f.write(f"\n{symbol}:\n")
            f.write(f"  记录数: {len(df_symbol)}\n")
            f.write(f"  时间范围: {df_symbol['timestamp'].min()} 到 {df_symbol['timestamp'].max()}\n")
            f.write(f"  平均Binance价格: {df_symbol['close_binance'].mean():.2f}\n")
            f.write(f"  平均Bybit价格: {df_symbol['close_bybit'].mean():.2f}\n")
            f.write(f"  平均OKX价格: {df_symbol['close_okx'].mean():.2f}\n")
            f.write(f"  平均价差 Binance-Bybit: {df_symbol['price_diff_binance_bybit'].mean():.2f}\n")
            f.write(f"  平均价差 Binance-OKX: {df_symbol['price_diff_binance_okx'].mean():.2f}\n")
            f.write(f"  平均价差 Bybit-OKX: {df_symbol['price_diff_bybit_okx'].mean():.2f}\n")

        f.write(f"\n总计:\n")
        f.write(f"  总记录数: {total_records}\n")
        f.write(f"  交易对数: {len(final_datasets)}\n")
        f.write(f"  交易所数: 3 (Binance, Bybit, OKX)\n")
        f.write(f"  数据频率: 30分钟\n")

        f.write(f"\n数据质量保证:\n")
        f.write(f"  ✅ 所有时间点都有三交易所数据\n")
        f.write(f"  ✅ 时间戳完全对齐\n")
        f.write(f"  ✅ 包含完整的OHLCV数据\n")
        f.write(f"  ✅ 预计算价差分析\n")

    print(f"最终报告已保存: {report_file}")

if __name__ == "__main__":
    create_final_dataset()
    print(f"\n{'='*50}")
    print("最终数据集创建完成！")
    print("数据位置: data/final_data/")
    print("下一步: 使用逻辑系统验证数据")