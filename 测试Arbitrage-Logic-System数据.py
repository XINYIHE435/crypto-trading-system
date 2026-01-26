#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 Arbitrage-Logic-System 的数据测试 a-r 系统
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

from src.arbitrage_system import ArbitrageSystem
from src.config import Config
import pandas as pd

def test_with_ar_logic_data():
    """使用转换后的数据测试系统"""
    print("=" * 60)
    print("使用 Arbitrage-Logic-System 数据测试 a-r 系统")
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
    
    # 加载转换后的数据
    aligned_file = "data/aligned/BTCUSDT_30m_aligned.csv"
    
    if not Path(aligned_file).exists():
        print(f"❌ 数据文件不存在: {aligned_file}")
        print("   请先运行: python 转换Arbitrage-Logic-System数据.py")
        return
    
    print(f"\n📊 加载数据: {aligned_file}")
    df = system.load_data(aligned_file, 'BTCUSDT')
    
    if df is None or df.empty:
        print("❌ 数据加载失败")
        return
    
    print(f"✅ 数据加载成功: {len(df)} 条记录")
    print(f"   时间范围: {df.index[0]} 至 {df.index[-1]}")
    
    # 运行回测
    print("\n" + "=" * 60)
    print("开始回测...")
    print("=" * 60)
    
    results = system.run_backtest(df=df, symbol='BTCUSDT')
    
    # 显示结果
    print("\n" + "=" * 60)
    print("回测结果")
    print("=" * 60)
    print(f"总交易次数: {results.get('total_trades', 0)}")
    print(f"总盈亏: ${results.get('total_pnl', 0):.2f}")
    print(f"收益率: {results.get('return_rate', 0)*100:.2f}%")
    print(f"胜率: {results.get('win_rate', 0)*100:.2f}%")
    print(f"最大盈利: ${results.get('max_profit', 0):.2f}")
    print(f"最大亏损: ${results.get('max_loss', 0):.2f}")
    print(f"平均盈亏: ${results.get('avg_profit', 0):.2f}")
    
    # 显示交易详情
    if system.closed_trades:
        print(f"\n📋 交易详情（前10笔）:")
        print("-" * 60)
        for i, trade in enumerate(system.closed_trades[:10], 1):
            print(f"{i}. 开仓: {trade.get('entry_time')} @ ${trade.get('entry_price', 0):.2f}")
            print(f"   平仓: {trade.get('exit_time')} @ ${trade.get('exit_price', 0):.2f}")
            print(f"   盈亏: ${trade.get('net_pnl', 0):.2f}")
            print(f"   原因: {trade.get('exit_reason', 'N/A')}")
            print()
    
    # 生成可视化
    print("\n📈 生成可视化...")
    try:
        system._visualize_results(results)
        print("✅ 可视化已生成")
    except Exception as e:
        print(f"⚠️  可视化生成失败: {e}")
    
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)

if __name__ == '__main__':
    test_with_ar_logic_data()
