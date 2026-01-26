# 跨交易所套利交易系统

一个完整的加密货币套利交易系统，支持多交易所价差套利、资金费率套利、回测分析和可视化展示。

## 功能特点

### 核心功能
- **多交易所套利**: 支持3个主流交易所（Binance、Bybit、KuCoin）
- **价差套利策略**: 自动识别交易所间价格差异，执行低买高卖套利
- **资金费率套利**: 利用不同交易所资金费率差异获利
- **市场中性策略**: 通过同时做多做空对冲方向性风险
- **智能风险管理**:
  - 止损: 5%
  - 止盈: 1.5%（风险收益比 1:3）
  - 持仓超时: 2小时自动平仓

### 数据与分析
- **历史数据下载**: 支持多交易所K线数据下载和对齐
- **回测系统**: 基于历史数据验证策略效果
- **可视化分析**:
  - K线图与交易信号
  - 交易所价格对比
  - 价差分析图表
  - 动态仪表板（HTML）
- **性能报告**: 详细的盈亏分析、胜率统计

## 项目结构

```
data project/
├── src/                                    # 源代码目录
│   ├── exchange/                           # 交易所接口
│   │   ├── base.py                         # 基础交易所类
│   │   ├── okx.py                          # OKX交易所
│   │   ├── binance.py                      # Binance交易所
│   │   ├── bybit.py                        # Bybit交易所
│   │   └── huobi.py                        # Huobi交易所
│   ├── data/                               # 数据处理模块
│   │   └── funding_rate_loader.py          # 资金费率加载器
│   ├── arbitrage_system.py                 # 核心套利系统 ⭐
│   ├── visualization.py                    # 基础可视化
│   ├── advanced_visualization.py           # 高级可视化
│   ├── time_series_visualization.py        # 时序可视化
│   ├── generate_all_symbols_charts.py      # 多币种图表生成
│   ├── config_manager.py                   # 配置管理
│   ├── data_downloader.py                  # 数据下载器
│   └── data_aligner.py                     # 数据对齐器
├── config/                                 # 配置目录
│   └── config.ini                          # 配置文件
├── data/                                   # 数据存储目录
│   ├── aligned/                            # 对齐后数据
│   │   ├── BTCUSDT_30m_aligned.csv
│   │   ├── ETHUSDT_30m_aligned.csv
│   │   ├── BNBUSDT_30m_aligned.csv
│   │   ├── SOLUSDT_30m_aligned.csv
│   │   └── ADAUSDT_30m_aligned.csv
│   ├── raw/                                # 原始数据
│   └── metadata/                           # 元信息
├── charts_*.png                            # 生成的图表文件（10个）
├── arbitrage_dashboard_dynamic.html        # 动态仪表板
├── arbitrage_report.html                   # 静态报告
├── 系统总结报告.md                         # 系统总结文档
├── 套利系统逻辑原理详解.md                 # 逻辑原理详解
├── main.py                                 # 主程序
├── requirements.txt                        # 依赖包
└── README.md                               # 本文档
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 准备数据

系统需要30分钟K线数据，已包含在 `data/aligned/` 目录中。

如需下载数据：

```bash
# 下载数据
python main.py

# 或测试模式
python main.py --test
```

### 3. 运行回测

```bash
# 进入src目录
cd src

# 运行回测（使用5个交易所，包含Kucoin）
python -c "
from arbitrage_system import ArbitrageSystem
import pandas as pd

# 创建系统实例
system = ArbitrageSystem(initial_balance=10000)

# 准备数据
symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
all_data = []
for symbol in symbols:
    df = pd.read_csv(f'../data/aligned/{symbol}_30m_aligned.csv',
                     index_col=0, parse_dates=True)
    all_data.append(df)

# 执行回测
results = system.backtest_multiple_symbols(all_data, symbols)

# 查看结果
print(f'总交易次数: {results[\"total_trades\"]}')
print(f'总盈亏: ${results[\"total_pnl\"]:.2f}')
print(f'胜率: {results[\"win_rate\"]:.2f}%')
"
```

### 4. 生成可视化图表

```bash
cd src

# 生成所有币种的图表（K线图+价格对比图）
python generate_all_symbols_charts.py

# 生成综合仪表板
python advanced_visualization.py

# 生成动态HTML报告
python visualization.py
```

## 系统配置

### 套利参数

```python
# src/arbitrage_system.py

config = {
    'min_profit_threshold': 0.002,      # 最小利润阈值 0.2%（用于开仓判断）
    'max_position_size': 10000,         # 最大持仓大小
    'stop_loss_pct': 0.05,              # 止损 5%
    'take_profit_pct': 0.015,          # 止盈 1.5%（风险收益比 1:3）
    'position_timeout': 7200,          # 最大持仓时间 2小时（7200秒）
    'trading_fee_rate': 0.001           # 手续费率 0.1%
}
```

### 交易所列表

当前支持3个交易所：
```python
exchanges = ['binance', 'bybit', 'kucoin']
```

⚠️ **重要发现**: Kucoin提供主要的套利机会
- 去除Kucoin后，价差降至0.06%以下（远低于0.5%阈值）
- 保留Kucoin时，价差可达1.4%-2.5%
- 建议：保留Kucoin或专门针对Kucoin设计套利策略

## 回测结果

### 5交易所配置（包含Kucoin）

| 指标 | 数值 |
|-----|------|
| 测试币种 | BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, ADAUSDT |
| 时间范围 | 2025-01-03 至 2025-01-13 |
| 总交易次数 | 150 |
| 总盈亏 | $1,837.82 |
| 胜率 | 58.67% |
| 收益率 | 18.38% |

### 4交易所配置（不含Kucoin）

| 指标 | 数值 |
|-----|------|
| 总交易次数 | 0 |
| 总盈亏 | $0.00 |

**原因**: 剩余4个交易所（OKX/Binance/Bybit/Huobi）价差过小（< 0.06%），无法触发交易

## 价差分析

### 含Kucoin的价差

| 币种 | 最大价差 | 平均价差 | 超阈值次数 |
|-----|---------|---------|-----------|
| BTCUSDT | 1.42% | 0.23% | 37-40次 |
| ETHUSDT | 2.04% | 0.34% | 52-53次 |
| BNBUSDT | 1.80% | 0.27% | 39-42次 |
| SOLUSDT | 2.43% | 0.37% | 66-69次 |
| ADAUSDT | 2.46% | 0.40% | 81-84次 |

### 不含Kucoin的价差

| 币种 | 最大价差 | 平均价差 |
|-----|---------|---------|
| BTCUSDT | 0.056% | 0.012% |
| ETHUSDT | 0.114% | 0.013% |
| BNBUSDT | 0.103% | 0.022% |
| SOLUSDT | 0.253% | 0.020% |
| ADAUSDT | 0.287% | 0.026% |

## 可视化输出

系统生成以下可视化文件：

### 静态图表（PNG格式）
- `charts_btcusdt_kline.png` - BTC K线图+交易信号
- `charts_btcusdt_comparison.png` - BTC价格对比+价差分析
- `charts_ethusdt_kline.png` - ETH K线图+交易信号
- `charts_ethusdt_comparison.png` - ETH价格对比+价差分析
- `charts_bnbusdt_kline.png` - BNB K线图+交易信号
- `charts_bnbusdt_comparison.png` - BNB价格对比+价差分析
- `charts_solusdt_kline.png` - SOL K线图+交易信号
- `charts_solusdt_comparison.png` - SOL价格对比+价差分析
- `charts_adausdt_kline.png` - ADA K线图+交易信号
- `charts_adausdt_comparison.png` - ADA价格对比+价差分析

### HTML报告
- `arbitrage_dashboard_dynamic.html` - 动态交互仪表板
- `arbitrage_report.html` - 综合分析报告

## 技术架构

### 核心模块

1. **ArbitrageSystem** (`arbitrage_system.py`)
   - 套利机会识别
   - 开仓/平仓逻辑
   - 风险管理
   - 利润计算

2. **数据加载器** (`data/funding_rate_loader.py`)
   - 资金费率数据加载
   - 价格数据处理
   - 数据验证

3. **可视化模块**
   - `visualization.py` - 基础图表
   - `advanced_visualization.py` - 多页仪表板
   - `generate_all_symbols_charts.py` - 批量图表生成

### 数据流程

```
原始数据 → 数据对齐 → 特征计算 → 套利信号 → 执行交易 → 盈亏计算
             ↓
       价差计算    资金费率    风险检查
```

## 策略逻辑

### 价差套利

1. **识别机会**: 当交易所间价差 > 0.5%时触发
2. **开仓逻辑**:
   - 做空高价交易所
   - 做多低价交易所
   - 等仓位对冲
3. **平仓条件**:
   - 价差收敛（盈利）
   - 止损/止盈触发
   - 持仓超时（2小时）

### 资金费率套利

考虑资金费率成本的预期利润计算：

```
净利润 = 价差 - 双边手续费 - 资金费率成本

其中:
- 价差 = (高价 - 低价) / 低价
- 双边手续费 = 2 × 0.1% = 0.2%
- 资金费率成本 = (做空费率 - 做多费率) × 持仓时间
```

## 重要发现

### Kucoin的重要性

通过数据分析发现：
- **Kucoin与其他交易所价差显著**: 1.4%-2.5%
- **其他4交易所价差微小**: 0.06%-0.29%
- **去除Kucoin后无套利机会**: 价差低于0.5%阈值

### 降低阈值的可行性

分析显示，**不推荐**降低阈值：
- 阈值 < 0.2%：大量交易亏损（无法覆盖0.2%手续费）
- 阈值 ≥ 0.2%：交易次数极少（0-7笔）
- **建议**: 保留Kucoin或调整策略架构

## 文档

项目包含详细文档：

- `系统总结报告.md` - 系统架构、数据、时间、结果总结
- `套利系统逻辑原理详解.md` - 详细逻辑说明和公式推导

## 注意事项

1. **风险警告**:
   - 本系统仅供学习研究使用
   - 实盘交易需谨慎，存在资金损失风险
   - 建议先在测试环境验证

2. **数据质量**:
   - 确保数据时间戳对齐
   - 检查缺失值和异常值
   - 验证资金费率数据准确性

3. **参数调优**:
   - 根据市场条件调整阈值
   - 优化止损止盈参数
   - 考虑滑点和手续费影响

4. **技术要求**:
   - Python 3.8+
   - 足够的内存和存储空间
   - 稳定的网络连接（实时数据）

## 依赖项

```
pandas
numpy
matplotlib
requests
aiohttp
python-dateutil
```

完整依赖见 `requirements.txt`

## 后续开发方向

1. **实时交易接口**: 连接交易所API实现实盘交易
2. **更多交易所**: Gate.io、Bitfinex等
3. **机器学习优化**: 使用ML模型预测价差趋势
4. **组合优化**: 多币种组合套利策略
5. **风险管理增强**: VaR计算、压力测试

## 许可证

本项目仅供学习和研究使用。使用者需自行承担实盘交易的风险。

## 联系方式

如有问题或建议，欢迎提交Issue或Pull Request。
