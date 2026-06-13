#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多交易所套利系统主程序
整合数据下载、套利回测等功能
"""
import sys
import os
import argparse
from pathlib import Path

# 设置 Windows 控制台编码
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'ignore')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'ignore')

# 添加src目录到Python路径
sys.path.append(str(Path(__file__).parent / "src"))

# 导入各个功能模块
from src.arbitrage_system import ArbitrageSystem, ArbitrageConfig
from src.data.run_arbitrage_backtest import ArbitrageBacktestRunner


def main():
    parser = argparse.ArgumentParser(description="多交易所套利系统")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 数据下载命令
    download_parser = subparsers.add_parser('download', help='下载多交易所数据')
    download_parser.add_argument("--days", type=int, default=30, help="下载天数，默认: 30")
    
    # 套利回测命令
    backtest_parser = subparsers.add_parser('backtest', help='运行套利回测')
    backtest_parser.add_argument("--symbols", nargs="+",
                                 default=["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"],
                                 help="交易对列表")
    backtest_parser.add_argument("--X", type=float, default=0.5, help="差价触发阈值 (%)")
    backtest_parser.add_argument("--Y", type=float, default=0.1, help="资金费率差触发阈值 (%)")
    backtest_parser.add_argument("--optimize", action="store_true", help="运行参数优化")
    backtest_parser.add_argument("--debug", action="store_true", help="启用调试模式，显示详细信息")
    
    # 完整流程命令
    full_parser = subparsers.add_parser('full', help='运行完整流程：下载->回测')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'download':
            print("🔄 开始下载多交易所数据...")
            # 使用根目录的下载脚本
            from data.download_and_align_data import CompleteDataDownloader
            downloader = CompleteDataDownloader()
            downloader.days = args.days
            downloader.download_all()
            print("✅ 数据下载完成!")
            
        elif args.command == 'backtest':
            print("🔄 开始套利回测...")

            # 创建配置
            config = ArbitrageConfig(
                X=args.X,
                Y=args.Y
            )

            # 创建回测运行器
            runner = ArbitrageBacktestRunner(config)
            runner.symbols = args.symbols

            if args.optimize:
                # 运行参数优化
                runner.run_parameter_optimization()
            else:
                # 运行标准回测
                # 如果启用调试模式，只测试第一个交易对
                if args.debug:
                    print(f"\n⚠️ 调试模式：仅测试 {args.symbols[0]}")
                    result = runner.run_single_backtest(args.symbols[0], config, debug=True)
                    print(f"\n✅ 调试完成")
                    if result.get('status') == 'success':
                        print(f"📊 结果: {result['total_trades']}笔交易")
                else:
                    report = runner.run_all_symbols()
                    runner.print_summary(report)
                    runner.save_results(report)

                    # 生成可视化图表
                    runner.generate_visualizations(report)

            print("✅ 套利回测完成!")
            
        elif args.command == 'full':
            print("🔄 开始运行完整流程...")
            
            # 1. 下载数据
            print("\n📥 步骤1: 下载数据...")
            from data.download_and_align_data import CompleteDataDownloader
            downloader = CompleteDataDownloader()
            downloader.download_all()
            
            # 2. 运行回测
            print("\n💰 步骤2: 运行套利回测...")
            config = ArbitrageConfig()
            runner = ArbitrageBacktestRunner(config)
            report = runner.run_all_symbols()
            runner.print_summary(report)
            runner.save_results(report)
            
            print("\n✅ 完整流程执行完成!")
            
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
