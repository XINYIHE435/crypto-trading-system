"""
K线数据聚合模块

将高频K线数据（如30分钟）聚合为低频数据（如1小时、4小时、1天等）

核心功能：
1. 支持可配置的时间间隔（interval）
2. 支持可配置的聚合规则（agg_rules）
3. 提供预设的聚合逻辑（标准K线模式、平滑均值模式）

使用示例：
    from src.data.data_aggregator import aggregate_data, OHLC_RULES, MEAN_RULES
    
    # 使用标准K线模式聚合为1小时
    df_1h = aggregate_data(df, '1H', OHLC_RULES)
    
    # 使用平滑均值模式聚合为4小时
    df_4h = aggregate_data(df, '4H', MEAN_RULES)
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Callable


# ==================== 预设聚合规则 ====================

def create_ohlc_rules(price_cols: list, volume_cols: list = None, 
                      other_cols: dict = None) -> Dict[str, Any]:
    """
    创建标准K线模式的聚合规则
    
    参数:
        price_cols: 价格列名列表，每个价格组需要有 _open, _high, _low, _close 后缀
        volume_cols: 成交量列名列表，使用 sum 聚合
        other_cols: 其他列的聚合规则字典，如 {'funding_rate': 'last'}
    
    返回:
        聚合规则字典
    """
    rules = {}
    
    # 处理价格列 - OHLC模式
    for prefix in price_cols:
        rules[f'{prefix}_open'] = 'first'    # 开盘价：取第一个
        rules[f'{prefix}_high'] = 'max'       # 最高价：取最大值
        rules[f'{prefix}_low'] = 'min'        # 最低价：取最小值
        rules[f'{prefix}_close'] = 'last'     # 收盘价：取最后一个
    
    # 处理成交量列 - 求和
    if volume_cols:
        for col in volume_cols:
            rules[col] = 'sum'
    
    # 处理其他列
    if other_cols:
        rules.update(other_cols)
    
    return rules


def create_mean_rules(price_cols: list, volume_cols: list = None,
                      other_cols: dict = None) -> Dict[str, Any]:
    """
    创建平滑均值模式的聚合规则
    
    参数:
        price_cols: 价格列名列表
        volume_cols: 成交量列名列表
        other_cols: 其他列的聚合规则字典
    
    返回:
        聚合规则字典
    """
    rules = {}
    
    # 处理价格列 - 均值模式
    for prefix in price_cols:
        rules[f'{prefix}_open'] = 'mean'     # 开盘价：取平均
        rules[f'{prefix}_high'] = 'mean'      # 最高价：取平均
        rules[f'{prefix}_low'] = 'mean'       # 最低价：取平均
        rules[f'{prefix}_close'] = 'mean'     # 收盘价：取平均
    
    # 处理成交量列 - 求和
    if volume_cols:
        for col in volume_cols:
            rules[col] = 'sum'
    
    # 处理其他列
    if other_cols:
        rules.update(other_cols)
    
    return rules


# ==================== 针对套利数据的预设规则 ====================

# 标准K线模式规则（适用于套利数据）
OHLC_RULES = {
    # Binance 价格 - OHLC
    'binance_open': 'first',
    'binance_high': 'max',
    'binance_low': 'min',
    'binance_close': 'last',
    
    # Binance 成交量
    'binance_volume': 'sum',
    'binance_quote_volume': 'sum',
    
    # KuCoin 价格 - OHLC
    'kucoin_open': 'first',
    'kucoin_high': 'max',
    'kucoin_low': 'min',
    'kucoin_close': 'last',
    
    # KuCoin 成交量
    'kucoin_volume': 'sum',
    
    # 资金费率 - 取最后一个（因为资金费率是周期性的）
    'binance_funding_rate': 'last',
    'kucoin_funding_rate': 'last',
    
    # 价差相关 - 取最后一个
    'spread_pct': 'last',
    'funding_spread': 'last',
}

# 平滑均值模式规则（适用于套利数据）
MEAN_RULES = {
    # Binance 价格 - 均值
    'binance_open': 'mean',
    'binance_high': 'mean',
    'binance_low': 'mean',
    'binance_close': 'mean',
    
    # Binance 成交量
    'binance_volume': 'sum',
    'binance_quote_volume': 'sum',
    
    # KuCoin 价格 - 均值
    'kucoin_open': 'mean',
    'kucoin_high': 'mean',
    'kucoin_low': 'mean',
    'kucoin_close': 'mean',
    
    # KuCoin 成交量
    'kucoin_volume': 'sum',
    
    # 资金费率 - 取平均
    'binance_funding_rate': 'mean',
    'kucoin_funding_rate': 'mean',
    
    # 价差相关 - 取平均
    'spread_pct': 'mean',
    'funding_spread': 'mean',
}

# 针对马丁策略的OHLC规则（单交易所数据）
MARTINGALE_OHLC_RULES = {
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum',
    'quote_volume': 'sum',  # 成交额
}

MARTINGALE_MEAN_RULES = {
    'open': 'mean',
    'high': 'mean',
    'low': 'mean',
    'close': 'mean',
    'volume': 'sum',
    'quote_volume': 'sum',  # 成交额
}


# ==================== 核心聚合函数 ====================

def aggregate_data(
    df: pd.DataFrame,
    interval: str,
    agg_rules: Dict[str, Any],
    timestamp_col: str = None,
    dropna: bool = True
) -> pd.DataFrame:
    """
    将高频数据聚合为低频数据的通用函数
    
    参数:
        df: 源数据 DataFrame
            - 如果 index 是 DatetimeIndex，直接使用
            - 否则需要指定 timestamp_col
        interval: 时间间隔字符串
            - 常用格式：'30T'(30分钟), '1H'(1小时), '4H'(4小时), '1D'(1天)
            - 也支持：'31T'(31分钟), '2H'(2小时) 等自定义间隔
        agg_rules: 聚合规则字典
            - key: 列名
            - value: 聚合方法，可以是：
                - 字符串: 'first', 'last', 'mean', 'sum', 'max', 'min', 'std', 'var', 'count'
                - 函数: lambda x: x.iloc[-1] 等自定义函数
        timestamp_col: 时间戳列名（如果 index 不是 DatetimeIndex）
        dropna: 是否删除包含 NaN 的行
    
    返回:
        聚合后的 DataFrame
    
    工作原理:
        1. resample(interval): 按指定时间间隔重新采样
           - 将连续的时间序列数据按固定间隔分组
           - 例如 '1H' 会将每小时的数据分为一组
           
        2. agg(agg_rules): 对每个分组应用聚合规则
           - 对每个列应用对应的聚合函数
           - 例如 {'close': 'last'} 表示取该时间段最后一个收盘价
    
    示例:
        # 将30分钟数据聚合为1小时
        df_1h = aggregate_data(df_30m, '1H', OHLC_RULES)
        
        # 将30分钟数据聚合为4小时，使用均值模式
        df_4h = aggregate_data(df_30m, '4H', MEAN_RULES)
        
        # 自定义31分钟间隔
        df_31m = aggregate_data(df_30m, '31T', OHLC_RULES)
    """
    # 复制数据避免修改原始数据
    df_copy = df.copy()
    
    # 处理时间索引
    if not isinstance(df_copy.index, pd.DatetimeIndex):
        if timestamp_col and timestamp_col in df_copy.columns:
            df_copy[timestamp_col] = pd.to_datetime(df_copy[timestamp_col])
            df_copy.set_index(timestamp_col, inplace=True)
        elif 'timestamp' in df_copy.columns:
            df_copy['timestamp'] = pd.to_datetime(df_copy['timestamp'])
            df_copy.set_index('timestamp', inplace=True)
        else:
            # 尝试将索引转换为日期时间
            df_copy.index = pd.to_datetime(df_copy.index)
    
    # 确保索引是有序的
    df_copy = df_copy.sort_index()
    
    # 过滤聚合规则，只保留存在的列
    valid_rules = {col: rule for col, rule in agg_rules.items() 
                   if col in df_copy.columns}
    
    if not valid_rules:
        raise ValueError("聚合规则中没有匹配的列名")
    
    # 标准化时间间隔字符串，避免 FutureWarning
    normalized_interval = normalize_interval(interval)
    
    # 执行重采样和聚合
    # resample(): 创建一个 Resampler 对象，按指定间隔分组
    # agg(): 对每个分组应用聚合函数
    df_aggregated = df_copy.resample(normalized_interval).agg(valid_rules)
    
    # 删除全为 NaN 的行（可能由于数据间隙产生）
    if dropna:
        df_aggregated = df_aggregated.dropna(how='all')
    
    return df_aggregated


def normalize_interval(interval: str) -> str:
    """
    标准化时间间隔字符串，避免 pandas FutureWarning
    
    将大写的 'H', 'D' 等转换为小写 'h', 'd'
    'T' (分钟) 转换为 'min'
    """
    # 提取数字和单位
    num = ''.join(filter(str.isdigit, interval)) or '1'
    unit = ''.join(filter(str.isalpha, interval)).upper()
    
    # 转换单位
    unit_map = {
        'T': 'min',    # 分钟
        'MIN': 'min',
        'H': 'h',      # 小时
        'D': 'd',      # 天
        'W': 'W',      # 周
    }
    
    new_unit = unit_map.get(unit, unit.lower())
    return f"{num}{new_unit}"


def get_interval_minutes(interval: str) -> int:
    """
    将时间间隔字符串转换为分钟数
    
    参数:
        interval: 时间间隔字符串，如 '30T', '1H', '4H', '1D'
    
    返回:
        分钟数
    """
    interval = interval.upper()
    
    # 提取数字部分
    num = int(''.join(filter(str.isdigit, interval))) if any(c.isdigit() for c in interval) else 1
    
    # 提取单位部分
    unit = ''.join(filter(str.isalpha, interval))
    
    # 转换为分钟
    multipliers = {
        'T': 1,       # 分钟
        'MIN': 1,     # 分钟
        'H': 60,      # 小时
        'D': 1440,    # 天
        'W': 10080,   # 周
    }
    
    return num * multipliers.get(unit, 1)


def calculate_periods_for_hours(hours: int, interval: str) -> int:
    """
    计算指定小时数对应的K线根数
    
    这个函数用于将策略中的"N小时"参数转换为"N根K线"
    
    参数:
        hours: 小时数
        interval: K线时间间隔
    
    返回:
        K线根数
    
    示例:
        # 30分钟K线，8小时 = 16根
        periods = calculate_periods_for_hours(8, '30T')  # 返回 16
        
        # 1小时K线，8小时 = 8根
        periods = calculate_periods_for_hours(8, '1H')   # 返回 8
        
        # 4小时K线，8小时 = 2根
        periods = calculate_periods_for_hours(8, '4H')   # 返回 2
    """
    interval_minutes = get_interval_minutes(interval)
    hours_in_minutes = hours * 60
    return max(1, hours_in_minutes // interval_minutes)


# ==================== 便捷函数 ====================

def aggregate_to_interval(
    df: pd.DataFrame,
    interval: str,
    mode: str = 'ohlc'
) -> pd.DataFrame:
    """
    便捷函数：根据模式聚合数据
    
    参数:
        df: 源数据
        interval: 目标时间间隔
        mode: 聚合模式
            - 'ohlc': 标准K线模式
            - 'mean': 平滑均值模式
    
    返回:
        聚合后的 DataFrame
    """
    # 检测数据类型
    if 'binance_close' in df.columns:
        # 套利数据
        rules = OHLC_RULES if mode == 'ohlc' else MEAN_RULES
    else:
        # 单交易所数据（马丁策略）
        rules = MARTINGALE_OHLC_RULES if mode == 'ohlc' else MARTINGALE_MEAN_RULES
    
    return aggregate_data(df, interval, rules)


def compare_aggregation_modes(
    df: pd.DataFrame,
    interval: str,
    n_rows: int = 5
) -> Dict[str, pd.DataFrame]:
    """
    对比两种聚合模式的结果
    
    参数:
        df: 源数据
        interval: 目标时间间隔
        n_rows: 显示的行数
    
    返回:
        包含两种模式结果的字典
    """
    df_ohlc = aggregate_to_interval(df, interval, 'ohlc')
    df_mean = aggregate_to_interval(df, interval, 'mean')
    
    return {
        'ohlc': df_ohlc.head(n_rows),
        'mean': df_mean.head(n_rows)
    }


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("K线数据聚合模块测试")
    print("=" * 60)
    
    # 加载测试数据
    data_file = "data/aligned/BTCUSDT_30m_aligned.csv"
    
    try:
        df = pd.read_csv(data_file, index_col=0, parse_dates=True)
        print(f"\n原始数据:")
        print(f"- 时间范围: {df.index[0]} 至 {df.index[-1]}")
        print(f"- 数据点数: {len(df)}")
        print(f"- 时间间隔: 30分钟")
        
        # 测试1: 聚合为1小时（OHLC模式）
        print("\n" + "-" * 40)
        print("【测试1】聚合为1小时 - OHLC模式")
        print("-" * 40)
        
        df_1h_ohlc = aggregate_data(df, '1H', OHLC_RULES)
        print(f"聚合后数据点数: {len(df_1h_ohlc)}")
        print("\n前5行数据:")
        print(df_1h_ohlc[['binance_open', 'binance_high', 'binance_low', 'binance_close']].head())
        
        # 测试2: 聚合为1小时（均值模式）
        print("\n" + "-" * 40)
        print("【测试2】聚合为1小时 - 均值模式")
        print("-" * 40)
        
        df_1h_mean = aggregate_data(df, '1H', MEAN_RULES)
        print(f"聚合后数据点数: {len(df_1h_mean)}")
        print("\n前5行数据:")
        print(df_1h_mean[['binance_open', 'binance_high', 'binance_low', 'binance_close']].head())
        
        # 测试3: 聚合为4小时
        print("\n" + "-" * 40)
        print("【测试3】聚合为4小时 - OHLC模式")
        print("-" * 40)
        
        df_4h = aggregate_data(df, '4H', OHLC_RULES)
        print(f"聚合后数据点数: {len(df_4h)}")
        print("\n前5行数据:")
        print(df_4h[['binance_close', 'kucoin_close', 'binance_volume']].head())
        
        # 测试4: 计算N小时对应的K线根数
        print("\n" + "-" * 40)
        print("【测试4】计算N小时对应的K线根数")
        print("-" * 40)
        
        for interval in ['30T', '1H', '4H']:
            periods = calculate_periods_for_hours(8, interval)
            print(f"8小时在 {interval} K线下 = {periods} 根")
        
        print("\n" + "=" * 60)
        print("所有测试完成!")
        print("=" * 60)
        
    except FileNotFoundError:
        print(f"数据文件不存在: {data_file}")
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
