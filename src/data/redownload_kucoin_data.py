#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新下载KuCoin数据以修复数据格式问题
"""

import pandas as pd
import requests
import time
import os
from datetime import datetime
import json

class KuCoinDataDownloader:
    def __init__(self):
        # 配置参数
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
        self.interval = '30m'
        self.start_date = '2025-11-01'
        self.end_date = '2025-11-30'
        
        # 创建输出目录
        self.kline_dir = 'data/raw/klines'
        os.makedirs(self.kline_dir, exist_ok=True)

    def get_kucoin_klines(self, symbol: str, interval: str, start_time: int, end_time: int):
        """下载KuCoin K线数据（修复版本）"""
        print(f"下载KuCoin {symbol} K线数据...")

        # KuCoin时间间隔
        interval_map = {
            '30m': '30min', '1h': '1hour', '1m': '1min', '5m': '5min', '15m': '15min'
        }
        kucoin_interval = interval_map.get(interval, interval)

        # KuCoin需要先获取symbol信息
        symbol_url = f"https://api.kucoin.com/api/v1/symbols"
        try:
            symbol_response = requests.get(symbol_url, timeout=30)
            symbol_response.raise_for_status()
            symbol_data = symbol_response.json()
            
            # 查找正确的symbol格式
            kucoin_symbol = None
            for s in symbol_data.get('data', []):
                if s.get('symbol') == symbol or s.get('symbol') == f"{symbol[:3]}-{symbol[3:]}":
                    kucoin_symbol = s['symbol']
                    break
            
            if not kucoin_symbol:
                # 尝试常见格式
                kucoin_symbol = f"{symbol[:3]}-{symbol[3:]}"
                
        except Exception as e:
            print(f"KuCoin symbol查询失败: {e}")
            kucoin_symbol = f"{symbol[:3]}-{symbol[3:]}"

        url = f"https://api.kucoin.com/api/v1/market/candles"
        params = {
            'symbol': kucoin_symbol,
            'type': kucoin_interval,
            'startAt': str(int(start_time / 1000)),
            'endAt': str(int(end_time / 1000))
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not data.get('data'):
                return None

            klines = data['data']
            df = pd.DataFrame(klines)

            # KuCoin返回的数据顺序是：timestamp, open, high, low, close, volume, quote_volume
            df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume']

            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='s')
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume']]
            df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']] = df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']].astype(float)
            df = df.sort_values('timestamp').reset_index(drop=True)

            return df

        except Exception as e:
            print(f"KuCoin K线数据下载失败: {e}")
            return None

    def download_kucoin_data(self):
        """下载所有KuCoin数据"""
        print("\n" + "="*60)
        print("开始重新下载KuCoin数据（修复版本）")
        print("="*60)

        start_ts = int(pd.to_datetime(self.start_date).timestamp() * 1000)
        end_ts = int(pd.to_datetime(self.end_date).timestamp() * 1000)

        results = {}

        for symbol in self.symbols:
            print(f"\n{'='*50}")
            print(f"下载 KuCoin {symbol} K线数据")
            print(f"{'='*50}")

            df = self.get_kucoin_klines(symbol, self.interval, start_ts, end_ts)

            if df is not None and len(df) > 0:
                filename = f"kucoin_{symbol}_{self.interval}.csv"
                filepath = os.path.join(self.kline_dir, filename)
                df.to_csv(filepath, index=False)

                results[symbol] = {
                    'file': filepath,
                    'count': len(df),
                    'start': df['timestamp'].min(),
                    'end': df['timestamp'].max()
                }

                print(f"✅ KuCoin {symbol} 成功: {len(df)} 条记录")
                
                # 显示前几行数据以验证格式
                print(f"前5行数据预览:")
                print(df.head().to_string(index=False))
                
            else:
                print(f"❌ KuCoin {symbol} 失败")

            time.sleep(0.5)  # 避免API限制

        return results

def main():
    """主函数"""
    downloader = KuCoinDataDownloader()

    try:
        results = downloader.download_kucoin_data()
        print(f"\n🎯 KuCoin数据重新下载完成！")

        # 验证数据格式
        print(f"\n📊 数据验证:")
        for symbol, info in results.items():
            print(f"\n{symbol}:")
            print(f"  文件: {info['file']}")
            print(f"  记录数: {info['count']}")
            print(f"  时间范围: {info['start']} 到 {info['end']}")
            
            # 读取文件验证格式
            df = pd.read_csv(info['file'])
            print(f"  列名: {list(df.columns)}")
            print(f"  数据类型: {df.dtypes.to_dict()}")

    except KeyboardInterrupt:
        print(f"\n⚠️ 下载被用户中断")
    except Exception as e:
        print(f"\n❌ 下载过程中出现错误: {e}")

if __name__ == "__main__":
    main()