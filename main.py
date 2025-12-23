#!/usr/bin/env python3
"""
多交易所套利系统主程序
整合数据下载、对齐、套利回测等功能
"""
import sys
import argparse
from pathlib import Path

# 添加src目录到Python路径
sys.path.append(str(Path(__file__).parent / "src"))

# 导入各个功能模块
from src.data.expanded_data_downloader import ExpandedDataDownloader
from src.data.create_multi_exchange_dataset import MultiExchangeDatasetCreator
from src.data.run_arbitrage_backtest import run_backtest
from src.arbitrage_system import ArbitrageSystem
from src.config import Config

def main():
    parser = argparse.ArgumentParser(description="多交易所套利系统")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 数据下载命令
    download_parser = subparsers.add_parser('download', help='下载多交易所数据')
    download_parser.add_argument("--symbols", nargs="+", help="交易对列表，例如: BTCUSDT ETHUSDT")
    download_parser.add_argument("--interval", default="30m", help="时间间隔，默认: 30m")
    download_parser.add_argument("--start-date", help="开始日期，格式: YYYY-MM-DD")
    download_parser.add_argument("--end-date", help="结束日期，格式: YYYY-MM-DD")
    download_parser.add_argument("--config", default="config/config.ini", help="配置文件路径")
    
    # 数据对齐命令
    align_parser = subparsers.add_parser('align', help='对齐多交易所数据')
    align_parser.add_argument("--config", default="config/config.ini", help="配置文件路径")
    
    # 套利回测命令
    backtest_parser = subparsers.add_parser('backtest', help='运行套利回测')
    backtest_parser.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"], help="交易对列表")
    backtest_parser.add_argument("--timeframes", nargs="+", default=["30m", "1h"], help="时间框架列表")
    backtest_parser.add_argument("--config", default="config/config.ini", help="配置文件路径")
    
    # 完整流程命令
    full_parser = subparsers.add_parser('full', help='运行完整流程：下载->对齐->回测')
    full_parser.add_argument("--config", default="config/config.ini", help="配置文件路径")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    config = Config(args.config)
    
    try:
        if args.command == 'download':
            print("🔄 开始下载多交易所数据...")
            downloader = ExpandedDataDownloader(args.config)
            
            # 如果提供了参数，更新下载器配置
            if args.symbols:
                downloader.symbols = args.symbols
            if args.interval != "30m":
                downloader.interval = args.interval
            if args.start_date:
                downloader.start_date = args.start_date
            if args.end_date:
                downloader.end_date = args.end_date
            
            downloader.download_all_data()
            print("✅ 数据下载完成!")
            
        elif args.command == 'align':
            print("🔄 开始对齐多交易所数据...")
            creator = MultiExchangeDatasetCreator()
            symbols = config.get_symbols()
            timeframes = config.get_timeframes()
            
            creator.create_dataset(symbols, timeframes)
            print("✅ 数据对齐完成!")
            
        elif args.command == 'backtest':
            print("🔄 开始套利回测...")
            run_backtest(
                symbols=args.symbols,
                timeframes=args.timeframes,
                config_path=args.config
            )
            print("✅ 套利回测完成!")
            
        elif args.command == 'full':
            print("🔄 开始运行完整流程...")
            
            # 1. 下载数据
            print("📥 步骤1: 下载数据...")
            downloader = MultiExchangeDataDownloader(args.config)
            symbols = config.get_symbols()
            downloader.run(symbols=symbols)
            
            # 2. 对齐数据
            print("📊 步骤2: 对齐数据...")
            creator = MultiExchangeDatasetCreator()
            timeframes = config.get_timeframes()
            creator.create_dataset(symbols, timeframes)
            
            # 3. 运行回测
            print("💰 步骤3: 运行套利回测...")
            run_backtest(
                symbols=symbols,
                timeframes=timeframes,
                config_path=args.config
            )
            
            print("✅ 完整流程执行完成!")
            
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()