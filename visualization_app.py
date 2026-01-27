"""
交易策略可视化网页应用
支持马丁双向策略和套利策略的回测可视化

运行方式: streamlit run visualization_app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import os
import sys

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入策略模块
from Martingale.main import (
    DualMartingaleStrategy,
    GridSpacingType,
    TakeProfitMode,
    BaselinePriceMode
)
from src.arbitrage_system import ArbitrageSystem, ArbitrageConfig

# 页面配置
st.set_page_config(
    page_title="交易策略可视化平台",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式 - 修复黑色色块问题
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1rem 0;
    }
    
    /* 强制修复metric卡片 - 使用多重选择器 */
    div[data-testid="stMetric"],
    div[data-testid="metric-container"],
    .stMetric {
        background: linear-gradient(135deg, #1e2130 0%, #252a3d 100%) !important;
        padding: 15px !important;
        border-radius: 10px !important;
        border-left: 3px solid #667eea !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
    }
    
    /* metric标签颜色 */
    div[data-testid="stMetric"] label,
    div[data-testid="stMetricLabel"],
    .stMetric label {
        color: #9ca3af !important;
        font-size: 0.9rem !important;
    }
    
    /* metric数值颜色 */
    div[data-testid="stMetric"] [data-testid="stMetricValue"],
    div[data-testid="stMetricValue"],
    .stMetric div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 1.5rem !important;
        font-weight: 600 !important;
    }
    
    /* metric delta颜色 */
    div[data-testid="stMetricDelta"] {
        font-size: 0.85rem !important;
    }
    
    div[data-testid="stMetricDelta"] svg {
        display: inline-block !important;
    }
    
    /* 滑块样式 */
    .stSlider > div > div > div {
        background-color: #667eea !important;
    }
    
    /* 表格样式 */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* 按钮样式 */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    /* 分隔线 */
    hr {
        border-color: #333 !important;
    }
    
    /* 侧边栏样式 */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0e1117 0%, #1a1a2e 100%) !important;
    }
    
    section[data-testid="stSidebar"] > div {
        background: transparent !important;
    }
    
    /* 标签页样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #1a1a2e !important;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #9ca3af !important;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #667eea !important;
        color: white !important;
    }
    
    /* 自定义卡片样式类 */
    .metric-card {
        background: linear-gradient(135deg, #1e2130 0%, #252a3d 100%);
        padding: 15px 20px;
        border-radius: 10px;
        border-left: 3px solid #667eea;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        margin-bottom: 10px;
    }
    
    .metric-card-green {
        border-left-color: #00ff88;
    }
    
    .metric-card-red {
        border-left-color: #ff4444;
    }
    
    .metric-card-gold {
        border-left-color: #ffd700;
    }
    
    .metric-label {
        color: #9ca3af;
        font-size: 0.85rem;
        margin-bottom: 5px;
    }
    
    .metric-value {
        color: #ffffff;
        font-size: 1.5rem;
        font-weight: 600;
    }
    
    .metric-delta-positive {
        color: #00ff88;
        font-size: 0.85rem;
    }
    
    .metric-delta-negative {
        color: #ff4444;
        font-size: 0.85rem;
    }
    
    /* 交易卡片 */
    .trade-card {
        background: linear-gradient(135deg, #1e2130 0%, #252a3d 100%);
        padding: 12px 15px;
        border-radius: 8px;
        margin: 8px 0;
        box-shadow: 0 2px 6px rgba(0,0,0,0.2);
    }
    
    .trade-card-long {
        border-left: 4px solid #00ff88;
    }
    
    .trade-card-short {
        border-left: 4px solid #ff4444;
    }
    
    .trade-card-open {
        border-left: 4px solid #00aaff;
    }
    
    .trade-card-close-profit {
        border-left: 4px solid #00ff88;
    }
    
    .trade-card-close-loss {
        border-left: 4px solid #ff4444;
    }
</style>
""", unsafe_allow_html=True)


# ==================== 辅助函数 ====================

def render_metric_card(label: str, value: str, delta: str = None, delta_positive: bool = True, border_color: str = "#667eea"):
    """渲染自定义指标卡片，解决黑色色块问题"""
    delta_html = ""
    if delta:
        delta_class = "metric-delta-positive" if delta_positive else "metric-delta-negative"
        arrow = "↑" if delta_positive else "↓"
        delta_html = f'<div class="{delta_class}">{arrow} {delta}</div>'
    
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1e2130 0%, #252a3d 100%);
                padding: 15px 20px; border-radius: 10px; border-left: 4px solid {border_color};
                box-shadow: 0 2px 8px rgba(0,0,0,0.3); margin-bottom: 5px;">
        <div style="color: #9ca3af; font-size: 0.85rem; margin-bottom: 5px;">{label}</div>
        <div style="color: #ffffff; font-size: 1.4rem; font-weight: 600;">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def render_stat_card(label: str, value: str, color: str = "#667eea"):
    """渲染简单统计卡片"""
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1e2130 0%, #252a3d 100%);
                padding: 12px 15px; border-radius: 8px; text-align: center;
                box-shadow: 0 2px 6px rgba(0,0,0,0.2);">
        <div style="color: #9ca3af; font-size: 0.8rem;">{label}</div>
        <div style="color: {color}; font-size: 1.3rem; font-weight: 600;">{value}</div>
    </div>
    """, unsafe_allow_html=True)


# ==================== 数据加载函数 ====================

@st.cache_data
def load_kline_data(symbol: str, exchange: str = "binance") -> pd.DataFrame:
    """加载K线数据"""
    file_path = f"data/raw/klines/{exchange}_{symbol}_30m.csv"
    if not os.path.exists(file_path):
        return None
    
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


@st.cache_data
def load_aligned_data(symbol: str) -> pd.DataFrame:
    """加载对齐后的数据（用于套利策略）"""
    file_path = f"data/aligned/{symbol}_30m_aligned.csv"
    if not os.path.exists(file_path):
        return None
    
    df = pd.read_csv(file_path, index_col=0, parse_dates=True)
    df = df.reset_index()
    df.columns = ['timestamp'] + list(df.columns[1:])
    return df


def get_available_symbols():
    """获取可用的交易对"""
    kline_dir = "data/raw/klines"
    if not os.path.exists(kline_dir):
        return []
    
    symbols = set()
    for f in os.listdir(kline_dir):
        if f.startswith("binance_") and f.endswith("_30m.csv"):
            symbol = f.replace("binance_", "").replace("_30m.csv", "")
            symbols.add(symbol)
    return sorted(list(symbols))


# ==================== 马丁策略回测 ====================

def run_martingale_backtest(df: pd.DataFrame, params: dict) -> dict:
    """运行马丁策略回测"""
    strategy = DualMartingaleStrategy(**params)
    
    equity_curve = []
    trades = []
    close_events = []
    
    # 获取网格参数用于计算交易原因
    grid_type = params.get('grid_spacing_type', GridSpacingType.FIXED)
    grid_step = params.get('grid_step', 200)
    grid_pct = params.get('grid_percentage', 0.5)
    
    for i, row in df.iterrows():
        timestamp = row['timestamp']
        close_price = row['close']
        
        price_data = {
            'open': row.get('open', close_price),
            'high': row.get('high', close_price),
            'low': row.get('low', close_price),
            'close': close_price
        }
        
        prev_long = strategy.long_state.current_level
        prev_short = strategy.short_state.current_level
        prev_realized = strategy.total_realized_pnl
        prev_baseline = strategy.baseline_price
        
        strategy.on_tick(close_price, price_data)
        
        status = strategy.get_status(close_price)
        current_baseline = status['baseline_price']
        
        equity_curve.append({
            'timestamp': timestamp,
            'price': close_price,
            'pnl': status['total_pnl'],
            'realized_pnl': status['total_realized_pnl'],
            'total_pnl': status['total_pnl'] + status['total_realized_pnl'],
            'long_level': status['long']['level'],
            'short_level': status['short']['level'],
            'long_size': status['long']['total_size'],
            'short_size': status['short']['total_size'],
            'baseline_price': status['baseline_price']
        })
        
        # 记录开仓 - 包含详细原因
        if strategy.long_state.current_level > prev_long:
            order = strategy.long_state.positions[-1]
            new_level = strategy.long_state.current_level
            
            # 计算触发价格和原因
            if grid_type == GridSpacingType.PERCENTAGE:
                trigger_drop = grid_pct * new_level
                reason = f"价格从基准价{current_baseline:.2f}下跌{trigger_drop:.2f}%，触发第{new_level}层多单网格"
            else:
                trigger_drop = grid_step * new_level
                reason = f"价格从基准价{current_baseline:.2f}下跌${trigger_drop:.0f}，触发第{new_level}层多单网格"
            
            # 马丁加仓倍数说明
            if new_level >= params.get('martingale_start_level', 2):
                mult = params.get('multiplier', 1.5)
                reason += f"（马丁{mult}倍加仓）"
            
            trades.append({
                'timestamp': timestamp,
                'type': 'LONG',
                'action': 'OPEN',
                'price': order.price,
                'size': order.size,
                'level': order.level,
                'baseline': current_baseline,
                'reason': reason
            })
        
        if strategy.short_state.current_level > prev_short:
            order = strategy.short_state.positions[-1]
            new_level = strategy.short_state.current_level
            
            # 计算触发价格和原因
            if grid_type == GridSpacingType.PERCENTAGE:
                trigger_rise = grid_pct * new_level
                reason = f"价格从基准价{current_baseline:.2f}上涨{trigger_rise:.2f}%，触发第{new_level}层空单网格"
            else:
                trigger_rise = grid_step * new_level
                reason = f"价格从基准价{current_baseline:.2f}上涨${trigger_rise:.0f}，触发第{new_level}层空单网格"
            
            # 马丁加仓倍数说明
            if new_level >= params.get('martingale_start_level', 2):
                mult = params.get('multiplier', 1.5)
                reason += f"（马丁{mult}倍加仓）"
            
            trades.append({
                'timestamp': timestamp,
                'type': 'SHORT',
                'action': 'OPEN',
                'price': order.price,
                'size': order.size,
                'level': order.level,
                'baseline': current_baseline,
                'reason': reason
            })
        
        # 记录平仓 - 包含详细原因
        if strategy.total_realized_pnl > prev_realized:
            realized_pnl = strategy.total_realized_pnl - prev_realized
            
            # 判断平仓原因
            tp_mode = params.get('take_profit_mode', TakeProfitMode.UNIFIED)
            if tp_mode == TakeProfitMode.UNIFIED:
                target = params.get('target_profit', 10)
                reason = f"统一止盈：总盈亏达到目标${target}，平仓获利${realized_pnl:.2f}"
            elif tp_mode == TakeProfitMode.PER_TRADE:
                target = params.get('per_trade_profit', 5)
                reason = f"逐笔止盈：单笔盈利达到${target}，平仓获利${realized_pnl:.2f}"
            else:
                reason = f"分层止盈：平仓获利${realized_pnl:.2f}"
            
            close_events.append({
                'timestamp': timestamp,
                'price': close_price,
                'pnl': realized_pnl,
                'reason': reason
            })
    
    return {
        'equity_curve': pd.DataFrame(equity_curve),
        'trades': pd.DataFrame(trades) if trades else pd.DataFrame(),
        'close_events': pd.DataFrame(close_events) if close_events else pd.DataFrame(),
        'final_status': strategy.get_status(df['close'].iloc[-1])
    }


# ==================== 套利策略回测 ====================

def run_arbitrage_backtest(df: pd.DataFrame, config: ArbitrageConfig) -> dict:
    """运行套利策略回测"""
    system = ArbitrageSystem(config)
    
    # 检测列名
    price_col_a = 'binance_close'
    price_col_b = 'kucoin_close'
    funding_col_a = 'binance_funding_rate'
    funding_col_b = 'kucoin_funding_rate'
    
    equity_curve = []
    
    df_indexed = df.set_index('timestamp') if 'timestamp' in df.columns else df
    
    for idx in range(len(df_indexed)):
        row = df_indexed.iloc[idx]
        timestamp = df_indexed.index[idx] if isinstance(df_indexed.index[idx], datetime) else pd.to_datetime(df_indexed.index[idx])
        
        system.process_tick(
            df_indexed, idx, "TEST",
            price_col_a, price_col_b,
            funding_col_a, funding_col_b
        )
        
        price_a = row.get(price_col_a, 0)
        price_b = row.get(price_col_b, 0)
        spread_pct = abs(price_a - price_b) / min(price_a, price_b) * 100 if price_a > 0 and price_b > 0 else 0
        
        equity_curve.append({
            'timestamp': timestamp,
            'price_a': price_a,
            'price_b': price_b,
            'spread_pct': spread_pct,
            'balance': system.balance,
            'pnl': system.total_pnl,
            'positions': len(system.positions)
        })
    
    # 生成交易记录 - 包含详细原因
    trades = []
    
    # 套利类型中文名
    type_names = {
        'price_spread': '价差套利',
        'funding_rate': '资金费率套利',
        'combined': '组合套利'
    }
    
    # 平仓原因中文名
    close_reason_names = {
        'price_profit': '价格回归盈利',
        'funding_reversal': '资金费率反转止损',
        'funding_expand': '资金费率扩大止损',
        'price_loss': '价差亏损止损',
        'funding_converge': '资金费率收敛',
        'spread_profit': '价差盈利平仓',
        'manual': '手动平仓',
        'timeout': '超时平仓'
    }
    
    for pos in system.closed_positions:
        arb_type = type_names.get(pos.arbitrage_type.value, pos.arbitrage_type.value)
        direction = "同向" if pos.direction.value == "same" else "反向"
        
        # 开仓原因
        open_reason = f"{arb_type}({direction}) - "
        if pos.arbitrage_type.value == 'price_spread':
            open_reason += f"价差{pos.open_price_spread_pct:.4f}%超过阈值{config.X}%，历史均值{pos.open_historical_avg:.4f}%"
        elif pos.arbitrage_type.value == 'funding_rate':
            funding_diff = abs(pos.open_funding_a - pos.open_funding_b) * 100
            open_reason += f"资金费率差{funding_diff:.4f}%超过阈值{config.Y}%，持续满足条件"
        else:  # combined
            funding_diff = abs(pos.open_funding_a - pos.open_funding_b) * 100
            open_reason += f"价差{pos.open_price_spread_pct:.4f}%+费率差{funding_diff:.4f}%，双重套利机会"
        
        trades.append({
            'timestamp': pos.open_time,
            'type': arb_type,
            'action': 'OPEN',
            'price_binance': pos.open_price_a,
            'price_kucoin': pos.open_price_b,
            'spread_pct': pos.open_price_spread_pct,
            'funding_diff': abs(pos.open_funding_a - pos.open_funding_b) * 100,
            'pnl': 0,
            'reason': open_reason
        })
        
        # 平仓原因
        close_reason_key = pos.close_reason.value if pos.close_reason else 'unknown'
        close_reason_cn = close_reason_names.get(close_reason_key, close_reason_key)
        
        close_reason = f"{close_reason_cn} - "
        if close_reason_key == 'price_profit':
            close_reason += f"价差从{pos.open_price_spread_pct:.4f}%收敛到{pos.close_price_spread_pct:.4f}%，盈利${pos.realized_pnl:.2f}"
        elif close_reason_key == 'price_loss':
            close_reason += f"价差扩大到{pos.close_price_spread_pct:.4f}%，亏损${abs(pos.realized_pnl):.2f}"
        elif close_reason_key == 'funding_converge':
            close_reason += f"资金费率差降至{pos.close_funding_spread:.4f}%，触发平仓"
        elif close_reason_key == 'spread_profit':
            close_reason += f"价差盈利达到目标，获利${pos.realized_pnl:.2f}"
        else:
            close_reason += f"持仓{pos.holding_hours:.1f}小时，盈亏${pos.realized_pnl:.2f}"
        
        trades.append({
            'timestamp': pos.close_time,
            'type': arb_type,
            'action': 'CLOSE',
            'price_binance': pos.close_price_a,
            'price_kucoin': pos.close_price_b,
            'spread_pct': pos.close_price_spread_pct,
            'funding_diff': pos.close_funding_spread,
            'pnl': pos.realized_pnl,
            'reason': close_reason,
            'holding_hours': pos.holding_hours
        })
    
    return {
        'equity_curve': pd.DataFrame(equity_curve),
        'trades': pd.DataFrame(trades) if trades else pd.DataFrame(),
        'closed_positions': system.closed_positions,
        'results': system.generate_results()
    }


# ==================== 图表绘制函数 ====================

def create_kline_chart(df: pd.DataFrame, trades_df: pd.DataFrame = None, 
                       close_events_df: pd.DataFrame = None, title: str = "K线图") -> go.Figure:
    """创建K线图"""
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(title, '成交量', '持仓')
    )
    
    # K线
    fig.add_trace(
        go.Candlestick(
            x=df['timestamp'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='K线',
            increasing_line_color='#00ff88',
            decreasing_line_color='#ff4444'
        ),
        row=1, col=1
    )
    
    # 交易标记
    if trades_df is not None and not trades_df.empty:
        long_trades = trades_df[trades_df['type'] == 'LONG']
        short_trades = trades_df[trades_df['type'] == 'SHORT']
        
        if not long_trades.empty:
            fig.add_trace(
                go.Scatter(
                    x=long_trades['timestamp'],
                    y=long_trades['price'],
                    mode='markers',
                    marker=dict(symbol='triangle-up', size=12, color='#00ff88'),
                    name=f'多单开仓 ({len(long_trades)})',
                    hovertemplate='多单开仓<br>价格: %{y:.2f}<br>时间: %{x}<extra></extra>'
                ),
                row=1, col=1
            )
        
        if not short_trades.empty:
            fig.add_trace(
                go.Scatter(
                    x=short_trades['timestamp'],
                    y=short_trades['price'],
                    mode='markers',
                    marker=dict(symbol='triangle-down', size=12, color='#ff4444'),
                    name=f'空单开仓 ({len(short_trades)})',
                    hovertemplate='空单开仓<br>价格: %{y:.2f}<br>时间: %{x}<extra></extra>'
                ),
                row=1, col=1
            )
    
    # 平仓标记
    if close_events_df is not None and not close_events_df.empty:
        fig.add_trace(
            go.Scatter(
                x=close_events_df['timestamp'],
                y=close_events_df['price'],
                mode='markers',
                marker=dict(symbol='x', size=14, color='#ffd700', line=dict(width=2)),
                name=f'平仓 ({len(close_events_df)})',
                hovertemplate='平仓<br>价格: %{y:.2f}<br>盈亏: %{customdata:.2f}<extra></extra>',
                customdata=close_events_df['pnl']
            ),
            row=1, col=1
        )
    
    # 成交量
    if 'volume' in df.columns:
        colors = ['#00ff88' if df['close'].iloc[i] >= df['open'].iloc[i] else '#ff4444' 
                  for i in range(len(df))]
        fig.add_trace(
            go.Bar(x=df['timestamp'], y=df['volume'], name='成交量', marker_color=colors, opacity=0.7),
            row=2, col=1
        )
    
    fig.update_layout(
        height=800,
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    fig.update_xaxes(gridcolor='#333')
    fig.update_yaxes(gridcolor='#333')
    
    return fig


def create_pnl_chart(equity_df: pd.DataFrame, strategy_type: str = "martingale") -> go.Figure:
    """创建盈亏曲线图"""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        row_heights=[0.7, 0.3],
        subplot_titles=('盈亏曲线', '持仓层数')
    )
    
    if strategy_type == "martingale":
        # 浮动盈亏
        fig.add_trace(
            go.Scatter(
                x=equity_df['timestamp'], y=equity_df['pnl'],
                mode='lines', name='浮动盈亏',
                line=dict(color='#00aaff', width=2),
                fill='tozeroy',
                fillcolor='rgba(0, 170, 255, 0.1)'
            ),
            row=1, col=1
        )
        
        # 已实现盈亏
        fig.add_trace(
            go.Scatter(
                x=equity_df['timestamp'], y=equity_df['realized_pnl'],
                mode='lines', name='已实现盈亏',
                line=dict(color='#00ff88', width=2, dash='dash')
            ),
            row=1, col=1
        )
        
        # 总盈亏
        fig.add_trace(
            go.Scatter(
                x=equity_df['timestamp'], y=equity_df['total_pnl'],
                mode='lines', name='总盈亏',
                line=dict(color='#ffd700', width=2.5)
            ),
            row=1, col=1
        )
        
        # 持仓层数
        fig.add_trace(
            go.Scatter(
                x=equity_df['timestamp'], y=equity_df['long_level'],
                mode='lines', name='多单层数',
                line=dict(color='#00ff88', width=1.5),
                fill='tozeroy', fillcolor='rgba(0, 255, 136, 0.2)'
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=equity_df['timestamp'], y=-equity_df['short_level'],
                mode='lines', name='空单层数',
                line=dict(color='#ff4444', width=1.5),
                fill='tozeroy', fillcolor='rgba(255, 68, 68, 0.2)'
            ),
            row=2, col=1
        )
    
    else:  # arbitrage
        fig.add_trace(
            go.Scatter(
                x=equity_df['timestamp'], y=equity_df['pnl'],
                mode='lines', name='累计盈亏',
                line=dict(color='#ffd700', width=2),
                fill='tozeroy',
                fillcolor='rgba(255, 215, 0, 0.1)'
            ),
            row=1, col=1
        )
        
        # 价差
        fig.add_trace(
            go.Scatter(
                x=equity_df['timestamp'], y=equity_df['spread_pct'],
                mode='lines', name='价差%',
                line=dict(color='#00aaff', width=1)
            ),
            row=2, col=1
        )
    
    # 零线
    fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5, row=1, col=1)
    
    fig.update_layout(
        height=500,
        template='plotly_dark',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    fig.update_xaxes(gridcolor='#333')
    fig.update_yaxes(gridcolor='#333')
    
    return fig


def create_spread_chart(df: pd.DataFrame) -> go.Figure:
    """创建价差对比图（套利策略）"""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        row_heights=[0.6, 0.4],
        subplot_titles=('价格对比', '价差百分比')
    )
    
    # 两个交易所的价格
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'], y=df['price_a'],
            mode='lines', name='Binance',
            line=dict(color='#f0b90b', width=1.5)
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'], y=df['price_b'],
            mode='lines', name='KuCoin',
            line=dict(color='#24ae8f', width=1.5)
        ),
        row=1, col=1
    )
    
    # 价差
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'], y=df['spread_pct'],
            mode='lines', name='价差%',
            line=dict(color='#00aaff', width=1.5),
            fill='tozeroy',
            fillcolor='rgba(0, 170, 255, 0.2)'
        ),
        row=2, col=1
    )
    
    fig.update_layout(
        height=500,
        template='plotly_dark',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    return fig


# ==================== 主应用界面 ====================

def main():
    # 标题
    st.markdown('<h1 class="main-header">📈 交易策略可视化平台</h1>', unsafe_allow_html=True)
    
    # 侧边栏配置
    with st.sidebar:
        st.header("⚙️ 策略配置")
        
        # 策略选择
        strategy_type = st.selectbox(
            "选择策略",
            ["马丁双向策略", "套利策略"],
            index=0
        )
        
        st.divider()
        
        # 数据选择
        st.subheader("📊 数据设置")
        symbols = get_available_symbols()
        if not symbols:
            st.error("未找到数据文件，请先下载数据")
            return
        
        selected_symbol = st.selectbox("交易对", symbols, index=0)
        
        # 时间范围
        if strategy_type == "马丁双向策略":
            df = load_kline_data(selected_symbol)
        else:
            df = load_aligned_data(selected_symbol)
        
        if df is None:
            st.error(f"无法加载 {selected_symbol} 数据")
            return
        
        min_date = df['timestamp'].min().date()
        max_date = df['timestamp'].max().date()
        
        date_range = st.date_input(
            "时间范围",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        if len(date_range) == 2:
            start_date, end_date = date_range
            mask = (df['timestamp'].dt.date >= start_date) & (df['timestamp'].dt.date <= end_date)
            df = df[mask].reset_index(drop=True)
        
        st.divider()
        
        # 策略参数
        if strategy_type == "马丁双向策略":
            st.subheader("🎯 马丁策略参数")
            
            grid_type = st.selectbox(
                "网格类型",
                ["百分比", "固定间距"],
                index=0
            )
            
            if grid_type == "百分比":
                grid_pct = st.slider("网格百分比 (%)", 0.1, 2.0, 0.5, 0.1)
                grid_spacing_type = GridSpacingType.PERCENTAGE
            else:
                grid_step = st.slider("网格间距 (USDT)", 50, 1000, 200, 50)
                grid_spacing_type = GridSpacingType.FIXED
            
            take_profit_mode = st.selectbox(
                "止盈模式",
                ["统一止盈", "逐笔止盈", "分层止盈"],
                index=1
            )
            
            if take_profit_mode == "统一止盈":
                tp_mode = TakeProfitMode.UNIFIED
                target_profit = st.slider("目标利润 (USDT)", 5, 50, 10, 5)
            elif take_profit_mode == "逐笔止盈":
                tp_mode = TakeProfitMode.PER_TRADE
                per_trade_profit = st.slider("逐笔利润 (USDT)", 1, 20, 5, 1)
            else:
                tp_mode = TakeProfitMode.TIERED
                target_profit = st.slider("目标利润 (USDT)", 5, 50, 10, 5)
            
            multiplier = st.slider("马丁倍数", 1.0, 2.5, 1.5, 0.1)
            max_levels = st.slider("最大层数", 3, 15, 8, 1)
            max_loss = st.slider("最大浮亏 (USDT)", 50, 500, 100, 50)
            
            # 构建参数
            avg_price = df['close'].mean()
            base_size = round(100 / avg_price, 6)
            
            params = {
                'base_size': base_size,
                'grid_spacing_type': grid_spacing_type,
                'multiplier': multiplier,
                'max_levels': max_levels,
                'martingale_start_level': 2,
                'take_profit_mode': tp_mode,
                'max_floating_loss': max_loss,
                'baseline_mode': BaselinePriceMode.DYNAMIC,
                'verbose': False
            }
            
            if grid_type == "百分比":
                params['grid_percentage'] = grid_pct
            else:
                params['grid_step'] = grid_step
            
            if take_profit_mode == "统一止盈":
                params['target_profit'] = target_profit
            elif take_profit_mode == "逐笔止盈":
                params['per_trade_profit'] = per_trade_profit
            else:
                params['target_profit'] = target_profit
                params['tiered_profit_ratios'] = {1: 0.3, 2: 0.5, 3: 0.7, 4: 1.0}
        
        else:  # 套利策略
            st.subheader("🎯 套利策略参数")
            
            X = st.slider("价差阈值 X (%)", 0.01, 1.0, 0.04, 0.01)
            Y = st.slider("费率阈值 Y (%)", 0.001, 0.1, 0.003, 0.001)
            P = st.slider("盈利目标 P (%)", 0.01, 0.5, 0.02, 0.01)
            Q = st.slider("止损阈值 Q (%)", 0.01, 0.5, 0.03, 0.01)
            leverage = st.slider("杠杆倍数", 1, 5, 3, 1)
            
            config = ArbitrageConfig(
                X=X, Y=Y, P=P, Q=Q,
                A=0.01, B=0.001,
                initial_balance=10000.0,
                position_size_pct=0.1,
                transaction_fee=0.0002,
                funding_settlement_hours=8.0,
                funding_income_multiplier=float(leverage)
            )
        
        st.divider()
        
        # 运行按钮
        run_button = st.button("🚀 运行回测", type="primary", use_container_width=True)
        
        # 实时模式
        st.divider()
        st.subheader("🔄 实时模拟")
        realtime_mode = st.checkbox("启用实时模拟")
        if realtime_mode:
            speed = st.slider("播放速度", 1, 10, 5)
    
    # 主内容区域
    if run_button or ('results' in st.session_state):
        
        with st.spinner("正在运行回测..."):
            if strategy_type == "马丁双向策略":
                results = run_martingale_backtest(df, params)
                st.session_state['results'] = results
                st.session_state['strategy_type'] = 'martingale'
                st.session_state['df'] = df
            else:
                results = run_arbitrage_backtest(df, config)
                st.session_state['results'] = results
                st.session_state['strategy_type'] = 'arbitrage'
                st.session_state['df'] = df
        
        results = st.session_state['results']
        strategy = st.session_state['strategy_type']
        df = st.session_state['df']
        
        # 统计卡片
        st.subheader("📊 回测统计")
        
        if strategy == 'martingale':
            equity_df = results['equity_curve']
            trades_df = results['trades']
            close_events_df = results['close_events']
            final = results['final_status']
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            total_pnl = final['total_pnl'] + final['total_realized_pnl']
            with col1:
                color = "#00ff88" if total_pnl >= 0 else "#ff4444"
                render_metric_card("总盈亏", f"${total_pnl:.2f}", f"{total_pnl:.2f}", total_pnl >= 0, color)
            
            with col2:
                pnl = final['total_pnl']
                color = "#00ff88" if pnl >= 0 else "#ff4444"
                render_metric_card("浮动盈亏", f"${pnl:.2f}", border_color=color)
            
            with col3:
                rpnl = final['total_realized_pnl']
                color = "#00ff88" if rpnl >= 0 else "#ff4444"
                render_metric_card("已实现盈亏", f"${rpnl:.2f}", border_color=color)
            
            with col4:
                render_metric_card("交易次数", str(len(trades_df) if not trades_df.empty else 0), border_color="#00aaff")
            
            with col5:
                render_metric_card("平仓次数", str(len(close_events_df) if not close_events_df.empty else 0), border_color="#ffd700")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                max_pnl = equity_df['pnl'].max()
                render_metric_card("最大浮盈", f"${max_pnl:.2f}", border_color="#00ff88")
            
            with col2:
                min_pnl = equity_df['pnl'].min()
                render_metric_card("最大浮亏", f"${min_pnl:.2f}", border_color="#ff4444")
            
            with col3:
                max_long = equity_df['long_level'].max()
                render_metric_card("最大多单层", str(int(max_long)), border_color="#00ff88")
            
            with col4:
                max_short = equity_df['short_level'].max()
                render_metric_card("最大空单层", str(int(max_short)), border_color="#ff4444")
        
        else:  # arbitrage
            equity_df = results['equity_curve']
            trades_df = results['trades']
            res = results['results']
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                pnl = res['total_pnl']
                color = "#00ff88" if pnl >= 0 else "#ff4444"
                render_metric_card("总盈亏", f"${pnl:.2f}", f"{res['return_rate']*100:.2f}%", pnl >= 0, color)
            
            with col2:
                wr = res['win_rate'] * 100
                color = "#00ff88" if wr >= 50 else "#ffd700"
                render_metric_card("胜率", f"{wr:.1f}%", border_color=color)
            
            with col3:
                render_metric_card("交易次数", str(res['total_trades']), border_color="#00aaff")
            
            with col4:
                render_metric_card("平均持仓", f"{res.get('avg_holding_hours', 0):.1f}h", border_color="#667eea")
            
            with col5:
                mp = res.get('max_profit', 0)
                render_metric_card("最大盈利", f"${mp:.2f}", border_color="#00ff88")
        
        st.divider()
        
        # 图表展示
        tab1, tab2, tab3 = st.tabs(["📈 K线图", "💰 盈亏曲线", "📋 交易记录"])
        
        with tab1:
            if strategy == 'martingale':
                fig = create_kline_chart(df, trades_df, close_events_df, 
                                        f"{selected_symbol} K线图 - 马丁策略")
                st.plotly_chart(fig, use_container_width=True)
            else:
                # 套利策略：优化的价差可视化
                st.markdown("#### 📊 套利价差分析")
                
                # 计算价差数据
                if 'binance_close' in df.columns:
                    df['spread_abs'] = df['binance_close'] - df['kucoin_close']  # 绝对价差
                    df['spread_pct'] = df['spread_abs'] / df['binance_close'] * 100  # 百分比价差
                    df['spread_pct_abs'] = abs(df['spread_pct'])
                    df['price_mean'] = (df['binance_close'] + df['kucoin_close']) / 2  # 均价
                
                # 创建四行子图
                fig = make_subplots(
                    rows=4, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.05,
                    row_heights=[0.35, 0.25, 0.2, 0.2],
                    subplot_titles=(
                        f'价格走势 (均价参考)', 
                        '价差百分比 (Binance - KuCoin)', 
                        '绝对价差 (USDT)',
                        '累计盈亏 & 持仓'
                    ),
                    specs=[[{"secondary_y": False}],
                           [{"secondary_y": False}],
                           [{"secondary_y": False}],
                           [{"secondary_y": True}]]
                )
                
                if 'binance_close' in df.columns:
                    # 第1行：均价走势（避免两条线重叠看不清）
                    fig.add_trace(go.Scatter(
                        x=df['timestamp'], y=df['price_mean'],
                        mode='lines', name='均价',
                        line=dict(color='#888', width=1),
                        opacity=0.5
                    ), row=1, col=1)
                    
                    # 用填充区域显示价差范围
                    fig.add_trace(go.Scatter(
                        x=df['timestamp'], y=df['binance_close'],
                        mode='lines', name='Binance',
                        line=dict(color='#f0b90b', width=2),
                        fill=None
                    ), row=1, col=1)
                    
                    fig.add_trace(go.Scatter(
                        x=df['timestamp'], y=df['kucoin_close'],
                        mode='lines', name='KuCoin',
                        line=dict(color='#24ae8f', width=2),
                        fill='tonexty',  # 填充到上一条线
                        fillcolor='rgba(100, 100, 255, 0.2)'  # 用蓝色填充价差区域
                    ), row=1, col=1)
                    
                    # 第2行：价差百分比（有正负）
                    # 用柱状图更直观显示价差方向
                    colors = ['#00ff88' if x >= 0 else '#ff4444' for x in df['spread_pct']]
                    fig.add_trace(go.Bar(
                        x=df['timestamp'], y=df['spread_pct'],
                        name='价差%',
                        marker_color=colors,
                        opacity=0.7
                    ), row=2, col=1)
                    
                    # 添加阈值线
                    fig.add_hline(y=config.X, line_dash="dash", line_color="#00ff88", 
                                 opacity=0.5, row=2, col=1, 
                                 annotation_text=f"开仓阈值 {config.X}%")
                    fig.add_hline(y=-config.X, line_dash="dash", line_color="#ff4444", 
                                 opacity=0.5, row=2, col=1)
                    fig.add_hline(y=0, line_color="white", opacity=0.3, row=2, col=1)
                    
                    # 第3行：绝对价差
                    fig.add_trace(go.Scatter(
                        x=df['timestamp'], y=df['spread_abs'],
                        mode='lines', name='绝对价差',
                        line=dict(color='#00aaff', width=1.5),
                        fill='tozeroy',
                        fillcolor='rgba(0, 170, 255, 0.2)'
                    ), row=3, col=1)
                    
                    fig.add_hline(y=0, line_color="white", opacity=0.3, row=3, col=1)
                
                # 第4行：盈亏和持仓
                if 'pnl' in equity_df.columns:
                    pnl_colors = ['#00ff88' if x >= 0 else '#ff4444' for x in equity_df['pnl']]
                    fig.add_trace(go.Scatter(
                        x=equity_df['timestamp'], y=equity_df['pnl'],
                        mode='lines', name='累计盈亏',
                        line=dict(color='#ffd700', width=2),
                        fill='tozeroy',
                        fillcolor='rgba(255, 215, 0, 0.15)'
                    ), row=4, col=1, secondary_y=False)
                
                if 'positions' in equity_df.columns:
                    fig.add_trace(go.Scatter(
                        x=equity_df['timestamp'], y=equity_df['positions'],
                        mode='lines', name='持仓数',
                        line=dict(color='#ff6b6b', width=1.5, dash='dot')
                    ), row=4, col=1, secondary_y=True)
                
                # 交易标记 - 在价差图上标记
                if not trades_df.empty:
                    open_trades = trades_df[trades_df['action'] == 'OPEN']
                    close_trades = trades_df[trades_df['action'] == 'CLOSE']
                    
                    if not open_trades.empty and 'spread_pct' in open_trades.columns:
                        fig.add_trace(go.Scatter(
                            x=open_trades['timestamp'], 
                            y=open_trades['spread_pct'],
                            mode='markers',
                            marker=dict(symbol='triangle-up', size=12, color='#00ff88',
                                       line=dict(color='white', width=1)),
                            name=f'开仓 ({len(open_trades)})',
                            hovertemplate='开仓<br>时间: %{x}<br>价差: %{y:.4f}%<extra></extra>'
                        ), row=2, col=1)
                    
                    if not close_trades.empty and 'spread_pct' in close_trades.columns:
                        fig.add_trace(go.Scatter(
                            x=close_trades['timestamp'], 
                            y=close_trades['spread_pct'],
                            mode='markers',
                            marker=dict(symbol='x', size=14, color='#ffd700',
                                       line=dict(color='white', width=2)),
                            name=f'平仓 ({len(close_trades)})',
                            hovertemplate='平仓<br>时间: %{x}<br>价差: %{y:.4f}%<br>盈亏: $%{customdata:.2f}<extra></extra>',
                            customdata=close_trades['pnl']
                        ), row=2, col=1)
                
                fig.update_layout(
                    height=900,
                    template='plotly_dark',
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    margin=dict(l=50, r=50, t=80, b=50),
                    barmode='relative'
                )
                
                # 设置Y轴标签
                fig.update_yaxes(title_text="价格 (USDT)", row=1, col=1)
                fig.update_yaxes(title_text="价差 (%)", row=2, col=1)
                fig.update_yaxes(title_text="价差 (USDT)", row=3, col=1)
                fig.update_yaxes(title_text="盈亏 ($)", row=4, col=1, secondary_y=False)
                fig.update_yaxes(title_text="持仓数", row=4, col=1, secondary_y=True)
                
                st.plotly_chart(fig, use_container_width=True)
                
                # 价差统计
                if 'spread_pct' in df.columns:
                    st.markdown("#### 📈 价差统计")
                    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
                    
                    with stat_col1:
                        render_metric_card("平均价差", f"{df['spread_pct_abs'].mean():.4f}%", border_color="#00aaff")
                    with stat_col2:
                        render_metric_card("最大价差", f"{df['spread_pct_abs'].max():.4f}%", border_color="#ffd700")
                    with stat_col3:
                        over_threshold = (df['spread_pct_abs'] > config.X).sum()
                        render_metric_card(f"超过{config.X}%次数", f"{over_threshold}次", border_color="#00ff88")
                    with stat_col4:
                        pct = over_threshold / len(df) * 100
                        render_metric_card("套利机会占比", f"{pct:.1f}%", border_color="#667eea")
        
        with tab2:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                pnl_fig = create_pnl_chart(equity_df, strategy)
                st.plotly_chart(pnl_fig, use_container_width=True)
            
            with col2:
                if strategy == 'arbitrage':
                    spread_fig = create_spread_chart(equity_df)
                    st.plotly_chart(spread_fig, use_container_width=True)
                else:
                    # 显示统计分布
                    st.subheader("盈亏分布")
                    if not close_events_df.empty:
                        fig = go.Figure()
                        fig.add_trace(go.Histogram(
                            x=close_events_df['pnl'],
                            nbinsx=20,
                            marker_color='#00aaff',
                            opacity=0.7
                        ))
                        fig.update_layout(
                            template='plotly_dark',
                            height=300,
                            margin=dict(l=20, r=20, t=20, b=20)
                        )
                        st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            st.subheader("📋 交易记录（含详细原因）")
            
            if strategy == 'martingale':
                # 马丁策略交易记录
                if not trades_df.empty:
                    st.markdown("#### 🔹 开仓记录")
                    
                    # 显示带原因的交易记录
                    for idx, trade in trades_df.tail(30).iterrows():
                        trade_type = trade['type']
                        color = "#00ff88" if trade_type == 'LONG' else "#ff4444"
                        icon = "📈" if trade_type == 'LONG' else "📉"
                        
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #1a1a2e, #16213e); 
                                    padding: 12px; border-radius: 8px; margin: 8px 0;
                                    border-left: 4px solid {color};">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="color: {color}; font-weight: bold; font-size: 14px;">
                                    {icon} {trade_type} 第{trade['level']}层
                                </span>
                                <span style="color: #888; font-size: 12px;">{trade['timestamp']}</span>
                            </div>
                            <div style="color: #fff; font-size: 13px; margin-top: 5px;">
                                价格: <span style="color: #ffd700;">${trade['price']:.2f}</span> | 
                                数量: <span style="color: #00aaff;">{trade['size']:.6f}</span>
                            </div>
                            <div style="color: #aaa; font-size: 12px; margin-top: 5px;">
                                💡 {trade.get('reason', '网格触发开仓')}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                if not close_events_df.empty:
                    st.markdown("#### 🔸 平仓记录")
                    
                    for idx, event in close_events_df.tail(15).iterrows():
                        pnl = event['pnl']
                        color = "#00ff88" if pnl >= 0 else "#ff4444"
                        icon = "✅" if pnl >= 0 else "❌"
                        
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #1a1a2e, #16213e); 
                                    padding: 12px; border-radius: 8px; margin: 8px 0;
                                    border-left: 4px solid {color};">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="color: {color}; font-weight: bold; font-size: 14px;">
                                    {icon} 平仓盈亏: ${pnl:.2f}
                                </span>
                                <span style="color: #888; font-size: 12px;">{event['timestamp']}</span>
                            </div>
                            <div style="color: #fff; font-size: 13px; margin-top: 5px;">
                                平仓价格: <span style="color: #ffd700;">${event['price']:.2f}</span>
                            </div>
                            <div style="color: #aaa; font-size: 12px; margin-top: 5px;">
                                💡 {event.get('reason', '止盈/止损平仓')}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            
            else:  # arbitrage
                # 套利策略交易记录
                if not trades_df.empty:
                    st.markdown("#### 🔹 套利交易记录")
                    
                    for idx, trade in trades_df.tail(40).iterrows():
                        action = trade['action']
                        
                        if action == 'OPEN':
                            color = "#00aaff"
                            icon = "🔓"
                            title = f"开仓 - {trade['type']}"
                        else:
                            pnl = trade.get('pnl', 0)
                            color = "#00ff88" if pnl >= 0 else "#ff4444"
                            icon = "🔒"
                            title = f"平仓 - {trade['type']} (${pnl:.2f})"
                        
                        # 获取价格信息
                        price_binance = trade.get('price_binance', trade.get('price', 0))
                        price_kucoin = trade.get('price_kucoin', 0)
                        spread = trade.get('spread_pct', 0)
                        
                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #1a1a2e, #16213e); 
                                    padding: 12px; border-radius: 8px; margin: 8px 0;
                                    border-left: 4px solid {color};">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="color: {color}; font-weight: bold; font-size: 14px;">
                                    {icon} {title}
                                </span>
                                <span style="color: #888; font-size: 12px;">{trade['timestamp']}</span>
                            </div>
                            <div style="color: #fff; font-size: 13px; margin-top: 5px;">
                                Binance: <span style="color: #f0b90b;">${price_binance:.2f}</span> | 
                                KuCoin: <span style="color: #24ae8f;">${price_kucoin:.2f}</span> | 
                                价差: <span style="color: #00aaff;">{spread:.4f}%</span>
                            </div>
                            <div style="color: #aaa; font-size: 12px; margin-top: 5px; line-height: 1.4;">
                                💡 {trade.get('reason', '条件触发')}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                # 按类型统计
                if 'by_type' in res and len(res['by_type']) > 0:
                    st.markdown("#### 📊 按套利类型统计")
                    
                    type_names = {'price_spread': '价差套利', 'funding_rate': '资金费率套利', 'combined': '组合套利'}
                    
                    cols = st.columns(len(res['by_type']))
                    for i, (t, stats) in enumerate(res['by_type'].items()):
                        with cols[i]:
                            type_name = type_names.get(t, t)
                            pnl_color = "#00ff88" if stats['total_pnl'] >= 0 else "#ff4444"
                            
                            st.markdown(f"""
                            <div style="background: linear-gradient(135deg, #1a1a2e, #16213e); 
                                        padding: 15px; border-radius: 10px; text-align: center;">
                                <div style="color: #888; font-size: 12px;">{type_name}</div>
                                <div style="color: {pnl_color}; font-size: 20px; font-weight: bold;">
                                    ${stats['total_pnl']:.2f}
                                </div>
                                <div style="color: #aaa; font-size: 12px; margin-top: 5px;">
                                    {stats['count']}笔 | 胜率{stats['win_rate']*100:.1f}%
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
        
        # 时间回放控制器
        if realtime_mode and 'results' in st.session_state:
            st.divider()
            st.subheader("时间回放")
            
            total_rows = len(equity_df)
            
            # 播放控制
            col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 1, 1])
            with col_ctrl1:
                # 时间滑块
                time_idx = st.slider(
                    "时间轴",
                    min_value=0,
                    max_value=total_rows - 1,
                    value=total_rows - 1,
                    key="time_slider"
                )
            with col_ctrl2:
                # 播放间隔（毫秒）
                play_interval = st.selectbox(
                    "播放速度",
                    options=[500, 300, 200, 100, 50],
                    index=2,
                    format_func=lambda x: f"{'很慢' if x==500 else '慢' if x==300 else '正常' if x==200 else '快' if x==100 else '很快'}"
                )
            with col_ctrl3:
                # 显示K线数量
                window_size = st.selectbox(
                    "显示范围",
                    options=[30, 50, 100, 200],
                    index=1,
                    format_func=lambda x: f"最近{x}根K线"
                )
            
            # 初始化播放状态
            if 'is_playing' not in st.session_state:
                st.session_state.is_playing = False
            if 'is_paused' not in st.session_state:
                st.session_state.is_paused = False
            if 'play_position' not in st.session_state:
                st.session_state.play_position = 0
            
            # 播放按钮
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            with col_btn1:
                if st.button("开始", use_container_width=True):
                    st.session_state.is_playing = True
                    st.session_state.is_paused = False
                    st.session_state.play_position = min(window_size, total_rows - 1)
                    st.rerun()
            with col_btn2:
                pause_label = "继续" if st.session_state.is_paused else "暂停"
                if st.button(pause_label, use_container_width=True):
                    st.session_state.is_paused = not st.session_state.is_paused
                    st.rerun()
            with col_btn3:
                if st.button("停止", use_container_width=True):
                    st.session_state.is_playing = False
                    st.session_state.is_paused = False
                    st.session_state.play_position = 0
                    st.rerun()
            
            # 播放状态显示
            if st.session_state.is_playing:
                if st.session_state.is_paused:
                    st.warning(f"已暂停 - 位置: {st.session_state.play_position}/{total_rows}")
                else:
                    st.info(f"播放中 - 位置: {st.session_state.play_position}/{total_rows}")
            
            # 动画播放逻辑 - 单帧渲染模式
            if st.session_state.is_playing and not st.session_state.is_paused:
                import time as time_module
                
                idx = st.session_state.play_position
                step = max(1, speed)
                interval_sec = play_interval / 1000.0
                
                if idx < total_rows:
                    # 进度条
                    progress = (idx + 1) / total_rows
                    st.progress(progress, text=f"进度: {idx+1}/{total_rows}")
                    
                    # 获取当前数据
                    current_row = equity_df.iloc[idx]
                    current_time = current_row['timestamp']
                    
                    # 计算窗口范围
                    start = max(0, idx - window_size + 1)
                    end = idx + 1
                    
                    # 获取窗口内数据
                    window_df = df.iloc[start:end].copy()
                    window_equity = equity_df.iloc[start:end].copy()
                    
                    # 状态信息
                    if strategy == 'martingale':
                        pnl = current_row['total_pnl']
                        pnl_sign = "+" if pnl >= 0 else ""
                        st.markdown(
                            f"**时间**: {current_time} | "
                            f"**价格**: ${current_row['price']:,.2f} | "
                            f"**盈亏**: {pnl_sign}${pnl:,.2f} | "
                            f"**多单**: {int(current_row['long_level'])}层 | "
                            f"**空单**: {int(current_row['short_level'])}层"
                        )
                        
                        # 创建K线图
                        fig = make_subplots(
                            rows=2, cols=1,
                            shared_xaxes=True,
                            vertical_spacing=0.05,
                            row_heights=[0.7, 0.3]
                        )
                        
                        # K线
                        fig.add_trace(go.Candlestick(
                            x=window_df['timestamp'],
                            open=window_df['open'],
                            high=window_df['high'],
                            low=window_df['low'],
                            close=window_df['close'],
                            name='K线',
                            increasing_line_color='#00ff88',
                            decreasing_line_color='#ff4444'
                        ), row=1, col=1)
                        
                        # 盈亏曲线
                        fig.add_trace(go.Scatter(
                            x=window_equity['timestamp'],
                            y=window_equity['total_pnl'],
                            mode='lines',
                            name='盈亏',
                            line=dict(color='#00aaff', width=2)
                        ), row=2, col=1)
                        
                    else:  # arbitrage
                        pnl = current_row.get('pnl', 0)
                        pnl_sign = "+" if pnl >= 0 else ""
                        spread = current_row.get('spread_pct', 0)
                        st.markdown(
                            f"**时间**: {current_time} | "
                            f"**价差**: {spread:.4f}% | "
                            f"**盈亏**: {pnl_sign}${pnl:,.2f} | "
                            f"**持仓**: {int(current_row.get('position_count', 0))}个"
                        )
                        
                        # 创建双交易所价格图
                        fig = make_subplots(
                            rows=2, cols=1,
                            shared_xaxes=True,
                            vertical_spacing=0.05,
                            row_heights=[0.7, 0.3]
                        )
                        
                        # Binance价格线
                        if 'binance_close' in window_df.columns:
                            fig.add_trace(go.Scatter(
                                x=window_df['timestamp'],
                                y=window_df['binance_close'],
                                mode='lines',
                                name='Binance',
                                line=dict(color='#f0b90b', width=2)
                            ), row=1, col=1)
                        
                        # KuCoin价格线
                        if 'kucoin_close' in window_df.columns:
                            fig.add_trace(go.Scatter(
                                x=window_df['timestamp'],
                                y=window_df['kucoin_close'],
                                mode='lines',
                                name='KuCoin',
                                line=dict(color='#24ae8f', width=2)
                            ), row=1, col=1)
                        
                        # 价差曲线
                        if 'spread_pct' in window_equity.columns:
                            fig.add_trace(go.Scatter(
                                x=window_equity['timestamp'],
                                y=window_equity['spread_pct'],
                                mode='lines',
                                name='价差%',
                                line=dict(color='#ff6b6b', width=2)
                            ), row=2, col=1)
                    
                    # 更新布局
                    fig.update_layout(
                        height=450,
                        template='plotly_dark',
                        margin=dict(l=10, r=10, t=30, b=10),
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02),
                        xaxis_rangeslider_visible=False
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 更新位置并继续播放
                    st.session_state.play_position = idx + step
                    time_module.sleep(interval_sec)
                    st.rerun()
                else:
                    # 播放完成
                    st.success("播放完成")
                    st.session_state.is_playing = False
                    st.session_state.play_position = 0
            
            # 静态显示（未播放时）
            if not st.session_state.is_playing:
                # 获取当前时间点的数据
                current_row = equity_df.iloc[time_idx]
                current_time = current_row['timestamp']
                partial_equity = equity_df.iloc[:time_idx+1]
                partial_df = df.iloc[:time_idx+1]
                
                # 统计卡片
                st.markdown("#### 当前状态")
                
                if strategy == 'martingale':
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        st.metric("价格", f"${current_row['price']:,.2f}")
                    with col2:
                        st.metric("总盈亏", f"${current_row['total_pnl']:,.2f}")
                    with col3:
                        st.metric("浮动盈亏", f"${current_row['pnl']:,.2f}")
                    with col4:
                        st.metric("多单层数", int(current_row['long_level']))
                    with col5:
                        st.metric("空单层数", int(current_row['short_level']))
                else:
                    col1, col2, col3, col4 = st.columns(4)
                    price_a = current_row.get('price_a', 0)
                    price_b = current_row.get('price_b', 0)
                    spread = current_row.get('spread_pct', 0)
                    pnl = current_row.get('pnl', 0)
                    with col1:
                        st.metric("Binance", f"${price_a:,.2f}")
                    with col2:
                        st.metric("KuCoin", f"${price_b:,.2f}")
                    with col3:
                        st.metric("价差", f"{spread:.4f}%")
                    with col4:
                        st.metric("累计盈亏", f"${pnl:,.2f}")
                
                # 图表区域
                chart_col1, chart_col2 = st.columns([3, 2])
                
                with chart_col1:
                    st.markdown("#### 价格走势")
                    
                    # 只显示到当前时间点的数据
                    display_start = max(0, time_idx - 100)
                    display_df = partial_df.iloc[display_start:]
                
                fig_price = go.Figure()
                
                if strategy == 'martingale':
                    # K线图
                    fig_price.add_trace(go.Candlestick(
                        x=display_df['timestamp'],
                        open=display_df['open'],
                        high=display_df['high'],
                        low=display_df['low'],
                        close=display_df['close'],
                        increasing_line_color='#00ff88',
                        decreasing_line_color='#ff4444',
                        name='K线'
                    ))
                    
                    # 基准价线
                    if 'baseline_price' in partial_equity.columns:
                        baseline_data = partial_equity.iloc[display_start:time_idx+1]
                        fig_price.add_trace(go.Scatter(
                            x=baseline_data['timestamp'],
                            y=baseline_data['baseline_price'],
                            mode='lines',
                            line=dict(color='#ffd700', width=1, dash='dash'),
                            name='基准价',
                            opacity=0.7
                        ))
                    
                    # 标记当前位置
                    fig_price.add_trace(go.Scatter(
                        x=[display_df['timestamp'].iloc[-1]],
                        y=[display_df['close'].iloc[-1]],
                        mode='markers',
                        marker=dict(color='#ffd700', size=15, symbol='circle',
                                   line=dict(color='white', width=2)),
                        name='当前',
                        showlegend=False
                    ))
                    
                    # 获取当前时间之前的交易
                    if not trades_df.empty:
                        past_trades = trades_df[trades_df['timestamp'] <= current_time]
                        
                        long_trades = past_trades[past_trades['type'] == 'LONG'].tail(20)
                        short_trades = past_trades[past_trades['type'] == 'SHORT'].tail(20)
                        
                        if not long_trades.empty:
                            fig_price.add_trace(go.Scatter(
                                x=long_trades['timestamp'],
                                y=long_trades['price'],
                                mode='markers',
                                marker=dict(symbol='triangle-up', size=10, color='#00ff88'),
                                name='多单',
                                showlegend=True
                            ))
                        
                        if not short_trades.empty:
                            fig_price.add_trace(go.Scatter(
                                x=short_trades['timestamp'],
                                y=short_trades['price'],
                                mode='markers',
                                marker=dict(symbol='triangle-down', size=10, color='#ff4444'),
                                name='空单',
                                showlegend=True
                            ))
                
                else:  # arbitrage
                    # 双价格线
                    if 'binance_close' in display_df.columns:
                        fig_price.add_trace(go.Scatter(
                            x=display_df['timestamp'],
                            y=display_df['binance_close'],
                            mode='lines',
                            line=dict(color='#f0b90b', width=2),
                            name='Binance'
                        ))
                        fig_price.add_trace(go.Scatter(
                            x=display_df['timestamp'],
                            y=display_df['kucoin_close'],
                            mode='lines',
                            line=dict(color='#24ae8f', width=2),
                            name='KuCoin'
                        ))
                
                fig_price.update_layout(
                    template='plotly_dark',
                    height=400,
                    margin=dict(l=10, r=10, t=10, b=10),
                    xaxis_rangeslider_visible=False,
                    legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="right", x=1),
                    xaxis=dict(gridcolor='#333'),
                    yaxis=dict(gridcolor='#333')
                )
                
                st.plotly_chart(fig_price, use_container_width=True, key=f"price_chart_{time_idx}")
                
                with chart_col2:
                    st.markdown("#### 盈亏曲线")
                    
                    fig_pnl = go.Figure()
                    
                    if strategy == 'martingale':
                        fig_pnl.add_trace(go.Scatter(
                            x=partial_equity['timestamp'],
                            y=partial_equity['total_pnl'],
                            mode='lines',
                            fill='tozeroy',
                            line=dict(color='#ffd700', width=2),
                            fillcolor='rgba(255, 215, 0, 0.15)',
                            name='总盈亏'
                        ))
                        if 'realized_pnl' in partial_equity.columns:
                            fig_pnl.add_trace(go.Scatter(
                                x=partial_equity['timestamp'],
                                y=partial_equity['realized_pnl'],
                                mode='lines',
                                line=dict(color='#00ff88', width=1.5, dash='dot'),
                                name='已实现'
                            ))
                    else:
                        fig_pnl.add_trace(go.Scatter(
                            x=partial_equity['timestamp'],
                            y=partial_equity['pnl'],
                            mode='lines',
                            fill='tozeroy',
                            line=dict(color='#00aaff', width=2),
                            fillcolor='rgba(0, 170, 255, 0.15)',
                            name='累计盈亏'
                        ))
                    
                    current_pnl = current_row['total_pnl'] if strategy == 'martingale' else current_row['pnl']
                    fig_pnl.add_trace(go.Scatter(
                        x=[current_time],
                        y=[current_pnl],
                        mode='markers',
                        marker=dict(color='#ffd700', size=12, symbol='circle',
                                   line=dict(color='white', width=2)),
                        name='当前',
                        showlegend=False
                    ))
                    
                    fig_pnl.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.3)
                    
                    fig_pnl.update_layout(
                        template='plotly_dark',
                        height=400,
                        margin=dict(l=10, r=10, t=10, b=10),
                        legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="right", x=1),
                        xaxis=dict(gridcolor='#333'),
                        yaxis=dict(gridcolor='#333')
                    )
                    
                    st.plotly_chart(fig_pnl, use_container_width=True, key=f"pnl_chart_{time_idx}")
                
                # 显示交易记录
                st.markdown("#### 最近交易")
                if strategy == 'martingale' and not trades_df.empty:
                    recent_trades = trades_df[trades_df['timestamp'] <= current_time].tail(10)
                    if not recent_trades.empty:
                        st.dataframe(recent_trades[['timestamp', 'type', 'price', 'size', 'level']], 
                                    use_container_width=True, hide_index=True)
                    else:
                        st.info("暂无交易记录")
                elif strategy == 'arbitrage' and not trades_df.empty:
                    recent_trades = trades_df[trades_df['timestamp'] <= current_time].tail(10)
                    if not recent_trades.empty:
                        st.dataframe(recent_trades, use_container_width=True, hide_index=True)
                    else:
                        st.info("暂无交易记录")
    
    else:
        # 欢迎页面
        st.info("👈 请在左侧配置策略参数，然后点击「运行回测」开始分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 🎯 马丁双向策略
            
            双向马丁格尔策略同时在多空两个方向上建仓，通过网格交易捕捉市场波动收益。
            
            **特点：**
            - 支持固定间距/百分比网格
            - 多种止盈模式（统一/逐笔/分层）
            - 动态/固定基准价模式
            - 自动仓位管理
            """)
        
        with col2:
            st.markdown("""
            ### 💱 套利策略
            
            跨交易所套利策略，利用不同交易所间的价差和资金费率差异获利。
            
            **特点：**
            - 价差套利
            - 资金费率套利
            - 组合套利
            - 多种开平仓条件
            """)


if __name__ == "__main__":
    main()
