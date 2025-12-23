#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据对齐功能测试器 - 测试多交易所数据对齐和套利逻辑
"""

import pandas as pd
import os
from datetime import datetime
import json
from typing import Dict, List, Tuple, Optional
import numpy as np

class DataAlignmentTester:
    def __init__(self):
        self.data_dir = 'data/raw/klines'
        self.funding_dir = 'data/raw/funding_rates'
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
        self.exchanges = ['binance', 'bybit', 'okx', 'huobi', 'kucoin']
        
    def load_aligned_data(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """加载对齐后的数据"""
        aligned_data = {}
        
        # 加载每个交易所的数据
        for exchange in self.exchanges:
            filename = f"{exchange}_{symbol}_30m.csv"
            filepath = os.path.join(self.data_dir, filename)
            
            if os.path.exists(filepath):
                try:
                    df = pd.read_csv(filepath)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df.set_index('timestamp', inplace=True)
                    aligned_data[exchange] = df
                except Exception as e:
                    print(f"加载 {filepath} 失败: {e}")
        
        return aligned_data
    
    def find_common_timestamps(self, data_dict: Dict[str, pd.DataFrame]) -> List[datetime]:
        """找到所有交易所共同的时间戳"""
        if not data_dict:
            return []
        
        # 获取第一个交易所的时间戳集合
        common_timestamps = set(data_dict[list(data_dict.keys())[0]].index)
        
        # 找到所有交易所的交集
        for exchange, df in data_dict.items():
            common_timestamps &= set(df.index)
        
        return sorted(list(common_timestamps))
    
    def create_aligned_dataset(self, symbol: str) -> Optional[pd.DataFrame]:
        """创建对齐后的数据集"""
        print(f"\n🔄 创建 {symbol} 对齐数据集...")
        
        # 加载数据
        data_dict = self.load_aligned_data(symbol)
        
        if len(data_dict) < 2:
            print(f"❌ {symbol} 数据不足，无法创建对齐数据集")
            return None
        
        # 找到共同时间戳
        common_timestamps = self.find_common_timestamps(data_dict)
        
        if not common_timestamps:
            print(f"❌ {symbol} 没有共同时间戳")
            return None
        
        print(f"✅ 找到 {len(common_timestamps)} 个共同时间戳")
        
        # 创建对齐后的数据集
        aligned_data = []
        
        for timestamp in common_timestamps:
            row = {'timestamp': timestamp}
            
            # 添加每个交易所的价格数据
            for exchange in self.exchanges:
                if exchange in data_dict:
                    df = data_dict[exchange]
                    if timestamp in df.index:
                        row[f'{exchange}_open'] = df.loc[timestamp, 'open']
                        row[f'{exchange}_high'] = df.loc[timestamp, 'high']
                        row[f'{exchange}_low'] = df.loc[timestamp, 'low']
                        row[f'{exchange}_close'] = df.loc[timestamp, 'close']
                        row[f'{exchange}_volume'] = df.loc[timestamp, 'volume']
                    else:
                        # 如果某个时间戳缺失，填充NaN
                        for col in ['open', 'high', 'low', 'close', 'volume']:
                            row[f'{exchange}_{col}'] = np.nan
            
            aligned_data.append(row)
        
        aligned_df = pd.DataFrame(aligned_data)
        aligned_df.set_index('timestamp', inplace=True)
        
        return aligned_df
    
    def calculate_price_differences(self, aligned_df: pd.DataFrame) -> pd.DataFrame:
        """计算交易所之间的价格差异"""
        if aligned_df.empty:
            return pd.DataFrame()
        
        price_diff_df = aligned_df.copy()
        
        # 计算所有交易所对之间的价格差异
        exchange_pairs = []
        for i, exchange1 in enumerate(self.exchanges):
            for j, exchange2 in enumerate(self.exchanges):
                if i < j:  # 避免重复计算
                    close1_col = f'{exchange1}_close'
                    close2_col = f'{exchange2}_close'
                    
                    if close1_col in aligned_df.columns and close2_col in aligned_df.columns:
                        # 绝对价格差异
                        price_diff_df[f'{exchange1}_vs_{exchange2}_diff'] = (
                            aligned_df[close1_col] - aligned_df[close2_col]
                        )
                        
                        # 相对价格差异（百分比）
                        price_diff_df[f'{exchange1}_vs_{exchange2}_pct'] = (
                            (aligned_df[close1_col] - aligned_df[close2_col]) / aligned_df[close2_col] * 100
                        )
                        
                        exchange_pairs.append(f"{exchange1}_vs_{exchange2}")
        
        return price_diff_df, exchange_pairs
    
    def identify_arbitrage_opportunities(self, price_diff_df: pd.DataFrame, 
                                    exchange_pairs: List[str], 
                                    threshold_pct: float = 0.1) -> pd.DataFrame:
        """识别套利机会"""
        if price_diff_df.empty:
            return pd.DataFrame()
        
        opportunities = []
        
        for pair in exchange_pairs:
            pct_col = f'{pair}_pct'
            diff_col = f'{pair}_diff'
            
            if pct_col in price_diff_df.columns:
                # 找到超过阈值的套利机会
                high_opportunities = price_diff_df[price_diff_df[pct_col] > threshold_pct]
                low_opportunities = price_diff_df[price_diff_df[pct_col] < -threshold_pct]
                
                for timestamp, row in high_opportunities.iterrows():
                    opportunities.append({
                        'timestamp': timestamp,
                        'pair': pair,
                        'type': 'high',
                        'price_diff_pct': row[pct_col],
                        'price_diff_abs': row[diff_col],
                        'signal': f"{pair.split('_vs_')[0]} 价格高于 {pair.split('_vs_')[1]}"
                    })
                
                for timestamp, row in low_opportunities.iterrows():
                    opportunities.append({
                        'timestamp': timestamp,
                        'pair': pair,
                        'type': 'low',
                        'price_diff_pct': row[pct_col],
                        'price_diff_abs': row[diff_col],
                        'signal': f"{pair.split('_vs_')[1]} 价格高于 {pair.split('_vs_')[0]}"
                    })
        
        if opportunities:
            return pd.DataFrame(opportunities).sort_values('price_diff_pct', ascending=False)
        else:
            return pd.DataFrame()
    
    def analyze_funding_rate_arbitrage(self, symbol: str) -> Dict:
        """分析资金费率套利机会"""
        print(f"\n💰 分析 {symbol} 资金费率套利机会...")
        
        funding_data = {}
        
        # 加载资金费率数据
        for exchange in ['binance', 'bybit']:
            filename = f"{exchange}_{symbol}_funding_rate.csv"
            filepath = os.path.join(self.funding_dir, filename)
            
            if os.path.exists(filepath):
                try:
                    df = pd.read_csv(filepath)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df.set_index('timestamp', inplace=True)
                    funding_data[exchange] = df
                except Exception as e:
                    print(f"加载资金费率数据 {filepath} 失败: {e}")
        
        if len(funding_data) < 2:
            return {'status': 'insufficient_data', 'message': '资金费率数据不足'}
        
        # 计算资金费率差异
        if 'binance' in funding_data and 'bybit' in funding_data:
            binance_rates = funding_data['binance']['funding_rate']
            bybit_rates = funding_data['bybit']['funding_rate']
            
            # 找到共同时间点
            common_times = binance_rates.index.intersection(bybit_rates.index)
            
            if len(common_times) == 0:
                return {'status': 'no_common_time', 'message': '没有共同的时间点'}
            
            # 计算费率差异
            rate_diffs = binance_rates.loc[common_times] - bybit_rates.loc[common_times]
            
            analysis = {
                'status': 'success',
                'common_timepoints': len(common_times),
                'avg_binance_rate': float(binance_rates.mean()),
                'avg_bybit_rate': float(bybit_rates.mean()),
                'avg_rate_difference': float(rate_diffs.mean()),
                'max_rate_difference': float(rate_diffs.max()),
                'min_rate_difference': float(rate_diffs.min()),
                'rate_difference_std': float(rate_diffs.std()),
                'arbitrage_opportunities': len(rate_diffs[abs(rate_diffs) > 0.0001])  # 0.01%差异
            }
            
            return analysis
        
        return {'status': 'missing_exchanges', 'message': '缺少交易所资金费率数据'}
    
    def test_symbol_arbitrage(self, symbol: str) -> Dict:
        """测试单个交易对的套利机会"""
        print(f"\n{'='*60}")
        print(f"测试 {symbol} 套利机会")
        print(f"{'='*60}")
        
        # 创建对齐数据集
        aligned_df = self.create_aligned_dataset(symbol)
        
        if aligned_df is None:
            return {'symbol': symbol, 'status': 'failed', 'message': '无法创建对齐数据集'}
        
        # 计算价格差异
        price_diff_df, exchange_pairs = self.calculate_price_differences(aligned_df)
        
        # 识别套利机会
        opportunities = self.identify_arbitrage_opportunities(price_diff_df, exchange_pairs)
        
        # 分析资金费率套利
        funding_analysis = self.analyze_funding_rate_arbitrage(symbol)
        
        # 统计信息
        stats = {
            'total_data_points': len(aligned_df),
            'exchange_pairs_analyzed': len(exchange_pairs),
            'price_arbitrage_opportunities': len(opportunities) if not opportunities.empty else 0,
            'funding_arbitrage_available': funding_analysis.get('status') == 'success'
        }
        
        # 如果有套利机会，提供详细信息
        top_opportunities = []
        if not opportunities.empty:
            top_opportunities = opportunities.head(5).to_dict('records')
        
        result = {
            'symbol': symbol,
            'status': 'success',
            'statistics': stats,
            'price_arbitrage': {
                'opportunities_found': len(opportunities) if not opportunities.empty else 0,
                'top_opportunities': top_opportunities
            },
            'funding_arbitrage': funding_analysis
        }
        
        return result
    
    def test_all_symbols(self) -> Dict:
        """测试所有交易对的套利机会"""
        print("🚀 开始测试多交易所套利机会")
        print(f"测试交易对: {', '.join(self.symbols)}")
        print(f"分析交易所: {', '.join(self.exchanges)}")
        
        results = {}
        
        for symbol in self.symbols:
            results[symbol] = self.test_symbol_arbitrage(symbol)
        
        # 生成总体报告
        overall_report = {
            'test_time': datetime.now().isoformat(),
            'symbols_tested': len(results),
            'successful_tests': len([r for r in results.values() if r.get('status') == 'success']),
            'results': results,
            'summary': self.generate_test_summary(results)
        }
        
        return overall_report
    
    def generate_test_summary(self, results: Dict) -> Dict:
        """生成测试摘要"""
        summary = {
            'total_opportunities': 0,
            'symbols_with_opportunities': [],
            'best_opportunities': [],
            'funding_arbitrage_symbols': []
        }
        
        all_opportunities = []
        
        for symbol, result in results.items():
            if result.get('status') == 'success':
                price_arb = result.get('price_arbitrage', {})
                opp_count = price_arb.get('opportunities_found', 0)
                
                if opp_count > 0:
                    summary['symbols_with_opportunities'].append(symbol)
                    summary['total_opportunities'] += opp_count
                    
                    # 收集最佳机会
                    top_ops = price_arb.get('top_opportunities', [])
                    all_opportunities.extend(top_ops)
                
                # 检查资金费率套利
                funding_arb = result.get('funding_arbitrage', {})
                if funding_arb.get('status') == 'success':
                    summary['funding_arbitrage_symbols'].append(symbol)
        
        # 找出最佳套利机会
        if all_opportunities:
            all_opportunities.sort(key=lambda x: abs(x.get('price_diff_pct', 0)), reverse=True)
            summary['best_opportunities'] = all_opportunities[:10]
        
        return summary
    
    def save_test_report(self, report: Dict, filename: str = 'data/arbitrage_test_report.json'):
        """保存测试报告"""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"\n📄 套利测试报告已保存到: {filename}")
    
    def print_test_summary(self, report: Dict):
        """打印测试摘要"""
        print(f"\n{'='*80}")
        print("🎯 套利机会测试摘要")
        print(f"{'='*80}")
        
        summary = report['summary']
        
        print(f"测试时间: {report['test_time']}")
        print(f"测试交易对数: {report['symbols_tested']}")
        print(f"成功测试数: {report['successful_tests']}")
        
        print(f"\n📈 价格套利机会:")
        print(f"  总机会数: {summary['total_opportunities']}")
        print(f"  有机会的交易对: {', '.join(summary['symbols_with_opportunities'])}")
        
        if summary['best_opportunities']:
            print(f"\n🏆 最佳套利机会 (前5个):")
            for i, opp in enumerate(summary['best_opportunities'][:5], 1):
                print(f"  {i}. {opp['timestamp']} - {opp['pair']}: {opp['price_diff_pct']:.4f}%")
                print(f"     {opp['signal']}")
        
        print(f"\n💰 资金费率套利:")
        print(f"  可用交易对: {', '.join(summary['funding_arbitrage_symbols'])}")
        
        # 详细结果
        print(f"\n{'='*80}")
        print("📋 详细测试结果")
        print(f"{'='*80}")
        
        for symbol, result in report['results'].items():
            if result.get('status') == 'success':
                stats = result['statistics']
                price_arb = result['price_arbitrage']
                funding_arb = result['funding_arbitrage']
                
                print(f"\n📊 {symbol}:")
                print(f"  数据点数: {stats['total_data_points']}")
                print(f"  价格套利机会: {price_arb['opportunities_found']}")
                print(f"  资金费率套利: {'✅' if funding_arb.get('status') == 'success' else '❌'}")
                
                if funding_arb.get('status') == 'success':
                    print(f"    平均费率差异: {funding_arb.get('avg_rate_difference', 0)*100:.4f}%")
                    print(f"    最大费率差异: {funding_arb.get('max_rate_difference', 0)*100:.4f}%")
            else:
                print(f"\n❌ {symbol}: {result.get('message', '测试失败')}")

def main():
    """主函数"""
    tester = DataAlignmentTester()
    
    # 测试所有交易对的套利机会
    report = tester.test_all_symbols()
    
    # 保存测试报告
    tester.save_test_report(report)
    
    # 打印测试摘要
    tester.print_test_summary(report)
    
    print(f"\n🎉 套利机会测试完成！")

if __name__ == "__main__":
    main()