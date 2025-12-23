#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一时间范围数据下载脚本
确保所有交易所下载相同时间范围的数据，实现完美对齐
"""

import pandas as pd
import requests
import time
import os
from datetime import datetime, timedelta
import json

class UnifiedDataDownloader:
    def __init__(self):
        # 配置参数
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        self.interval = '30m'
        self.start_date = '2025-11-01'  # 统一开始时间
        self.end_date = '2025-11-30'    # 统一结束时间
        self.output_dir = 'data/raw_unified'

        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)

    def get_binance_klines(self, symbol, interval, start_time, end_time):
        """下载Binance数据"""
        print(f"下载Binance {symbol} 数据...")

        url = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': start_time,
            'endTime': end_time,
            'limit': 1000
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # 转换为DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_volume',
                'taker_buy_quote_volume', 'ignore'
            ])

            # 数据清洗
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume']]
            df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']] = df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']].astype(float)

            return df

        except Exception as e:
            print(f"Binance数据下载失败: {e}")
            return None

    def get_bybit_klines(self, symbol, interval, start_time, end_time):
        """下载Bybit数据"""
        print(f"下载Bybit {symbol} 数据...")

        url = "https://api.bybit.com/v5/market/kline"
        params = {
            'category': 'spot',
            'symbol': symbol,
            'interval': interval,
            'start': int(pd.to_datetime(start_time).timestamp() * 1000),
            'end': int(pd.to_datetime(end_time).timestamp() * 1000),
            'limit': 1000
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            print(f"Bybit API响应: {data}")  # 调试信息

            if data['retCode'] != 0:
                print(f"Bybit API错误: {data['retMsg']}")
                return None

            klines = data['result']['list']
            if not klines:
                print("Bybit返回空数据")
                return None

            # 转换为DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
            ])

            # 数据清洗
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover']]
            df[['open', 'high', 'low', 'close', 'volume', 'turnover']] = df[['open', 'high', 'low', 'close', 'volume', 'turnover']].astype(float)
            df.rename(columns={'turnover': 'quote_volume'}, inplace=True)

            return df

        except Exception as e:
            print(f"Bybit数据下载失败: {e}")
            return None

    def get_okx_klines(self, symbol, interval, start_time, end_time):
        """下载OKX数据"""
        print(f"下载OKX {symbol} 数据...")

        # OKX现货市场的交易对格式
        okx_symbol = f"{symbol[:3]}-{symbol[3:]}" if len(symbol) > 6 else symbol

        url = "https://www.okx.com/api/v5/market/history-candles"
        params = {
            'instId': okx_symbol,
            'bar': interval,
            'before': str(int(pd.to_datetime(end_date).timestamp() * 1000)) if 'end_date' in locals() else str(int(pd.to_datetime('2025-11-30').timestamp() * 1000)),
            'after': str(int(pd.to_datetime('2025-11-01').timestamp() * 1000)),
            'limit': '300'
        }

        try:
            print(f"OKX请求参数: {params}")  # 调试信息
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            print(f"OKX API响应: {data}")  # 调试信息

            if data['code'] != '0':
                print(f"OKX API错误: {data['msg']}")
                return None

            klines = data['data']
            if not klines:
                print("OKX返回空数据")
                return None

            # 转换为DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume', 'currency_volume', 'currency_quote_volume'
            ])

            # 数据清洗
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume']]
            df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']] = df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']].astype(float)

            return df

        except Exception as e:
            print(f"OKX数据下载失败: {e}")
            return None

    def download_all_data(self):
        """下载所有交易所的统一时间范围数据"""
        print("开始统一时间范围数据下载...")
        print(f"时间范围: {self.start_date} 到 {self.end_date}")
        print(f"交易对: {', '.join(self.symbols)}")

        # 转换时间戳
        start_ts = int(pd.to_datetime(self.start_date).timestamp() * 1000)
        end_ts = int(pd.to_datetime(self.end_date).timestamp() * 1000)

        download_results = {}

        for symbol in self.symbols:
            print(f"\n{'='*50}")
            print(f"处理交易对: {symbol}")
            print(f"{'='*50}")

            download_results[symbol] = {}

            # 下载Binance数据
            binance_df = self.get_binance_klines(symbol, self.interval, start_ts, end_ts)
            if binance_df is not None:
                binance_file = os.path.join(self.output_dir, f"binance_{symbol}_{self.interval}.csv")
                binance_df.to_csv(binance_file, index=False)
                download_results[symbol]['binance'] = {
                    'file': binance_file,
                    'count': len(binance_df),
                    'start': binance_df['timestamp'].min(),
                    'end': binance_df['timestamp'].max()
                }
                print(f"Binance成功: {len(binance_df)} 条记录")

            time.sleep(1)  # 避免API限制

            # 下载Bybit数据
            bybit_df = self.get_bybit_klines(symbol, self.interval, start_ts, end_ts)
            if bybit_df is not None:
                bybit_file = os.path.join(self.output_dir, f"bybit_{symbol}_{self.interval}.csv")
                bybit_df.to_csv(bybit_file, index=False)
                download_results[symbol]['bybit'] = {
                    'file': bybit_file,
                    'count': len(bybit_df),
                    'start': bybit_df['timestamp'].min(),
                    'end': bybit_df['timestamp'].max()
                }
                print(f"Bybit成功: {len(bybit_df)} 条记录")

            time.sleep(1)  # 避免API限制

            # 下载OKX数据
            okx_df = self.get_okx_klines(symbol, self.interval, start_ts, end_ts)
            if okx_df is not None:
                okx_file = os.path.join(self.output_dir, f"okx_{symbol}_{self.interval}.csv")
                okx_df.to_csv(okx_file, index=False)
                download_results[symbol]['okx'] = {
                    'file': okx_file,
                    'count': len(okx_df),
                    'start': okx_df['timestamp'].min(),
                    'end': okx_df['timestamp'].max()
                }
                print(f"OKX成功: {len(okx_df)} 条记录")

            time.sleep(2)  # 避免API限制

        # 生成下载报告
        self.generate_download_report(download_results)

        return download_results

    def generate_download_report(self, results):
        """生成下载报告"""
        report_file = os.path.join(self.output_dir, 'download_report.json')

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n下载完成！报告已保存到: {report_file}")

        # 打印摘要
        print(f"\n下载摘要:")
        print(f"{'交易对':<10} {'交易所':<10} {'数据量':<8} {'时间范围'}")
        print(f"{'-'*50}")

        for symbol, exchanges in results.items():
            for exchange, info in exchanges.items():
                print(f"{symbol:<10} {exchange:<10} {info['count']:<8} {info['start']} 到 {info['end']}")

def main():
    """主函数"""
    downloader = UnifiedDataDownloader()

    try:
        results = downloader.download_all_data()

        print(f"\n下载完成！")
        print(f"数据文件保存在: {downloader.output_dir}")
        print(f"\n下一步: 使用 align_by_symbol.py 处理新下载的数据")
        print(f"命令: python3 align_by_symbol.py")

    except Exception as e:
        print(f"下载过程中出现错误: {e}")

if __name__ == "__main__":
    main()