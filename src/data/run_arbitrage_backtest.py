#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行套利系统回测 - 使用对齐数据集测试套利策略
"""

import sys
import os
# 修复导入路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from arbitrage_system import ArbitrageSystem
from datetime import datetime
import json
import pandas as pd
from typing import Dict, List

class ArbitrageBacktestRunner:
    def __init__(self):
        self.data_dir = 'data/aligned'
        self.results_dir = 'data/backtest_results'
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
        
        # 创建结果目录
        os.makedirs(self.results_dir, exist_ok=True)
        
    def run_single_symbol_backtest(self, symbol: str, config: Dict = None) -> Dict:
        """运行单个交易对的回测"""
        print(f"\n{'='*60}")
        print(f"运行 {symbol} 套利回测")
        print(f"{'='*60}")
        
        # 初始化套利系统
        arbitrage_system = ArbitrageSystem(config)
        
        # 数据文件路径
        data_file = os.path.join(self.data_dir, f"aligned_{symbol}_30m.csv")
        
        if not os.path.exists(data_file):
            return {
                'symbol': symbol,
                'status': 'error',
                'message': f'数据文件不存在: {data_file}'
            }
        
        try:
            # 运行回测
            results = arbitrage_system.run_backtest_direct(
                df=pd.read_csv(data_file, index_col=0, parse_dates=True),
                symbol=symbol,
                account_balance=100000  # 10万初始资金
            )
            
            # 添加配置信息
            results['config'] = config or arbitrage_system.config
            results['symbol'] = symbol
            results['data_file'] = data_file
            
            return results
            
        except Exception as e:
            return {
                'symbol': symbol,
                'status': 'error',
                'message': str(e)
            }
    
    def run_all_symbols_backtest(self, config: Dict = None) -> Dict:
        """运行所有交易对的回测"""
        print("🚀 开始运行套利系统回测")
        print(f"测试交易对: {', '.join(self.symbols)}")
        print(f"配置参数: {config}")
        
        all_results = {}
        
        for symbol in self.symbols:
            result = self.run_single_symbol_backtest(symbol, config)
            all_results[symbol] = result
            
            # 打印简要结果
            if result.get('status') == 'success':
                print(f"✅ {symbol}: {result['total_trades']} 笔交易, "
                      f"收益率: {result.get('return_rate', 0):.2%}, "
                      f"胜率: {result.get('win_rate', 0):.2%}")
            else:
                print(f"❌ {symbol}: {result.get('message', '未知错误')}")
        
        # 生成综合报告
        comprehensive_report = self.generate_comprehensive_report(all_results, config)
        
        return comprehensive_report
    
    def generate_comprehensive_report(self, results: Dict, config: Dict) -> Dict:
        """生成综合回测报告"""
        successful_results = [r for r in results.values() if r.get('status') == 'success']
        
        if not successful_results:
            return {
                'backtest_time': datetime.now().isoformat(),
                'config': config,
                'summary': {
                    'total_symbols': len(results),
                    'successful_symbols': 0,
                    'total_trades': 0,
                    'avg_return_rate': 0,
                    'avg_win_rate': 0
                },
                'results': results
            }
        
        # 计算汇总统计
        total_trades = sum(r.get('total_trades', 0) for r in successful_results)
        total_pnl = sum(r.get('total_pnl', 0) for r in successful_results)
        return_rates = [r.get('return_rate', 0) for r in successful_results]
        win_rates = [r.get('win_rate', 0) for r in successful_results]
        
        comprehensive_report = {
            'backtest_time': datetime.now().isoformat(),
            'config': config,
            'summary': {
                'total_symbols': len(results),
                'successful_symbols': len(successful_results),
                'total_trades': total_trades,
                'total_pnl': total_pnl,
                'avg_return_rate': sum(return_rates) / len(return_rates) if return_rates else 0,
                'avg_win_rate': sum(win_rates) / len(win_rates) if win_rates else 0,
                'best_performer': max(successful_results, key=lambda x: x.get('return_rate', 0)) if successful_results else None,
                'worst_performer': min(successful_results, key=lambda x: x.get('return_rate', 0)) if successful_results else None
            },
            'results': results
        }
        
        return comprehensive_report
    
    def save_backtest_report(self, report: Dict, filename: str = None):
        """保存回测报告"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"arbitrage_backtest_report_{timestamp}.json"
        
        filepath = os.path.join(self.results_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 回测报告已保存到: {filepath}")
        return filepath
    
    def print_comprehensive_summary(self, report: Dict):
        """打印综合回测摘要"""
        print(f"\n{'='*80}")
        print("📊 套利系统回测综合报告")
        print(f"{'='*80}")
        
        summary = report['summary']
        
        print(f"回测时间: {report['backtest_time']}")
        print(f"配置参数: {report['config']}")
        
        print(f"\n📈 总体统计:")
        print(f"  测试交易对: {summary['total_symbols']}")
        print(f"  成功交易对: {summary['successful_symbols']}")
        print(f"  总交易次数: {summary['total_trades']}")
        print(f"  总盈亏: ${summary['total_pnl']:.2f}")
        print(f"  平均收益率: {summary['avg_return_rate']:.2%}")
        print(f"  平均胜率: {summary['avg_win_rate']:.2%}")
        
        if summary['best_performer']:
            best = summary['best_performer']
            print(f"\n🏆 最佳表现:")
            print(f"  交易对: {best['symbol']}")
            print(f"  收益率: {best.get('return_rate', 0):.2%}")
            print(f"  交易次数: {best.get('total_trades', 0)}")
            print(f"  胜率: {best.get('win_rate', 0):.2%}")
        
        if summary['worst_performer']:
            worst = summary['worst_performer']
            print(f"\n📉 最差表现:")
            print(f"  交易对: {worst['symbol']}")
            print(f"  收益率: {worst.get('return_rate', 0):.2%}")
            print(f"  交易次数: {worst.get('total_trades', 0)}")
            print(f"  胜率: {worst.get('win_rate', 0):.2%}")
        
        # 详细结果
        print(f"\n{'='*80}")
        print("📋 详细回测结果")
        print(f"{'='*80}")
        
        for symbol, result in report['results'].items():
            print(f"\n📊 {symbol}:")
            
            if result.get('status') == 'success':
                print(f"  状态: ✅ 成功")
                print(f"  交易次数: {result.get('total_trades', 0)}")
                print(f"  总盈亏: ${result.get('total_pnl', 0):.2f}")
                print(f"  收益率: {result.get('return_rate', 0):.2%}")
                print(f"  胜率: {result.get('win_rate', 0):.2%}")
                print(f"  最大盈利: ${result.get('max_profit', 0):.2f}")
                print(f"  最大亏损: ${result.get('max_loss', 0):.2f}")
                print(f"  平均盈亏: ${result.get('avg_profit', 0):.2f}")
            else:
                print(f"  状态: ❌ 失败")
                print(f"  错误信息: {result.get('message', '未知错误')}")
    
    def run_parameter_optimization(self) -> Dict:
        """运行参数优化测试"""
        print("\n🔧 开始参数优化测试...")
        
        # 定义测试参数组合
        test_configs = [
            {
                'name': '保守策略',
                'config': {
                    'min_profit_threshold': 0.003,  # 0.3%
                    'max_positions': 3,
                    'position_timeout': 1800,     # 30分钟
                    'risk_max_drawdown': 0.02      # 2%
                }
            },
            {
                'name': '平衡策略',
                'config': {
                    'min_profit_threshold': 0.002,  # 0.2%
                    'max_positions': 5,
                    'position_timeout': 3600,     # 60分钟
                    'risk_max_drawdown': 0.05      # 5%
                }
            },
            {
                'name': '激进策略',
                'config': {
                    'min_profit_threshold': 0.001,  # 0.1%
                    'max_positions': 8,
                    'position_timeout': 7200,     # 120分钟
                    'risk_max_drawdown': 0.10      # 10%
                }
            }
        ]
        
        optimization_results = {}
        
        for test_config in test_configs:
            print(f"\n🧪 测试 {test_config['name']}...")
            config_name = test_config['name']
            config_params = test_config['config']
            
            # 运行回测
            report = self.run_all_symbols_backtest(config_params)
            optimization_results[config_name] = {
                'config': config_params,
                'report': report
            }
            
            # 打印简要结果
            summary = report['summary']
            print(f"  平均收益率: {summary['avg_return_rate']:.2%}")
            print(f"  平均胜率: {summary['avg_win_rate']:.2%}")
            print(f"  总交易次数: {summary['total_trades']}")
        
        # 找出最佳配置
        best_config = None
        best_return = -float('inf')
        
        for config_name, result in optimization_results.items():
            avg_return = result['report']['summary']['avg_return_rate']
            if avg_return > best_return:
                best_return = avg_return
                best_config = config_name
        
        optimization_summary = {
            'optimization_time': datetime.now().isoformat(),
            'test_configs': test_configs,
            'results': optimization_results,
            'best_config': best_config,
            'best_return_rate': best_return
        }
        
        # 保存优化结果
        opt_filename = f"parameter_optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        opt_filepath = os.path.join(self.results_dir, opt_filename)
        
        with open(opt_filepath, 'w', encoding='utf-8') as f:
            json.dump(optimization_summary, f, indent=2, default=str)
        
        print(f"\n🏆 最佳配置: {best_config}")
        print(f"   最佳收益率: {best_return:.2%}")
        print(f"📄 优化报告已保存到: {opt_filepath}")
        
        return optimization_summary

def main():
    """主函数"""
    runner = ArbitrageBacktestRunner()
    
    try:
        # 直接运行标准回测
        print("\n🔄 运行标准回测...")
        report = runner.run_all_symbols_backtest()
        runner.save_backtest_report(report)
        runner.print_comprehensive_summary(report)
            
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")
    except Exception as e:
        print(f"\n❌ 运行失败: {e}")
    
    print(f"\n🎉 套利系统回测完成！")

def run_backtest(symbols=None, timeframes=None, config_path="config/config.ini"):
    """简化的回测函数，供main.py调用"""
    if symbols is None:
        symbols = ['BTCUSDT', 'ETHUSDT']
    if timeframes is None:
        timeframes = ['30m', '1h']
    
    print("🚀 开始运行套利回测...")
    print(f"交易对: {symbols}")
    print(f"时间框架: {timeframes}")
    
    runner = ArbitrageBacktestRunner()
    
    # 为每个交易对和时间框架运行回测
    all_results = {}
    
    for symbol in symbols:
        symbol_results = {}
        
        for timeframe in timeframes:
            print(f"\n📊 运行 {symbol} {timeframe} 回测...")
            
            # 数据文件路径
            data_file = f"data/aligned/{symbol}_{timeframe}_aligned.csv"
            
            if not os.path.exists(data_file):
                print(f"❌ 数据文件不存在: {data_file}")
                continue
            
            try:
                # 初始化套利系统
                arbitrage_system = ArbitrageSystem()
                
                # 运行回测
                results = arbitrage_system.run_backtest_direct(
                    df=pd.read_csv(data_file, index_col=0, parse_dates=True),
                    symbol=symbol,
                    account_balance=100000
                )
                
                # 打印结果
                if results.get('status') == 'success':
                    print(f"✅ {symbol} {timeframe}: {results['total_trades']} 笔交易, "
                          f"收益率: {results.get('return_rate', 0):.2%}, "
                          f"胜率: {results.get('win_rate', 0):.2%}")
                else:
                    print(f"❌ {symbol} {timeframe}: {results.get('message', '未知错误')}")
                
                symbol_results[timeframe] = results
                
            except Exception as e:
                print(f"❌ {symbol} {timeframe} 回测失败: {e}")
                symbol_results[timeframe] = {'status': 'error', 'message': str(e)}
        
        all_results[symbol] = symbol_results
    
    # 保存结果
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"backtest_results_{timestamp}.json"
    filepath = os.path.join(runner.results_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, default=str)
    
    print(f"\n📄 回测结果已保存到: {filepath}")
    
    # 打印总体摘要
    print(f"\n{'='*80}")
    print("📊 总体回测摘要")
    print(f"{'='*80}")
    
    for symbol, symbol_results in all_results.items():
        for timeframe, results in symbol_results.items():
            if results.get('status') == 'success':
                print(f"{symbol}_{timeframe}: 收益率 {results.get('return_rate', 0):.2%}, "
                      f"夏普比率 {results.get('sharpe_ratio', 0):.2f}, "
                      f"胜率 {results.get('win_rate', 0):.2%}")
    
    return all_results

if __name__ == "__main__":
    main()