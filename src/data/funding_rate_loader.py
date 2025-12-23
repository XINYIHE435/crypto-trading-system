#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资金费率数据加载器
用于加载和管理各交易所的资金费率数据
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import glob

class FundingRateLoader:
    """资金费率数据加载器"""
    
    def __init__(self, funding_rate_dir="data/raw/funding_rates"):
        self.funding_rate_dir = funding_rate_dir
        self.funding_data = {}
        self.load_all_funding_rates()
    
    def load_all_funding_rates(self):
        """加载所有交易所的资金费率数据"""
        print("🔄 加载资金费率数据...")
        
        # 获取所有资金费率文件
        funding_files = glob.glob(os.path.join(self.funding_rate_dir, "*_funding_rate.csv"))
        
        for file_path in funding_files:
            filename = os.path.basename(file_path)
            parts = filename.replace('_funding_rate.csv', '').split('_')
            
            if len(parts) >= 2:
                exchange = parts[0]
                symbol = parts[1]
                
                try:
                    df = pd.read_csv(file_path)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.sort_values('timestamp')
                    
                    if exchange not in self.funding_data:
                        self.funding_data[exchange] = {}
                    
                    self.funding_data[exchange][symbol] = df
                    print(f"✅ 加载 {exchange} {symbol} 资金费率数据: {len(df)} 条记录")
                    
                except Exception as e:
                    print(f"❌ 加载 {exchange} {symbol} 资金费率数据失败: {e}")
        
        print(f"📊 总共加载 {len(self.funding_data)} 个交易所的资金费率数据")
    
    def get_funding_rate(self, exchange: str, symbol: str, timestamp: datetime) -> Optional[float]:
        """获取指定时间的资金费率"""
        if exchange not in self.funding_data:
            return None
        
        if symbol not in self.funding_data[exchange]:
            return None
        
        df = self.funding_data[exchange][symbol]
        
        # 找到最接近的资金费率
        df_before = df[df['timestamp'] <= timestamp]
        if len(df_before) == 0:
            return None
        
        # 获取最新的资金费率
        latest_rate = df_before.iloc[-1]['funding_rate']
        return latest_rate
    
    def get_funding_rate_history(self, exchange: str, symbol: str, 
                              start_time: datetime, end_time: datetime) -> Optional[pd.DataFrame]:
        """获取指定时间范围的资金费率历史"""
        if exchange not in self.funding_data:
            return None
        
        if symbol not in self.funding_data[exchange]:
            return None
        
        df = self.funding_data[exchange][symbol]
        
        # 筛选时间范围
        mask = (df['timestamp'] >= start_time) & (df['timestamp'] <= end_time)
        return df[mask]
    
    def calculate_funding_cost(self, exchange: str, symbol: str, 
                           position_size: float, 
                           start_time: datetime, 
                           end_time: datetime) -> float:
        """计算资金费用"""
        funding_rates = self.get_funding_rate_history(exchange, symbol, start_time, end_time)
        
        if funding_rates is None or len(funding_rates) == 0:
            return 0.0
        
        total_cost = 0.0
        
        for _, row in funding_rates.iterrows():
            # 计算这个资金费率周期的持续时间（通常是8小时）
            next_timestamp = row['timestamp'] + timedelta(hours=8)
            
            # 如果下一个时间超出了持仓时间，只计算到持仓结束
            if next_timestamp > end_time:
                next_timestamp = end_time
            
            # 计算这个周期的持续时间（小时）
            duration_hours = (next_timestamp - row['timestamp']).total_seconds() / 3600
            
            # 资金费用 = 仓位大小 * 资金费率 * 持续时间 / 24
            cost = position_size * row['funding_rate'] * duration_hours / 24
            total_cost += cost
            
            if next_timestamp >= end_time:
                break
        
        return total_cost
    
    def get_available_exchanges(self) -> List[str]:
        """获取有资金费率数据的交易所列表"""
        return list(self.funding_data.keys())
    
    def get_available_symbols(self, exchange: str) -> List[str]:
        """获取指定交易所的交易对列表"""
        if exchange not in self.funding_data:
            return []
        return list(self.funding_data[exchange].keys())
    
    def get_latest_funding_rates(self) -> Dict[str, Dict[str, float]]:
        """获取所有交易所最新的资金费率"""
        latest_rates = {}
        
        for exchange, symbols in self.funding_data.items():
            latest_rates[exchange] = {}
            
            for symbol, df in symbols.items():
                if len(df) > 0:
                    latest_rate = df.iloc[-1]['funding_rate']
                    latest_rates[exchange][symbol] = latest_rate
        
        return latest_rates
    
    def print_funding_rate_summary(self):
        """打印资金费率数据摘要"""
        print("\n" + "="*60)
        print("📊 资金费率数据摘要")
        print("="*60)
        
        for exchange, symbols in self.funding_data.items():
            print(f"\n🏦 {exchange.upper()} 交易所:")
            
            for symbol, df in symbols.items():
                if len(df) > 0:
                    latest_rate = df.iloc[-1]['funding_rate']
                    time_range = f"{df['timestamp'].min()} - {df['timestamp'].max()}"
                    avg_rate = df['funding_rate'].mean()
                    
                    print(f"  {symbol}:")
                    print(f"    最新费率: {latest_rate:.6f}")
                    print(f"    平均费率: {avg_rate:.6f}")
                    print(f"    数据范围: {time_range}")
                    print(f"    记录数量: {len(df)}")
        
        print(f"\n📈 总计: {len(self.funding_data)} 个交易所")
        total_symbols = sum(len(symbols) for symbols in self.funding_data.values())
        print(f"📊 总交易对: {total_symbols} 个")

# 测试代码
if __name__ == "__main__":
    loader = FundingRateLoader()
    loader.print_funding_rate_summary()
    
    # 测试获取资金费率
    test_time = datetime(2025, 11, 25, 12, 0, 0)
    rate = loader.get_funding_rate('binance', 'BTCUSDT', test_time)
    print(f"\n🧪 测试: Binance BTCUSDT 在 {test_time} 的资金费率: {rate}")
    
    # 测试计算资金费用
    start_time = datetime(2025, 11, 24, 0, 0, 0)
    end_time = datetime(2025, 11, 26, 0, 0, 0)
    cost = loader.calculate_funding_cost('binance', 'BTCUSDT', 1000, start_time, end_time)
    print(f"🧪 测试: 1000 USDT 持仓2天的资金费用: {cost:.6f} USDT")