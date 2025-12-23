"""
多交易所数据下载器
支持从OKX、Binance、Bybit等交易所下载K线数据
"""

import asyncio
import aiohttp
import pandas as pd
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging
import configparser
from concurrent.futures import ThreadPoolExecutor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataDownloader:
    """多交易所数据下载器"""

    def __init__(self, config_file: str = "config/config.ini"):
        """
        初始化下载器

        Args:
            config_file: 配置文件路径
        """
        self.config = configparser.ConfigParser()
        self.config.read(config_file)

        # API端点配置
        self.endpoints = {
            'okx': 'https://www.okx.com/api/v5/market/candles',
            'binance': 'https://api.binance.com/api/v3/klines',
            'bybit': 'https://api.bybit.com/v5/market/kline'
        }

        # 数据保存路径
        self.data_dir = Path(self.config.get('data', 'save_path', fallback='data/raw'))
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 并发控制
        self.max_concurrent = self.config.getint('download', 'max_concurrent', fallback=5)
        self.rate_limit = self.config.getfloat('download', 'rate_limit', fallback=0.1)

        logger.info(f"数据下载器初始化完成，数据保存路径: {self.data_dir}")

    async def download_okx_data(self, session: aiohttp.ClientSession,
                               symbol: str, interval: str,
                               start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """下载OKX数据"""
        try:
            # 转换交易对格式 (BTC/USDT -> BTC-USDT)
            okx_symbol = symbol.replace('/', '-')

            # 转换时间间隔
            interval_map = {
                '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
                '1h': '1H', '4h': '4H', '1d': '1D'
            }
            okx_interval = interval_map.get(interval, '30m')

            # 转换时间格式
            start_timestamp = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
            end_timestamp = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)

            params = {
                'instId': okx_symbol,
                'bar': okx_interval,
                'after': str(end_timestamp),
                'before': str(start_timestamp),
                'limit': '100'
            }

            async with session.get(self.endpoints['okx'], params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get('code') == '0' and data.get('data'):
                        # 解析数据
                        df_data = []
                        for item in data['data']:
                            # OKX返回的数据格式: [timestamp, open, high, low, close, volume, volume_currency, volume_currency_quote, confirm]
                            df_data.append({
                                'timestamp': pd.to_datetime(int(item[0]), unit='ms'),
                                'open': float(item[1]),
                                'high': float(item[2]),
                                'low': float(item[3]),
                                'close': float(item[4]),
                                'volume': float(item[5]),
                                'quote_volume': float(item[6])
                            })

                        df = pd.DataFrame(df_data)
                        df.set_index('timestamp', inplace=True)
                        df.sort_index(inplace=True)

                        logger.info(f"OKX {symbol} 下载完成: {len(df)} 条记录")
                        return df
                    else:
                        logger.error(f"OKX API返回错误: {data}")
                        return None
                else:
                    logger.error(f"OKX请求失败: HTTP {response.status}")
                    return None

        except Exception as e:
            logger.error(f"下载OKX数据时出错: {e}")
            return None

    async def download_binance_data(self, session: aiohttp.ClientSession,
                                   symbol: str, interval: str,
                                   start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """下载Binance数据"""
        try:
            # 转换交易对格式 (BTC/USDT -> BTCUSDT)
            binance_symbol = symbol.replace('/', '')

            # 转换时间间隔
            interval_map = {
                '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
                '1h': '1h', '4h': '4h', '1d': '1d'
            }
            binance_interval = interval_map.get(interval, '30m')

            params = {
                'symbol': binance_symbol,
                'interval': binance_interval,
                'startTime': int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000),
                'endTime': int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000),
                'limit': 1000
            }

            async with session.get(self.endpoints['binance'], params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    if data:
                        # 解析数据
                        df_data = []
                        for item in data:
                            # Binance返回的数据格式: [open_time, open, high, low, close, volume, close_time, quote_volume, ...]
                            df_data.append({
                                'timestamp': pd.to_datetime(item[0], unit='ms'),
                                'open': float(item[1]),
                                'high': float(item[2]),
                                'low': float(item[3]),
                                'close': float(item[4]),
                                'volume': float(item[5]),
                                'quote_volume': float(item[7])
                            })

                        df = pd.DataFrame(df_data)
                        df.set_index('timestamp', inplace=True)
                        df.sort_index(inplace=True)

                        logger.info(f"Binance {symbol} 下载完成: {len(df)} 条记录")
                        return df
                    else:
                        logger.error("Binance API返回空数据")
                        return None
                else:
                    logger.error(f"Binance请求失败: HTTP {response.status}")
                    return None

        except Exception as e:
            logger.error(f"下载Binance数据时出错: {e}")
            return None

    async def download_bybit_data(self, session: aiohttp.ClientSession,
                                 symbol: str, interval: str,
                                 start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """下载Bybit数据"""
        try:
            # 转换交易对格式 (BTC/USDT -> BTCUSDT)
            bybit_symbol = symbol.replace('/', '')

            # 转换时间间隔
            interval_map = {
                '1m': '1', '5m': '5', '15m': '15', '30m': '30',
                '1h': '60', '4h': '240', '1d': 'D'
            }
            bybit_interval = interval_map.get(interval, '30')

            # 转换时间格式
            start_timestamp = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
            end_timestamp = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)

            params = {
                'category': 'linear',
                'symbol': bybit_symbol,
                'interval': bybit_interval,
                'start': start_timestamp,
                'end': end_timestamp,
                'limit': 200
            }

            async with session.get(self.endpoints['bybit'], params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    if data.get('retCode') == 0 and data.get('result', {}).get('list'):
                        # 解析数据
                        df_data = []
                        for item in data['result']['list']:
                            # Bybit返回的数据格式: [start_time, open, high, low, close, volume, turnover]
                            df_data.append({
                                'timestamp': pd.to_datetime(int(item[0]), unit='ms'),
                                'open': float(item[1]),
                                'high': float(item[2]),
                                'low': float(item[3]),
                                'close': float(item[4]),
                                'volume': float(item[5]),
                                'quote_volume': float(item[6])
                            })

                        df = pd.DataFrame(df_data)
                        df.set_index('timestamp', inplace=True)
                        df.sort_index(inplace=True)

                        logger.info(f"Bybit {symbol} 下载完成: {len(df)} 条记录")
                        return df
                    else:
                        logger.error(f"Bybit API返回错误: {data}")
                        return None
                else:
                    logger.error(f"Bybit请求失败: HTTP {response.status}")
                    return None

        except Exception as e:
            logger.error(f"下载Bybit数据时出错: {e}")
            return None

    def save_data(self, df: pd.DataFrame, exchange: str, symbol: str, interval: str):
        """保存数据到文件"""
        try:
            # 文件名格式: exchange_symbol_interval.csv
            filename = f"{exchange}_{symbol.replace('/', '')}_{interval}.csv"
            filepath = self.data_dir / filename

            df.to_csv(filepath)
            logger.info(f"数据已保存到: {filepath}")

        except Exception as e:
            logger.error(f"保存数据时出错: {e}")

    async def download_symbol_data(self, symbol: str, interval: str,
                                  start_date: str, end_date: str,
                                  exchanges: List[str] = None):
        """下载单个交易对的所有交易所数据"""
        if exchanges is None:
            exchanges = ['okx', 'binance', 'bybit']

        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def download_with_semaphore(exchange: str):
            async with semaphore:
                # 添加速率限制
                await asyncio.sleep(self.rate_limit)

                connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
                timeout = aiohttp.ClientTimeout(total=30)

                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                    if exchange == 'okx':
                        df = await self.download_okx_data(session, symbol, interval, start_date, end_date)
                    elif exchange == 'binance':
                        df = await self.download_binance_data(session, symbol, interval, start_date, end_date)
                    elif exchange == 'bybit':
                        df = await self.download_bybit_data(session, symbol, interval, start_date, end_date)
                    else:
                        logger.warning(f"不支持的交易所: {exchange}")
                        return

                    if df is not None:
                        self.save_data(df, exchange, symbol, interval)

        # 并行下载所有交易所的数据
        tasks = [download_with_semaphore(exchange) for exchange in exchanges]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def test_single_symbol(self, symbol: str, interval: str):
        """测试单个交易对的下载"""
        logger.info(f"测试下载 {symbol} {interval} 数据...")

        # 使用最近7天的数据进行测试
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        await self.download_symbol_data(symbol, interval, start_date, end_date)

    def run(self, symbols: List[str] = None, interval: str = "30m",
            start_date: str = None, end_date: str = None,
            max_concurrent: int = None):
        """运行下载器"""
        if max_concurrent:
            self.max_concurrent = max_concurrent

        # 从配置文件获取默认参数
        if symbols is None:
            symbols = [s.strip() for s in self.config.get('data', 'symbols', fallback='BTC/USDT,ETH/USDT').split(',')]

        if start_date is None:
            start_date = self.config.get('data', 'start_date', fallback='2024-01-01')

        if end_date is None:
            end_date = self.config.get('data', 'end_date', fallback='2024-12-31')

        logger.info(f"开始下载数据: {len(symbols)} 个交易对")
        logger.info(f"时间范围: {start_date} 至 {end_date}")
        logger.info(f"时间间隔: {interval}")
        logger.info(f"最大并发数: {self.max_concurrent}")

        # 逐个交易对下载
        for i, symbol in enumerate(symbols, 1):
            logger.info(f"处理交易对 {i}/{len(symbols)}: {symbol}")

            try:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(
                    self.download_symbol_data(symbol, interval, start_date, end_date)
                )
            except Exception as e:
                logger.error(f"下载 {symbol} 数据时出错: {e}")
                continue

            # 在交易对之间添加延迟
            if i < len(symbols):
                time.sleep(1)

        logger.info("所有数据下载完成!")