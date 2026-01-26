#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试所有货币的套利逻辑
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

import pandas as pd
from src.arbitrage_system import ArbitrageSystem
from src.config import Config
import json
from datetime import datetime

def test_all_symbols():
    """测试所有货币"""
    print("=" * 60)
    print("测试所有货币的套利逻辑")
    print("=" * 60)
    
    # 加载配置
    config = Config("config/config.ini")
    arbitrage_config = config.get_arbitrage_config()
    
    # 创建套利系统
    system = ArbitrageSystem(
        config=arbitrage_config,
        initial_balance=10000,
        transaction_fee=0.001,
        enable_funding_rate=True
    )
    
    # 测试所有交易对
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
    results = {}
    
    for symbol in symbols:
        print(f"\n{'='*60}")
        print(f"测试交易对: {symbol}")
        print(f"{'='*60}")
        
        aligned_file = f"data/aligned/{symbol}_30m_aligned.csv"
        
        if not Path(aligned_file).exists():
            print(f"❌ 对齐数据文件不存在: {aligned_file}")
            results[symbol] = {'status': 'error', 'message': '数据文件不存在'}
            continue
        
        # 加载数据
        try:
            df = system.load_data(aligned_file, symbol)
            print(f"   数据形状: {df.shape[0]} 行 × {df.shape[1]} 列")
            print(f"   时间范围: {df.index.min()} 至 {df.index.max()}")
            
            # 检查包含的交易所
            exchanges = set()
            for col in df.columns:
                if '_close' in col:
                    exchange = col.split('_')[0]
                    exchanges.add(exchange)
            print(f"   包含交易所: {', '.join(sorted(exchanges))}")
            
            # 运行回测
            print(f"\n   运行回测...")
            backtest_results = system.run_backtest(df=df, symbol=symbol)
            
            # 保存结果
            results[symbol] = {
                'status': 'success',
                'total_trades': backtest_results.get('total_trades', 0),
                'total_pnl': backtest_results.get('total_pnl', 0),
                'return_rate': backtest_results.get('return_rate', 0),
                'win_rate': backtest_results.get('win_rate', 0),
                'max_profit': backtest_results.get('max_profit', 0),
                'max_loss': backtest_results.get('max_loss', 0),
                'winning_trades': backtest_results.get('winning_trades', 0),
                'losing_trades': backtest_results.get('losing_trades', 0),
            }
            
            print(f"   ✅ 完成: {backtest_results.get('total_trades', 0)} 笔交易, "
                  f"收益率: {backtest_results.get('return_rate', 0):.2%}, "
                  f"胜率: {backtest_results.get('win_rate', 0):.2%}")
            
        except Exception as e:
            print(f"   ❌ 失败: {e}")
            results[symbol] = {'status': 'error', 'message': str(e)}
    
    # 生成汇总报告
    print(f"\n{'='*60}")
    print("汇总报告")
    print(f"{'='*60}")
    
    successful = [r for r in results.values() if r.get('status') == 'success']
    
    if successful:
        print(f"\n成功测试: {len(successful)}/{len(symbols)} 个交易对")
        print(f"\n{'交易对':<12} {'交易数':<8} {'收益率':<10} {'胜率':<10} {'总盈亏':<12}")
        print("-" * 60)
        
        total_pnl = 0
        total_trades = 0
        
        for symbol in symbols:
            if symbol in results and results[symbol].get('status') == 'success':
                r = results[symbol]
                print(f"{symbol:<12} {r['total_trades']:<8} {r['return_rate']:>8.2%} "
                      f"{r['win_rate']:>8.2%} ${r['total_pnl']:>10.2f}")
                total_pnl += r['total_pnl']
                total_trades += r['total_trades']
        
        print("-" * 60)
        print(f"{'总计':<12} {total_trades:<8} {'':<10} {'':<10} ${total_pnl:>10.2f}")
        print(f"\n总收益率: {(total_pnl / 10000):.2%}")
    
    # 保存结果
    result_file = f"data/backtest_results/all_symbols_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    Path("data/backtest_results").mkdir(parents=True, exist_ok=True)
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str, ensure_ascii=False)
    print(f"\n✅ 结果已保存: {result_file}")
    
    return results

if __name__ == '__main__':
    test_all_symbols()
