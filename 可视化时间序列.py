#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间序列可视化 - 展现交易过程
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "src"))

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from src.arbitrage_system import ArbitrageSystem
from src.config import Config

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Helvetica', 'PingFang SC', 'STHeiti', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

def run_backtest_with_trades(symbol='BTCUSDT'):
    """运行回测并获取交易详情"""
    print(f"运行 {symbol} 回测以获取交易详情...")
    
    config = Config("config/config.ini")
    arbitrage_config = config.get_arbitrage_config()
    
    system = ArbitrageSystem(
        config=arbitrage_config,
        initial_balance=10000,
        transaction_fee=0.001,
        enable_funding_rate=True
    )
    
    aligned_file = f"data/aligned/{symbol}_30m_aligned.csv"
    df = system.load_data(aligned_file, symbol)
    
    # 运行回测
    results = system.run_backtest(df=df, symbol=symbol)
    
    # 获取交易历史
    trades = system.closed_trades
    
    return df, results, trades, system

def create_time_series_visualization(symbol='BTCUSDT'):
    """创建时间序列可视化"""
    
    print(f"\n{'='*60}")
    print(f"生成 {symbol} 时间序列可视化")
    print(f"{'='*60}")
    
    # 运行回测获取交易详情
    df, results, trades, system = run_backtest_with_trades(symbol)
    
    if not trades:
        print(f"❌ {symbol} 没有交易记录")
        return
    
    # 创建图表 - 增加间距
    fig = plt.figure(figsize=(18, 14))
    gs = fig.add_gridspec(4, 1, hspace=0.4, height_ratios=[2.5, 1.2, 1.2, 1.2])
    
    # 获取价格数据
    exchanges = set()
    for col in df.columns:
        if '_close' in col:
            exchange = col.split('_')[0]
            exchanges.add(exchange)
    
    exchanges = sorted(list(exchanges))
    if len(exchanges) < 2:
        print(f"❌ {symbol} 需要至少2个交易所的数据")
        return
    
    # 1. 价格走势和交易信号
    ax1 = fig.add_subplot(gs[0])
    
    # 绘制价格
    for i, exchange in enumerate(exchanges):
        price_col = f"{exchange}_close"
        if price_col in df.columns:
            ax1.plot(df.index, df[price_col], 
                    label=f'{exchange.upper()} 价格', 
                    linewidth=1.5, alpha=0.7)
    
    # 绘制交易点
    buy_times = []
    sell_times = []
    buy_prices = []
    sell_prices = []
    buy_labeled = False
    sell_profit_labeled = False
    sell_loss_labeled = False
    
    for trade in trades:
        # trades是字典列表
        if isinstance(trade, dict):
            entry_time = pd.to_datetime(trade.get('entry_time'))
            exit_time = pd.to_datetime(trade.get('exit_time'))
            entry_price = trade.get('entry_price', 0)
            exit_price = trade.get('exit_price', 0)
            realized_pnl = trade.get('net_pnl', 0)
            
            # 开仓点
            if entry_time in df.index or (df.index[0] <= entry_time <= df.index[-1]):
                buy_times.append(entry_time)
                buy_prices.append(entry_price)
                ax1.scatter(entry_time, entry_price, 
                           color='green', marker='^', s=100, 
                           zorder=5, label='开仓' if not buy_labeled else '')
                buy_labeled = True
            
            # 平仓点
            if exit_time in df.index or (df.index[0] <= exit_time <= df.index[-1]):
                sell_times.append(exit_time)
                sell_prices.append(exit_price)
                color = 'red' if realized_pnl < 0 else 'blue'
                label = ''
                if realized_pnl >= 0 and not sell_profit_labeled:
                    label = '平仓(盈利)'
                    sell_profit_labeled = True
                elif realized_pnl < 0 and not sell_loss_labeled:
                    label = '平仓(亏损)'
                    sell_loss_labeled = True
                
                ax1.scatter(exit_time, exit_price, 
                           color=color, marker='v', s=100, 
                           zorder=5, label=label)
    
    ax1.set_title(f'{symbol} 价格走势与交易信号', fontsize=16, fontweight='bold', pad=15)
    ax1.set_ylabel('价格 (USDT)', fontsize=12)
    ax1.legend(loc='upper left', ncol=4, fontsize=9)
    ax1.grid(True, alpha=0.3)
    # 优化时间轴显示
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=3))  # 每3天一个刻度
    ax1.xaxis.set_minor_locator(mdates.DayLocator(interval=1))  # 每天一个次刻度
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)
    
    # 2. 累计盈亏曲线
    ax2 = fig.add_subplot(gs[1])
    
    # 计算累计盈亏
    cumulative_pnl = []
    cumulative_times = []
    running_pnl = 0
    
    # 按时间排序交易
    sorted_trades = sorted(trades, key=lambda t: pd.to_datetime(t.get('exit_time', df.index[0])) if isinstance(t, dict) else (t.exit_time if hasattr(t, 'exit_time') else df.index[0]))
    
    for trade in sorted_trades:
        if isinstance(trade, dict):
            exit_time = pd.to_datetime(trade.get('exit_time'))
            realized_pnl = trade.get('net_pnl', 0)
        else:
            exit_time = trade.exit_time if hasattr(trade, 'exit_time') else df.index[0]
            realized_pnl = trade.realized_pnl if hasattr(trade, 'realized_pnl') else 0
        
        running_pnl += realized_pnl
        cumulative_pnl.append(running_pnl)
        cumulative_times.append(exit_time)
    
    if cumulative_times:
        ax2.plot(cumulative_times, cumulative_pnl, 
                linewidth=2, color='blue', label='累计盈亏')
        ax2.fill_between(cumulative_times, 0, cumulative_pnl, 
                        where=np.array(cumulative_pnl) >= 0, 
                        color='green', alpha=0.3, label='盈利区域')
        ax2.fill_between(cumulative_times, 0, cumulative_pnl, 
                        where=np.array(cumulative_pnl) < 0, 
                        color='red', alpha=0.3, label='亏损区域')
        ax2.axhline(y=0, color='black', linestyle='--', linewidth=1)
    
    ax2.set_title('累计盈亏曲线', fontsize=14, fontweight='bold', pad=15)
    ax2.set_ylabel('累计盈亏 ($)', fontsize=12)
    ax2.legend(loc='upper left', fontsize=9)
    ax2.grid(True, alpha=0.3)
    # 优化时间轴显示
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax2.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    ax2.xaxis.set_minor_locator(mdates.DayLocator(interval=1))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)
    
    # 3. 单笔交易盈亏分布
    ax3 = fig.add_subplot(gs[2])
    
    trade_pnls = []
    trade_times = []
    for t in sorted_trades:
        if isinstance(t, dict):
            pnl = t.get('net_pnl', 0)
            exit_time = pd.to_datetime(t.get('exit_time'))
        else:
            pnl = t.realized_pnl if hasattr(t, 'realized_pnl') else 0
            exit_time = t.exit_time if hasattr(t, 'exit_time') else df.index[0]
        trade_pnls.append(pnl)
        trade_times.append(exit_time)
    
    if trade_pnls:
        colors_bar = ['green' if pnl >= 0 else 'red' for pnl in trade_pnls]
        ax3.bar(range(len(trade_pnls)), trade_pnls, color=colors_bar, alpha=0.6)
        ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
        ax3.set_title('单笔交易盈亏分布', fontsize=14, fontweight='bold', pad=15)
        ax3.set_ylabel('盈亏 ($)', fontsize=12)
        ax3.set_xlabel('交易序号', fontsize=12)
        ax3.grid(True, alpha=0.3, axis='y')
        
        # 添加统计信息
        winning = [p for p in trade_pnls if p > 0]
        losing = [p for p in trade_pnls if p < 0]
        if winning:
            ax3.axhline(y=np.mean(winning), color='green', linestyle='--', 
                       linewidth=1.5, alpha=0.7, label=f'平均盈利: ${np.mean(winning):.2f}')
        if losing:
            ax3.axhline(y=np.mean(losing), color='red', linestyle='--', 
                       linewidth=1.5, alpha=0.7, label=f'平均亏损: ${np.mean(losing):.2f}')
        ax3.legend()
    
    # 4. 持仓数量变化
    ax4 = fig.add_subplot(gs[3])
    
    # 计算每个时间点的持仓数量
    position_counts = []
    position_times = []
    
    for timestamp in df.index:
        count = 0
        for trade in trades:
            if isinstance(trade, dict):
                entry_time = pd.to_datetime(trade.get('entry_time', df.index[0]))
                exit_time = pd.to_datetime(trade.get('exit_time', df.index[-1]))
            else:
                entry_time = trade.entry_time if hasattr(trade, 'entry_time') else df.index[0]
                exit_time = trade.exit_time if hasattr(trade, 'exit_time') else df.index[-1]
            
            if entry_time <= timestamp <= exit_time:
                count += 1
        position_counts.append(count)
        position_times.append(timestamp)
    
    ax4.fill_between(position_times, 0, position_counts, 
                    color='orange', alpha=0.5, label='持仓数量')
    ax4.plot(position_times, position_counts, 
            color='orange', linewidth=1.5)
    ax4.set_title('持仓数量变化', fontsize=14, fontweight='bold', pad=15)
    ax4.set_ylabel('持仓数', fontsize=12)
    ax4.set_xlabel('时间', fontsize=12)
    ax4.legend(loc='upper left', fontsize=9)
    ax4.grid(True, alpha=0.3, axis='y')
    # 优化时间轴显示
    ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    ax4.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    ax4.xaxis.set_minor_locator(mdates.DayLocator(interval=1))
    plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)
    
    # 添加总标题 - 重新计算胜率确保准确
    total_trades = len(trades)
    total_pnl = results.get('total_pnl', 0)
    
    # 重新计算胜率（确保正确）
    winning_trades = [t for t in trades if t.get('net_pnl', 0) > 0]
    losing_trades = [t for t in trades if t.get('net_pnl', 0) < 0]
    actual_win_rate = len(winning_trades) / len(trades) * 100 if trades else 0
    
    fig.suptitle(f'{symbol} 交易时间序列分析\n总交易: {total_trades} 笔 | 总盈亏: ${total_pnl:.2f} | 胜率: {actual_win_rate:.2f}% (盈利: {len(winning_trades)}, 亏损: {len(losing_trades)})',
                fontsize=16, fontweight='bold', y=0.995)
    
    # 保存图表
    output_file = f'data/results/{symbol}_time_series_analysis.png'
    Path("data/results").mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"✅ 时间序列图表已保存: {output_file}")
    plt.close()

def create_all_symbols_time_series():
    """为所有货币创建时间序列可视化"""
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
    
    print("=" * 60)
    print("生成所有货币的时间序列可视化")
    print("=" * 60)
    
    for symbol in symbols:
        try:
            create_time_series_visualization(symbol)
        except Exception as e:
            print(f"❌ {symbol} 可视化失败: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n✅ 所有时间序列可视化完成！")
    print(f"\n生成的文件在: data/results/")

if __name__ == '__main__':
    create_all_symbols_time_series()
