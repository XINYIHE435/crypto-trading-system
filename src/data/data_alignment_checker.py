#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据对齐检查器 - 验证多交易所数据的时间戳对齐情况
"""

import pandas as pd
import os
from datetime import datetime
import json
from typing import Dict, List, Tuple

class DataAlignmentChecker:
    def __init__(self):
        self.data_dir = 'data/raw/klines'
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
        self.exchanges = ['binance', 'bybit', 'okx', 'huobi', 'kucoin']
        
    def load_data(self, symbol: str, exchange: str) -> pd.DataFrame:
        """加载数据文件"""
        filename = f"{exchange}_{symbol}_30m.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        if not os.path.exists(filepath):
            return None
            
        try:
            df = pd.read_csv(filepath)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        except Exception as e:
            print(f"加载 {filepath} 失败: {e}")
            return None
    
    def check_symbol_alignment(self, symbol: str) -> Dict:
        """检查单个交易对的数据对齐情况"""
        print(f"\n{'='*60}")
        print(f"检查 {symbol} 数据对齐情况")
        print(f"{'='*60}")
        
        symbol_data = {}
        time_ranges = {}
        
        # 加载所有交易所的数据
        for exchange in self.exchanges:
            df = self.load_data(symbol, exchange)
            if df is not None and len(df) > 0:
                symbol_data[exchange] = df
                time_ranges[exchange] = {
                    'start': df['timestamp'].min(),
                    'end': df['timestamp'].max(),
                    'count': len(df)
                }
                print(f"{exchange.upper()}: {len(df)} 条记录, {time_ranges[exchange]['start']} 到 {time_ranges[exchange]['end']}")
            else:
                print(f"{exchange.upper()}: 无数据")
        
        if len(symbol_data) < 2:
            return {'symbol': symbol, 'status': 'insufficient_data', 'exchanges': list(symbol_data.keys())}
        
        # 找到共同的时间范围
        all_starts = [info['start'] for info in time_ranges.values()]
        all_ends = [info['end'] for info in time_ranges.values()]
        
        common_start = max(all_starts)
        common_end = min(all_ends)
        
        print(f"\n共同时间范围: {common_start} 到 {common_end}")
        
        # 检查每个交易所在共同时间范围内的数据
        alignment_results = {}
        common_timestamps = None
        
        for exchange, df in symbol_data.items():
            # 筛选共同时间范围内的数据
            common_df = df[(df['timestamp'] >= common_start) & (df['timestamp'] <= common_end)]
            
            if common_timestamps is None:
                common_timestamps = set(common_df['timestamp'])
            else:
                common_timestamps &= set(common_df['timestamp'])
            
            alignment_results[exchange] = {
                'total_count': len(df),
                'common_range_count': len(common_df),
                'missing_in_common': len(df) - len(common_df)
            }
        
        # 转换为排序的时间戳列表
        common_timestamps = sorted(list(common_timestamps))
        
        # 检查时间戳对齐情况
        alignment_summary = {
            'symbol': symbol,
            'common_time_range': {
                'start': str(common_start),
                'end': str(common_end)
            },
            'common_timestamps_count': len(common_timestamps),
            'exchanges': alignment_results,
            'time_alignment': {}
        }
        
        # 检查时间间隔
        if len(common_timestamps) > 1:
            time_diffs = [(common_timestamps[i+1] - common_timestamps[i]).total_seconds() / 60 
                         for i in range(len(common_timestamps)-1)]
            unique_intervals = set(time_diffs)
            alignment_summary['time_alignment'] = {
                'intervals_minutes': list(unique_intervals),
                'is_consistent': len(unique_intervals) == 1,
                'expected_interval': 30  # 30分钟
            }
        
        # 计算对齐率
        for exchange in alignment_results:
            total_possible = len(common_timestamps)
            if total_possible > 0:
                # 检查该交易所在共同时间戳上的数据完整性
                exchange_df = symbol_data[exchange]
                exchange_timestamps = set(exchange_df[exchange_df['timestamp'].isin(common_timestamps)]['timestamp'])
                aligned_count = len(exchange_timestamps)
                alignment_results[exchange]['alignment_rate'] = aligned_count / total_possible
                alignment_results[exchange]['aligned_count'] = aligned_count
        
        return alignment_summary
    
    def check_all_symbols(self) -> Dict:
        """检查所有交易对的数据对齐情况"""
        print("🔍 开始检查多交易所数据对齐情况")
        print(f"检查目录: {self.data_dir}")
        print(f"交易对: {', '.join(self.symbols)}")
        print(f"交易所: {', '.join(self.exchanges)}")
        
        results = {}
        
        for symbol in self.symbols:
            results[symbol] = self.check_symbol_alignment(symbol)
        
        # 生成总体报告
        overall_report = {
            'check_time': datetime.now().isoformat(),
            'symbols': results,
            'summary': self.generate_summary(results)
        }
        
        return overall_report
    
    def generate_summary(self, results: Dict) -> Dict:
        """生成对齐情况摘要"""
        summary = {
            'total_symbols': len(results),
            'successful_checks': 0,
            'alignment_issues': [],
            'best_aligned_symbols': [],
            'worst_aligned_symbols': []
        }
        
        symbol_alignment_rates = {}
        
        for symbol, result in results.items():
            if result.get('status') != 'insufficient_data':
                summary['successful_checks'] += 1
                
                # 计算平均对齐率
                exchanges = result.get('exchanges', {})
                if exchanges:
                    avg_alignment = sum(info.get('alignment_rate', 0) for info in exchanges.values()) / len(exchanges)
                    symbol_alignment_rates[symbol] = avg_alignment
                    
                    # 检查时间对齐问题
                    time_alignment = result.get('time_alignment', {})
                    if not time_alignment.get('is_consistent', True):
                        summary['alignment_issues'].append({
                            'symbol': symbol,
                            'issue': 'inconsistent_time_intervals',
                            'details': time_alignment.get('intervals_minutes', [])
                        })
        
        # 找出对齐最好和最差的交易对
        if symbol_alignment_rates:
            sorted_symbols = sorted(symbol_alignment_rates.items(), key=lambda x: x[1], reverse=True)
            summary['best_aligned_symbols'] = sorted_symbols[:3]
            summary['worst_aligned_symbols'] = sorted_symbols[-3:]
        
        return summary
    
    def save_report(self, report: Dict, filename: str = 'data/alignment_report.json'):
        """保存对齐报告"""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 对齐报告已保存到: {filename}")
    
    def print_summary(self, report: Dict):
        """打印对齐摘要"""
        print(f"\n{'='*80}")
        print("📊 数据对齐摘要报告")
        print(f"{'='*80}")
        
        summary = report['summary']
        print(f"检查时间: {report['check_time']}")
        print(f"总交易对数: {summary['total_symbols']}")
        print(f"成功检查数: {summary['successful_checks']}")
        
        if summary['alignment_issues']:
            print(f"\n⚠️  发现 {len(summary['alignment_issues'])} 个对齐问题:")
            for issue in summary['alignment_issues']:
                print(f"  - {issue['symbol']}: {issue['issue']}")
        
        if summary['best_aligned_symbols']:
            print(f"\n✅ 对齐最好的交易对:")
            for symbol, rate in summary['best_aligned_symbols']:
                print(f"  - {symbol}: {rate:.2%}")
        
        if summary['worst_aligned_symbols']:
            print(f"\n❌ 对齐最差的交易对:")
            for symbol, rate in summary['worst_aligned_symbols']:
                print(f"  - {symbol}: {rate:.2%}")
        
        # 详细对齐信息
        print(f"\n{'='*80}")
        print("📋 详细对齐信息")
        print(f"{'='*80}")
        
        for symbol, result in report['symbols'].items():
            if result.get('status') == 'insufficient_data':
                print(f"\n❌ {symbol}: 数据不足")
                continue
                
            print(f"\n📈 {symbol}:")
            print(f"  共同时间范围: {result['common_time_range']['start']} 到 {result['common_time_range']['end']}")
            print(f"  共同时间戳数: {result['common_timestamps_count']}")
            
            time_alignment = result.get('time_alignment', {})
            if time_alignment:
                is_consistent = time_alignment.get('is_consistent', False)
                intervals = time_alignment.get('intervals_minutes', [])
                print(f"  时间间隔一致性: {'✅' if is_consistent else '❌'} ({intervals})")
            
            print(f"  交易所对齐情况:")
            for exchange, info in result['exchanges'].items():
                alignment_rate = info.get('alignment_rate', 0)
                aligned_count = info.get('aligned_count', 0)
                total_count = info.get('total_count', 0)
                print(f"    {exchange.upper()}: {aligned_count}/{total_count} ({alignment_rate:.2%})")

def main():
    """主函数"""
    checker = DataAlignmentChecker()
    
    # 检查所有交易对的数据对齐情况
    report = checker.check_all_symbols()
    
    # 保存报告
    checker.save_report(report)
    
    # 打印摘要
    checker.print_summary(report)
    
    print(f"\n🎉 数据对齐检查完成！")

if __name__ == "__main__":
    main()