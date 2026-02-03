#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
W&B Sweeps 自动化调参平台
支持套利系统和马丁格尔系统的超参数优化

使用方法：
1. 安装依赖: pip install wandb
2. 登录 W&B: wandb login
3. 运行调参:
   - 套利系统: python run_sweep.py --system arbitrage --count 50
   - 马丁系统: python run_sweep.py --system martingale --count 50
   - 快速搜索: python run_sweep.py --system arbitrage --mode quick --count 20
"""

import sys
import os
import argparse
from datetime import datetime

# 获取项目根目录（绝对路径）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 添加项目路径
sys.path.append(PROJECT_ROOT)

import wandb
import pandas as pd
from typing import Dict, Optional

from sweep_config import (
    ARBITRAGE_SWEEP_CONFIG,
    ARBITRAGE_SWEEP_CONFIG_QUICK,
    MARTINGALE_SWEEP_CONFIG,
    MARTINGALE_SWEEP_CONFIG_QUICK,
    COMBINED_SWEEP_CONFIG
)


class ArbitrageSweepRunner:
    """套利系统超参数搜索运行器"""
    
    def __init__(self, data_dir: str = None):
        # 使用绝对路径
        self.data_dir = data_dir or os.path.join(PROJECT_ROOT, 'data', 'aligned')
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
        print(f"数据目录: {self.data_dir}")
    
    def load_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """加载数据"""
        file_path = os.path.join(self.data_dir, f"{symbol}_30m_aligned.csv")
        if os.path.exists(file_path):
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            print(f"  加载 {symbol}: {len(df)} 行, 列: {list(df.columns)[:5]}...")
            return df
        else:
            print(f"  文件不存在: {file_path}")
        return None
    
    def detect_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """检测数据列"""
        columns = {}
        for col in df.columns:
            col_lower = col.lower()
            if 'binance' in col_lower and 'close' in col_lower:
                columns['price_col_a'] = col
            elif 'kucoin' in col_lower and 'close' in col_lower:
                columns['price_col_b'] = col
            elif 'bybit' in col_lower and 'close' in col_lower and 'price_col_b' not in columns:
                columns['price_col_b'] = col
            elif 'binance' in col_lower and 'funding' in col_lower:
                columns['funding_col_a'] = col
            elif 'kucoin' in col_lower and 'funding' in col_lower:
                columns['funding_col_b'] = col
            elif 'bybit' in col_lower and 'funding' in col_lower and 'funding_col_b' not in columns:
                columns['funding_col_b'] = col
        return columns
    
    def train(self, config=None):
        """
        训练函数 - 被 W&B agent 调用
        每次调用会使用不同的超参数组合进行回测
        """
        from src.arbitrage_system import ArbitrageSystem, ArbitrageConfig
        
        with wandb.init(config=config) as run:
            # 从 W&B 获取本次运行的配置
            config = run.config
            
            # 创建套利系统配置
            # 获取手续费参数（如果没有则使用默认值）
            transaction_fee = getattr(config, 'transaction_fee', 0.001)
            
            arb_config = ArbitrageConfig(
                X=config.X,
                Y=config.Y,
                A=config.A,
                B=config.B,
                N=config.N,
                M=config.M,
                P=config.P,
                Q=config.Q,
                initial_balance=config.initial_balance,
                transaction_fee=transaction_fee
            )
            
            print(f"  手续费率: {transaction_fee} (总手续费: {transaction_fee*4*100:.2f}%)")
            
            # 运行多币种回测
            total_trades = 0
            total_pnl = 0.0
            total_wins = 0
            successful_symbols = 0
            
            for symbol in self.symbols:
                df = self.load_data(symbol)
                if df is None:
                    print(f"  跳过 {symbol}: 数据加载失败")
                    continue
                
                columns = self.detect_columns(df)
                print(f"  {symbol} 列检测: {columns}")
                
                if 'price_col_a' not in columns or 'price_col_b' not in columns:
                    print(f"  跳过 {symbol}: 缺少价格列")
                    continue
                
                try:
                    system = ArbitrageSystem(arb_config)
                    results = system.run_backtest(
                        df=df,
                        symbol=symbol,
                        price_col_a=columns['price_col_a'],
                        price_col_b=columns['price_col_b'],
                        funding_col_a=columns.get('funding_col_a', 'binance_funding_rate'),
                        funding_col_b=columns.get('funding_col_b', 'kucoin_funding_rate')
                    )
                    
                    symbol_trades = results.get('total_trades', 0)
                    symbol_pnl = results.get('total_pnl', 0)
                    symbol_win_rate = results.get('win_rate', 0)
                    symbol_return = results.get('return_rate', 0)
                    # 计算盈利交易数
                    symbol_wins = int(symbol_trades * symbol_win_rate)
                    
                    print(f"  {symbol} 回测完成: {symbol_trades} 笔交易, 盈亏={symbol_pnl:.2f}, 胜率={symbol_win_rate:.2%}")
                    
                    if symbol_trades > 0:
                        total_trades += symbol_trades
                        total_pnl += symbol_pnl
                        total_wins += symbol_wins
                        successful_symbols += 1
                        
                        # 记录每个币种的结果
                        run.log({
                            f"{symbol}_trades": symbol_trades,
                            f"{symbol}_pnl": symbol_pnl,
                            f"{symbol}_return_rate": symbol_return,
                            f"{symbol}_win_rate": symbol_win_rate
                        })
                        
                except Exception as e:
                    import traceback
                    print(f"Error processing {symbol}: {e}")
                    traceback.print_exc()
                    continue
            
            # 计算汇总指标
            avg_return_rate = total_pnl / (config.initial_balance * successful_symbols) if successful_symbols > 0 else 0
            win_rate = total_wins / total_trades if total_trades > 0 else 0
            
            # 记录最终指标
            run.log({
                'total_trades': total_trades,
                'total_pnl': total_pnl,
                'avg_return_rate': avg_return_rate,
                'win_rate': win_rate,
                'successful_symbols': successful_symbols
            })
            
            print(f"Run completed: trades={total_trades}, pnl={total_pnl:.2f}, return={avg_return_rate:.4f}")


class MartingaleSweepRunner:
    """马丁格尔系统超参数搜索运行器"""
    
    def __init__(self, data_file: str = None):
        # 使用绝对路径
        self.data_file = data_file or os.path.join(PROJECT_ROOT, 'data', 'raw', 'klines', 'binance_BTCUSDT_30m.csv')
        print(f"数据文件: {self.data_file}")
    
    def train(self, config=None):
        """
        训练函数 - 被 W&B agent 调用
        """
        from Martingale.main import (
            DualMartingaleStrategy,
            GridSpacingType,
            TakeProfitMode,
            BaselinePriceMode
        )
        
        with wandb.init(config=config) as run:
            config = run.config
            
            # 映射枚举值
            grid_type_map = {
                0: GridSpacingType.FIXED,
                1: GridSpacingType.PERCENTAGE
            }
            tp_mode_map = {
                0: TakeProfitMode.UNIFIED,
                1: TakeProfitMode.PER_TRADE,
                2: TakeProfitMode.TIERED
            }
            baseline_map = {
                0: BaselinePriceMode.DYNAMIC,
                1: BaselinePriceMode.FIXED
            }
            
            # 创建策略配置
            strategy_params = {
                'base_size': config.base_size,
                'multiplier': config.multiplier,
                'max_levels': config.max_levels,
                'martingale_start_level': config.martingale_start_level,
                'grid_spacing_type': grid_type_map.get(config.grid_spacing_type, GridSpacingType.FIXED),
                'grid_step': config.grid_step,
                'grid_percentage': config.grid_percentage,
                'max_position_value': config.max_position_value,
                'total_capital': config.total_capital,
                'take_profit_mode': tp_mode_map.get(config.take_profit_mode, TakeProfitMode.UNIFIED),
                'target_profit': config.target_profit,
                'per_trade_profit': config.per_trade_profit,
                'max_floating_loss': config.max_floating_loss,
                'baseline_mode': baseline_map.get(config.baseline_mode, BaselinePriceMode.DYNAMIC),
                'verbose': False
            }
            
            # 加载数据
            if not os.path.exists(self.data_file):
                print(f"Data file not found: {self.data_file}")
                run.log({'total_pnl': -1000, 'error': 'data_not_found'})
                return
            
            df = pd.read_csv(self.data_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            # 运行回测
            strategy = DualMartingaleStrategy(**strategy_params)
            
            trade_count = 0
            max_drawdown = 0
            equity_curve = []
            
            for i, row in df.iterrows():
                close_price = row['close']
                
                price_data = {
                    'open': row.get('open', close_price),
                    'high': row.get('high', close_price),
                    'low': row.get('low', close_price),
                    'close': close_price
                }
                
                strategy.on_tick(close_price, price_data)
                
                # 记录状态
                status = strategy.get_status(close_price)
                current_pnl = status['total_pnl']
                equity_curve.append(current_pnl)
                
                if current_pnl < max_drawdown:
                    max_drawdown = current_pnl
                
                # 每 1000 个数据点记录一次
                if i % 1000 == 0 and i > 0:
                    run.log({
                        'step': i,
                        'current_pnl': current_pnl,
                        'trade_count': strategy.trade_count,
                        'long_level': status['long']['level'],
                        'short_level': status['short']['level']
                    })
            
            # 最终状态
            final_status = strategy.get_status(df['close'].iloc[-1])
            # 使用 cumulative_pnl（所有轮次的累计盈亏）作为真正的收益指标
            # 而不是 total_pnl（当前浮动盈亏）
            cumulative_pnl = final_status['cumulative_pnl']
            floating_pnl = final_status['total_pnl']
            # 总盈亏 = 累计已实现 + 当前浮动
            total_pnl = cumulative_pnl + floating_pnl
            
            # 计算风险调整收益
            sharpe_ratio = 0
            if len(equity_curve) > 1:
                import numpy as np
                returns = np.diff(equity_curve)
                if np.std(returns) > 0:
                    sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(365 * 48)  # 30分钟K线
            
            # 记录最终指标
            run.log({
                'total_pnl': total_pnl,
                'cumulative_pnl': final_status['cumulative_pnl'],
                'total_trades': final_status['trade_count'],
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'final_long_level': final_status['long']['level'],
                'final_short_level': final_status['short']['level']
            })
            
            print(f"Run completed: total_pnl={total_pnl:.2f} (cumulative={cumulative_pnl:.2f}, floating={floating_pnl:.2f}), "
                  f"trades={final_status['trade_count']}, drawdown={max_drawdown:.2f}")


def run_sweep(system: str, mode: str = 'full', count: int = 50, project: str = None):
    """
    运行超参数搜索
    
    Args:
        system: 系统类型 ('arbitrage', 'martingale', 'combined')
        mode: 搜索模式 ('full', 'quick')
        count: 运行次数
        project: W&B 项目名称
    """
    # 选择配置
    if system == 'arbitrage':
        config = ARBITRAGE_SWEEP_CONFIG if mode == 'full' else ARBITRAGE_SWEEP_CONFIG_QUICK
        runner = ArbitrageSweepRunner()
        train_fn = runner.train
        default_project = 'arbitrage-hyperparameter-tuning'
    elif system == 'martingale':
        config = MARTINGALE_SWEEP_CONFIG if mode == 'full' else MARTINGALE_SWEEP_CONFIG_QUICK
        runner = MartingaleSweepRunner()
        train_fn = runner.train
        default_project = 'martingale-hyperparameter-tuning'
    elif system == 'combined':
        config = COMBINED_SWEEP_CONFIG
        # TODO: 实现联合优化
        print("Combined optimization not yet implemented")
        return
    else:
        raise ValueError(f"Unknown system: {system}")
    
    project_name = project or default_project
    
    print("=" * 60)
    print(f"W&B Sweeps 超参数优化")
    print("=" * 60)
    print(f"系统: {system}")
    print(f"模式: {mode}")
    print(f"运行次数: {count}")
    print(f"项目: {project_name}")
    print(f"搜索方法: {config['method']}")
    print(f"优化目标: {config['metric']['name']} ({config['metric']['goal']})")
    print("=" * 60)
    
    # 初始化 sweep
    sweep_id = wandb.sweep(config, project=project_name)
    print(f"\nSweep ID: {sweep_id}")
    print(f"Dashboard: https://wandb.ai/{project_name}/sweeps/{sweep_id}")
    
    # 运行 agent
    print(f"\n开始运行 {count} 次超参数搜索...\n")
    wandb.agent(sweep_id, train_fn, count=count)
    
    print("\n" + "=" * 60)
    print("超参数搜索完成!")
    print(f"查看结果: https://wandb.ai/{project_name}/sweeps/{sweep_id}")
    print("=" * 60)


def resume_sweep(sweep_id: str, system: str, count: int = 50):
    """
    恢复已有的 sweep
    
    Args:
        sweep_id: 已有的 sweep ID
        system: 系统类型
        count: 继续运行次数
    """
    if system == 'arbitrage':
        runner = ArbitrageSweepRunner()
        train_fn = runner.train
    elif system == 'martingale':
        runner = MartingaleSweepRunner()
        train_fn = runner.train
    else:
        raise ValueError(f"Unknown system: {system}")
    
    print(f"恢复 Sweep: {sweep_id}")
    print(f"继续运行 {count} 次...")
    
    wandb.agent(sweep_id, train_fn, count=count)


def main():
    parser = argparse.ArgumentParser(description='W&B Sweeps 自动化调参平台')
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # 新建 sweep 命令
    new_parser = subparsers.add_parser('new', help='新建超参数搜索')
    new_parser.add_argument('--system', '-s', required=True, 
                           choices=['arbitrage', 'martingale', 'combined'],
                           help='系统类型')
    new_parser.add_argument('--mode', '-m', default='full',
                           choices=['full', 'quick'],
                           help='搜索模式 (full=完整搜索, quick=快速搜索)')
    new_parser.add_argument('--count', '-c', type=int, default=50,
                           help='运行次数 (默认: 50)')
    new_parser.add_argument('--project', '-p', type=str, default=None,
                           help='W&B 项目名称')
    
    # 恢复 sweep 命令
    resume_parser = subparsers.add_parser('resume', help='恢复已有的搜索')
    resume_parser.add_argument('--sweep-id', '-id', required=True,
                              help='Sweep ID')
    resume_parser.add_argument('--system', '-s', required=True,
                              choices=['arbitrage', 'martingale'],
                              help='系统类型')
    resume_parser.add_argument('--count', '-c', type=int, default=50,
                              help='继续运行次数')
    
    args = parser.parse_args()
    
    if args.command == 'new':
        run_sweep(
            system=args.system,
            mode=args.mode,
            count=args.count,
            project=args.project
        )
    elif args.command == 'resume':
        resume_sweep(
            sweep_id=args.sweep_id,
            system=args.system,
            count=args.count
        )
    else:
        # 默认行为：交互式选择
        print("W&B Sweeps 自动化调参平台")
        print("=" * 40)
        print("1. 套利系统 - 快速搜索")
        print("2. 套利系统 - 完整搜索")
        print("3. 马丁格尔系统 - 快速搜索")
        print("4. 马丁格尔系统 - 完整搜索")
        print("=" * 40)
        
        choice = input("请选择 (1-4): ").strip()
        
        if choice == '1':
            run_sweep('arbitrage', 'quick', 20)
        elif choice == '2':
            run_sweep('arbitrage', 'full', 50)
        elif choice == '3':
            run_sweep('martingale', 'quick', 20)
        elif choice == '4':
            run_sweep('martingale', 'full', 50)
        else:
            print("无效选择")


if __name__ == "__main__":
    main()
