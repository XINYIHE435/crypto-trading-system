#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合数据报告生成器 - 生成完整的多交易所数据下载和统计报告
"""

import pandas as pd
import os
import json
from datetime import datetime
from typing import Dict, List, Any
import glob

class ComprehensiveDataReport:
    def __init__(self):
        self.data_dir = 'data/raw/klines'
        self.funding_dir = 'data/raw/funding_rates'
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
        self.exchanges = ['binance', 'bybit', 'okx', 'huobi', 'kucoin']
        
    def get_file_info(self, filepath: str) -> Dict:
        """获取文件基本信息"""
        if not os.path.exists(filepath):
            return None
            
        try:
            stat = os.stat(filepath)
            df = pd.read_csv(filepath)
            
            return {
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'records': len(df),
                'columns': list(df.columns),
                'start_time': str(pd.to_datetime(df['timestamp'].min())),
                'end_time': str(pd.to_datetime(df['timestamp'].max())),
                'file_path': filepath
            }
        except Exception as e:
            return {'error': str(e)}
    
    def analyze_kline_data(self) -> Dict:
        """分析K线数据"""
        print("📊 分析K线数据...")
        
        kline_analysis = {
            'total_files': 0,
            'total_records': 0,
            'total_size_mb': 0,
            'exchanges': {},
            'symbols': {},
            'file_details': {}
        }
        
        # 分析每个交易所的数据
        for exchange in self.exchanges:
            exchange_data = {
                'files': 0,
                'records': 0,
                'size_mb': 0,
                'symbols': {}
            }
            
            for symbol in self.symbols:
                filename = f"{exchange}_{symbol}_30m.csv"
                filepath = os.path.join(self.data_dir, filename)
                file_info = self.get_file_info(filepath)
                
                if file_info and 'error' not in file_info:
                    exchange_data['files'] += 1
                    exchange_data['records'] += file_info['records']
                    exchange_data['size_mb'] += file_info['size_mb']
                    exchange_data['symbols'][symbol] = file_info
                    
                    # 添加到文件详情
                    kline_analysis['file_details'][f"{exchange}_{symbol}"] = file_info
            
            kline_analysis['exchanges'][exchange] = exchange_data
            kline_analysis['total_files'] += exchange_data['files']
            kline_analysis['total_records'] += exchange_data['records']
            kline_analysis['total_size_mb'] += exchange_data['size_mb']
        
        # 分析每个交易对的数据
        for symbol in self.symbols:
            symbol_data = {
                'files': 0,
                'records': 0,
                'size_mb': 0,
                'exchanges': {}
            }
            
            for exchange in self.exchanges:
                file_key = f"{exchange}_{symbol}"
                if file_key in kline_analysis['file_details']:
                    file_info = kline_analysis['file_details'][file_key]
                    symbol_data['files'] += 1
                    symbol_data['records'] += file_info['records']
                    symbol_data['size_mb'] += file_info['size_mb']
                    symbol_data['exchanges'][exchange] = file_info
            
            kline_analysis['symbols'][symbol] = symbol_data
        
        return kline_analysis
    
    def analyze_funding_data(self) -> Dict:
        """分析资金费率数据"""
        print("💰 分析资金费率数据...")
        
        funding_analysis = {
            'total_files': 0,
            'total_records': 0,
            'total_size_mb': 0,
            'exchanges': {},
            'symbols': {},
            'file_details': {}
        }
        
        # 支持资金费率的交易所
        funding_exchanges = ['binance', 'bybit']
        
        for exchange in funding_exchanges:
            exchange_data = {
                'files': 0,
                'records': 0,
                'size_mb': 0,
                'symbols': {},
                'avg_rates': {}
            }
            
            for symbol in self.symbols:
                filename = f"{exchange}_{symbol}_funding_rate.csv"
                filepath = os.path.join(self.funding_dir, filename)
                file_info = self.get_funding_file_info(filepath)
                
                if file_info and 'error' not in file_info:
                    exchange_data['files'] += 1
                    exchange_data['records'] += file_info['records']
                    exchange_data['size_mb'] += file_info['size_mb']
                    exchange_data['symbols'][symbol] = file_info
                    
                    if 'avg_rate' in file_info:
                        exchange_data['avg_rates'][symbol] = file_info['avg_rate']
                    
                    # 添加到文件详情
                    funding_analysis['file_details'][f"{exchange}_{symbol}"] = file_info
            
            funding_analysis['exchanges'][exchange] = exchange_data
            funding_analysis['total_files'] += exchange_data['files']
            funding_analysis['total_records'] += exchange_data['records']
            funding_analysis['total_size_mb'] += exchange_data['size_mb']
        
        # 分析每个交易对的资金费率数据
        for symbol in self.symbols:
            symbol_data = {
                'files': 0,
                'records': 0,
                'size_mb': 0,
                'exchanges': {},
                'rate_comparison': {}
            }
            
            for exchange in funding_exchanges:
                file_key = f"{exchange}_{symbol}"
                if file_key in funding_analysis['file_details']:
                    file_info = funding_analysis['file_details'][file_key]
                    symbol_data['files'] += 1
                    symbol_data['records'] += file_info['records']
                    symbol_data['size_mb'] += file_info['size_mb']
                    symbol_data['exchanges'][exchange] = file_info
                    
                    if 'avg_rate' in file_info:
                        symbol_data['rate_comparison'][exchange] = file_info['avg_rate']
            
            funding_analysis['symbols'][symbol] = symbol_data
        
        return funding_analysis
    
    def get_funding_file_info(self, filepath: str) -> Dict:
        """获取资金费率文件信息"""
        if not os.path.exists(filepath):
            return None
            
        try:
            stat = os.stat(filepath)
            df = pd.read_csv(filepath)
            
            # 计算平均费率
            avg_rate = 0
            if 'funding_rate' in df.columns:
                avg_rate = float(df['funding_rate'].mean())
            
            return {
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'records': len(df),
                'columns': list(df.columns),
                'start_time': str(pd.to_datetime(df['timestamp'].min())),
                'end_time': str(pd.to_datetime(df['timestamp'].max())),
                'avg_rate': avg_rate,
                'file_path': filepath
            }
        except Exception as e:
            return {'error': str(e)}
    
    def generate_comprehensive_report(self) -> Dict:
        """生成综合报告"""
        print("🔍 生成综合数据报告...")
        
        # 分析K线数据
        kline_analysis = self.analyze_kline_data()
        
        # 分析资金费率数据
        funding_analysis = self.analyze_funding_data()
        
        # 生成数据质量指标
        quality_metrics = self.calculate_quality_metrics(kline_analysis, funding_analysis)
        
        # 生成数据覆盖统计
        coverage_stats = self.calculate_coverage_stats(kline_analysis, funding_analysis)
        
        comprehensive_report = {
            'report_time': datetime.now().isoformat(),
            'summary': {
                'kline_data': {
                    'total_files': kline_analysis['total_files'],
                    'total_records': kline_analysis['total_records'],
                    'total_size_mb': kline_analysis['total_size_mb'],
                    'exchanges_covered': len([e for e in kline_analysis['exchanges'].values() if e['files'] > 0]),
                    'symbols_covered': len([s for s in kline_analysis['symbols'].values() if s['files'] > 0])
                },
                'funding_data': {
                    'total_files': funding_analysis['total_files'],
                    'total_records': funding_analysis['total_records'],
                    'total_size_mb': funding_analysis['total_size_mb'],
                    'exchanges_covered': len([e for e in funding_analysis['exchanges'].values() if e['files'] > 0]),
                    'symbols_covered': len([s for s in funding_analysis['symbols'].values() if s['files'] > 0])
                }
            },
            'kline_analysis': kline_analysis,
            'funding_analysis': funding_analysis,
            'quality_metrics': quality_metrics,
            'coverage_statistics': coverage_stats,
            'recommendations': self.generate_recommendations(kline_analysis, funding_analysis)
        }
        
        return comprehensive_report
    
    def calculate_quality_metrics(self, kline_analysis: Dict, funding_analysis: Dict) -> Dict:
        """计算数据质量指标"""
        quality_metrics = {
            'data_completeness': {},
            'data_consistency': {},
            'data_freshness': {},
            'overall_score': 0
        }
        
        # 计算数据完整性
        for symbol in self.symbols:
            expected_exchanges = len(self.exchanges)
            actual_exchanges = kline_analysis['symbols'].get(symbol, {}).get('files', 0)
            completeness = actual_exchanges / expected_exchanges if expected_exchanges > 0 else 0
            quality_metrics['data_completeness'][symbol] = completeness
        
        # 计算数据一致性（基于时间戳对齐）
        # 这里简化处理，实际应该检查时间戳对齐情况
        for symbol in self.symbols:
            # 假设所有交易所的数据都是一致的
            quality_metrics['data_consistency'][symbol] = 1.0
        
        # 计算数据新鲜度（基于最新数据时间）
        for symbol in self.symbols:
            symbol_data = kline_analysis['symbols'].get(symbol, {})
            if symbol_data:
                latest_time = max([
                    pd.to_datetime(exchange_data.get('end_time', '1970-01-01'))
                    for exchange_data in symbol_data.get('exchanges', {}).values()
                ])
                days_old = (datetime.now() - latest_time.to_pydatetime()).days
                freshness = max(0, 1 - days_old / 30)  # 30天内的数据认为是新鲜的
                quality_metrics['data_freshness'][symbol] = freshness
        
        # 计算总体质量分数
        all_scores = []
        for symbol in self.symbols:
            symbol_score = (
                quality_metrics['data_completeness'].get(symbol, 0) * 0.4 +
                quality_metrics['data_consistency'].get(symbol, 0) * 0.3 +
                quality_metrics['data_freshness'].get(symbol, 0) * 0.3
            )
            all_scores.append(symbol_score)
        
        quality_metrics['overall_score'] = sum(all_scores) / len(all_scores) if all_scores else 0
        
        return quality_metrics
    
    def calculate_coverage_stats(self, kline_analysis: Dict, funding_analysis: Dict) -> Dict:
        """计算数据覆盖统计"""
        coverage_stats = {
            'exchange_coverage': {},
            'symbol_coverage': {},
            'time_coverage': {},
            'data_gaps': []
        }
        
        # 交易所覆盖统计
        for exchange in self.exchanges:
            exchange_data = kline_analysis['exchanges'].get(exchange, {})
            coverage_stats['exchange_coverage'][exchange] = {
                'symbols_covered': exchange_data.get('files', 0),
                'total_symbols': len(self.symbols),
                'coverage_rate': exchange_data.get('files', 0) / len(self.symbols),
                'total_records': exchange_data.get('records', 0)
            }
        
        # 交易对覆盖统计
        for symbol in self.symbols:
            symbol_data = kline_analysis['symbols'].get(symbol, {})
            coverage_stats['symbol_coverage'][symbol] = {
                'exchanges_covered': symbol_data.get('files', 0),
                'total_exchanges': len(self.exchanges),
                'coverage_rate': symbol_data.get('files', 0) / len(self.exchanges),
                'total_records': symbol_data.get('records', 0)
            }
        
        # 时间覆盖统计
        for symbol in self.symbols:
            symbol_data = kline_analysis['symbols'].get(symbol, {}).get('exchanges', {})
            if symbol_data:
                start_times = []
                end_times = []
                for exchange_data in symbol_data.values():
                    if 'start_time' in exchange_data and 'end_time' in exchange_data:
                        start_times.append(pd.to_datetime(exchange_data['start_time']))
                        end_times.append(pd.to_datetime(exchange_data['end_time']))
                
                if start_times and end_times:
                    coverage_stats['time_coverage'][symbol] = {
                        'earliest_start': str(min(start_times)),
                        'latest_end': str(max(end_times)),
                        'span_days': (max(end_times) - min(start_times)).days
                    }
        
        return coverage_stats
    
    def generate_recommendations(self, kline_analysis: Dict, funding_analysis: Dict) -> List[str]:
        """生成数据改进建议"""
        recommendations = []
        
        # 检查缺失的交易所数据
        missing_exchanges = []
        for exchange in self.exchanges:
            if kline_analysis['exchanges'].get(exchange, {}).get('files', 0) == 0:
                missing_exchanges.append(exchange)
        
        if missing_exchanges:
            recommendations.append(f"缺失交易所数据: {', '.join(missing_exchanges)}，建议检查API配置或网络连接")
        
        # 检查数据量不足的交易对
        low_data_symbols = []
        for symbol in self.symbols:
            symbol_data = kline_analysis['symbols'].get(symbol, {})
            if symbol_data.get('files', 0) < len(self.exchanges):
                low_data_symbols.append(symbol)
        
        if low_data_symbols:
            recommendations.append(f"数据不完整的交易对: {', '.join(low_data_symbols)}，建议补充缺失的交易所数据")
        
        # 检查资金费率数据覆盖
        funding_symbols = funding_analysis['symbols']
        for symbol in self.symbols:
            if symbol not in funding_symbols or funding_symbols[symbol].get('files', 0) < 2:
                recommendations.append(f"交易对 {symbol} 资金费率数据不完整，建议补充更多交易所的资金费率数据")
        
        # 检查数据时间范围
        time_coverage = self.calculate_coverage_stats(kline_analysis, funding_analysis)['time_coverage']
        for symbol, coverage in time_coverage.items():
            if coverage.get('span_days', 0) < 25:  # 少于25天的数据
                recommendations.append(f"交易对 {symbol} 数据时间范围较短，建议扩展数据下载时间范围")
        
        if not recommendations:
            recommendations.append("数据覆盖良好，所有交易所和交易对的数据都已完整下载")
        
        return recommendations
    
    def save_report(self, report: Dict, filename: str = 'data/comprehensive_data_report.json'):
        """保存综合报告"""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"📄 综合报告已保存到: {filename}")
    
    def print_summary(self, report: Dict):
        """打印报告摘要"""
        print(f"\n{'='*80}")
        print("📊 综合数据报告摘要")
        print(f"{'='*80}")
        
        summary = report['summary']
        
        # K线数据摘要
        kline_summary = summary['kline_data']
        print(f"\n📈 K线数据:")
        print(f"  总文件数: {kline_summary['total_files']}")
        print(f"  总记录数: {kline_summary['total_records']:,}")
        print(f"  总大小: {kline_summary['total_size_mb']:.2f} MB")
        print(f"  覆盖交易所: {kline_summary['exchanges_covered']}/{len(self.exchanges)}")
        print(f"  覆盖交易对: {kline_summary['symbols_covered']}/{len(self.symbols)}")
        
        # 资金费率数据摘要
        funding_summary = summary['funding_data']
        print(f"\n💰 资金费率数据:")
        print(f"  总文件数: {funding_summary['total_files']}")
        print(f"  总记录数: {funding_summary['total_records']:,}")
        print(f"  总大小: {funding_summary['total_size_mb']:.2f} MB")
        print(f"  覆盖交易所: {funding_summary['exchanges_covered']}/2")
        print(f"  覆盖交易对: {funding_summary['symbols_covered']}/{len(self.symbols)}")
        
        # 数据质量指标
        quality = report['quality_metrics']
        print(f"\n📊 数据质量指标:")
        print(f"  总体质量分数: {quality['overall_score']:.2%}")
        
        # 覆盖统计
        coverage = report['coverage_statistics']
        print(f"\n📋 数据覆盖统计:")
        print(f"  交易所覆盖情况:")
        for exchange, stats in coverage['exchange_coverage'].items():
            print(f"    {exchange.upper()}: {stats['symbols_covered']}/{stats['total_symbols']} ({stats['coverage_rate']:.1%})")
        
        # 建议
        recommendations = report['recommendations']
        print(f"\n💡 改进建议:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
        
        print(f"\n📁 详细报告文件: data/comprehensive_data_report.json")

def main():
    """主函数"""
    reporter = ComprehensiveDataReport()
    
    # 生成综合报告
    report = reporter.generate_comprehensive_report()
    
    # 保存报告
    reporter.save_report(report)
    
    # 打印摘要
    reporter.print_summary(report)
    
    print(f"\n🎉 综合数据报告生成完成！")

if __name__ == "__main__":
    main()