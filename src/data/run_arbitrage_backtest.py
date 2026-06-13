#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
套利系统回测运行器 - 适配重构后的套利逻辑系统

支持功能：
1. 单币种回测
2. 多币种批量回测
3. 参数优化测试
4. 结果分析和可视化
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.arbitrage_system import ArbitrageSystem, ArbitrageConfig, ArbitrageType
from datetime import datetime
import json
import pandas as pd
from typing import Dict, List, Optional
import matplotlib.pyplot as plt

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti', 'PingFang SC']
plt.rcParams['axes.unicode_minus'] = False


class ArbitrageBacktestRunner:
    """套利回测运行器"""
    
    def __init__(self, config: ArbitrageConfig = None):
        """
        初始化回测运行器
        
        Args:
            config: 套利系统配置，默认使用标准配置
        """
        self.config = config or ArbitrageConfig()
        self.data_dir = 'data/aligned'
        self.results_dir = 'data/backtest_results'
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
        
        # 创建结果目录
        os.makedirs(self.results_dir, exist_ok=True)
    
    def load_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """加载对齐数据"""
        # 尝试多种文件名格式
        possible_files = [
            f"{self.data_dir}/{symbol}_30m_aligned.csv",
            f"{self.data_dir}/aligned_{symbol}_30m.csv",
            f"{self.data_dir}/{symbol}_aligned.csv"
        ]
        
        for file_path in possible_files:
            if os.path.exists(file_path):
                print(f"📂 加载数据: {file_path}")
                df = pd.read_csv(file_path, index_col=0, parse_dates=True)
                return df
        
        print(f"❌ 未找到 {symbol} 的数据文件")
        return None
    
    def detect_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """自动检测数据列名"""
        columns = {
            'price_col_a': None,
            'price_col_b': None,
            'funding_col_a': None,
            'funding_col_b': None
        }
        
        # 检测价格列
        for col in df.columns:
            col_lower = col.lower()
            if 'binance' in col_lower and 'close' in col_lower:
                columns['price_col_a'] = col
            elif 'kucoin' in col_lower and 'close' in col_lower:
                columns['price_col_b'] = col
            elif 'binance' in col_lower and 'funding' in col_lower:
                columns['funding_col_a'] = col
            elif 'kucoin' in col_lower and 'funding' in col_lower:
                columns['funding_col_b'] = col
        
        # 如果没找到kucoin，尝试其他交易所
        if columns['price_col_b'] is None:
            for col in df.columns:
                col_lower = col.lower()
                if 'bybit' in col_lower and 'close' in col_lower:
                    columns['price_col_b'] = col
                elif 'bybit' in col_lower and 'funding' in col_lower:
                    columns['funding_col_b'] = col
        
        return columns
    
    def run_single_backtest(self, symbol: str, config: ArbitrageConfig = None, debug: bool = False) -> Dict:
        """
        运行单个交易对的回测

        Args:
            symbol: 交易对符号
            config: 可选的配置覆盖
            debug: 是否启用调试模式

        Returns:
            回测结果字典
        """
        print(f"\n{'='*60}")
        print(f"运行 {symbol} 套利回测")
        print(f"{'='*60}")

        # 加载数据
        df = self.load_data(symbol)
        if df is None:
            return {'symbol': symbol, 'status': 'error', 'message': '数据文件不存在'}

        # 检测列名
        columns = self.detect_columns(df)

        if columns['price_col_a'] is None or columns['price_col_b'] is None:
            return {'symbol': symbol, 'status': 'error', 'message': '无法检测到价格列'}

        print(f"📊 检测到的列: {columns}")
        print(f"📈 数据行数: {len(df)}")
        print(f"📅 时间范围: {df.index[0]} 至 {df.index[-1]}")

        # 初始化系统
        use_config = config or self.config
        system = ArbitrageSystem(use_config)

        try:
            # 运行回测
            results = system.run_backtest(
                df=df,
                symbol=symbol,
                price_col_a=columns['price_col_a'],
                price_col_b=columns['price_col_b'],
                funding_col_a=columns.get('funding_col_a', 'binance_funding_rate'),
                funding_col_b=columns.get('funding_col_b', 'kucoin_funding_rate'),
                debug=debug
            )
            
            results['symbol'] = symbol
            results['status'] = 'success'
            results['config'] = {
                'X': use_config.X,
                'Y': use_config.Y,
                'A': use_config.A,
                'B': use_config.B,
                'N': use_config.N,
                'M': use_config.M,
                'P': use_config.P,
                'Q': use_config.Q
            }
            
            return results
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {'symbol': symbol, 'status': 'error', 'message': str(e)}
    
    def run_all_symbols(self, config: ArbitrageConfig = None) -> Dict:
        """运行所有交易对的回测"""
        print("🚀 开始运行套利系统回测")
        print(f"测试交易对: {', '.join(self.symbols)}")
        
        all_results = {}
        
        for symbol in self.symbols:
            result = self.run_single_backtest(symbol, config)
            all_results[symbol] = result
            
            if result.get('status') == 'success':
                print(f"✅ {symbol}: {result['total_trades']}笔交易, "
                      f"收益率: {result.get('return_rate', 0):.2%}, "
                      f"胜率: {result.get('win_rate', 0):.2%}")
            else:
                print(f"❌ {symbol}: {result.get('message', '未知错误')}")
        
        # 生成综合报告
        return self.generate_comprehensive_report(all_results, config)
    
    def generate_comprehensive_report(self, results: Dict, config: ArbitrageConfig = None) -> Dict:
        """生成综合回测报告"""
        successful = [r for r in results.values() if r.get('status') == 'success']
        
        if not successful:
            return {
                'timestamp': datetime.now().isoformat(),
                'config': None,
                'summary': {'total_symbols': len(results), 'successful': 0},
                'results': results
            }
        
        # 统计汇总
        total_trades = sum(r.get('total_trades', 0) for r in successful)
        total_pnl = sum(r.get('total_pnl', 0) for r in successful)
        avg_return = sum(r.get('return_rate', 0) for r in successful) / len(successful)
        avg_win_rate = sum(r.get('win_rate', 0) for r in successful) / len(successful)
        
        # 按套利类型汇总
        type_stats = {}
        for arb_type in ArbitrageType:
            type_trades = 0
            type_pnl = 0.0
            for r in successful:
                if arb_type.value in r.get('by_type', {}):
                    stats = r['by_type'][arb_type.value]
                    type_trades += stats['count']
                    type_pnl += stats['total_pnl']
            if type_trades > 0:
                type_stats[arb_type.value] = {
                    'total_trades': type_trades,
                    'total_pnl': type_pnl
                }
        
        return {
            'timestamp': datetime.now().isoformat(),
            'config': {
                'X': config.X if config else self.config.X,
                'Y': config.Y if config else self.config.Y,
                'A': config.A if config else self.config.A,
                'B': config.B if config else self.config.B,
                'N': config.N if config else self.config.N,
                'M': config.M if config else self.config.M,
                'P': config.P if config else self.config.P,
                'Q': config.Q if config else self.config.Q
            },
            'summary': {
                'total_symbols': len(results),
                'successful_symbols': len(successful),
                'total_trades': total_trades,
                'total_pnl': total_pnl,
                'avg_return_rate': avg_return,
                'avg_win_rate': avg_win_rate
            },
            'by_type': type_stats,
            'results': results
        }
    
    def run_parameter_optimization(self) -> Dict:
        """运行参数优化测试"""
        print("\n🔧 开始参数优化测试...")
        
        # 定义测试参数组合
        test_configs = [
            {
                'name': '保守策略',
                'config': ArbitrageConfig(
                    X=0.8, Y=0.15, A=0.15, B=0.08,
                    N=12, M=6, P=0.5, Q=0.3
                )
            },
            {
                'name': '平衡策略',
                'config': ArbitrageConfig(
                    X=0.5, Y=0.1, A=0.1, B=0.05,
                    N=8, M=4, P=0.3, Q=0.5
                )
            },
            {
                'name': '激进策略',
                'config': ArbitrageConfig(
                    X=0.3, Y=0.05, A=0.05, B=0.03,
                    N=4, M=2, P=0.2, Q=0.8
                )
            }
        ]
        
        optimization_results = {}
        
        for test in test_configs:
            print(f"\n🧪 测试 {test['name']}...")
            report = self.run_all_symbols(test['config'])
            optimization_results[test['name']] = {
                'config': test['config'].__dict__,
                'report': report
            }
            
            summary = report['summary']
            print(f"  平均收益率: {summary['avg_return_rate']:.2%}")
            print(f"  平均胜率: {summary['avg_win_rate']:.2%}")
            print(f"  总交易次数: {summary['total_trades']}")
        
        # 找出最佳配置
        best_config = max(
            optimization_results.items(),
            key=lambda x: x[1]['report']['summary']['avg_return_rate']
        )
        
        print(f"\n🏆 最佳配置: {best_config[0]}")
        print(f"   最佳收益率: {best_config[1]['report']['summary']['avg_return_rate']:.2%}")
        
        return optimization_results
    
    def save_results(self, report: Dict, filename: str = None):
        """保存回测结果"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"arbitrage_backtest_{timestamp}.json"
        
        filepath = os.path.join(self.results_dir, filename)
        
        # 处理不可序列化的对象
        def convert(obj):
            if hasattr(obj, '__dict__'):
                return obj.__dict__
            return str(obj)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=convert, ensure_ascii=False)
        
        print(f"\n📄 回测报告已保存: {filepath}")
        return filepath
    
    def print_summary(self, report: Dict):
        """打印回测摘要"""
        print(f"\n{'='*80}")
        print("📊 套利系统回测综合报告")
        print(f"{'='*80}")
        
        summary = report['summary']
        config = report.get('config', {})
        
        print(f"\n【配置参数】")
        print(f"  X={config.get('X')}% Y={config.get('Y')}% A={config.get('A')}% B={config.get('B')}%")
        print(f"  N={config.get('N')}h M={config.get('M')}h P={config.get('P')}% Q={config.get('Q')}%")
        
        print(f"\n【总体统计】")
        print(f"  测试交易对: {summary['total_symbols']}")
        print(f"  成功交易对: {summary['successful_symbols']}")
        print(f"  总交易次数: {summary['total_trades']}")
        print(f"  总盈亏: ${summary['total_pnl']:.2f}")
        print(f"  平均收益率: {summary['avg_return_rate']:.2%}")
        print(f"  平均胜率: {summary['avg_win_rate']:.2%}")
        
        if report.get('by_type'):
            print(f"\n【按套利类型统计】")
            for type_name, stats in report['by_type'].items():
                print(f"  {type_name}: {stats['total_trades']}笔, 盈亏${stats['total_pnl']:.2f}")
        
        print(f"\n{'='*80}")
        print("【各交易对详情】")
        print(f"{'='*80}")
        
        for symbol, result in report['results'].items():
            if result.get('status') == 'success':
                print(f"\n📈 {symbol}:")
                print(f"  交易次数: {result.get('total_trades', 0)}")
                print(f"  总盈亏: ${result.get('total_pnl', 0):.2f}")
                print(f"  收益率: {result.get('return_rate', 0):.2%}")
                print(f"  胜率: {result.get('win_rate', 0):.2%}")
                
                if result.get('by_type'):
                    for type_name, stats in result['by_type'].items():
                        print(f"    - {type_name}: {stats['count']}笔, 胜率{stats['win_rate']:.2%}")
            else:
                print(f"\n❌ {symbol}: {result.get('message', '未知错误')}")

    def generate_visualizations(self, report: Dict):
        """
        生成回测结果的可视化图表

        为每个交易对生成时间序列分析图表，保存到 data/results/ 目录
        """
        print(f"\n{'='*60}")
        print("📊 生成可视化图表...")
        print(f"{'='*60}")

        results_dir = 'data/results'
        os.makedirs(results_dir, exist_ok=True)

        for symbol, result in report['results'].items():
            if result.get('status') != 'success':
                continue

            try:
                # 加载数据
                df = self.load_data(symbol)
                if df is None:
                    print(f"  ⚠️ {symbol}: 无法加载数据")
                    continue

                # 检测列名
                columns = self.detect_columns(df)

                print(f"  📈 生成 {symbol} 图表...")

                # 创建图表
                fig, axes = plt.subplots(4, 1, figsize=(14, 12))
                fig.suptitle(f'{symbol} 时间序列分析', fontsize=16, fontweight='bold')

                # 1. 价格对比图
                ax1 = axes[0]
                ax1.plot(df.index, df[columns['price_col_a']], label='Binance', linewidth=1.5, alpha=0.8)
                ax1.plot(df.index, df[columns['price_col_b']], label='KuCoin/Bybit', linewidth=1.5, alpha=0.8)
                ax1.set_ylabel('价格 (USDT)', fontsize=10)
                ax1.set_title('交易所价格对比', fontsize=12)
                ax1.legend(loc='best')
                ax1.grid(True, alpha=0.3)

                # 2. 价差百分比图
                ax2 = axes[1]
                price_spread_pct = abs(df[columns['price_col_a']] - df[columns['price_col_b']]) / \
                                   df[[columns['price_col_a'], columns['price_col_b']]].min(axis=1) * 100
                ax2.plot(df.index, price_spread_pct, color='orange', linewidth=1.0, alpha=0.7)

                # 添加阈值线
                config = report.get('config', {})
                if config:
                    ax2.axhline(y=config.get('X', 0.5), color='red', linestyle='--',
                               label=f'触发阈值 X={config.get("X", 0.5)}%', alpha=0.5)

                ax2.set_ylabel('价差 (%)', fontsize=10)
                ax2.set_title('价差百分比', fontsize=12)
                ax2.legend(loc='best')
                ax2.grid(True, alpha=0.3)

                # 3. 资金费率对比图
                ax3 = axes[2]
                if columns.get('funding_col_a') and columns.get('funding_col_b'):
                    funding_a = df[columns['funding_col_a']] * 100
                    funding_b = df[columns['funding_col_b']] * 100
                    ax3.plot(df.index, funding_a, label='Binance', linewidth=1.0, alpha=0.7)
                    ax3.plot(df.index, funding_b, label='KuCoin/Bybit', linewidth=1.0, alpha=0.7)
                    ax3.set_ylabel('资金费率 (%)', fontsize=10)
                    ax3.set_title('资金费率对比', fontsize=12)
                    ax3.legend(loc='best')
                    ax3.grid(True, alpha=0.3)
                    ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)

                # 4. 资金费率差图
                ax4 = axes[3]
                if columns.get('funding_col_a') and columns.get('funding_col_b'):
                    funding_spread = abs(df[columns['funding_col_a']] - df[columns['funding_col_b']]) * 100
                    ax4.plot(df.index, funding_spread, color='green', linewidth=1.0, alpha=0.7)

                    # 添加阈值线
                    if config:
                        ax4.axhline(y=config.get('Y', 0.1), color='red', linestyle='--',
                                   label=f'触发阈值 Y={config.get("Y", 0.1)}%', alpha=0.5)

                    ax4.set_ylabel('费率差 (%)', fontsize=10)
                    ax4.set_title('资金费率差', fontsize=12)
                    ax4.set_xlabel('时间', fontsize=10)
                    ax4.legend(loc='best')
                    ax4.grid(True, alpha=0.3)

                # 调整布局
                plt.tight_layout()

                # 保存图表
                filepath = os.path.join(results_dir, f'{symbol}_time_series_analysis.png')
                plt.savefig(filepath, dpi=100, bbox_inches='tight')
                plt.close(fig)

                print(f"    ✅ 已保存: {filepath}")

            except Exception as e:
                print(f"    ❌ {symbol} 图表生成失败: {e}")
                import traceback
                traceback.print_exc()

        print(f"\n✅ 可视化图表生成完成！")



def main():
    """主函数"""
    print("=" * 80)
    print("套利执行逻辑系统 - 回测工具")
    print("=" * 80)
    
    # 创建配置
    config = ArbitrageConfig(
        X=0.5,    # 0.5% 价差触发
        Y=0.1,    # 0.1% 资金费率差触发
        A=0.1,    # 0.1% 可忽视价差
        B=0.05,   # 0.05% 可忽视资金费率差
        N=8,      # 8小时历史
        M=4,      # 4小时持续时间
        P=0.3,    # 0.3% 盈利目标
        Q=0.5,    # 0.5% 止损
        initial_balance=10000
    )
    
    # 创建运行器
    runner = ArbitrageBacktestRunner(config)
    
    try:
        # 运行所有交易对回测
        report = runner.run_all_symbols()
        
        # 打印摘要
        runner.print_summary(report)
        
        # 保存结果
        runner.save_results(report)
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
    except Exception as e:
        print(f"\n❌ 运行失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎉 回测完成！")


if __name__ == "__main__":
    main()
