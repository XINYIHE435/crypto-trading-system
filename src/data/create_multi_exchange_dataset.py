"""
创建多交易所合并数据集
将不同交易所的数据合并为统一格式，供套利系统使用
"""
import os
import pandas as pd
import numpy as np
from datetime import datetime
import glob
from .funding_rate_loader import FundingRateLoader

class MultiExchangeDatasetCreator:
    """多交易所数据集创建器"""
    
    def __init__(self, raw_data_dir="data/raw", output_dir="data/aligned"):
        self.raw_data_dir = raw_data_dir
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 初始化资金费率加载器
        self.funding_loader = FundingRateLoader()
        
    def load_aligned_data(self, timeframe="30m", symbol="BTCUSDT"):
        """加载对齐后的数据"""
        # 动态检测可用的交易所数据文件
        available_exchanges = []
        
        # 检查原始数据目录中的交易所文件
        pattern = os.path.join(self.raw_data_dir, "klines", f"*_{symbol}_{timeframe}.csv")
        available_files = glob.glob(pattern)
        
        for file_path in available_files:
            filename = os.path.basename(file_path)
            exchange = filename.split('_')[0]
            if exchange not in available_exchanges:
                available_exchanges.append(exchange)
        
        print(f"检测到的交易所: {available_exchanges}")
        
        data_frames = {}
        
        for exchange in available_exchanges:
            file_path = os.path.join(self.raw_data_dir, "klines", f"{exchange}_{symbol}_{timeframe}.csv")
            
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                data_frames[exchange] = df
                print(f"加载 {exchange} 数据: {len(df)} 行")
            else:
                print(f"警告: {exchange} 数据文件不存在: {file_path}")
                
        return data_frames
    
    def merge_exchange_data(self, data_frames, symbol="BTCUSDT", timeframe="30m"):
        """合并多交易所数据（使用最短时间序列对齐）"""
        if not data_frames:
            raise ValueError("没有可用的数据帧")
        
        # 计算时间窗口（根据timeframe）
        timeframe_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440
        }
        window_minutes = timeframe_minutes.get(timeframe, 30)
        
        # 按时间窗口对齐：将时间戳向下取整到最近的窗口边界
        def round_to_window(ts, minutes):
            """将时间戳向下取整到最近的窗口边界"""
            if isinstance(ts, pd.Timestamp):
                # 计算分钟数
                total_minutes = ts.hour * 60 + ts.minute
                rounded_minutes = (total_minutes // minutes) * minutes
                return ts.replace(hour=rounded_minutes // 60, minute=rounded_minutes % 60, second=0, microsecond=0)
            return ts
        
        # 先对齐每个交易所的时间戳
        aligned_data_frames = {}
        for exchange, df in data_frames.items():
            df_aligned = df.copy()
            df_aligned.index = [round_to_window(ts, window_minutes) for ts in df_aligned.index]
            # 如果有重复的时间戳，取最后一个（最新的数据）
            df_aligned = df_aligned.groupby(df_aligned.index).last()
            aligned_data_frames[exchange] = df_aligned
        
        # 获取所有交易所的时间戳交集（最短时间序列）
        common_timestamps = None
        for exchange, df in aligned_data_frames.items():
            exchange_timestamps = set(df.index)
            if common_timestamps is None:
                common_timestamps = exchange_timestamps
            else:
                common_timestamps = common_timestamps.intersection(exchange_timestamps)
        
        if not common_timestamps:
            raise ValueError("所有交易所没有共同的时间戳")
        
        common_timestamps = sorted(common_timestamps)
        print(f"对齐后时间戳数量（使用交集）: {len(common_timestamps)}")
        
        # 显示各交易所的时间范围
        print(f"共同时间范围: {common_timestamps[0]} 至 {common_timestamps[-1]}")
        
        # 创建合并后的数据框（只使用共同时间戳）
        merged_data = pd.DataFrame(index=common_timestamps)
        
        # 添加各交易所数据（只使用共同时间戳）
        for exchange, df in aligned_data_frames.items():
            # 只取共同时间戳的数据
            exchange_df = df.loc[common_timestamps].copy()
            
            # 重命名列以包含交易所名称
            for col in exchange_df.columns:
                if col not in ['timestamp']:
                    merged_data[f"{exchange}_{col}"] = exchange_df[col]
        
        # 动态计算价差
        exchanges = list(data_frames.keys())
        if len(exchanges) >= 2:
            # 以第一个交易所作为基准
            base_exchange = exchanges[0]
            base_close_col = f"{base_exchange}_close"
            
            for i in range(1, len(exchanges)):
                compare_exchange = exchanges[i]
                compare_close_col = f"{compare_exchange}_close"
                
                if base_close_col in merged_data.columns and compare_close_col in merged_data.columns:
                    # 创建价差列名
                    spread_name = f"price_spread_{base_exchange[:2]}{compare_exchange[:2]}"
                    relative_spread_name = f"relative_spread_{base_exchange[:2]}{compare_exchange[:2]}"
                    
                    # 计算绝对价差
                    merged_data[spread_name] = merged_data[base_close_col] - merged_data[compare_close_col]
                    
                    # 计算相对价差（百分比）
                    merged_data[relative_spread_name] = (merged_data[spread_name] / merged_data[base_close_col]) * 100
        
        # 添加资金费率数据
        merged_data = self.add_funding_rate_data(merged_data, symbol, exchanges)
        
        return merged_data
    
    def add_funding_rate_data(self, merged_data, symbol, exchanges):
        """添加资金费率数据到合并数据集"""
        print("🔄 添加资金费率数据...")
        
        for exchange in exchanges:
            funding_rate_col = f"{exchange}_funding_rate"
            
            # 为每个时间戳获取对应的资金费率
            funding_rates = []
            for timestamp in merged_data.index:
                rate = self.funding_loader.get_funding_rate(exchange.lower(), symbol, timestamp)
                funding_rates.append(rate if rate is not None else 0.0)
            
            merged_data[funding_rate_col] = funding_rates
            
            # 检查实际添加的数据
            non_zero_count = sum(1 for rate in funding_rates if rate != 0.0)
            if non_zero_count > 0:
                print(f"✅ 添加 {exchange} 资金费率数据 (非零数据点: {non_zero_count}/{len(funding_rates)})")
            else:
                print(f"⚠️ {exchange} 资金费率数据为空或时间范围不匹配")
        
        # 计算资金费率差异
        if len(exchanges) >= 2:
            for i in range(len(exchanges)):
                for j in range(i+1, len(exchanges)):
                    exchange1 = exchanges[i]
                    exchange2 = exchanges[j]
                    
                    rate1_col = f"{exchange1}_funding_rate"
                    rate2_col = f"{exchange2}_funding_rate"
                    
                    if rate1_col in merged_data.columns and rate2_col in merged_data.columns:
                        # 资金费率差异
                        funding_diff_name = f"funding_diff_{exchange1[:2]}{exchange2[:2]}"
                        merged_data[funding_diff_name] = merged_data[rate1_col] - merged_data[rate2_col]
                        
                        # 资金费率套利机会（8小时持仓的预期收益）
                        funding_arbitrage_name = f"funding_arbitrage_{exchange1[:2]}{exchange2[:2]}"
                        # 假设8小时持仓，计算资金费率差异带来的收益
                        merged_data[funding_arbitrage_name] = merged_data[funding_diff_name] * 8 * 3  # 8小时*每天3次
        
        return merged_data
    
    def create_dataset(self, symbols=["BTCUSDT", "ETHUSDT"], timeframes=["30m", "1h"]):
        """创建多交易所数据集"""
        for symbol in symbols:
            for timeframe in timeframes:
                print(f"\n创建 {symbol} {timeframe} 数据集...")
                
                try:
                    # 加载对齐数据
                    data_frames = self.load_aligned_data(timeframe, symbol)
                    
                    if not data_frames:
                        print(f"跳过 {symbol} {timeframe}: 没有可用数据")
                        continue
                    
                    # 合并数据
                    merged_data = self.merge_exchange_data(data_frames, symbol, timeframe)
                    
                    # 保存数据集
                    output_file = os.path.join(self.output_dir, f"{symbol}_{timeframe}_aligned.csv")
                    merged_data.to_csv(output_file)
                    print(f"保存数据集到: {output_file}")
                    
                    # 生成数据集报告
                    self.generate_dataset_report(merged_data, symbol, timeframe, output_file)
                    
                except Exception as e:
                    print(f"创建 {symbol} {timeframe} 数据集失败: {e}")
    
    def generate_dataset_report(self, data, symbol, timeframe, file_path):
        """生成数据集报告"""
        report = []
        report.append(f"=== {symbol} {timeframe} 数据集报告 ===\n")
        report.append(f"文件路径: {file_path}\n")
        report.append(f"数据行数: {len(data)}\n")
        report.append(f"时间范围: {data.index.min()} - {data.index.max()}\n")
        report.append(f"列数: {len(data.columns)}\n")
        
        # 动态检测交易所
        exchanges = set()
        for col in data.columns:
            if '_' in col and not col.startswith('price_spread_') and not col.startswith('relative_spread_'):
                exchange = col.split('_')[0]
                exchanges.add(exchange)
        
        report.append("\n包含的交易所数据列:\n")
        for exchange in sorted(exchanges):
            cols = [col for col in data.columns if col.startswith(f"{exchange}_")]
            if cols:
                report.append(f"  {exchange}: {', '.join(cols)}\n")
        
        report.append("\n价差统计:\n")
        spread_cols = [col for col in data.columns if 'price_spread' in col or 'relative_spread' in col]
        for col in spread_cols:
            if col in data.columns:
                mean_spread = data[col].mean()
                std_spread = data[col].std()
                max_spread = data[col].max()
                min_spread = data[col].min()
                report.append(f"  {col}:\n")
                report.append(f"    平均值: {mean_spread:.6f}\n")
                report.append(f"    标准差: {std_spread:.6f}\n")
                report.append(f"    最大值: {max_spread:.6f}\n")
                report.append(f"    最小值: {min_spread:.6f}\n")
        
        report.append("\n资金费率统计:\n")
        funding_cols = [col for col in data.columns if 'funding_rate' in col]
        for col in funding_cols:
            if col in data.columns and not 'diff' in col and not 'arbitrage' in col:
                mean_rate = data[col].mean()
                std_rate = data[col].std()
                max_rate = data[col].max()
                min_rate = data[col].min()
                non_zero_count = (data[col] != 0).sum()
                report.append(f"  {col}:\n")
                report.append(f"    平均费率: {mean_rate:.6f}\n")
                report.append(f"    标准差: {std_rate:.6f}\n")
                report.append(f"    最大费率: {max_rate:.6f}\n")
                report.append(f"    最小费率: {min_rate:.6f}\n")
                report.append(f"    非零数据点: {non_zero_count}/{len(data)}\n")
        
        report.append("\n资金费率套利机会:\n")
        funding_arbitrage_cols = [col for col in data.columns if 'funding_arbitrage' in col]
        for col in funding_arbitrage_cols:
            if col in data.columns:
                mean_arbitrage = data[col].mean()
                std_arbitrage = data[col].std()
                max_arbitrage = data[col].max()
                min_arbitrage = data[col].min()
                positive_count = (data[col] > 0).sum()
                report.append(f"  {col}:\n")
                report.append(f"    平均套利收益: {mean_arbitrage:.6f}\n")
                report.append(f"    标准差: {std_arbitrage:.6f}\n")
                report.append(f"    最大收益: {max_arbitrage:.6f}\n")
                report.append(f"    最小收益: {min_arbitrage:.6f}\n")
                report.append(f"    正收益机会: {positive_count}/{len(data)} ({positive_count/len(data)*100:.1f}%)\n")
        
        # 保存报告
        report_file = os.path.join(self.output_dir, f"{symbol}_{timeframe}_report.txt")
        with open(report_file, 'w') as f:
            f.write(''.join(report))
        
        print(f"数据集报告保存到: {report_file}")

def main():
    """主函数"""
    print("开始创建多交易所合并数据集...")
    
    creator = MultiExchangeDatasetCreator()
    
    # 创建数据集
    symbols = ["BTCUSDT", "ETHUSDT"]
    timeframes = ["30m", "1h"]
    
    creator.create_dataset(symbols, timeframes)
    
    print("\n多交易所数据集创建完成！")
    print("数据文件保存在 data/aligned/ 目录下")

if __name__ == "__main__":
    main()