#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建对齐数据集 - 将多交易所数据合并为套利系统可用的格式
"""

import pandas as pd
import os
from datetime import datetime
import json
from typing import Dict, List, Optional

class AlignedDatasetCreator:
    def __init__(self):
        self.data_dir = 'data/raw/klines'
        self.output_dir = 'data/aligned'
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
        self.exchanges = ['binance', 'bybit', 'okx', 'huobi', 'kucoin']
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        
    def load_exchange_data(self, symbol: str, exchange: str) -> Optional[pd.DataFrame]:
        """加载单个交易所的数据"""
        filename = f"{exchange}_{symbol}_30m.csv"
        filepath = os.path.join(self.data_dir, filename)
        
        if not os.path.exists(filepath):
            return None
            
        try:
            df = pd.read_csv(filepath)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            print(f"加载 {filepath} 失败: {e}")
            return None
    
    def create_aligned_dataset(self, symbol: str) -> Optional[pd.DataFrame]:
        """创建对齐后的数据集"""
        print(f"\n🔄 创建 {symbol} 对齐数据集...")
        
        # 加载所有交易所的数据
        exchange_data = {}
        
        for exchange in self.exchanges:
            df = self.load_exchange_data(symbol, exchange)
            if df is not None:
                exchange_data[exchange] = df
                print(f"✅ {exchange}: {len(df)} 条记录")
            else:
                print(f"❌ {exchange}: 无数据")
        
        if len(exchange_data) < 2:
            print(f"❌ {symbol} 数据不足，无法创建对齐数据集")
            return None
        
        # 找到共同时间戳
        common_timestamps = self.find_common_timestamps(exchange_data)
        
        if not common_timestamps:
            print(f"❌ {symbol} 没有共同时间戳")
            return None
        
        print(f"✅ 找到 {len(common_timestamps)} 个共同时间戳")
        
        # 创建对齐后的数据集
        aligned_data = []
        
        for timestamp in common_timestamps:
            row = {'timestamp': timestamp}
            
            # 添加每个交易所的数据
            for exchange in self.exchanges:
                if exchange in exchange_data:
                    df = exchange_data[exchange]
                    if timestamp in df.index:
                        data = df.loc[timestamp]
                        row[f'{exchange}_open'] = data['open']
                        row[f'{exchange}_high'] = data['high']
                        row[f'{exchange}_low'] = data['low']
                        row[f'{exchange}_close'] = data['close']
                        row[f'{exchange}_volume'] = data['volume']
                    else:
                        # 如果某个时间戳缺失，填充NaN
                        for col in ['open', 'high', 'low', 'close', 'volume']:
                            row[f'{exchange}_{col}'] = None
            
            aligned_data.append(row)
        
        aligned_df = pd.DataFrame(aligned_data)
        aligned_df.set_index('timestamp', inplace=True)
        
        # 填充缺失值
        aligned_df = aligned_df.ffill().bfill()
        
        return aligned_df
    
    def find_common_timestamps(self, exchange_data: Dict[str, pd.DataFrame]) -> List[datetime]:
        """找到所有交易所共同的时间戳"""
        if not exchange_data:
            return []
        
        # 获取第一个交易所的时间戳集合
        common_timestamps = set(exchange_data[list(exchange_data.keys())[0]].index)
        
        # 找到所有交易所的交集
        for exchange, df in exchange_data.items():
            common_timestamps &= set(df.index)
        
        return sorted(list(common_timestamps))
    
    def create_all_aligned_datasets(self) -> Dict:
        """创建所有交易对的对齐数据集"""
        print("🚀 开始创建对齐数据集")
        print(f"输出目录: {self.output_dir}")
        
        results = {}
        
        for symbol in self.symbols:
            aligned_df = self.create_aligned_dataset(symbol)
            
            if aligned_df is not None:
                # 保存对齐数据集
                filename = f"aligned_{symbol}_30m.csv"
                filepath = os.path.join(self.output_dir, filename)
                aligned_df.to_csv(filepath)
                
                # 记录统计信息
                stats = {
                    'file': filepath,
                    'records': len(aligned_df),
                    'start_time': str(aligned_df.index.min()),
                    'end_time': str(aligned_df.index.max()),
                    'exchanges': len([col for col in aligned_df.columns if '_close' in col])
                }
                
                results[symbol] = stats
                print(f"✅ {symbol} 对齐数据集已保存: {filepath}")
                print(f"   记录数: {stats['records']}, 时间范围: {stats['start_time']} 到 {stats['end_time']}")
            else:
                print(f"❌ {symbol} 对齐数据集创建失败")
        
        # 保存创建报告
        creation_report = {
            'creation_time': datetime.now().isoformat(),
            'symbols_processed': len(results),
            'results': results,
            'summary': {
                'total_files': len(results),
                'total_records': sum(r['records'] for r in results.values()),
                'exchanges_supported': self.exchanges
            }
        }
        
        report_path = os.path.join(self.output_dir, 'dataset_creation_report.json')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(creation_report, f, indent=2, default=str)
        
        print(f"\n📄 数据集创建报告已保存到: {report_path}")
        
        return creation_report
    
    def validate_aligned_datasets(self) -> Dict:
        """验证对齐数据集的质量"""
        print("\n🔍 验证对齐数据集质量...")
        
        validation_results = {}
        
        for symbol in self.symbols:
            filename = f"aligned_{symbol}_30m.csv"
            filepath = os.path.join(self.output_dir, filename)
            
            if not os.path.exists(filepath):
                validation_results[symbol] = {
                    'status': 'missing',
                    'message': f'文件不存在: {filepath}'
                }
                continue
            
            try:
                df = pd.read_csv(filepath, index_col=0, parse_dates=True)
                
                # 检查数据完整性
                total_cells = len(df) * len(self.exchanges)
                missing_cells = df.isnull().sum().sum()
                completeness = (total_cells - missing_cells) / total_cells
                
                # 检查时间间隔一致性
                time_diffs = df.index.to_series().diff().dropna()
                unique_intervals = time_diffs.unique()
                is_consistent = len(unique_intervals) == 1
                
                # 检查价格合理性
                price_columns = [f'{exchange}_close' for exchange in self.exchanges if f'{exchange}_close' in df.columns]
                price_stats = {}
                
                for col in price_columns:
                    prices = df[col].dropna()
                    if len(prices) > 0:
                        price_stats[col] = {
                            'min': float(prices.min()),
                            'max': float(prices.max()),
                            'mean': float(prices.mean()),
                            'std': float(prices.std())
                        }
                
                validation_results[symbol] = {
                    'status': 'valid',
                    'records': len(df),
                    'completeness': completeness,
                    'time_consistent': is_consistent,
                    'time_intervals': [str(td) for td in unique_intervals],
                    'price_stats': price_stats,
                    'file_size_mb': round(os.path.getsize(filepath) / (1024 * 1024), 2)
                }
                
                print(f"✅ {symbol}: 完整性 {completeness:.2%}, 时间一致性 {'✅' if is_consistent else '❌'}")
                
            except Exception as e:
                validation_results[symbol] = {
                    'status': 'error',
                    'message': str(e)
                }
                print(f"❌ {symbol}: 验证失败 - {e}")
        
        # 保存验证报告
        validation_report = {
            'validation_time': datetime.now().isoformat(),
            'results': validation_results,
            'summary': {
                'total_symbols': len(validation_results),
                'valid_symbols': len([r for r in validation_results.values() if r.get('status') == 'valid']),
                'avg_completeness': sum(r.get('completeness', 0) for r in validation_results.values()) / len(validation_results)
            }
        }
        
        report_path = os.path.join(self.output_dir, 'dataset_validation_report.json')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(validation_report, f, indent=2, default=str)
        
        print(f"\n📄 数据集验证报告已保存到: {report_path}")
        
        return validation_report
    
    def print_summary(self, creation_report: Dict, validation_report: Dict):
        """打印创建和验证摘要"""
        print(f"\n{'='*80}")
        print("📊 对齐数据集创建摘要")
        print(f"{'='*80}")
        
        # 创建摘要
        creation_summary = creation_report['summary']
        print(f"创建时间: {creation_report['creation_time']}")
        print(f"处理交易对: {creation_summary.get('total_files', 0)}")
        print(f"总记录数: {creation_summary.get('total_records', 0):,}")
        print(f"支持交易所: {', '.join(creation_summary.get('exchanges_supported', []))}")
        
        # 验证摘要
        validation_summary = validation_report['summary']
        print(f"\n📋 验证结果:")
        print(f"  有效交易对: {validation_summary['valid_symbols']}/{validation_summary['total_symbols']}")
        print(f"  平均完整性: {validation_summary['avg_completeness']:.2%}")
        
        # 详细结果
        print(f"\n📈 详细结果:")
        for symbol in self.symbols:
            if symbol in creation_report['results']:
                creation = creation_report['results'][symbol]
                print(f"\n  {symbol}:")
                print(f"    记录数: {creation['records']:,}")
                print(f"    时间范围: {creation['start_time']} 到 {creation['end_time']}")
                print(f"    交易所数: {creation['exchanges']}")
                
                if symbol in validation_report['results']:
                    validation = validation_report['results'][symbol]
                    if validation.get('status') == 'valid':
                        print(f"    数据完整性: {validation['completeness']:.2%}")
                        print(f"    时间一致性: {'✅' if validation['time_consistent'] else '❌'}")
                        print(f"    文件大小: {validation['file_size_mb']} MB")
                    else:
                        print(f"    验证状态: ❌ {validation.get('message', '未知错误')}")

def main():
    """主函数"""
    creator = AlignedDatasetCreator()
    
    # 创建所有对齐数据集
    creation_report = creator.create_all_aligned_datasets()
    
    # 验证对齐数据集
    validation_report = creator.validate_aligned_datasets()
    
    # 打印摘要
    creator.print_summary(creation_report, validation_report)
    
    print(f"\n🎉 对齐数据集创建和验证完成！")
    print(f"📁 数据集位置: {creator.output_dir}")

if __name__ == "__main__":
    main()