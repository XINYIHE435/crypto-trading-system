# 加密货币量化交易系统

一个完整的加密货币量化交易系统，包含**双向马丁网格策略**和**跨交易所套利策略**，支持回测分析和交互式可视化。

## 功能特点

### 1. 双向马丁网格策略 (`Martingale/`)

基于《马丁双向.pdf》实现的完整网格交易策略：

- **网格间距模式**：固定点数 / 百分比 / ATR动态
- **马丁倍投机制**：普通层使用基础手数，马丁层倍数加仓
- **三种止盈模式**：
  - 统一回本止盈（总盈亏≥目标）
  - 逐笔小止盈（多空对冲完成后，合计盈亏达到目标）
  - 分层止盈（不同层级不同比例）
- **风险管理**：
  - 最大仓位限制（多空合计，绝对值/百分比）
  - 最大层数限制
  - 浮亏止损保护
- **基准价模式**：动态基准 / 固定区间

### 2. 跨交易所套利策略 (`src/arbitrage_system.py`)

基于《套利开平仓逻辑系统.pdf》实现的完整套利系统：

- **三种套利类型**：
  - 差价套利（价格回归）
  - 资金费率套利（费率差收益）
  - 组合套利（差价+费率）
- **开仓条件**：6种精确的开仓条件判断
- **平仓条件**：12种平仓条件逻辑
- **方向判断**：相同方向 / 不同方向
- **资金费率结算**：每8小时自动结算
- **边界处理**：当价差或费率差为 0 时，方向视为“不同方向”

### 3. 数据聚合功能 (`src/data/data_aggregator.py`)

用于将高频K线聚合为低频数据，支持自定义时间间隔与聚合规则：

- **标准K线聚合**：OHLC + 成交量求和
- **平滑均值聚合**：价格均值 + 成交量求和
- **套利/马丁专用规则**：提供预设规则字典

### 4. 可视化系统 (`visualization_app.py`)

基于Streamlit的交互式可视化应用：

- **数据选择**：币种、时间范围、K线周期
- **策略模拟**：时间轴滑块控制，逐步回放
- **K线图表**：交易信号标注、多交易所对比
- **交易记录**：详细的开平仓原因和盈亏分析
- **统计面板**：实时盈亏、胜率、交易次数

## 项目结构

```
a-r/
├── Martingale/                      # 马丁网格策略
│   ├── main.py                      # 策略核心实现
│   └── backtest.py                  # 回测脚本
├── src/                             # 套利策略
│   ├── arbitrage_system.py          # 套利系统核心 ⭐
│   ├── data/
│   │   ├── run_arbitrage_backtest.py    # 套利回测
│   │   ├── data_aggregator.py           # 数据聚合工具
│   │   └── funding_rate_loader.py       # 资金费率加载
│   ├── visualization.py             # 基础可视化
│   └── config.py                    # 配置管理
├── config/
│   ├── arbitrage_config.yaml        # 套利参数配置
│   └── config.ini                   # 系统配置
├── data/
│   ├── aligned/                     # 对齐后的数据
│   │   ├── BTCUSDT_30m_aligned.csv
│   │   ├── ETHUSDT_30m_aligned.csv
│   │   ├── BNBUSDT_30m_aligned.csv
│   │   ├── SOLUSDT_30m_aligned.csv
│   │   └── ADAUSDT_30m_aligned.csv
│   ├── raw/                         # 原始数据
│   │   ├── klines/                  # K线数据
│   │   └── funding_rates/           # 资金费率
│   ├── backtest_results/            # 回测结果
│   └── results/                     # 可视化结果
├── visualization_app.py             # Streamlit可视化应用 ⭐
├── main.py                          # 主入口
├── requirements.txt                 # 依赖包
├── 马丁双向.pdf                      # 马丁策略文档
├── 套利开平仓逻辑系统.pdf            # 套利策略文档
└── README.md                        # 本文档
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动可视化应用

```bash
streamlit run visualization_app.py
```

访问 http://localhost:8501 查看交互式界面。

### 3. 运行回测

#### 马丁网格策略回测

```bash
cd Martingale
python backtest.py
```

#### 套利策略回测

```bash
python -c "
from src.arbitrage_system import ArbitrageSystem, ArbitrageConfig
import pandas as pd

# 创建配置
config = ArbitrageConfig(
    X=0.5,    # 差价触发阈值 0.5%
    Y=0.1,    # 资金费率差触发阈值 0.1%
    P=0.3,    # 盈利目标 0.3%
    Q=0.5,    # 止损阈值 0.5%
)

# 创建系统
system = ArbitrageSystem(config)

# 加载数据
df = pd.read_csv('data/aligned/BTCUSDT_30m_aligned.csv', 
                 index_col=0, parse_dates=True)

# 运行回测
results = system.run_backtest(df, symbol='BTCUSDT')

print(f'总交易: {results[\"total_trades\"]}')
print(f'总盈亏: \${results[\"total_pnl\"]:.2f}')
print(f'胜率: {results[\"win_rate\"]:.2%}')
"
```

### 4. 数据聚合示例

```bash
python -c "
import pandas as pd
from src.data.data_aggregator import aggregate_data, OHLC_RULES, MEAN_RULES

# 读取对齐后的30分钟数据
df = pd.read_csv('data/aligned/BTCUSDT_30m_aligned.csv', index_col=0, parse_dates=True)

# 聚合为1小时（标准K线）
df_1h = aggregate_data(df, '1H', OHLC_RULES)

# 聚合为4小时（平滑均值）
df_4h = aggregate_data(df, '4H', MEAN_RULES)

print(df_1h.head())
print(df_4h.head())
"
```

## 策略参数

### 马丁网格策略参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `base_size` | 初始手数 | 0.01 |
| `multiplier` | 马丁倍数 | 1.6 |
| `max_levels` | 最大层数 | 10 |
| `grid_step` | 网格间距（固定点数）| 10.0 |
| `grid_percentage` | 网格间距（百分比）| 0.5% |
| `target_profit` | 止盈目标 | 5.0 |
| `max_floating_loss` | 最大浮亏 | 100.0 |

### 套利策略参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `X` | 差价触发阈值 | 0.5% |
| `Y` | 资金费率差触发阈值 | 0.1% |
| `A` | 可忽视差价阈值 | 0.1% |
| `B` | 可忽视资金费率阈值 | 0.05% |
| `N` | 历史数据小时数 | 8h |
| `M` | 不利持续时间 | 4h |
| `P` | 盈利目标 | 0.3% |
| `Q` | 止损阈值 | 0.5% |
| `kline_interval_minutes` | K线分钟数 | 30 |

## 策略逻辑

### 马丁网格开仓逻辑

```
价格上涨区间 (高于基准+间距) → 开多单
价格下跌区间 (低于基准-间距) → 开空单
```

### 套利开仓条件

1. **差价套利条件a**（相同方向）：差价≥X + 差价>历史均值 + 方向相同 + 费率差<Y
2. **差价套利条件b**（不同方向）：差价≥X + 差价>历史均值 + 方向不同 + 费率差<B
3. **资金费率套利条件a**（相同方向）：费率差≥Y + 历史N小时都≥Y + 方向相同 + 差价<X
4. **资金费率套利条件b**（不同方向）：费率差≥Y + 历史N小时都≥Y + 方向不同 + 差价<A
5. **组合套利**：差价≥X + 费率差≥Y + 方向相同

### 套利平仓条件

- **差价套利**：价格回归盈利 / 资金费率反转 / 价差亏损止损
- **资金费率套利**：费率收敛或反转 / 价差盈利≥P / 价差亏损≥Q
- **组合套利**：费率≤B / 费率反转 / 盈利≥P / 亏损≥Q

## 数据说明

### 支持的交易所

- **K线数据**：Binance、KuCoin
- **资金费率**：Binance、Bybit

### 支持的币种

- BTCUSDT
- ETHUSDT
- BNBUSDT
- SOLUSDT
- ADAUSDT

### 数据格式

对齐后的数据包含以下列：
- `binance_close` - Binance收盘价
- `kucoin_close` - KuCoin收盘价
- `binance_funding_rate` - Binance资金费率
- `kucoin_funding_rate` - KuCoin资金费率（来自Bybit）

## 技术栈

- **Python 3.8+**
- **Pandas** - 数据处理
- **NumPy** - 数值计算
- **Streamlit** - Web应用框架
- **Plotly** - 交互式图表
- **Matplotlib** - 静态图表

## 注意事项

1. **风险警告**：本系统仅供学习研究，实盘交易需谨慎
2. **策略验证**：建议在回测中充分验证后再考虑实盘
3. **参数调优**：根据市场条件调整策略参数
4. **手续费影响**：策略已考虑0.1%的交易手续费

## 参考文档

- `马丁双向.pdf` - 双向马丁网格策略详细说明
- `套利开平仓逻辑系统.pdf` - 套利策略完整逻辑

## 许可证

本项目仅供学习和研究使用。使用者需自行承担实盘交易的风险。
