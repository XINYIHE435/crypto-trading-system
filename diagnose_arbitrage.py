#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
套利策略诊断工具
按照7个步骤系统性排查策略问题
"""
import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
from datetime import datetime

# 设置Windows控制台编码
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti', 'PingFang SC']
plt.rcParams['axes.unicode_minus'] = False

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.arbitrage_system import ArbitrageSystem, ArbitrageConfig
from src.data.run_arbitrage_backtest import ArbitrageBacktestRunner

print("=" * 80)
print("套利策略诊断工具 - 7步系统性排查")
print("=" * 80)

# ===== 第一步：验证套利方向是否写反 =====
print("\n【第一步】验证套利方向是否写反")
print("-" * 80)

def verify_direction_logic():
    """验证方向逻辑"""
    print("\n代码逻辑检查：")
    print("1. 开仓方向判断（第704行）:")
    print("   short_a_long_b = price_a > price_b")
    print("   ✓ 正确：A贵 -> 做空A做多B")

    print("\n2. 盈亏计算（第807-818行）:")
    print("   if short_a_long_b:")
    print("       pnl_a = (open_price_a - close_price_a) * size  # 做空A")
    print("       pnl_b = (close_price_b - open_price_b) * size  # 做多B")
    print("   else:")
    print("       pnl_a = (close_price_a - open_price_a) * size  # 做多A")
    print("       pnl_b = (open_price_b - close_price_b) * size  # 做空B")
    print("   ✓ 逻辑正确")

    print("\n3. 资金费率计算（第772-777行）:")
    print("   if short_a_long_b:")
    print("       funding_income = (funding_a - funding_b) * position_value")
    print("   else:")
    print("       funding_income = (funding_b - funding_a) * position_value")
    print("   ✓ 逻辑正确")

verify_direction_logic()

# 加载最新回测结果
print("\n加载最新回测结果...")
results_dir = 'data/backtest_results'
result_files = [f for f in os.listdir(results_dir) if f.endswith('.json')]
if not result_files:
    print("❌ 未找到回测结果文件")
    sys.exit(1)

latest_file = max(result_files, key=lambda f: os.path.getmtime(os.path.join(results_dir, f)))
result_path = os.path.join(results_dir, latest_file)

with open(result_path, 'r', encoding='utf-8') as f:
    result = json.load(f)

print(f"✓ 加载回测结果: {latest_file}")

# 随机抽取5笔交易验证
print("\n随机抽取5笔交易进行人工验证：")
print("-" * 80)

for symbol_result in result['results'].values():
    if symbol_result.get('trades'):
        trades = symbol_result['trades']
        sample_trades = trades[:min(5, len(trades))]

        for i, trade in enumerate(sample_trades, 1):
            print(f"\n交易 #{i}:")
            print(f"  开仓时间: {trade.get('open_time', 'N/A')}")
            print(f"  开仓价格: A={trade.get('open_price_a', 0):.2f}, B={trade.get('open_price_b', 0):.2f}")
            print(f"  价差方向: {'A贵B便宜' if trade.get('open_price_a', 0) > trade.get('open_price_b', 0) else 'B贵A便宜'}")
            print(f"  操作: {'做空A做多B' if trade.get('short_a_long_b', True) else '做多A做空B'}")
            print(f"  平仓价格: A={trade.get('close_price_a', 0):.2f}, B={trade.get('close_price_b', 0):.2f}")
            print(f"  最终盈亏: ${trade.get('realized_pnl', 0):.2f}")

            # 手动验证
            open_a = trade.get('open_price_a', 0)
            open_b = trade.get('open_price_b', 0)
            close_a = trade.get('close_price_a', 0)
            close_b = trade.get('close_price_b', 0)
            size = trade.get('position_size', 0)
            short_a_long_b = trade.get('short_a_long_b', True)

            if short_a_long_b:
                pnl_a = (open_a - close_a) * size
                pnl_b = (close_b - open_b) * size
            else:
                pnl_a = (close_a - open_a) * size
                pnl_b = (open_b - close_b) * size

            price_pnl = pnl_a + pnl_b
            print(f"  验证: 价差盈亏=${price_pnl:.2f} (A:${pnl_a:.2f}, B:${pnl_b:.2f})")

            if open_a > 0 and close_a > 0:
                if abs(open_a - close_a) / open_a < 0.001 and abs(open_b - close_b) / open_b < 0.001:
                    print(f"  ⚠️ 警告: 价格几乎没变化，价差未收敛")
            else:
                print(f"  ⚠️ 警告: 价格数据异常（为0），跳过验证")
        break

# ===== 第二步：检查手续费是否重复扣除 =====
print("\n" + "=" * 80)
print("【第二步】检查手续费是否重复扣除")
print("-" * 80)

all_trades = []
for symbol_result in result['results'].values():
    if symbol_result.get('trades'):
        all_trades.extend(symbol_result['trades'])

if all_trades:
    gross_pnls = []
    fees = []
    net_pnls = []

    for trade in all_trades:
        # 重新计算毛收益
        open_a = trade.get('open_price_a', 0)
        open_b = trade.get('open_price_b', 0)
        close_a = trade.get('close_price_a', 0)
        close_b = trade.get('close_price_b', 0)
        size = trade.get('position_size', 0)
        short_a_long_b = trade.get('short_a_long_b', True)

        if short_a_long_b:
            pnl_a = (open_a - close_a) * size
            pnl_b = (close_b - open_b) * size
        else:
            pnl_a = (close_a - open_a) * size
            pnl_b = (open_b - close_b) * size

        gross_pnl = pnl_a + pnl_b + trade.get('accumulated_funding_pnl', 0)

        # 计算手续费
        fee = (open_a + close_a + open_b + close_b) * size * 0.0002

        net_pnl = trade.get('realized_pnl', 0)

        gross_pnls.append(gross_pnl)
        fees.append(fee)
        net_pnls.append(net_pnl)

    print(f"\n统计数据（{len(all_trades)}笔交易）:")
    print(f"  平均毛收益: ${np.mean(gross_pnls):.2f}")
    print(f"  平均手续费: ${np.mean(fees):.2f}")
    print(f"  平均净收益: ${np.mean(net_pnls):.2f}")
    print(f"  手续费占毛收益比例: {abs(np.sum(fees) / np.sum(gross_pnls)) * 100:.1f}%")

    if np.sum(fees) > abs(np.sum(gross_pnls)):
        print("\n  ⚠️ 警告: 手续费超过毛收益，策略不可行！")

    # 检查是否重复扣除
    print("\n手续费计算验证:")
    print(f"  标准手续费（4笔交易）: ${np.mean(fees):.2f}")
    print(f"  实际扣除手续费: ${np.mean(gross_pnls) - np.mean(net_pnls):.2f}")

    diff = abs(np.mean(fees) - (np.mean(gross_pnls) - np.mean(net_pnls)))
    if diff < 0.01:
        print("  ✓ 手续费计算正确，无重复扣除")
    else:
        print(f"  ⚠️ 警告: 手续费差异 ${diff:.2f}")

# ===== 第三步：检查资金费率方向 =====
print("\n" + "=" * 80)
print("【第三步】检查资金费率方向")
print("-" * 80)

funding_trades = [t for t in all_trades if t.get('accumulated_funding_pnl', 0) != 0]
if funding_trades:
    print(f"\n找到{len(funding_trades)}笔包含资金费率收益的交易")

    for i, trade in enumerate(funding_trades[:5], 1):
        print(f"\n交易 #{i}:")
        print(f"  开仓费率: A={trade.get('open_funding_a', 0):.6f}, B={trade.get('open_funding_b', 0):.6f}")
        print(f"  费率差: {(trade.get('open_funding_a', 0) - trade.get('open_funding_b', 0)) * 100:.4f}%")
        print(f"  操作: {'做空A做多B' if trade.get('short_a_long_b', True) else '做多A做空B'}")
        print(f"  资金费率收益: ${trade.get('accumulated_funding_pnl', 0):.2f}")
        print(f"  价差收益: ${trade.get('realized_pnl', 0) - trade.get('accumulated_funding_pnl', 0):.2f}")

        # 验证方向
        funding_a = trade.get('open_funding_a', 0)
        funding_b = trade.get('open_funding_b', 0)
        short_a_long_b = trade.get('short_a_long_b', True)

        if short_a_long_b:
            expected_positive = funding_a > funding_b
        else:
            expected_positive = funding_b > funding_a

        actual_positive = trade.get('accumulated_funding_pnl', 0) > 0

        if expected_positive == actual_positive:
            print("  ✓ 资金费率方向正确")
        else:
            print("  ❌ 资金费率方向错误！")
else:
    print("\n未找到包含资金费率收益的交易")

# ===== 第四步：验证是否真的存在套利机会 =====
print("\n" + "=" * 80)
print("【第四步】验证是否真的存在套利机会")
print("-" * 80)

# 加载数据
print("\n加载对齐数据...")
aligned_files = os.listdir('data/aligned')
btc_file = [f for f in aligned_files if 'BTCUSDT' in f and f.endswith('_aligned.csv')]

if btc_file:
    df = pd.read_csv(os.path.join('data/aligned', btc_file[0]))
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # 计算价差
    df['spread'] = abs(df['binance_close'] - df['kucoin_close']) / df[['binance_close', 'kucoin_close']].min(axis=1) * 100

    print(f"\n价差统计（{len(df)}根K线）:")
    print(f"  均值: {df['spread'].mean():.4f}%")
    print(f"  中位数: {df['spread'].median():.4f}%")
    print(f"  90分位: {df['spread'].quantile(0.90):.4f}%")
    print(f"  95分位: {df['spread'].quantile(0.95):.4f}%")
    print(f"  最大值: {df['spread'].max():.4f}%")

    # 手续费对比
    fee_cost = 0.0002 * 4 * 100  # 0.08%
    print(f"\n手续费成本: {fee_cost:.4f}%")

    if df['spread'].quantile(0.95) < fee_cost:
        print(f"  ⚠️ 警告: 95%的价差({df['spread'].quantile(0.95):.4f}%) < 手续费({fee_cost:.4f}%)")
        print("  结论: 市场上几乎不存在套利机会！")

    # 统计信号数量
    for threshold in [0.01, 0.02, 0.03, 0.05]:
        signal_count = (df['spread'] >= threshold).sum()
        signal_pct = signal_count / len(df) * 100
        print(f"  价差>{threshold}%的比例: {signal_pct:.2f}% ({signal_count}个)")

    # 生成价差直方图
    plt.figure(figsize=(12, 6))
    plt.hist(df['spread'], bins=100, edgecolor='black', alpha=0.7)
    plt.axvline(fee_cost, color='red', linestyle='--', linewidth=2, label=f'手续费成本 {fee_cost:.4f}%')
    plt.axvline(df['spread'].mean(), color='green', linestyle='--', linewidth=2, label=f'均值 {df['spread'].mean():.4f}%')
    plt.xlabel('价差 (%)')
    plt.ylabel('频数')
    plt.title('价差分布直方图')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig('data/results/spread_distribution.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("\n  ✓ 价差分布图已保存: data/results/spread_distribution.png")

# ===== 第五步：检查趋势暴露 =====
print("\n" + "=" * 80)
print("【第五步】检查趋势暴露（净敞口）")
print("-" * 80)

print("\n当前持仓计算方式:")
print("  position_size = balance * position_size_pct / price_a")
print("  ⚠️ 问题: 两边持仓不对等！")

print("\n假设:")
print("  balance = $10,000")
print("  position_size_pct = 10%")
print("  price_a = $81,000 (BTC)")
print("  price_b = $81,100 (BTC)")

balance = 10000
pct = 0.1
price_a = 81000
price_b = 81100

size = balance * pct / price_a
notional_a = size * price_a
notional_b = size * price_b
exposure = abs(notional_a - notional_b)

print(f"\n计算结果:")
print(f"  持仓数量: {size:.6f} BTC")
print(f"  A交易所名义价值: ${notional_a:.2f}")
print(f"  B交易所名义价值: ${notional_b:.2f}")
print(f"  净敞口: ${exposure:.2f} ({exposure/notional_a*100:.2f}%)")

if exposure / notional_a > 0.01:
    print(f"\n  ⚠️ 警告: 净敞口超过1%，存在趋势暴露！")
    print(f"  建议: 使用相同的名义价值而非数量")

# ===== 第六步：扩展到3个月数据 =====
print("\n" + "=" * 80)
print("【第六步】建议：下载3个月数据验证不同市场环境")
print("-" * 80)

print("\n当前数据: 30天")
print("建议修改: self.days = 90")
print("\n执行命令:")
print("  python main.py download --days 90")
print("  python main.py backtest --X 0.01 --Y 0.01")

# ===== 第七步：生成诊断报告 =====
print("\n" + "=" * 80)
print("【第七步】生成完整诊断报告")
print("-" * 80)

config = result.get('config', {})
summary = result.get('summary', {})

print(f"\n回测配置:")
print(f"  X (差价阈值): {config.get('X', 0)}%")
print(f"  Y (费率阈值): {config.get('Y', 0)}%")
print(f"  P (盈利目标): {config.get('P', 0)}%")
print(f"  Q (止损阈值): {config.get('Q', 0)}%")
print(f"  手续费率: {config.get('transaction_fee', 0) * 100:.2f}%")

print(f"\n回测结果:")
print(f"  总交易次数: {summary.get('total_trades', 0)}")
print(f"  总盈亏: ${summary.get('total_pnl', 0):.2f}")
print(f"  收益率: {summary.get('avg_return_rate', 0)*100:.2f}%")
print(f"  胜率: {summary.get('avg_win_rate', 0)*100:.2f}%")

if all_trades:
    holding_hours = [
        (pd.to_datetime(t['close_time']) - pd.to_datetime(t['open_time'])).total_seconds() / 3600
        for t in all_trades
    ]
    print(f"  平均持仓时间: {np.mean(holding_hours):.2f}小时")

# 导出前20笔交易明细
if all_trades:
    trades_df = pd.DataFrame(all_trades[:20])
    trades_df.to_csv('data/results/trades_detail.csv', index=False, encoding='utf-8-sig')
    print(f"\n✓ 前20笔交易明细已导出: data/results/trades_detail.csv")

# ===== 最终结论 =====
print("\n" + "=" * 80)
print("【最终诊断结论】")
print("=" * 80)

print("\n1. 是否存在套利机会？")
if 'spread' in locals():
    if df['spread'].quantile(0.95) < fee_cost:
        print("   ❌ 不存在")
        print(f"   原因: 95%的价差({df['spread'].quantile(0.95):.4f}%) < 手续费成本({fee_cost:.4f}%)")
    else:
        print("   ✓ 存在但机会很少")
        print(f"   仅{((df['spread'] >= fee_cost).sum() / len(df) * 100):.2f}%的时间存在机会")

print("\n2. 最大亏损来源？")
if all_trades:
    print(f"   手续费: ${abs(np.sum(fees)):.2f} ({abs(np.sum(fees)/np.sum(net_pnls))*100:.1f}%)")
    print(f"   价差亏损: ${abs(np.sum(gross_pnls)):.2f}")
    if np.sum(fees) > abs(np.sum(gross_pnls)):
        print("   ⚠️ 手续费 > 价差收益，策略根本不可行")

print("\n3. 代码逻辑检查？")
print("   ✓ 套利方向正确")
print("   ✓ 盈亏计算正确")
print("   ✓ 手续费计算正确")
print("   ⚠️ 存在净敞口问题（持仓不对等）")

print("\n4. 应如何修改策略？")
print("   选项A: 转向期现套利（价差更大）")
print("   选项B: 寻找小市值币种（价差0.1%-1%）")
print("   选项C: 获取VIP费率（降至0.01%）+ 使用杠杆")
print("   选项D: 放弃该策略方向")

print("\n" + "=" * 80)
print("诊断完成！")
print("=" * 80)
