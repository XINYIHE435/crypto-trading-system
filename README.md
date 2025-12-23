# 多交易所K线数据下载系统

这是一个用于下载和同步多个交易所K线数据的Python系统，支持OKX、Binance和Bybit三个主要交易所。

## 功能特点

- **多交易所支持**: 支持OKX、Binance、Bybit三个主流交易所
- **数据对齐**: 自动对齐不同交易所的时间戳
- **价差计算**: 计算交易所之间的价格差异
- **数据存储**: 支持CSV和压缩格式存储
- **配置管理**: 灵活的配置文件管理
- **异步下载**: 高效的异步数据下载
- **数据质量检查**: 自动检查数据完整性和质量

## 项目结构

```
data project/
├── src/                          # 源代码目录
│   ├── exchange/                 # 交易所接口
│   │   ├── __init__.py
│   │   ├── base.py              # 基础交易所类
│   │   ├── okx.py               # OKX交易所实现
│   │   ├── binance.py           # Binance交易所实现
│   │   └── bybit.py             # Bybit交易所实现
│   ├── __init__.py
│   ├── config_manager.py        # 配置管理
│   ├── data_downloader.py       # 主下载器
│   ├── data_aligner.py          # 数据对齐器
│   └── data_manager.py          # 数据管理器
├── config/                       # 配置目录
│   └── config.ini               # 配置文件
├── data/                         # 数据存储目录
│   ├── raw/                     # 原始数据
│   ├── aligned/                 # 对齐后数据
│   ├── processed/               # 处理后数据
│   └── metadata/                # 元信息
├── logs/                         # 日志目录
├── main.py                       # 主程序
├── test_downloader.py            # 测试脚本
├── requirements.txt              # 依赖包
└── README.md                     # 说明文档
```

## 安装和使用

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置设置

编辑 `config/config.ini` 文件，配置：

- 交易所API URLs
- 数据下载参数
- 时间范围
- 交易对列表
- 存储设置

### 3. 运行测试

```bash
python test_downloader.py
```

### 4. 下载数据

#### 测试模式（下载少量数据进行测试）
```bash
python main.py --test
```

#### 完整下载模式
```bash
# 使用默认配置下载所有数据
python main.py

# 指定交易对和时间范围
python main.py --symbols BTC/USDT ETH/USDT --interval 5m --start-date 2024-11-01 --end-date 2024-11-30
```

### 5. 参数说明

- `--symbols`: 交易对列表，格式如 `BTC/USDT ETH/USDT`
- `--interval`: 时间间隔，支持 `1m`, `5m`, `15m`, `1h`, `1d` 等
- `--start-date`: 开始日期，格式 `YYYY-MM-DD`
- `--end-date`: 结束日期，格式 `YYYY-MM-DD`
- `--test`: 测试模式
- `--config`: 配置文件路径

## 数据格式

### 原始数据格式

每个交易所的数据包含以下字段：

- `timestamp`: 时间戳（毫秒）
- `open`: 开盘价
- `high`: 最高价
- `low`: 最低价
- `close`: 收盘价
- `volume`: 交易量
- `quote_volume`: 计价货币交易量

### 对齐后数据格式

对齐后的数据包含所有交易所的价格字段：

- `close_OKX`: OKX收盘价
- `close_Binance`: Binance收盘价
- `close_Bybit`: Bybit收盘价
- `diff_OKX_Binance`: OKX-Binance价差
- `rel_diff_OKX_Binance_pct`: OKX-Binance相对价差百分比

## 配置文件说明

### [EXCHANGES] - 交易所配置
```ini
okx_base_url = https://www.okx.com
binance_base_url = https://api.binance.com
bybit_base_url = https://api.bybit.com
```

### [DATA_SETTINGS] - 数据下载设置
```ini
default_interval = 1m              # 默认时间间隔
max_records_per_request = 1000     # 每次请求最大记录数
request_delay = 0.1                # 请求间隔（秒）
retry_attempts = 3                 # 重试次数
timeout = 30                       # 超时时间（秒）
```

### [TIME_RANGE] - 时间范围
```ini
start_date = 2024-11-01
end_date = 2025-11-30
```

### [SYMBOLS] - 交易对列表
```ini
common_symbols = BTC/USDT,ETH/USDT,BNB/USDT,SOL/USDT,ADA/USDT
```

### [STORAGE] - 存储设置
```ini
data_directory = ./data            # 数据存储目录
file_format = csv                  # 文件格式
compression = gzip                 # 压缩格式
```

## 注意事项

1. **API限制**: 请遵守各交易所的API速率限制，避免过于频繁的请求
2. **数据量**: 一年的分钟级数据量很大，请确保有足够的存储空间
3. **网络稳定**: 下载大量数据时需要稳定的网络连接
4. **时间对齐**: 不同交易所的时间戳可能存在微小差异，系统会进行自动对齐

## 输出示例

### 下载过程输出
```
开始下载 10 个交易对的数据
下载交易对: 100%|██████████| 10/10 [05:32<00:00, 33.20s/it]
完成下载，成功处理 10 个交易对
数据下载完成。摘要: {'raw': {'total_files': 30, 'total_size_mb': 245.67}}
```

### 数据质量输出
```
数据对齐成功，合并后数据量: 525600
数据完整性: 99.87% (525000/525600)
最新价差示例: {'diff_OKX_Binance': 12.5, 'rel_diff_OKX_Binance_pct': 0.025}
```

## 故障排除

### 常见问题

1. **连接超时**: 检查网络连接和防火墙设置
2. **API限制**: 增加请求间隔或减少并发数
3. **数据格式错误**: 检查交易对符号格式是否正确
4. **存储空间不足**: 清理旧数据或增加存储空间

### 日志查看

详细日志保存在 `logs/data_downloader.log` 文件中。

## 后续开发

这个数据下载系统是套利系统的基础，后续可以基于此开发：

1. **实时价差监控**
2. **套利信号生成**
3. **自动交易执行**
4. **风险管理系统**
5. **收益分析模块**

## 许可证

本项目仅供学习和研究使用。