# W&B Sweeps 自动化调参平台

基于 [Weights & Biases Sweeps](https://docs.wandb.ai/models/tutorials/sweeps) 的超参数自动优化平台，支持套利系统和马丁格尔系统的参数调优。

## 功能特点

- **多种搜索策略**: 支持随机搜索、贝叶斯优化等方法
- **可视化面板**: 实时查看训练进度和参数影响
- **并行执行**: 支持多机器并行搜索
- **断点恢复**: 可以随时暂停和恢复搜索
- **结果分析**: 自动生成参数重要性报告

## 快速开始

### 1. 安装依赖

```bash
pip install wandb
```

### 2. 登录 W&B

```bash
wandb login
```

首次使用会要求输入 API Key，可以在 https://wandb.ai/authorize 获取。

### 3. 运行超参数搜索

#### 套利系统

```bash
# 快速搜索（约20次运行，用于测试）
python run_sweep.py new --system arbitrage --mode quick --count 20

# 完整搜索（约50次运行，贝叶斯优化）
python run_sweep.py new --system arbitrage --mode full --count 50
```

#### 马丁格尔系统

```bash
# 快速搜索
python run_sweep.py new --system martingale --mode quick --count 20

# 完整搜索
python run_sweep.py new --system martingale --mode full --count 50
```

### 4. 查看结果

运行后会输出 Dashboard 链接，例如：
```
Dashboard: https://wandb.ai/your-project/sweeps/abc123
```

在 Dashboard 可以查看：
- 平行坐标图：参数组合与结果的关系
- 参数重要性图：哪些参数对结果影响最大
- 收敛曲线：搜索过程中最优值的变化

### 5. 分析结果

```bash
python analyze_sweep.py --sweep-id abc123 --project arbitrage-hyperparameter-tuning
```

## 搜索配置说明

### 套利系统参数

| 参数 | 说明 | 搜索范围 |
|------|------|----------|
| X | 价差触发阈值 (%) | 0.1 - 1.5 |
| Y | 资金费率差触发阈值 (%) | 0.01 - 0.3 |
| A | 可忽视价差 (%) | 0.01 - 0.3 |
| B | 可忽视资金费率差 (%) | 0.01 - 0.15 |
| N | 历史窗口 (小时) | 4, 6, 8, 12, 16, 24 |
| M | 持续时间 (小时) | 2, 4, 6, 8, 12 |
| P | 盈利目标 (%) | 0.1 - 1.0 |
| Q | 止损阈值 (%) | 0.2 - 1.5 |

### 马丁格尔系统参数

| 参数 | 说明 | 搜索范围 |
|------|------|----------|
| base_size | 基础手数 | 0.0005 - 0.01 |
| multiplier | 马丁倍数 | 1.2 - 3.0 |
| max_levels | 最大层数 | 4 - 10 |
| martingale_start_level | 马丁起始层 | 1 - 4 |
| grid_step | 固定网格间距 | 50 - 500 |
| grid_percentage | 百分比网格间距 (%) | 0.2 - 2.0 |
| target_profit | 止盈目标 | 5 - 50 |
| max_floating_loss | 最大浮亏 | 50 - 300 |

## 高级用法

### 恢复已有搜索

```bash
python run_sweep.py resume --sweep-id abc123 --system arbitrage --count 30
```

### 自定义搜索配置

编辑 `sweep_config.py` 修改搜索空间：

```python
ARBITRAGE_SWEEP_CONFIG = {
    'method': 'bayes',  # 或 'random', 'grid'
    'metric': {
        'name': 'avg_return_rate',
        'goal': 'maximize'
    },
    'parameters': {
        'X': {
            'distribution': 'uniform',
            'min': 0.1,
            'max': 1.5
        },
        # ... 其他参数
    }
}
```

### 多机器并行搜索

在多台机器上运行相同的 sweep_id 即可并行搜索：

```bash
# 机器 1
wandb agent your-entity/your-project/sweep_id

# 机器 2
wandb agent your-entity/your-project/sweep_id
```

## 优化目标

### 套利系统

- **主要指标**: `avg_return_rate` (平均收益率)
- **次要指标**: `win_rate` (胜率), `total_trades` (交易次数)

### 马丁格尔系统

- **主要指标**: `total_pnl` (总盈亏)
- **次要指标**: `sharpe_ratio` (夏普比率), `max_drawdown` (最大回撤)

## 文件结构

```
hyperparameter_tuning/
├── __init__.py         # 模块初始化
├── sweep_config.py     # 搜索配置定义
├── run_sweep.py        # 运行搜索脚本
├── analyze_sweep.py    # 结果分析工具
└── README.md           # 使用说明
```

## 参考链接

- [W&B Sweeps 文档](https://docs.wandb.ai/models/tutorials/sweeps)
- [搜索配置详解](https://docs.wandb.ai/models/sweeps/sweep-config-keys/)
- [可视化面板指南](https://docs.wandb.ai/models/sweeps/walkthrough/)
