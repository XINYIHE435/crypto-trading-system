#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对齐完整一个月的数据：2025-11-01 到 2025-11-30
"""

import pandas as pd
import os
import glob
from datetime import datetime, timedelta

def read_csv_file(file_path):
    """读取CSV文件并提取交易所和币种信息"""
    df = pd.read_csv(file_path)

    # 从文件名提取交易所和币种信息
    filename = os.path.basename(file_path)
    parts = filename.replace('.csv', '').split('_')
    exchange = parts[0]
    symbol = parts[1]

    # 添加交易所和币种列
    df['exchange'] = exchange
    df['symbol'] = symbol

    # 转换时间戳
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    return df

def create_time_grid_for_symbol(symbol_data, freq='30min'):
    """为特定币种创建时间网格"""
    all_timestamps = []
    for df in symbol_data:
        all_timestamps.extend(df['timestamp'].tolist())

    if not all_timestamps:
        return None

    start_time = min(all_timestamps)
    end_time = max(all_timestamps)

    # 创建30分钟时间网格
    time_grid = pd.date_range(start=start_time, end=end_time, freq=freq)
    return time_grid

def align_symbol_data(symbol, symbol_data_list):
    """对齐单个币种的数据"""
    print(f"\n开始对齐 {symbol} 数据...")

    # 创建时间网格
    time_grid = create_time_grid_for_symbol(symbol_data_list)
    if time_grid is None:
        print(f"警告: {symbol} 没有数据")
        return None

    print(f"时间网格: {time_grid[0]} 到 {time_grid[-1]} ({len(time_grid)} 个时间点)")

    # 创建完整的时间序列DataFrame
    symbol_aligned = pd.DataFrame({'timestamp': time_grid})

    # 为每个交易所的数据列创建占位符
    exchanges = [df['exchange'].iloc[0] for df in symbol_data_list]
    price_columns = ['open', 'high', 'low', 'close', 'volume', 'quote_volume']

    for exchange in exchanges:
        for col in price_columns:
            symbol_aligned[f"{col}_{exchange}"] = None

    # 填充实际数据
    for df in symbol_data_list:
        exchange = df['exchange'].iloc[0]
        print(f"  处理 {exchange} 数据: {len(df)} 条记录")

        # 按时间戳合并数据
        for _, row in df.iterrows():
            timestamp = row['timestamp']

            # 找到时间网格中最接近的时间点
            if timestamp in time_grid:
                idx = symbol_aligned[symbol_aligned['timestamp'] == timestamp].index[0]

                # 填充价格数据
                for col in price_columns:
                    if col in row and pd.notna(row[col]):
                        symbol_aligned.at[idx, f"{col}_{exchange}"] = row[col]

    # 添加币种标识
    symbol_aligned['symbol'] = symbol

    # 计算数据完整性统计
    data_completeness = {}
    for exchange in exchanges:
        non_null_count = symbol_aligned[f"close_{exchange}"].notna().sum()
        total_count = len(symbol_aligned)
        completeness = (non_null_count / total_count) * 100 if total_count > 0 else 0
        data_completeness[exchange] = {
            'non_null_count': non_null_count,
            'total_count': total_count,
            'completeness_percent': completeness
        }
        print(f"  {exchange}: {non_null_count}/{total_count} 数据点 ({completeness:.1f}% 覆盖率)")

    # 计算每个时间点的数据源数量
    close_columns = [f"close_{exchange}" for exchange in exchanges]
    symbol_aligned['data_sources'] = symbol_aligned[close_columns].notna().sum(axis=1)

    # 找出多数据源的时间点
    multi_source_count = (symbol_aligned['data_sources'] >= 2).sum()
    three_source_count = (symbol_aligned['data_sources'] == 3).sum()
    print(f"  多数据源时间点: {multi_source_count}/{len(symbol_aligned)}")
    print(f"  三交易所重叠时间点: {three_source_count}/{len(symbol_aligned)}")

    return symbol_aligned, data_completeness

def main():
    """主函数：处理完整一个月数据并按币种对齐"""
    print("开始对齐完整一个月数据...")
    print("时间范围: 2025-11-01 到 2025-11-30")
    print("=" * 50)

    # 确保输入目录存在
    raw_dir = 'data/raw_full_month'
    if not os.path.exists(raw_dir):
        print(f"错误: 找不到原始数据目录 {raw_dir}")
        print("请先运行: python3 download_full_month.py")
        return

    # 创建输出目录
    aligned_dir = 'data/aligned_full_month'
    os.makedirs(aligned_dir, exist_ok=True)

    # 获取所有CSV文件
    csv_files = glob.glob(os.path.join(raw_dir, '*.csv'))
    if not csv_files:
        print(f"错误: 在 {raw_dir} 中没有找到CSV文件")
        return

    print(f"找到 {len(csv_files)} 个数据文件")

    # 读取所有数据
    all_data = {}
    for file_path in csv_files:
        print(f"读取文件: {file_path}")
        df = read_csv_file(file_path)
        symbol = df['symbol'].iloc[0]
        exchange = df['exchange'].iloc[0]

        if symbol not in all_data:
            all_data[symbol] = []
        all_data[symbol].append(df)

    # 按币种对齐数据
    aligned_results = {}
    summary_stats = {}

    for symbol, symbol_data_list in all_data.items():
        print(f"\n{'='*50}")
        print(f"处理币种: {symbol}")
        print(f"{'='*50}")

        result = align_symbol_data(symbol, symbol_data_list)
        if result is not None:
            aligned_data, completeness_stats = result
            aligned_results[symbol] = aligned_data
            summary_stats[symbol] = completeness_stats

            # 保存对齐后的数据
            output_file = os.path.join(aligned_dir, f"{symbol}_aligned_full_month.csv")
            aligned_data.to_csv(output_file, index=False)
            print(f"已保存: {output_file}")
            print(f"数据维度: {aligned_data.shape}")

    # 生成汇总报告
    print(f"\n{'='*50}")
    print("完整月份数据对齐汇总报告")
    print(f"{'='*50}")

    total_aligned_files = 0
    total_records = 0
    total_three_source = 0

    for symbol, stats in summary_stats.items():
        print(f"\n{symbol}:")
        for exchange, stat in stats.items():
            print(f"  {exchange}: {stat['non_null_count']} 数据点 ({stat['completeness_percent']:.1f}% 覆盖率)")

        if symbol in aligned_results:
            df = aligned_results[symbol]
            multi_source = (df['data_sources'] >= 2).sum()
            three_source = (df['data_sources'] == 3).sum()
            print(f"  多数据源时间点: {multi_source}/{len(df)} ({(multi_source/len(df))*100:.1f}%)")
            print(f"  三交易所重叠时间点: {three_source}/{len(df)} ({(three_source/len(df))*100:.1f}%)")

            total_aligned_files += 1
            total_records += len(df)
            total_three_source += three_source

    print(f"\n总计:")
    print(f"  对齐币种数: {total_aligned_files}")
    print(f"  总时间点数: {total_records}")
    print(f"  总三交易所重叠时间点: {total_three_source}")

    # 创建汇总表格
    if aligned_results:
        # 合并所有币种的对齐数据
        all_aligned = pd.concat(aligned_results.values(), ignore_index=True)
        summary_file = os.path.join(aligned_dir, 'all_symbols_aligned_full_month.csv')
        all_aligned.to_csv(summary_file, index=False)
        print(f"\n所有币种合并数据已保存: {summary_file}")
        print(f"合并数据维度: {all_aligned.shape}")

        # 生成详细的重叠分析
        generate_overlap_analysis(aligned_results, aligned_dir)

    # 生成详细报告
    report_file = os.path.join(aligned_dir, 'full_month_alignment_report.txt')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("完整月份数据对齐报告\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"处理时间: {datetime.now()}\n")
        f.write(f"时间范围: 2025-11-01 到 2025-11-30\n")
        f.write(f"原始文件数: {len(csv_files)}\n")
        f.write(f"处理币种数: {total_aligned_files}\n")
        f.write(f"总时间点数: {total_records}\n")
        f.write(f"总三交易所重叠时间点: {total_three_source}\n\n")

        for symbol, stats in summary_stats.items():
            f.write(f"{symbol}:\n")
            for exchange, stat in stats.items():
                f.write(f"  {exchange}: {stat['non_null_count']}/{stat['total_count']} ({stat['completeness_percent']:.1f}%)\n")
            f.write("\n")

    print(f"\n详细报告已保存: {report_file}")
    print(f"\n完整月份数据对齐完成！结果保存在 {aligned_dir} 目录中")

def generate_overlap_analysis(aligned_results, output_dir):
    """生成重叠数据详细分析"""
    print(f"\n生成重叠数据详细分析...")

    overlap_analysis = []

    for symbol, df in aligned_results.items():
        # 找出三交易所重叠的时间点
        three_source_data = df[df['data_sources'] == 3].copy()

        if len(three_source_data) > 0:
            three_source_data['symbol'] = symbol
            overlap_analysis.append(three_source_data)

    if overlap_analysis:
        # 合并所有三交易所重叠数据
        all_overlap = pd.concat(overlap_analysis, ignore_index=True)
        overlap_file = os.path.join(output_dir, 'three_exchange_overlap_data.csv')
        all_overlap.to_csv(overlap_file, index=False)
        print(f"三交易所重叠数据已保存: {overlap_file}")
        print(f"重叠数据维度: {all_overlap.shape}")

        # 按时间范围分析
        print(f"\n重叠时间段分析:")
        for symbol, df in aligned_results.items():
            three_source = df[df['data_sources'] == 3]
            if len(three_source) > 0:
                start_time = three_source['timestamp'].min()
                end_time = three_source['timestamp'].max()
                print(f"{symbol}: {len(three_source)} 个重叠时间点")
                print(f"  时间范围: {start_time} 到 {end_time}")

if __name__ == "__main__":
    main()