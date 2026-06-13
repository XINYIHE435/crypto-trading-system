#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整数据下载和对齐脚本
下载 Binance 和 KuCoin 的 K线数据和资金费率数据，并进行对齐
"""

import pandas as pd
import requests
import time
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import warnings
warnings.filterwarnings('ignore')


class CompleteDataDownloader:
    """完整数据下载器"""
    
    def __init__(self):
        # 配置
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
        self.interval = '30m'
        self.days = 30  # 下载30天数据

        # 输出目录
        self.kline_dir = 'data/raw/klines'
        self.funding_dir = 'data/raw/funding_rates'
        self.aligned_dir = 'data/aligned'

        os.makedirs(self.kline_dir, exist_ok=True)
        os.makedirs(self.funding_dir, exist_ok=True)
        os.makedirs(self.aligned_dir, exist_ok=True)

        # 时间范围
        self.end_time = datetime.now()
        self.start_time = self.end_time - timedelta(days=self.days)

        print(f"数据下载时间范围: {self.start_time} 至 {self.end_time}")
        print(f"交易对: {self.symbols}")

    # ==================== Binance ====================
    
    def download_binance_klines(self, symbol: str) -> Optional[pd.DataFrame]:
        """下载 Binance K线数据"""
        print(f"  📥 下载 Binance {symbol} K线...")
        
        url = "https://fapi.binance.com/fapi/v1/klines"  # 使用合约API
        all_data = []
        
        start_ts = int(self.start_time.timestamp() * 1000)
        end_ts = int(self.end_time.timestamp() * 1000)
        current_start = start_ts
        
        while current_start < end_ts:
            params = {
                'symbol': symbol,
                'interval': self.interval,
                'startTime': current_start,
                'endTime': end_ts,
                'limit': 1500
            }
            
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if not data:
                    break
                
                all_data.extend(data)
                current_start = data[-1][0] + 1
                time.sleep(0.1)
                
            except Exception as e:
                print(f"    ❌ Binance K线下载错误: {e}")
                break
        
        if not all_data:
            return None
        
        df = pd.DataFrame(all_data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_volume',
            'taker_buy_quote_volume', 'ignore'
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume']]
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
        
        print(f"    ✅ 下载完成: {len(df)} 条")
        return df

    def download_binance_funding_rates(self, symbol: str) -> Optional[pd.DataFrame]:
        """下载 Binance 资金费率"""
        print(f"  📥 下载 Binance {symbol} 资金费率...")
        
        url = "https://fapi.binance.com/fapi/v1/fundingRate"
        all_data = []
        
        start_ts = int(self.start_time.timestamp() * 1000)
        end_ts = int(self.end_time.timestamp() * 1000)
        current_start = start_ts
        
        while current_start < end_ts:
            params = {
                'symbol': symbol,
                'startTime': current_start,
                'endTime': end_ts,
                'limit': 1000
            }
            
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if not data:
                    break
                
                all_data.extend(data)
                current_start = data[-1]['fundingTime'] + 1
                time.sleep(0.1)
                
            except Exception as e:
                print(f"    ❌ Binance 资金费率下载错误: {e}")
                break
        
        if not all_data:
            return None
        
        df = pd.DataFrame(all_data)
        df['timestamp'] = pd.to_datetime(df['fundingTime'], unit='ms')
        df['funding_rate'] = pd.to_numeric(df['fundingRate'], errors='coerce')
        df = df[['timestamp', 'funding_rate']]
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
        
        print(f"    ✅ 下载完成: {len(df)} 条")
        return df

    # ==================== KuCoin ====================
    
    def download_kucoin_klines(self, symbol: str) -> Optional[pd.DataFrame]:
        """下载 KuCoin K线数据"""
        print(f"  📥 下载 KuCoin {symbol} K线...")
        
        # KuCoin 合约符号格式
        kucoin_symbol = symbol.replace('USDT', 'USDTM')
        
        url = "https://api-futures.kucoin.com/api/v1/kline/query"
        all_data = []
        
        start_ts = int(self.start_time.timestamp() * 1000)
        end_ts = int(self.end_time.timestamp() * 1000)
        
        # KuCoin 需要分批下载
        batch_size = 200  # KuCoin 限制
        interval_ms = 30 * 60 * 1000  # 30分钟
        
        current_start = start_ts
        
        while current_start < end_ts:
            current_end = min(current_start + batch_size * interval_ms, end_ts)
            
            params = {
                'symbol': kucoin_symbol,
                'granularity': 30,  # 30分钟
                'from': current_start,
                'to': current_end
            }
            
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                result = response.json()
                
                if result.get('code') != '200000':
                    print(f"    ⚠️ KuCoin API 错误: {result.get('msg')}")
                    break
                
                data = result.get('data', [])
                if not data:
                    current_start = current_end
                    continue
                
                all_data.extend(data)
                current_start = current_end
                time.sleep(0.2)
                
            except Exception as e:
                print(f"    ❌ KuCoin K线下载错误: {e}")
                break
        
        if not all_data:
            return None
        
        # KuCoin 返回格式可能是: [timestamp, open, high, low, close, volume] 或 [timestamp, open, high, low, close, volume, turnover]
        # 动态处理列数
        df = pd.DataFrame(all_data)
        
        # 根据列数确定列名
        if len(df.columns) == 6:
            df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        elif len(df.columns) == 7:
            df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover']
            df = df.drop(columns=['turnover'])
        else:
            print(f"    ⚠️ KuCoin 返回意外的列数: {len(df.columns)}")
            # 取前6列
            df = df.iloc[:, :6]
            df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
        
        print(f"    ✅ 下载完成: {len(df)} 条")
        return df

    def download_kucoin_funding_rates(self, symbol: str) -> Optional[pd.DataFrame]:
        """下载 KuCoin 资金费率"""
        print(f"  📥 下载 KuCoin {symbol} 资金费率...")
        KUCOIN_SYMBOL_MAP = {
            "BTCUSDT": "XBTUSDTM",
            "ETHUSDT": "ETHUSDTM",
            "BNBUSDT": "BNBUSDTM",
            "SOLUSDT": "SOLUSDTM",
            "ADAUSDT": "ADAUSDTM"
        }
        kucoin_symbol = KUCOIN_SYMBOL_MAP.get(symbol)

        all_data = []

        # 尝试获取历史资金费率
        url = "https://api-futures.kucoin.com/api/v1/contract/funding-rates"

        start_ts = int(self.start_time.timestamp() * 1000)
        end_ts = int(self.end_time.timestamp() * 1000)

        params = {
            'symbol': kucoin_symbol,
            'from': start_ts,
            'to': end_ts
        }

        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 200:
                result = response.json()
                if result.get('code') == '200000':
                    data = result.get('data', {})
                    if isinstance(data, list):
                        all_data = data
                    elif isinstance(data, dict) and 'dataList' in data:
                        all_data = data['dataList']
                else:
                    print(f"    ⚠️ KuCoin API 返回错误: {result.get('msg', '未知错误')}")
        except Exception as e:
            print(f"    ⚠️ KuCoin 资金费率 API 失败: {e}")

        # 如果没有数据，直接返回 None
        if not all_data:
            print(f"    ⚠️ KuCoin 历史资金费率不可用，将使用 Bybit 作为后备")
            return None

        df = pd.DataFrame(all_data)

        # 打印可用的列名以便调试
        print(f"    📋 KuCoin 返回的列: {list(df.columns)}")

        # 动态处理列名 - 扩展更多可能的字段名
        timestamp_col = None
        for col in ['timePoint','timepoint', 'fundingTime', 'timestamp', 'time', 'fundingRateTimestamp']:
            if col in df.columns:
                timestamp_col = col
                break

        if timestamp_col is None:
            print(f"    ⚠️ 无法识别时间列，可用列: {list(df.columns)}")
            return None

        # 安全地转换时间戳
        try:
            df['timestamp'] = pd.to_datetime(pd.to_numeric(df[timestamp_col], errors='coerce'), unit='ms')
        except Exception as e:
            print(f"    ⚠️ 时间戳转换失败: {e}")
            return None

        # 处理资金费率列
        rate_col = None
        for col in ['fundingRate', 'rate', 'funding_rate']:
            if col in df.columns:
                rate_col = col
                break

        if rate_col is None:
            print(f"    ⚠️ 无法识别费率列，可用列: {list(df.columns)}")
            return None

        df['funding_rate'] = pd.to_numeric(df[rate_col], errors='coerce')

        df = df[['timestamp', 'funding_rate']]
        df = df.dropna(subset=['timestamp', 'funding_rate'])
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')

        print(f"    ✅ 下载完成: {len(df)} 条")
        return df

    # ==================== Bybit (备用) ====================
    
    def download_bybit_klines(self, symbol: str) -> Optional[pd.DataFrame]:
        """下载 Bybit K线数据"""
        print(f"  📥 下载 Bybit {symbol} K线...")
        
        url = "https://api.bybit.com/v5/market/kline"
        all_data = []
        
        start_ts = int(self.start_time.timestamp() * 1000)
        end_ts = int(self.end_time.timestamp() * 1000)
        current_end = end_ts
        
        while current_end > start_ts:
            params = {
                'category': 'linear',
                'symbol': symbol,
                'interval': '30',
                'end': current_end,
                'limit': 1000
            }
            
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                result = response.json()
                
                if result.get('retCode') != 0:
                    print(f"    ⚠️ Bybit API 错误: {result.get('retMsg')}")
                    break
                
                data = result.get('result', {}).get('list', [])
                print("timestamp=", data[-1][0])
                print(type(data[-1][0]))
                if not data:
                    break
                
                all_data.extend(data)
                
                # Bybit 返回降序数据，最后一条是最早的
                current_end = int(data[-1][0]) - 1
                time.sleep(0.1)
                
            except Exception as e:
                print(f"    ❌ Bybit K线下载错误: {e}")
                break
        
        if not all_data:
            return None
        
        # Bybit 返回格式: [startTime, open, high, low, close, volume, turnover]
        df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
        df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
        # print("timestamp range:", df['timestamp'].min(), df['timestamp'].max())
        abnormal = df[(df['timestamp'] < 1000000000000)|(df['timestamp'] > 2000000000000)]
        if len(abnormal):
            print("异常时间戳:")
            print(abnormal.head())
        df = df.dropna(subset=['timestamp'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')
        
        # 过滤时间范围
        df = df[(df['timestamp'] >= self.start_time) & (df['timestamp'] <= self.end_time)]
        
        print(f"    ✅ 下载完成: {len(df)} 条")
        return df
    
    def download_bybit_funding_rates(self, symbol: str) -> Optional[pd.DataFrame]:
        """下载 Bybit 资金费率（作为 KuCoin 的备用）"""
        print(f"  📥 下载 Bybit {symbol} 资金费率...")

        url = "https://api.bybit.com/v5/market/funding/history"
        all_data = []

        start_ts = int(self.start_time.timestamp() * 1000)
        end_ts = int(self.end_time.timestamp() * 1000)

        params = {
            'category': 'linear',
            'symbol': symbol,
            'startTime': start_ts,
            'endTime': end_ts,
            'limit': 200
        }

        cursor = None

        while True:
            if cursor:
                params['cursor'] = cursor

            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                result = response.json()

                if result.get('retCode') != 0:
                    print(f"    ⚠️ Bybit API 错误: {result.get('retMsg')}")
                    break

                data = result.get('result', {}).get('list', [])
                print("timestamp=", data[-1][0])
                print(type(data[-1][0]))
                if not data:
                    break

                all_data.extend(data)

                cursor = result.get('result', {}).get('nextPageCursor')
                if not cursor:
                    break

                time.sleep(0.2)

            except Exception as e:
                print(f"    ❌ {symbol} 下载失败: {e}")
                break

        if not all_data:
            return None

        df = pd.DataFrame(all_data)

        # 安全地转换时间戳 - 使用 pd.to_numeric 避免溢出
        try:
            df['timestamp'] = pd.to_datetime(
                pd.to_numeric(df['fundingRateTimestamp'], errors='coerce'),
                unit='ms',
                errors='coerce'
            )
        except Exception as e:
            print(f"    ⚠️ 时间戳转换失败: {e}")
            return None

        df['funding_rate'] = pd.to_numeric(df['fundingRate'], errors='coerce')
        df = df[['timestamp', 'funding_rate']]

        # 移除无效数据
        df = df.dropna(subset=['timestamp', 'funding_rate'])
        df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp')

        print(f"    ✅ 下载完成: {len(df)} 条")
        return df

    # ==================== 数据对齐 ====================
    
    def align_data(self, symbol: str, 
                   binance_klines: pd.DataFrame, 
                   kucoin_klines: pd.DataFrame,
                   binance_funding: pd.DataFrame,
                   kucoin_funding: pd.DataFrame) -> pd.DataFrame:
        """对齐数据"""
        print(f"  🔄 对齐 {symbol} 数据...")
        
        # 创建时间索引
        binance_klines = binance_klines.set_index('timestamp')
        kucoin_klines = kucoin_klines.set_index('timestamp')
        
        # 重命名列
        binance_klines.columns = [f'binance_{c}' for c in binance_klines.columns]
        kucoin_klines.columns = [f'kucoin_{c}' for c in kucoin_klines.columns]
        
        # 合并K线数据
        aligned = binance_klines.join(kucoin_klines, how='inner')
        
        # 处理资金费率 - 前向填充到每个K线
        if binance_funding is not None and not binance_funding.empty:
            binance_funding = binance_funding.set_index('timestamp')
            binance_funding.columns = ['binance_funding_rate']
            aligned = aligned.join(binance_funding, how='left')
            aligned['binance_funding_rate'] = aligned['binance_funding_rate'].ffill()
        else:
            aligned['binance_funding_rate'] = 0.0
        
        if kucoin_funding is not None and not kucoin_funding.empty:
            kucoin_funding = kucoin_funding.set_index('timestamp')
            kucoin_funding.columns = ['kucoin_funding_rate']
            aligned = aligned.join(kucoin_funding, how='left')
            aligned['kucoin_funding_rate'] = aligned['kucoin_funding_rate'].ffill()
        else:
            aligned['kucoin_funding_rate'] = 0.0
        
        # 填充缺失值
        aligned = aligned.ffill().bfill()
        
        # 计算价差
        aligned['spread_pct'] = (aligned['binance_close'] - aligned['kucoin_close']).abs() / \
                                aligned[['binance_close', 'kucoin_close']].min(axis=1) * 100
        
        # 计算资金费率差
        aligned['funding_spread'] = aligned['binance_funding_rate'] - aligned['kucoin_funding_rate']
        
        aligned = aligned.reset_index()
        aligned = aligned.rename(columns={'index': 'timestamp'})
        
        print(f"    ✅ 对齐完成: {len(aligned)} 条")
        return aligned

    # ==================== 主流程 ====================
    
    def download_symbol(self, symbol: str) -> bool:
        """下载单个交易对的所有数据"""
        print(f"\n{'='*60}")
        print(f"📊 下载 {symbol}")
        print(f"{'='*60}")
        
        # 下载 Binance 数据
        binance_klines = self.download_binance_klines(symbol)
        binance_funding = self.download_binance_funding_rates(symbol)
        
        if binance_klines is None:
            print(f"  ❌ Binance K线下载失败")
            return False
        
        # 保存 Binance 原始数据
        binance_klines.to_csv(f"{self.kline_dir}/binance_{symbol}_30m.csv", index=False)
        if binance_funding is not None:
            binance_funding.to_csv(f"{self.funding_dir}/binance_{symbol}_funding_rate.csv", index=False)
        
        # 下载 KuCoin 数据
        kucoin_klines = self.download_kucoin_klines(symbol)
        
        # 如果 KuCoin K线下载失败，使用 Bybit 作为第二交易所
        use_bybit = False
        if kucoin_klines is None or kucoin_klines.empty:
            print(f"  ⚠️ KuCoin K线不可用，尝试 Bybit...")
            kucoin_klines = self.download_bybit_klines(symbol)
            use_bybit = True
        
        if kucoin_klines is None:
            print(f"  ❌ 第二交易所 K线下载失败")
            return False
        
        # 下载资金费率
        kucoin_funding = self.download_kucoin_funding_rates(symbol)
        
        # 如果 KuCoin 资金费率下载失败，使用 Bybit
        if kucoin_funding is None or (hasattr(kucoin_funding, 'empty') and kucoin_funding.empty):
            print(f"  ⚠️ KuCoin 资金费率不可用，使用 Bybit...")
            kucoin_funding = self.download_bybit_funding_rates(symbol)
        
        # 保存第二交易所原始数据
        exchange_name = "bybit" if use_bybit else "kucoin"
        kucoin_klines.to_csv(f"{self.kline_dir}/{exchange_name}_{symbol}_30m.csv", index=False)
        if kucoin_funding is not None:
            kucoin_funding.to_csv(f"{self.funding_dir}/{exchange_name}_{symbol}_funding_rate.csv", index=False)
        
        # 对齐数据
        aligned = self.align_data(symbol, binance_klines, kucoin_klines, 
                                  binance_funding, kucoin_funding)
        
        # 保存对齐数据
        aligned_file = f"{self.aligned_dir}/{symbol}_30m_aligned.csv"
        aligned.to_csv(aligned_file, index=False)
        print(f"  💾 已保存: {aligned_file}")
        
        # 生成报告
        self.generate_report(symbol, aligned)
        
        return True

    def generate_report(self, symbol: str, df: pd.DataFrame):
        """生成数据报告"""
        report_file = f"{self.aligned_dir}/{symbol}_30m_report.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"数据报告: {symbol}\n")
            f.write(f"{'='*50}\n\n")
            f.write(f"时间范围: {df['timestamp'].iloc[0]} 至 {df['timestamp'].iloc[-1]}\n")
            f.write(f"数据点数: {len(df)}\n\n")
            
            f.write(f"Binance 价格:\n")
            f.write(f"  最高: {df['binance_close'].max():.2f}\n")
            f.write(f"  最低: {df['binance_close'].min():.2f}\n")
            f.write(f"  平均: {df['binance_close'].mean():.2f}\n\n")
            
            f.write(f"KuCoin 价格:\n")
            f.write(f"  最高: {df['kucoin_close'].max():.2f}\n")
            f.write(f"  最低: {df['kucoin_close'].min():.2f}\n")
            f.write(f"  平均: {df['kucoin_close'].mean():.2f}\n\n")
            
            f.write(f"价差统计:\n")
            f.write(f"  最大: {df['spread_pct'].max():.4f}%\n")
            f.write(f"  最小: {df['spread_pct'].min():.4f}%\n")
            f.write(f"  平均: {df['spread_pct'].mean():.4f}%\n\n")
            
            f.write(f"资金费率:\n")
            binance_fr_nonzero = (df['binance_funding_rate'] != 0).sum()
            kucoin_fr_nonzero = (df['kucoin_funding_rate'] != 0).sum()
            f.write(f"  Binance 非零数据: {binance_fr_nonzero}/{len(df)}\n")
            f.write(f"  KuCoin 非零数据: {kucoin_fr_nonzero}/{len(df)}\n")
            
        print(f"  📄 报告已保存: {report_file}")

    def download_all(self):
        """下载所有交易对数据"""
        print("=" * 60)
        print("开始下载所有数据")
        print("=" * 60)
        
        success_count = 0
        
        for symbol in self.symbols:
            try:
                if self.download_symbol(symbol):
                    success_count += 1
            except Exception as e:
                print(f"  ❌ {symbol} 下载失败: {e}")
        
        print("\n" + "=" * 60)
        print(f"下载完成: {success_count}/{len(self.symbols)} 成功")
        print("=" * 60)
        
        return success_count


def main():
    """主函数"""
    downloader = CompleteDataDownloader()
    downloader.download_all()
    
    # 验证数据
    print("\n" + "=" * 60)
    print("验证下载的数据")
    print("=" * 60)
    
    aligned_dir = 'data/aligned'
    for f in os.listdir(aligned_dir):
        if f.endswith('_aligned.csv'):
            filepath = os.path.join(aligned_dir, f)
            df = pd.read_csv(filepath)
            
            # 检查资金费率
            binance_fr = (df['binance_funding_rate'] != 0).sum()
            kucoin_fr = (df['kucoin_funding_rate'] != 0).sum()
            
            status = "✅" if binance_fr > 0 and kucoin_fr > 0 else "⚠️"
            print(f"{status} {f}: {len(df)}行, Binance费率:{binance_fr}, KuCoin费率:{kucoin_fr}")


if __name__ == "__main__":
    main()
