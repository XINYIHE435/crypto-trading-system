# 期现套利策略实现方案

**创建日期**: 2026-06-13  
**状态**: 规划中  
**预期开发时间**: 2-3天

---

## 策略概述

### 什么是期现套利？

期现套利是利用**现货价格**和**永续合约价格**之间的价差进行套利。

**核心逻辑**：
- 当合约价格 > 现货价格（正溢价）→ 做空合约，做多现货
- 当合约价格 < 现货价格（负溢价）→ 做多合约，做空现货
- 同时收取资金费率收益

### 为什么期现套利更可行？

| 对比项 | 跨交易所套利 | 期现套利 |
|-------|------------|---------|
| 价差范围 | 0.003%-0.037% | **0.05%-0.5%** |
| 手续费成本 | 0.08% (4次交易) | **0.04%** (2次交易) |
| 转账成本 | 有（跨交易所） | **无**（同交易所） |
| 资金费率 | 可能对冲 | **额外收益** |
| 执行速度 | 慢（需等确认） | **快**（瞬时） |
| 盈利可能性 | ❌ 不可行 | ✅ **可行** |

---

## 数据需求

### 当前数据（已有）
- ✅ Binance 现货价格（30分钟K线）
- ✅ Binance 现货资金费率

### 需要新增
- 📋 Binance 永续合约价格（30分钟K线）
- 📋 Binance 永续合约资金费率
- 📋 合约持仓数据

### 数据源API

```python
# 现货K线（已有）
spot_url = "https://api.binance.com/api/v3/klines"

# 永续合约K线（需新增）
futures_url = "https://fapi.binance.com/fapi/v1/klines"

# 永续合约资金费率（需新增）
funding_url = "https://fapi.binance.com/fapi/v1/fundingRate"
```

---

## 策略逻辑

### 开仓条件

```python
# 计算期现价差
basis = (futures_price - spot_price) / spot_price * 100  # 百分比

# 计算年化收益率
funding_rate_annual = funding_rate * 3 * 365  # 每天3次，一年365天

# 开仓条件
if basis > X:  # 正溢价
    # 做空合约 + 做多现货
    if funding_rate_annual > Y:  # 资金费率也为正
        open_position(short_futures=True, long_spot=True)

elif basis < -X:  # 负溢价
    # 做多合约 + 做空现货
    if funding_rate_annual < -Y:
        open_position(long_futures=True, short_spot=True)
```

### 平仓条件

```python
# 1. 盈利平仓
if position.pnl >= P:
    close_position()

# 2. 止损平仓
if position.pnl <= -Q:
    close_position()

# 3. 价差收敛平仓
if abs(current_basis) < convergence_threshold:
    close_position()

# 4. 资金费率反转平仓
if funding_rate * position.direction < 0:
    close_position()
```

### 盈亏计算

```python
# 价差盈亏
basis_pnl = (open_basis - close_basis) * position_size * spot_price

# 资金费率收益（累计）
funding_pnl = sum(funding_rate * position_size * mark_price 
                  for each settlement)

# 手续费
fee = (spot_open + spot_close + futures_open + futures_close) * fee_rate

# 净盈亏
net_pnl = basis_pnl + funding_pnl - fee
```

---

## 实现步骤

### Phase 1: 数据采集（0.5天）

**任务**：
1. 修改 `download_and_align_data.py`
2. 新增合约数据下载函数
3. 对齐现货和合约数据

**代码框架**：
```python
def download_futures_klines(symbol):
    """下载永续合约K线"""
    url = "https://fapi.binance.com/fapi/v1/klines"
    # ... 实现逻辑
    
def download_futures_funding_rate(symbol):
    """下载永续合约资金费率"""
    url = "https://fapi.binance.com/fapi/v1/fundingRate"
    # ... 实现逻辑
    
def align_spot_futures_data(symbol):
    """对齐现货和合约数据"""
    spot_df = load_spot_data(symbol)
    futures_df = load_futures_data(symbol)
    
    # 基于timestamp合并
    aligned_df = pd.merge(spot_df, futures_df, 
                         on='timestamp', how='inner')
    
    # 计算价差
    aligned_df['basis'] = (aligned_df['futures_close'] - 
                          aligned_df['spot_close']) / aligned_df['spot_close'] * 100
    
    return aligned_df
```

### Phase 2: 策略引擎（1天）

**任务**：
1. 创建 `basis_arbitrage_system.py`
2. 实现开平仓逻辑
3. 实现盈亏计算

**代码框架**：
```python
@dataclass
class BasisArbitrageConfig:
    """期现套利配置"""
    X: float = 0.1          # 价差触发阈值（%）
    Y: float = 10.0         # 年化资金费率阈值（%）
    P: float = 0.5          # 盈利目标（%）
    Q: float = 0.3          # 止损阈值（%）
    
    convergence_threshold: float = 0.05  # 价差收敛阈值
    transaction_fee: float = 0.0002      # 手续费率
    
class BasisArbitrageSystem:
    """期现套利系统"""
    
    def __init__(self, config: BasisArbitrageConfig):
        self.config = config
        self.positions = {}
        
    def check_open_condition(self, basis, funding_rate):
        """检查开仓条件"""
        funding_annual = funding_rate * 3 * 365 * 100
        
        if basis > self.config.X and funding_annual > self.config.Y:
            return True, "short_futures_long_spot"
        elif basis < -self.config.X and funding_annual < -self.config.Y:
            return True, "long_futures_short_spot"
        return False, None
        
    def calculate_pnl(self, position, current_data):
        """计算盈亏"""
        # 价差变化盈亏
        basis_change = position.open_basis - current_data['basis']
        basis_pnl = basis_change / 100 * position.size * current_data['spot_close']
        
        # 资金费率累计收益
        funding_pnl = position.accumulated_funding
        
        # 手续费
        fee = self.calculate_fee(position)
        
        return basis_pnl + funding_pnl - fee
```

### Phase 3: 回测验证（0.5天）

**任务**：
1. 使用30天数据回测
2. 验证策略盈利性
3. 优化参数

**预期结果**：
```python
# 期望回测结果
总交易次数: 50-100笔
总盈亏: +$200 to +$500
收益率: +2% to +5%
胜率: 60%-70%
```

### Phase 4: 集成到系统（1天）

**任务**：
1. 更新 `main.py` 添加期现套利选项
2. 更新 Dashboard 支持期现套利
3. 生成可视化图表

**命令行接口**：
```bash
# 运行期现套利回测
python main.py backtest --strategy basis --X 0.1 --Y 10

# 运行参数优化
python main.py backtest --strategy basis --optimize
```

---

## 预期效果

### 理论分析

**价差统计（预估）**：
```
均值: 0.15%
中位数: 0.12%
90分位: 0.35%
95分位: 0.50%
```

**盈亏模拟**：
```
场景1：正常套利
  开仓价差: 0.20%
  平仓价差: 0.05%
  价差收敛: 0.15%
  收益: 0.15% × $1000 = $1.50
  手续费: 0.04% × $1000 = $0.40
  净盈亏: $1.10 ✅

场景2：含资金费率
  价差收益: $1.00
  资金费率收益: $0.50 (8小时 × 0.01%)
  手续费: $0.40
  净盈亏: $1.10 ✅

场景3：极端价差
  开仓价差: 0.50%
  平仓价差: 0.10%
  收益: $4.00
  手续费: $0.40
  净盈亏: $3.60 ✅✅
```

### 风险因素

1. **交割风险** - 永续合约无交割，风险小
2. **资金费率反转** - 需要及时平仓
3. **极端行情** - 价差可能扩大而非收敛
4. **保证金风险** - 合约需要保证金，可能被强平

---

## 开发计划

### Timeline

| Day | 任务 | 输出 |
|-----|-----|------|
| 1 | 数据采集 | 现货+合约对齐数据 |
| 2 | 策略引擎 | basis_arbitrage_system.py |
| 3 | 回测+集成 | 完整的期现套利系统 |

### 里程碑

- ✅ Day 0: 方案设计完成
- 📋 Day 1: 数据下载成功，价差>0.1%的机会>50%
- 📋 Day 2: 策略逻辑实现，单元测试通过
- 📋 Day 3: 回测结果为正，收益率>2%

---

## 技术挑战

### 挑战1: 数据对齐

**问题**：现货和合约的时间戳可能不完全对齐

**解决**：
```python
# 使用nearest方法对齐
aligned_df = pd.merge_asof(spot_df, futures_df, 
                          on='timestamp', 
                          direction='nearest',
                          tolerance=pd.Timedelta('1min'))
```

### 挑战2: 资金费率结算

**问题**：资金费率每8小时结算一次，需要准确计算

**解决**：
```python
# 记录结算时间点
settlement_times = ['00:00', '08:00', '16:00']

# 在每个结算点计算收益
if current_time.hour in [0, 8, 16] and current_time.minute == 0:
    funding_pnl = funding_rate * position_size * mark_price
    position.accumulated_funding += funding_pnl
```

### 挑战3: 手续费计算

**问题**：现货和合约手续费可能不同

**解决**：
```python
# 分别计算
spot_fee = spot_notional * 0.001  # 现货 0.1%
futures_fee = futures_notional * 0.0002  # 合约 0.02%
total_fee = spot_fee + futures_fee
```

---

## 与跨交易所套利的对比

### 代码复用

可以复用的模块：
- ✅ 数据下载框架（80%复用）
- ✅ 回测引擎框架（70%复用）
- ✅ 可视化模块（100%复用）
- ✅ 诊断工具（80%复用）

需要新写的部分：
- 📋 合约数据API调用（20%）
- 📋 期现价差计算（10%）
- 📋 开平仓逻辑（30%）

**总体工作量**: 约30%的新代码

### 参数对比

| 参数 | 跨交易所 | 期现套利 |
|-----|---------|---------|
| 触发阈值 | 0.01-0.02% | **0.1-0.2%** |
| 盈利目标 | 1.0% | **0.5%** |
| 止损阈值 | 0.8% | **0.3%** |
| 平均持仓 | 1小时 | **4-12小时** |

---

## 成功标准

### 最低要求

- ✅ 代码无bug，逻辑正确
- ✅ 回测收益率 > 0%
- ✅ 胜率 > 50%

### 理想目标

- 🎯 回测收益率 > 3%
- 🎯 胜率 > 65%
- 🎯 最大回撤 < 5%
- 🎯 夏普比率 > 1.5

---

## 替代方案

如果期现套利也不可行：

### Plan B: 统计套利
- BTC vs ETH 配对交易
- 基于协整关系
- 价差波动更大

### Plan C: 做市策略
- 在订单簿上挂单
- 赚取买卖价差
- 收取Maker返佣

### Plan D: 趋势策略
- 放弃中性策略
- 做单边多空
- 风险更高但机会更多

---

## 附录

### 参考资料

1. Binance API文档
   - https://binance-docs.github.io/apidocs/futures/cn/

2. 期现套利研究
   - "Cryptocurrency Basis Trading" (2021)
   - 平均年化收益：15-30%

3. 资金费率机制
   - 每8小时结算
   - 典型范围：-0.05% to +0.05%
   - 年化可达10-20%

### 代码模板

完整的代码模板见：
- `src/basis_arbitrage_system.py` (待创建)
- `src/data/download_basis_data.py` (待创建)

---

**文档状态**: 规划完成  
**下一步**: 开始实现 Phase 1 - 数据采集  
**预计完成**: 2-3个工作日
