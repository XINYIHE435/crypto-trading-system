#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扩展数据下载器 - 支持多个交易所
包括K线数据和资金费率数据
支持：Binance, Bybit, OKX, Huobi/HTX, KuCoin, Gate.io, Bitget
"""

import pandas as pd
import requests
import time
import os
from datetime import datetime, timedelta
import json
from typing import Dict, Optional, List
import hmac
import hashlib
import base64
from urllib.parse import urlencode

class ExpandedDataDownloader:
    def __init__(self, config_path="config/config.ini"):
        # 加载配置
        self.config_path = config_path
        self.load_config()
        
        # 创建输出目录
        self.kline_dir = 'data/raw/klines'
        self.funding_dir = 'data/raw/funding_rates'
        os.makedirs(self.kline_dir, exist_ok=True)
        os.makedirs(self.funding_dir, exist_ok=True)
    
    def load_config(self):
        """加载配置文件"""
        import configparser
        config = configparser.ConfigParser()
        
        if os.path.exists(self.config_path):
            config.read(self.config_path, encoding='utf-8')
            
            # 从配置文件读取参数
            symbols_str = config.get('DEFAULT', 'symbols', fallback='BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,ADAUSDT')
            self.symbols = [s.strip() for s in symbols_str.split(',')]
            
            self.interval = config.get('DEFAULT', 'interval', fallback='30m')
            self.start_date = config.get('DEFAULT', 'start_date', fallback='2025-11-01')
            self.end_date = config.get('DEFAULT', 'end_date', fallback='2025-12-12')
        else:
            # 默认配置
            self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
            self.interval = '30m'
            self.start_date = '2025-11-01'
            self.end_date = '2025-12-12'
        
        # 支持的交易所列表
        self.exchanges = ['binance', 'bybit', 'okx', 'huobi', 'kucoin', 'gate', 'bitget']

        # 创建输出目录
        self.kline_dir = 'data/raw/klines'
        self.funding_dir = 'data/raw/funding_rates'
        os.makedirs(self.kline_dir, exist_ok=True)
        os.makedirs(self.funding_dir, exist_ok=True)

    # ==================== 原有三交易所方法 ====================

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

                if len(data) > 0:
                    current_start = data[-1][0] + 1

                time.sleep(0.1)

            except Exception as e:
                print(f"Binance K线数据下载错误: {e}")
                break

        if not all_data:
            return None

        df = pd.DataFrame(all_data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_volume',
            'taker_buy_quote_volume', 'ignore'
        ])

        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume']]
        df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']] = df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']].astype(float)

        return df

    def get_bybit_klines(self, symbol: str, interval: str, start_time: int, end_time: int) -> Optional[pd.DataFrame]:
        """下载Bybit K线数据"""
        print(f"下载Bybit {symbol} K线数据...")

        interval_map = {
            '30m': '30', '1h': '60', '1m': '1', '5m': '5', '15m': '15'
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
                return None

            klines = data['result']['list']
            if not klines:
                return None

            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
            ])

            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover']]
            df[['open', 'high', 'low', 'close', 'volume', 'turnover']] = df[['open', 'high', 'low', 'close', 'volume', 'turnover']].astype(float)
            df.rename(columns={'turnover': 'quote_volume'}, inplace=True)
            df = df.sort_values('timestamp').reset_index(drop=True)

            return df

        except Exception as e:
            print(f"Bybit K线数据下载失败: {e}")
            return None

    def get_okx_klines(self, symbol: str, interval: str, start_time: int, end_time: int) -> Optional[pd.DataFrame]:
        """下载OKX K线数据"""
        print(f"下载OKX {symbol} K线数据...")

        # OKX交易对格式转换
        okx_symbol = f"{symbol[:3]}-{symbol[3:]}" if len(symbol) > 6 else symbol

        okx_interval = {
            '30m': '30m', '1h': '1H', '1m': '1m', '5m': '5m', '15m': '15m'
        }.get(interval, interval)

        # 使用正确的OKX API端点
        url = "https://www.okx.com/api/v5/market/candles"
        params = {
            'instId': okx_symbol,
            'bar': okx_interval,
            'after': str(end_time),
            'before': str(start_time),
            'limit': '300'
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('code') != '0' or not data.get('data'):
                print(f"OKX API错误: {data}")
                return None

            klines = data['data']
            if not klines:
                return None

            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume',
                'currency_volume', 'currency_quote_volume'
            ])

            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume']]
            df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']] = df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']].astype(float)
            df = df.sort_values('timestamp').reset_index(drop=True)

            return df

        except Exception as e:
            print(f"OKX K线数据下载失败: {e}")
            return None

    # ==================== 新增交易所方法 ====================

    def get_huobi_klines(self, symbol: str, interval: str, start_time: int, end_time: int) -> Optional[pd.DataFrame]:
        """下载Huobi/HTX K线数据"""
        print(f"下载Huobi {symbol} K线数据...")

        # Huobi需要lowercase
        huobi_symbol = symbol.lower()

        # 转换时间间隔
        interval_map = {
            '30m': '30min', '1h': '60min', '1m': '1min', '5m': '5min', '15m': '15min'
        }
        huobi_interval = interval_map.get(interval, interval)

        url = "https://api.huobi.pro/market/history/kline"
        params = {
            'symbol': huobi_symbol,
            'period': huobi_interval,
            'size': 2000,
            'from': int(start_time / 1000),
            'to': int(end_time / 1000)
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('status') != 'ok':
                print(f"Huobi API错误: {data}")
                return None

            klines = data.get('data', [])
            if not klines:
                return None

            df = pd.DataFrame(klines)
            df['timestamp'] = pd.to_datetime(df['id'], unit='s')
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'vol', 'amount']]
            df.rename(columns={
                'vol': 'volume',
                'amount': 'quote_volume'
            }, inplace=True)
            df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']] = df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']].astype(float)
            df = df.sort_values('timestamp').reset_index(drop=True)

            return df

        except Exception as e:
            print(f"Huobi K线数据下载失败: {e}")
            return None

    def get_kucoin_klines(self, symbol: str, interval: str, start_time: int, end_time: int) -> Optional[pd.DataFrame]:
        """下载KuCoin K线数据"""
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

    def get_gate_klines(self, symbol: str, interval: str, start_time: int, end_time: int) -> Optional[pd.DataFrame]:
        """下载Gate.io K线数据"""
        print(f"下载Gate.io {symbol} K线数据...")

        # Gate.io时间间隔
        interval_map = {
            '30m': '30m', '1h': '1h', '1m': '1m', '5m': '5m', '15m': '15m'
        }
        gate_interval = interval_map.get(interval, interval)

        # Gate.io交易对格式转换
        gate_symbol = f"{symbol[:3]}_{symbol[3:]}" if len(symbol) > 6 else symbol

        url = f"https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': gate_symbol,
            'interval': gate_interval,
            'from': int(start_time / 1000),
            'to': int(end_time / 1000),
            'limit': 1000
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not data or isinstance(data, dict):
                return None

            df = pd.DataFrame(data, columns=[
                'timestamp', 'volume', 'quote_volume', 'open', 'high', 'low', 'close'
            ])

            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='s')
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume']]
            df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']] = df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']].astype(float)
            df = df.sort_values('timestamp').reset_index(drop=True)

            return df

        except Exception as e:
            print(f"Gate.io K线数据下载失败: {e}")
            return None

    def get_bitget_klines(self, symbol: str, interval: str, start_time: int, end_time: int) -> Optional[pd.DataFrame]:
        """下载Bitget K线数据"""
        print(f"下载Bitget {symbol} K线数据...")

        # Bitget时间间隔
        interval_map = {
            '30m': '30m', '1h': '1H', '1m': '1m', '5m': '5m', '15m': '15m'
        }
        bitget_interval = interval_map.get(interval, interval)

        # 使用更新的Bitget API
        url = f"https://api.bitget.com/v2/spot/market/candles"
        params = {
            'symbol': symbol,
            'granularity': bitget_interval,
            'startTime': str(start_time),
            'endTime': str(end_time),
            'limit': '100'
        }

        # 添加请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('code') != '00000' or not data.get('data'):
                print(f"Bitget API错误: {data}")
                return None

            klines = data['data']
            df = pd.DataFrame(klines)

            # Bitget返回顺序：时间戳, 开盘价, 最高价, 最低价, 收盘价, 成交量
            df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            # 添加quote_volume（成交额），使用close*volume估算
            df['quote_volume'] = df['close'].astype(float) * df['volume'].astype(float)
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume']]
            df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']] = df[['open', 'high', 'low', 'close', 'volume', 'quote_volume']].astype(float)
            df = df.sort_values('timestamp').reset_index(drop=True)

            return df

        except Exception as e:
            print(f"Bitget K线数据下载失败: {e}")
            return None

    # ==================== 资金费率下载 ====================

    def get_binance_funding_rate(self, symbol: str) -> Optional[pd.DataFrame]:
        """下载Binance资金费率"""
        print(f"下载Binance {symbol} 资金费率...")

        url = "https://fapi.binance.com/fapi/v1/fundingRate"

        try:
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
                return None

            df = pd.DataFrame(data)
            df['fundingTime'] = pd.to_datetime(df['fundingTime'], unit='ms')
            df.rename(columns={
                'fundingTime': 'timestamp',
                'fundingRate': 'funding_rate',
                'markPrice': 'mark_price'
            }, inplace=True)
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
                return None

            funding_list = data['result']['list']
            if not funding_list:
                return None

            df = pd.DataFrame(funding_list, columns=[
                'symbol', 'fundingRate', 'fundingRateTimestamp'
            ])

            df['timestamp'] = pd.to_datetime(df['fundingRateTimestamp'].astype(int), unit='ms')
            df.rename(columns={'fundingRate': 'funding_rate'}, inplace=True)
            df = df[['timestamp', 'funding_rate']]
            df['funding_rate'] = df['funding_rate'].astype(float)
            df = df.sort_values('timestamp').reset_index(drop=True)

            return df

        except Exception as e:
            print(f"Bybit资金费率下载失败: {e}")
            return None

    # ==================== 主下载函数 ====================

    def download_all_klines(self) -> Dict:
        """下载所有交易所的K线数据"""
        print("\n" + "="*60)
        print("开始下载所有交易所K线数据")
        print("="*60)

        start_ts = int(pd.to_datetime(self.start_date).timestamp() * 1000)
        end_ts = int(pd.to_datetime(self.end_date).timestamp() * 1000)

        results = {}

        # 交易所下载函数映射
        exchange_functions = {
            'binance': self.get_binance_klines,
            'bybit': self.get_bybit_klines,
            'okx': self.get_okx_klines,
            'huobi': self.get_huobi_klines,
            'kucoin': self.get_kucoin_klines,
            'gate': self.get_gate_klines,
            'bitget': self.get_bitget_klines
        }

        for symbol in self.symbols:
            print(f"\n{'='*50}")
            print(f"下载 {symbol} K线数据")
            print(f"{'='*50}")

            results[symbol] = {}

            for exchange_name, download_func in exchange_functions.items():
                print(f"\n--- {exchange_name.upper()} ---")
                df = download_func(symbol, self.interval, start_ts, end_ts)

                if df is not None and len(df) > 0:
                    filename = f"{exchange_name}_{symbol}_{self.interval}.csv"
                    filepath = os.path.join(self.kline_dir, filename)
                    df.to_csv(filepath, index=False)

                    results[symbol][exchange_name] = {
                        'file': filepath,
                        'count': len(df),
                        'start': df['timestamp'].min(),
                        'end': df['timestamp'].max()
                    }

                    print(f"✅ {exchange_name.upper()} 成功: {len(df)} 条记录")
                else:
                    print(f"❌ {exchange_name.upper()} 失败")
                    # 如果下载失败，尝试重新下载
                    print(f"🔄 重试 {exchange_name.upper()} {symbol}...")
                    time.sleep(1)  # 等待1秒后重试
                    df = download_func(symbol, self.interval, start_ts, end_ts)
                    
                    if df is not None and len(df) > 0:
                        filename = f"{exchange_name}_{symbol}_{self.interval}.csv"
                        filepath = os.path.join(self.kline_dir, filename)
                        df.to_csv(filepath, index=False)

                        results[symbol][exchange_name] = {
                            'file': filepath,
                            'count': len(df),
                            'start': df['timestamp'].min(),
                            'end': df['timestamp'].max()
                        }

                        print(f"✅ {exchange_name.upper()} 重试成功: {len(df)} 条记录")
                    else:
                        print(f"❌ {exchange_name.upper()} 重试仍然失败")

                time.sleep(0.5)  # 避免API限制

        return results

    def download_all_funding_rates(self) -> Dict:
        """下载所有交易所的资金费率数据"""
        print("\n" + "="*60)
        print("开始下载资金费率数据")
        print("="*60)

        results = {}

        for symbol in self.symbols:
            print(f"\n{'='*50}")
            print(f"下载 {symbol} 资金费率数据")
            print(f"{'='*50}")

            results[symbol] = {}

            # 只下载有资金费率的交易所
            exchanges = [
                ('binance', self.get_binance_funding_rate),
                ('bybit', self.get_bybit_funding_rate)
            ]

            for exchange_name, download_func in exchanges:
                df = download_func(symbol)
                if df is not None and len(df) > 0:
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

                    print(f"✅ {exchange_name.upper()} 资金费率成功: {len(df)} 条记录")
                else:
                    print(f"❌ {exchange_name.upper()} 资金费率失败")

                time.sleep(0.5)

        return results

    def download_all_data(self) -> Dict:
        """下载所有数据"""
        print("🚀 扩展数据下载器启动")
        print(f"支持交易所: {', '.join([e.upper() for e in self.exchanges])}")
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
                'end_date': self.end_date,
                'exchanges': self.exchanges
            }
        }

        # 生成报告
        self.generate_download_report(all_results)

        return all_results

    def generate_download_report(self, results: Dict):
        """生成下载报告"""
        report_file = 'data/expanded_download_report.json'

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\n" + "="*60)
        print("✅ 下载完成！")
        print("="*60)

        # K线数据摘要
        print("\n📊 K线数据下载摘要:")
        print("-" * 70)
        print(f"{'交易对':<10} {'交易所':<10} {'数据量':<8} {'开始时间':<20} {'结束时间'}")
        print("-" * 70)

        for symbol, exchanges in results['klines'].items():
            for exchange, info in exchanges.items():
                print(f"{symbol:<10} {exchange:<10} {info['count']:<8} {str(info['start']):<20} {info['end']}")

        # 统计
        total_kline_files = sum(len(exchanges) for exchanges in results['klines'].values())
        total_kline_records = sum(
            sum(info['count'] for info in exchanges.values())
            for exchanges in results['klines'].values()
        )

        print(f"\n📈 K线数据统计:")
        print(f"   总文件数: {total_kline_files}")
        print(f"   总记录数: {total_kline_records:,}")

        # 资金费率数据摘要
        if results['funding_rates']:
            print("\n💰 资金费率数据下载摘要:")
            print("-" * 50)
            print(f"{'交易对':<10} {'交易所':<10} {'数据量':<8} {'平均费率'}")
            print("-" * 50)

            for symbol, exchanges in results['funding_rates'].items():
                for exchange, info in exchanges.items():
                    avg_rate = f"{info['avg_rate']*100:.4f}%" if 'avg_rate' in info else "N/A"
                    print(f"{symbol:<10} {exchange:<10} {info['count']:<8} {avg_rate}")

        print(f"\n📁 数据保存位置:")
        print(f"   K线数据: {self.kline_dir}")
        print(f"   资金费率: {self.funding_dir}")
        print(f"   下载报告: {report_file}")

        print(f"\n🎉 扩展数据下载任务完成！")

def main():
    """主函数"""
    downloader = ExpandedDataDownloader()

    try:
        results = downloader.download_all_data()
        print(f"\n🎯 所有交易所数据下载完成！可以开始构建完整的套利逻辑系统。")

    except KeyboardInterrupt:
        print(f"\n⚠️ 下载被用户中断")
    except Exception as e:
        print(f"\n❌ 下载过程中出现错误: {e}")

if __name__ == "__main__":
    main()