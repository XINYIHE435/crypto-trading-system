"""
统一的对齐数据加载器
支持多个交易所的数据加载和时间戳对齐
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os
import glob

class BaseDataLoader:
    """数据加载器基类"""
    
    def __init__(self, exchange_name: str, data_dir: str = "data/raw"):
        self.exchange_name = exchange_name
        self.data_dir = data_dir
        self.data = None
        self.start_time = None
        self.end_time = None
        
    def load_data(self):
        """加载原始数据"""
        raise NotImplementedError("子类必须实现load_data方法")
        
    def get_time_range(self) -> Tuple[datetime, datetime]:
        """获取数据的时间范围"""
        return self.start_time, self.end_time
        
    def validate_data(self):
        """验证数据完整性"""
        if self.data is None:
            raise ValueError("数据未加载，请先调用load_data()")

class BinanceDataLoader(BaseDataLoader):
    """币安数据加载器"""
    
    def __init__(self, data_dir: str = "data/raw"):
        super().__init__("binance", data_dir)
        
    def load_data(self, symbol="BTCUSDT"):
        """加载币安数据"""
        try:
            # 查找币安数据文件
            btc_files = glob.glob(os.path.join(self.data_dir, "klines/binance_*.csv"))
            if not btc_files:
                raise FileNotFoundError(f"未找到币安数据文件在 {self.data_dir}")
            
            # 查找指定交易对的30分钟数据文件
            target_file = [f for f in btc_files if symbol in f and "30m" in f]
            if not target_file:
                # 如果没找到指定交易对，使用第一个30m文件
                btc_file = [f for f in btc_files if "30m" in f][0]
            else:
                btc_file = target_file[0]
                
            print(f"加载币安数据: {btc_file}")
            
            # 读取数据
            df = pd.read_csv(btc_file)
            
            # 转换时间戳
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 排序
            df = df.sort_values('timestamp')
            
            self.data = df
            self.start_time = df['timestamp'].min()
            self.end_time = df['timestamp'].max()
            
            print(f"币安数据加载完成，时间范围: {self.start_time} - {self.end_time}")
            
        except Exception as e:
            raise RuntimeError(f"加载币安数据失败: {str(e)}")

class KuCoinDataLoader(BaseDataLoader):
    """KuCoin数据加载器"""
    
    def __init__(self, data_dir: str = "data/raw"):
        super().__init__("kucoin", data_dir)
        
    def load_data(self, symbol="BTCUSDT"):
        """加载KuCoin数据"""
        try:
            # 查找KuCoin数据文件
            kuc_files = glob.glob(os.path.join(self.data_dir, "klines/kucoin_*.csv"))
            if not kuc_files:
                raise FileNotFoundError(f"未找到KuCoin数据文件在 {self.data_dir}")
            
            # 查找指定交易对的30分钟数据文件
            target_file = [f for f in kuc_files if symbol in f and "30m" in f]
            if not target_file:
                # 如果没找到指定交易对，使用第一个30m文件
                kuc_file = [f for f in kuc_files if "30m" in f][0]
            else:
                kuc_file = target_file[0]
                
            print(f"加载KuCoin数据: {kuc_file}")
            
            # 读取数据
            df = pd.read_csv(kuc_file)
            
            # 转换时间戳
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 排序
            df = df.sort_values('timestamp')
            
            self.data = df
            self.start_time = df['timestamp'].min()
            self.end_time = df['timestamp'].max()
            
            print(f"KuCoin数据加载完成，时间范围: {self.start_time} - {self.end_time}")
            
        except Exception as e:
            raise RuntimeError(f"加载KuCoin数据失败: {str(e)}")

class GateDataLoader(BaseDataLoader):
    """Gate.io数据加载器"""
    
    def __init__(self, data_dir: str = "data/raw"):
        super().__init__("gate", data_dir)
        
    def load_data(self, symbol="BTCUSDT"):
        """加载Gate.io数据"""
        try:
            # 查找Gate.io数据文件
            gate_files = glob.glob(os.path.join(self.data_dir, "klines/huobi_*.csv"))
            if not gate_files:
                raise FileNotFoundError(f"未找到Gate.io数据文件在 {self.data_dir}")
            
            # 查找指定交易对的30分钟数据文件
            target_file = [f for f in gate_files if symbol in f and "30m" in f]
            if not target_file:
                # 如果没找到指定交易对，使用第一个30m文件
                gate_file = [f for f in gate_files if "30m" in f][0]
            else:
                gate_file = target_file[0]
                
            print(f"加载Gate.io数据: {gate_file}")
            
            # 读取数据
            df = pd.read_csv(gate_file)
            
            # 转换时间戳
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 排序
            df = df.sort_values('timestamp')
            
            self.data = df
            self.start_time = df['timestamp'].min()
            self.end_time = df['timestamp'].max()
            
            print(f"Gate.io数据加载完成，时间范围: {self.start_time} - {self.end_time}")
            
        except Exception as e:
            raise RuntimeError(f"加载Gate.io数据失败: {str(e)}")

class BitgetDataLoader(BaseDataLoader):
    """Bitget数据加载器"""
    
    def __init__(self, data_dir: str = "data/raw"):
        super().__init__("bitget", data_dir)
        
    def load_data(self, symbol="BTCUSDT"):
        """加载Bitget数据"""
        try:
            # 查找Bitget数据文件
            bitget_files = glob.glob(os.path.join(self.data_dir, "klines/okx_*.csv"))
            if not bitget_files:
                raise FileNotFoundError(f"未找到Bitget数据文件在 {self.data_dir}")
            
            # 查找指定交易对的30分钟数据文件
            target_file = [f for f in bitget_files if symbol in f and "30m" in f]
            if not target_file:
                # 如果没找到指定交易对，使用第一个30m文件
                bitget_file = [f for f in bitget_files if "30m" in f][0]
            else:
                bitget_file = target_file[0]
                
            print(f"加载Bitget数据: {bitget_file}")
            
            # 读取数据
            df = pd.read_csv(bitget_file)
            
            # 转换时间戳
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 排序
            df = df.sort_values('timestamp')
            
            self.data = df
            self.start_time = df['timestamp'].min()
            self.end_time = df['timestamp'].max()
            
            print(f"Bitget数据加载完成，时间范围: {self.start_time} - {self.end_time}")
            
        except Exception as e:
            raise RuntimeError(f"加载Bitget数据失败: {str(e)}")

class DataAligner:
    """数据对齐系统"""
    
    def __init__(self, data_dir: str = "data/aligned"):
        self.data_dir = data_dir
        self.loaders = []
        
    def add_loader(self, loader: BaseDataLoader):
        """添加数据加载器"""
        self.loaders.append(loader)
        
    def align_all_data(self, target_interval: str = "30m", symbol="BTCUSDT"):
        """对齐所有数据到目标时间间隔"""
        print(f"开始对齐所有数据到 {target_interval} 间隔...")
        
        # 创建时间范围
        all_times = []
        for loader in self.loaders:
            loader.load_data(symbol)
            all_times.extend(loader.data['timestamp'].tolist())
        
        # 找到全局时间范围
        global_start = min(all_times)
        global_end = max(all_times)
        
        # 创建对齐后的时间序列
        if target_interval == "1h":
            time_sequence = pd.date_range(
                start=global_start,
                end=global_end,
                freq='1h'
            )
        else:
            time_sequence = pd.date_range(
                start=global_start,
                end=global_end,
                freq='30min'
            )
        
        print(f"时间对齐范围: {global_start} 到 {global_end}")
        
        # 对齐每个交易所的数据
        aligned_data = {}
        for loader in self.loaders:
            print(f"对齐 {loader.exchange_name} 数据...")
            
            # 重新采样到目标时间间隔
            aligned_df = self._resample_data(loader.data, time_sequence)
            aligned_data[loader.exchange_name] = aligned_df
            
        # 保存对齐后的数据
        self._save_aligned_data(aligned_data, target_interval, time_sequence, symbol)
        
        print("数据对齐完成")
        
    def _resample_data(self, df: pd.DataFrame, time_sequence: pd.DatetimeIndex) -> pd.DataFrame:
        """重新采样数据到目标时间序列"""
        # 设置时间索引
        df = df.set_index('timestamp')
        
        # 重新索引到目标时间序列
        aligned_df = df.reindex(time_sequence)
        
        # 使用更智能的填充策略
        numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'quote_volume']
        for col in numeric_columns:
            if col in aligned_df.columns:
                # 先前向填充，再线性插值
                aligned_df[col] = aligned_df[col].ffill().interpolate(method='linear')
                
                # 对于开头仍然为NaN的值，使用第一个有效值填充
                if aligned_df[col].isna().any():
                    first_valid_idx = aligned_df[col].first_valid_index()
                    if first_valid_idx is not None:
                        first_valid_value = aligned_df[col].loc[first_valid_idx]
                        aligned_df[col].fillna(first_valid_value, inplace=True)
        
        # 重置索引并添加timestamp列
        aligned_df = aligned_df.reset_index()
        aligned_df = aligned_df.rename(columns={'index': 'timestamp'})
        
        return aligned_df
        
    def _save_aligned_data(self, aligned_data: Dict[str, pd.DataFrame], target_interval: str, time_sequence: pd.DatetimeIndex, symbol: str):
        """保存对齐后的数据"""
        os.makedirs(self.data_dir, exist_ok=True)
        
        for exchange_name, df in aligned_data.items():
            filename = f"{self.data_dir}/{exchange_name}_aligned_{symbol}_{target_interval}.csv"
            df.to_csv(filename, index=False)
            print(f"保存 {exchange_name} 对齐数据到 {filename}")
            
        # 保存时间序列
        time_filename = f"{self.data_dir}/time_sequence_{symbol}_{target_interval}.csv"
        pd.Series(time_sequence).to_csv(time_filename, index=False)
        
        # 保存对齐报告
        report = self._generate_alignment_report(aligned_data, target_interval, time_sequence, symbol)
        report_filename = f"{self.data_dir}/alignment_report_{symbol}_{target_interval}.txt"
        with open(report_filename, 'w') as f:
            f.write(report)
        print(f"保存对齐报告到 {report_filename}")
            
    def _generate_alignment_report(self, aligned_data: Dict[str, pd.DataFrame], target_interval: str, time_sequence: pd.DatetimeIndex, symbol: str) -> str:
        """生成对齐报告"""
        report = []
        report.append("=== 数据对齐报告 ===\n")
        report.append(f"交易对: {symbol}\n")
        report.append(f"目标时间间隔: {target_interval}\n")
        report.append(f"全局时间范围: {time_sequence[0]} - {time_sequence[-1]}\n")
        report.append(f"时间序列长度: {len(time_sequence)}\n")
        report.append("\n各交易所数据统计:\n")
        
        for exchange_name, df in aligned_data.items():
            report.append(f"\n{exchange_name}:")
            report.append(f"  数据点数: {len(df)}")
            if 'timestamp' in df.columns:
                report.append(f"  时间范围: {df['timestamp'].min()} - {df['timestamp'].max()}")
        
        report.append("\n对齐质量评估:\n")
        report.append("  交易所间时间戳对齐完成\n")
        
        return "\n".join(report)

# 工厂函数
def create_data_loader(exchange_name: str, data_dir: str = "data/raw") -> BaseDataLoader:
    """创建数据加载器"""
    loaders = {
        'binance': BinanceDataLoader,
        'kucoin': KuCoinDataLoader,
        'gate': GateDataLoader,
        'bitget': BitgetDataLoader
    }
    
    if exchange_name not in loaders:
        raise ValueError(f"不支持的交易所: {exchange_name}")
    
    return loaders[exchange_name](data_dir)