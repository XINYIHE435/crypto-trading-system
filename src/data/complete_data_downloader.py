#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整数据下载器
支持下载K线数据和资金费率数据
支持Binance、Bybit、OKX三个交易所
"""

import pandas as pd
import requests
import time
import os
from datetime import datetime, timedelta
import json
from typing import Dict, Optional, List

class CompleteDataDownloader:
    def __init__(self):
        # 配置参数
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        self.interval = '30m'
        self.start_date = '2025-11-01'  # 统一开始时间
        self.end_date = '2025-11-30'    # 统一结束时间

        # 创建输出目录
        self.kline_dir = 'data/raw/klines'
        self.funding_dir = 'data/raw/funding_rates'
        os.makedirs(self.kline_dir, exist_ok=True)
        os.makedirs(self.funding_dir, exist_ok=True)

    # ==================== K线数据下载 ====================

    def get_binance_klines(self, symbol: str, interval: str, start_time: int, end_time: int) -> Optional[pd.DataFrame]:
        """下载Binance K线数据"""
        print(f"下载Binance {symbol} K线数据...")

        url = "https://api.binance.com/api/v3/klines"
        all_data = []
        current_start = start_time

        while current_start < end_time:
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': current_start,
                'endTime': end_time,
                'limit': 1000
            }

            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                if not data:
                    break

                all_data.extend(data)

                # 更新起始时间为最后一条数据的时间戳
                if len(data) > 0:
                    current_start = data[-1][0] + 1

                # 避免API限制
                time.sleep(0.1)

            except Exception as e:
                print(f"Binance K线数据下载错误: {e}")
                break

        if not all_data:
            return None

        # 转换为DataFrame
        df = pd.DataFrame(all_data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_volume',
            'taker_buy_quote_volume', 'ignore'
        ])

        # 数据清洗
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume']]
        df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']] = df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']].astype(float)

        return df

    def get_bybit_klines(self, symbol: str, interval: str, start_time: int, end_time: int) -> Optional[pd.DataFrame]:
        """下载Bybit K线数据"""
        print(f"下载Bybit {symbol} K线数据...")

        # Bybit的时间间隔格式需要转换
        interval_map = {
            '30m': '30',
            '1h': '60',
            '1m': '1',
            '5m': '5',
            '15m': '15'
        }
        bybit_interval = interval_map.get(interval, interval)

        url = "https://api.bybit.com/v5/market/kline"
        params = {
            'category': 'spot',
            'symbol': symbol,
            'interval': bybit_interval,
            'start': start_time,
            'end': end_time,
            'limit': 1000
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data['retCode'] != 0:
                print(f"Bybit K线API错误: {data['retMsg']}")
                return None

            klines = data['result']['list']
            if not klines:
                print("Bybit返回空K线数据")
                return None

            # 转换为DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
            ])

            # 数据清洗
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover']]
            df[['open', 'high', 'low', 'close', 'volume', 'turnover']] = df[['open', 'high', 'low', 'close', 'volume', 'turnover']].astype(float)
            df.rename(columns={'turnover': 'quote_volume'}, inplace=True)

            # 按时间戳排序（Bybit返回的是倒序）
            df = df.sort_values('timestamp').reset_index(drop=True)

            return df

        except Exception as e:
            print(f"Bybit K线数据下载失败: {e}")
            return None

    def get_okx_klines(self, symbol: str, interval: str, start_time: int, end_time: int) -> Optional[pd.DataFrame]:
        """下载OKX K线数据"""
        print(f"下载OKX {symbol} K线数据...")

        # OKX现货市场的交易对格式
        okx_symbol = f"{symbol[:3]}-{symbol[3:]}" if len(symbol) > 6 else symbol

        # OKX的时间间隔格式
        okx_interval = {
            '30m': '30m',
            '1h': '1H',
            '1m': '1m',
            '5m': '5m',
            '15m': '15m'
        }.get(interval, interval)

        url = "https://www.okx.com/api/v5/market/history-candles"
        params = {
            'instId': okx_symbol,
            'bar': okx_interval,
            'before': str(end_time),
            'after': str(start_time),
            'limit': '100'
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data['code'] != '0':
                print(f"OKX K线API错误: {data['msg']}")
                return None

            klines = data['data']
            if not klines:
                print("OKX返回空K线数据")
                return None

            # 转换为DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume',
                'currency_volume', 'currency_quote_volume'
            ])

            # 数据清洗
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume']]
            df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']] = df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']].astype(float)

            # OKX返回的是倒序，需要排序
            df = df.sort_values('timestamp').reset_index(drop=True)

            return df

        except Exception as e:
            print(f"OKX K线数据下载失败: {e}")
            return None

    # ==================== 资金费率下载 ====================

    def get_binance_funding_rate(self, symbol: str) -> Optional[pd.DataFrame]:
        """下载Binance资金费率"""
        print(f"下载Binance {symbol} 资金费率...")

        url = "https://fapi.binance.com/fapi/v1/fundingRate"
        all_data = []

        try:
            # 转换时间格式
            start_time = int(pd.to_datetime(self.start_date).timestamp() * 1000)
            end_time = int(pd.to_datetime(self.end_date).timestamp() * 1000)

            params = {
                'symbol': symbol,
                'startTime': start_time,
                'endTime': end_time,
                'limit': 1000
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not data:
                print(f"Binance {symbol} 没有资金费率数据（可能是现货交易对）")
                return None

            # 转换为DataFrame
            df = pd.DataFrame(data)
            df['fundingTime'] = pd.to_datetime(df['fundingTime'], unit='ms')
            df.rename(columns={
                'fundingTime': 'timestamp',
                'fundingRate': 'funding_rate',
                'markPrice': 'mark_price'
            }, inplace=True)

            # 选择需要的列
            df = df[['timestamp', 'funding_rate', 'mark_price']]
            df['funding_rate'] = df['funding_rate'].astype(float)
            df['mark_price'] = df['mark_price'].astype(float)

            return df

        except Exception as e:
            print(f"Binance资金费率下载失败: {e}")
            return None

    def get_bybit_funding_rate(self, symbol: str) -> Optional[pd.DataFrame]:
        """下载Bybit资金费率"""
        print(f"下载Bybit {symbol} 资金费率...")

        # Bybit需要使用永续合约的symbol
        if not symbol.endswith('USDT'):
            return None

        url = "https://api.bybit.com/v5/market/funding/history"

        try:
            params = {
                'category': 'linear',
                'symbol': symbol,
                'limit': 200
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data['retCode'] != 0:
                print(f"Bybit资金费率API错误: {data['retMsg']}")
                return None

            funding_list = data['result']['list']
            if not funding_list:
                print("Bybit返回空资金费率数据")
                return None

            # 转换为DataFrame
            df = pd.DataFrame(funding_list, columns=[
                'symbol', 'fundingRate', 'fundingRateTimestamp'
            ])

            # 数据清洗
            df['timestamp'] = pd.to_datetime(df['fundingRateTimestamp'].astype(int), unit='ms')
            df.rename(columns={'fundingRate': 'funding_rate'}, inplace=True)
            df = df[['timestamp', 'funding_rate']]
            df['funding_rate'] = df['funding_rate'].astype(float)

            # 按时间排序
            df = df.sort_values('timestamp').reset_index(drop=True)

            return df

        except Exception as e:
            print(f"Bybit资金费率下载失败: {e}")
            return None

    def get_okx_funding_rate(self, symbol: str) -> Optional[pd.DataFrame]:
        """下载OKX资金费率"""
        print(f"下载OKX {symbol} 资金费率...")

        # OKX需要使用永续合约格式
        if symbol.endswith('USDT'):
            okx_symbol = f"{symbol[:3]}-USDT-SWAP"
        else:
            return None

        url = "https://www.okx.com/api/v5/public/funding-rate"

        try:
            params = {
                'instId': okx_symbol,
                'before': str(int(pd.to_datetime(self.end_date).timestamp() * 1000)),
                'after': str(int(pd.to_datetime(self.start_date).timestamp() * 1000)),
                'limit': '100'
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data['code'] != '0':
                print(f"OKX资金费率API错误: {data['msg']}")
                return None

            funding_list = data['data']
            if not funding_list:
                print("OKX返回空资金费率数据")
                return None

            # 转换为DataFrame
            df = pd.DataFrame(funding_list, columns=[
                'fundingRate', 'fundingTime'
            ])

            # 数据清洗
            df['timestamp'] = pd.to_datetime(df['fundingTime'].astype(int), unit='ms')
            df.rename(columns={'fundingRate': 'funding_rate'}, inplace=True)
            df = df[['timestamp', 'funding_rate']]
            df['funding_rate'] = df['funding_rate'].astype(float)

            # 按时间排序（OKX返回倒序）
            df = df.sort_values('timestamp').reset_index(drop=True)

            return df

        except Exception as e:
            print(f"OKX资金费率下载失败: {e}")
            return None

    # ==================== 主下载函数 ====================

    def download_all_klines(self) -> Dict:
        """下载所有K线数据"""
        print("\n" + "="*60)
        print("开始下载K线数据")
        print("="*60)

        # 转换时间戳
        start_ts = int(pd.to_datetime(self.start_date).timestamp() * 1000)
        end_ts = int(pd.to_datetime(self.end_date).timestamp() * 1000)

        results = {}

        for symbol in self.symbols:
            print(f"\n{'='*50}")
            print(f"下载 {symbol} K线数据")
            print(f"{'='*50}")

            results[symbol] = {}

            # 下载各交易所数据
            exchanges = [
                ('binance', self.get_binance_klines),
                ('bybit', self.get_bybit_klines),
                ('okx', self.get_okx_klines)
            ]

            for exchange_name, download_func in exchanges:
                df = download_func(symbol, self.interval, start_ts, end_ts)
                if df is not None and len(df) > 0:
                    # 保存文件
                    filename = f"{exchange_name}_{symbol}_{self.interval}.csv"
                    filepath = os.path.join(self.kline_dir, filename)
                    df.to_csv(filepath, index=False)

                    results[symbol][exchange_name] = {
                        'file': filepath,
                        'count': len(df),
                        'start': df['timestamp'].min(),
                        'end': df['timestamp'].max()
                    }

                    print(f"{exchange_name.upper()} K线数据下载成功: {len(df)} 条记录")
                else:
                    print(f"{exchange_name.upper()} K线数据下载失败")

                time.sleep(1)  # 避免API限制

        return results

    def download_all_funding_rates(self) -> Dict:
        """下载所有资金费率数据"""
        print("\n" + "="*60)
        print("开始下载资金费率数据")
        print("="*60)

        results = {}

        for symbol in self.symbols:
            print(f"\n{'='*50}")
            print(f"下载 {symbol} 资金费率数据")
            print(f"{'='*50}")

            results[symbol] = {}

            # 下载各交易所资金费率
            exchanges = [
                ('binance', self.get_binance_funding_rate),
                ('bybit', self.get_bybit_funding_rate),
                ('okx', self.get_okx_funding_rate)
            ]

            for exchange_name, download_func in exchanges:
                df = download_func(symbol)
                if df is not None and len(df) > 0:
                    # 保存文件
                    filename = f"{exchange_name}_{symbol}_funding_rate.csv"
                    filepath = os.path.join(self.funding_dir, filename)
                    df.to_csv(filepath, index=False)

                    results[symbol][exchange_name] = {
                        'file': filepath,
                        'count': len(df),
                        'start': df['timestamp'].min(),
                        'end': df['timestamp'].max(),
                        'avg_rate': df['funding_rate'].mean()
                    }

                    print(f"{exchange_name.upper()} 资金费率下载成功: {len(df)} 条记录")
                else:
                    print(f"{exchange_name.upper()} 资金费率下载失败或无数据")

                time.sleep(1)  # 避免API限制

        return results

    def download_all_data(self) -> Dict:
        """下载所有数据（K线 + 资金费率）"""
        print("开始完整数据下载...")
        print(f"时间范围: {self.start_date} 到 {self.end_date}")
        print(f"交易对: {', '.join(self.symbols)}")
        print(f"时间间隔: {self.interval}")

        # 下载K线数据
        kline_results = self.download_all_klines()

        # 下载资金费率数据
        funding_results = self.download_all_funding_rates()

        # 合并结果
        all_results = {
            'klines': kline_results,
            'funding_rates': funding_results,
            'download_time': datetime.now().isoformat(),
            'config': {
                'symbols': self.symbols,
                'interval': self.interval,
                'start_date': self.start_date,
                'end_date': self.end_date
            }
        }

        # 生成报告
        self.generate_download_report(all_results)

        return all_results

    def generate_download_report(self, results: Dict):
        """生成下载报告"""
        report_file = 'data/download_report.json'

        # 保存详细报告
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n" + "="*60)
        print("下载完成！")
        print("="*60)

        # K线数据摘要
        print("\n📊 K线数据下载摘要:")
        print("-" * 60)
        print(f"{'交易对':<10} {'交易所':<10} {'数据量':<8} {'时间范围'}")
        print("-" * 60)

        for symbol, exchanges in results['klines'].items():
            for exchange, info in exchanges.items():
                print(f"{symbol:<10} {exchange:<10} {info['count']:<8} {info['start']} 到 {info['end']}")

        # 资金费率数据摘要
        print("\n💰 资金费率数据下载摘要:")
        print("-" * 60)
        print(f"{'交易对':<10} {'交易所':<10} {'数据量':<8} {'平均费率'}")
        print("-" * 60)

        for symbol, exchanges in results['funding_rates'].items():
            for exchange, info in exchanges.items():
                avg_rate = f"{info['avg_rate']*100:.4f}%" if 'avg_rate' in info else "N/A"
                print(f"{symbol:<10} {exchange:<10} {info['count']:<8} {avg_rate}")

        print(f"\n📁 数据保存位置:")
        print(f"   K线数据: {self.kline_dir}")
        print(f"   资金费率: {self.funding_dir}")
        print(f"   下载报告: {report_file}")

        print(f"\n✅ 数据下载完成！可以开始构建逻辑系统。")

def main():
    """主函数"""
    print("🚀 完整数据下载器启动")
    print("将下载K线数据和资金费率数据，用于构建套利逻辑系统")

    downloader = CompleteDataDownloader()

    try:
        results = downloader.download_all_data()

        print(f"\n🎉 所有数据下载任务完成！")

    except KeyboardInterrupt:
        print(f"\n⚠️ 下载被用户中断")
    except Exception as e:
        print(f"\n❌ 下载过程中出现错误: {e}")

if __name__ == "__main__":
    main()