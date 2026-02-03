"""
W&B Sweeps 配置文件
定义套利系统和马丁格尔系统的超参数搜索空间
"""

# ==================== 套利系统 Sweep 配置 ====================
# 注意：参数范围根据实际数据调整
# 实测数据中价差约 0.0075% (平均), 最大 0.04%
# 资金费率差约 0.00002 (平均)
ARBITRAGE_SWEEP_CONFIG = {
    'method': 'bayes',  # 贝叶斯优化，更高效地搜索参数空间
    'metric': {
        'name': 'avg_return_rate',
        'goal': 'maximize'
    },
    'parameters': {
        # 价差触发阈值 X (%) - 根据实际数据调整，数据中价差约 0.005-0.04%
        'X': {
            'distribution': 'uniform',
            'min': 0.005,
            'max': 0.05
        },
        # 资金费率差触发阈值 Y (%) - 数据中约 0.001-0.01%
        'Y': {
            'distribution': 'uniform',
            'min': 0.001,
            'max': 0.02
        },
        # 可忽视价差 A (%)
        'A': {
            'distribution': 'uniform',
            'min': 0.001,
            'max': 0.02
        },
        # 可忽视资金费率差 B (%)
        'B': {
            'distribution': 'uniform',
            'min': 0.0005,
            'max': 0.01
        },
        # 历史窗口 N (小时)
        'N': {
            'values': [4, 6, 8, 12, 16, 24]
        },
        # 持续时间 M (小时)
        'M': {
            'values': [2, 4, 6, 8, 12]
        },
        # 盈利目标 P (%) - 低价差环境下目标也要降低
        'P': {
            'distribution': 'uniform',
            'min': 0.01,
            'max': 0.1
        },
        # 止损阈值 Q (%)
        'Q': {
            'distribution': 'uniform',
            'min': 0.02,
            'max': 0.2
        },
        # 初始资金
        'initial_balance': {
            'value': 10000
        },
        # 手续费率（单边）- 影响盈利能力的关键参数
        'transaction_fee': {
            'distribution': 'log_uniform_values',
            'min': 0.0001,  # 0.01% (VIP/Maker)
            'max': 0.001    # 0.1% (普通用户)
        }
    }
}

# 套利系统快速搜索配置（参数范围更小，搜索更快）
# 根据实际数据调整：价差约 0.005-0.04%, 资金费率差约 0.001-0.01%
# 注意：手续费必须低于价差才能盈利
ARBITRAGE_SWEEP_CONFIG_QUICK = {
    'method': 'random',
    'metric': {
        'name': 'avg_return_rate',
        'goal': 'maximize'
    },
    'parameters': {
        'X': {'values': [0.005, 0.01, 0.02, 0.03, 0.04]},  # 价差阈值 %
        'Y': {'values': [0.002, 0.005, 0.01, 0.015]},       # 资金费率差阈值 %
        'A': {'values': [0.002, 0.005, 0.01]},              # 可忽视价差 %
        'B': {'values': [0.001, 0.003, 0.005]},             # 可忽视资金费率差 %
        'N': {'values': [6, 8, 12]},                         # 历史窗口 小时
        'M': {'values': [4, 6, 8]},                          # 持续时间 小时
        'P': {'values': [0.02, 0.03, 0.05, 0.08]},          # 盈利目标 %
        'Q': {'values': [0.03, 0.05, 0.1, 0.15]},           # 止损阈值 %
        'initial_balance': {'value': 10000},
        # 手续费率（单边）- 4笔交易总手续费 = 此值 × 4
        # 0.0001 = 0.01%, 总 0.04% (VIP/Maker)
        # 0.0002 = 0.02%, 总 0.08%
        # 0.0005 = 0.05%, 总 0.20%
        'transaction_fee': {'values': [0.0001, 0.0002, 0.0005]}
    }
}


# ==================== 马丁格尔系统 Sweep 配置 ====================
MARTINGALE_SWEEP_CONFIG = {
    'method': 'bayes',
    'metric': {
        'name': 'total_pnl',
        'goal': 'maximize'
    },
    'parameters': {
        # 基础手数
        'base_size': {
            'distribution': 'log_uniform_values',
            'min': 0.0005,
            'max': 0.01
        },
        # 马丁倍数
        'multiplier': {
            'distribution': 'uniform',
            'min': 1.2,
            'max': 3.0
        },
        # 最大层数
        'max_levels': {
            'values': [4, 5, 6, 7, 8, 10]
        },
        # 马丁起始层级
        'martingale_start_level': {
            'values': [1, 2, 3, 4]
        },
        # 网格间距类型: 0=FIXED, 1=PERCENTAGE
        'grid_spacing_type': {
            'values': [0, 1]
        },
        # 固定网格间距 (当 grid_spacing_type=0)
        'grid_step': {
            'distribution': 'uniform',
            'min': 50,
            'max': 500
        },
        # 百分比网格间距 (当 grid_spacing_type=1)
        'grid_percentage': {
            'distribution': 'uniform',
            'min': 0.2,
            'max': 2.0
        },
        # 最大仓位价值
        'max_position_value': {
            'values': [500, 1000, 2000, 5000]
        },
        # 止盈模式: 0=UNIFIED, 1=PER_TRADE, 2=TIERED
        'take_profit_mode': {
            'values': [0, 1, 2]
        },
        # 统一止盈目标
        'target_profit': {
            'distribution': 'uniform',
            'min': 5,
            'max': 50
        },
        # 逐笔止盈金额
        'per_trade_profit': {
            'distribution': 'uniform',
            'min': 1,
            'max': 20
        },
        # 最大浮亏
        'max_floating_loss': {
            'distribution': 'uniform',
            'min': 50,
            'max': 300
        },
        # 基准价模式: 0=DYNAMIC, 1=FIXED
        'baseline_mode': {
            'values': [0, 1]
        },
        # 总资金
        'total_capital': {
            'value': 10000
        }
    }
}

# 马丁格尔快速搜索配置
MARTINGALE_SWEEP_CONFIG_QUICK = {
    'method': 'random',
    'metric': {
        'name': 'total_pnl',
        'goal': 'maximize'
    },
    'parameters': {
        'base_size': {'values': [0.001, 0.002, 0.005]},
        'multiplier': {'values': [1.5, 2.0, 2.5]},
        'max_levels': {'values': [5, 6, 8]},
        'martingale_start_level': {'values': [2, 3]},
        'grid_spacing_type': {'values': [0, 1]},
        'grid_step': {'values': [100, 200, 300]},
        'grid_percentage': {'values': [0.5, 1.0, 1.5]},
        'max_position_value': {'values': [500, 1000]},
        'take_profit_mode': {'values': [0, 1]},
        'target_profit': {'values': [10, 20, 30]},
        'per_trade_profit': {'values': [3, 5, 10]},
        'max_floating_loss': {'values': [100, 150, 200]},
        'baseline_mode': {'values': [0, 1]},
        'total_capital': {'value': 10000}
    }
}


# ==================== 联合优化配置 ====================
# 同时优化两个系统的资金分配比例
COMBINED_SWEEP_CONFIG = {
    'method': 'bayes',
    'metric': {
        'name': 'combined_pnl',
        'goal': 'maximize'
    },
    'parameters': {
        # 套利系统资金分配比例 (0-1)
        'arbitrage_allocation': {
            'distribution': 'uniform',
            'min': 0.2,
            'max': 0.8
        },
        # 套利系统核心参数
        'arb_X': {'values': [0.3, 0.5, 0.8]},
        'arb_Y': {'values': [0.05, 0.1, 0.15]},
        'arb_P': {'values': [0.2, 0.3, 0.5]},
        'arb_Q': {'values': [0.3, 0.5, 0.8]},
        # 马丁格尔核心参数
        'mart_multiplier': {'values': [1.5, 2.0, 2.5]},
        'mart_max_levels': {'values': [5, 6, 8]},
        'mart_grid_step': {'values': [100, 200, 300]},
        'mart_target_profit': {'values': [10, 20, 30]},
        # 总资金
        'total_capital': {'value': 10000}
    }
}
