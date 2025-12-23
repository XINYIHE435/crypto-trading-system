"""
套利系统弹窗可视化模块
基于matplotlib的弹窗图表，无需生成HTML文件

主要功能：
1. 弹窗显示回测结果图表
2. 实时数据可视化
3. 参数优化图表展示
4. 交互式图表界面
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
import time

# 设置字体和样式，支持中文显示
import matplotlib.font_manager as fm

def _test_chinese_fonts():
    """测试所有可用的中文字体（内部函数）"""
    font_list = [font.name for font in fm.fontManager.ttflist]
    
    chinese_fonts = [
        'PingFang SC', 'PingFang TC', 'PingFang HK',
        'Hiragino Sans GB', 'Hiragino Sans CNS',
        'STHeiti', 'STHeiti Light', 'STHeiti Medium',
        'STXihei', 'Songti SC', 'Songti TC',
        'Arial Unicode MS', 'Microsoft YaHei', 'SimHei', 'SimSun'
    ]
    
    return [font for font in chinese_fonts if font in font_list]

def _setup_chinese_matplotlib():
    """设置matplotlib支持中文显示（内部函数）"""
    try:
        fm._rebuild()
    except:
        # 在某些环境下，重建缓存可能会失败，但这不应该阻碍程序运行
        print("ℹ️ 注意：刷新matplotlib字体缓存失败，将继续尝试设置字体。")

    available_fonts = _test_chinese_fonts()

    if not available_fonts:
        print("⚠️ 警告：未找到可用的中文字体，图表中的中文可能显示为方框。")
        print("   请尝试在系统中安装'PingFang SC'、'Hiragino Sans GB'或'Microsoft YaHei'等字体。")
        return

    preferred_fonts = ['PingFang SC', 'Hiragino Sans GB', 'STHeiti', 'Microsoft YaHei', 'Arial Unicode MS']
    
    selected_font = None
    for font in preferred_fonts:
        if font in available_fonts:
            selected_font = font
            break
    
    if selected_font:
        plt.rcParams['font.sans-serif'] = [selected_font]
        plt.rcParams['axes.unicode_minus'] = False
        print(f"✅ 已自动设置中文字体: {selected_font}")
    else:
        # 如果优先列表中的字体都不可用，则使用找到的第一个中文字体
        plt.rcParams['font.sans-serif'] = [available_fonts[0]]
        plt.rcParams['axes.unicode_minus'] = False
        print(f"✅ 已自动设置中文字体: {available_fonts[0]}")

# 自动执行中文字体设置
_setup_chinese_matplotlib()

plt.style.use('default')

class PopupVisualizer:
    """弹窗可视化类"""

    def __init__(self):
        """初始化可视化器"""
        self.colors = {
            'primary': '#1f77b4',
            'success': '#2ca02c',
            'danger': '#d62728',
            'warning': '#ff7f0e',
            'info': '#17becf',
            'profit': '#00cc96',
            'loss': '#ff6b6b',
            'background': '#f8f9fa'
        }
        self.figures = {}  # 存储图形对象

    def plot_backtest_summary(self, results: Dict, trades: List[Dict] = None, show=True):
        """
        绘制回测结果概览

        Args:
            results: 回测结果字典
            trades: 交易记录列表
            show: 是否立即显示图表
        """
        # 创建2x2的子图
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('套利策略回测分析', fontsize=16, fontweight='bold')
        fig.patch.set_facecolor(self.colors['background'])

        # 1. 收益率仪表盘式图表
        self._plot_return_gauge(ax1, results['return_rate'])
        ax1.set_title(f'总收益率: {results["return_rate"]:.2%}', fontweight='bold')

        # 2. 盈亏分布柱状图
        self._plot_pnl_distribution(ax2, results)
        ax2.set_title('盈亏分布', fontweight='bold')

        # 3. 胜率饼图
        self._plot_win_rate_pie(ax3, results['win_rate'])
        ax3.set_title(f'胜率: {results["win_rate"]:.1%}', fontweight='bold')

        # 4. 关键指标雷达图
        self._plot_key_metrics_radar(ax4, results)
        ax4.set_title('关键指标雷达图', fontweight='bold')

        plt.tight_layout()

        if show:
            plt.show()
        else:
            self.figures['backtest_summary'] = fig

    def _plot_return_gauge(self, ax, return_rate):
        """绘制收益率仪表盘"""
        # 创建半圆形仪表盘
        theta = np.linspace(0, np.pi, 100)
        r = 1

        # 绘制背景弧
        ax.plot(np.cos(theta), np.sin(theta), 'lightgray', linewidth=20, alpha=0.3)

        # 根据收益率选择颜色
        if return_rate > 0:
            color = self.colors['profit']
        else:
            color = self.colors['loss']

        # 绘制收益率弧
        return_theta = np.pi * (0.5 + return_rate)  # 映射到半圆
        ax.plot(np.cos(theta[:int(return_theta/np.pi*100)]),
                np.sin(theta[:int(return_theta/np.pi*100)]),
                color=color, linewidth=20, alpha=0.8)

        # 添加文字
        ax.text(0, -0.3, f'{return_rate:.2%}', ha='center', va='center',
                fontsize=20, fontweight='bold', color=color)
        ax.text(0, -0.5, '总收益率', ha='center', va='center', fontsize=12)

        ax.set_xlim(-1.2, 1.2)
        ax.set_ylim(-0.6, 1.2)
        ax.set_aspect('equal')
        ax.axis('off')

    def _plot_pnl_distribution(self, ax, results):
        """绘制盈亏分布"""
        metrics = ['最大盈利', '最大亏损', '平均盈亏']
        values = [results.get('max_profit', 0), abs(results.get('max_loss', 0)), abs(results.get('avg_profit', 0))]
        colors = [self.colors['profit'], self.colors['loss'], self.colors['info']]

        bars = ax.bar(metrics, values, color=colors, alpha=0.7, edgecolor='black')
        ax.set_ylabel('金额 (USDT)')
        ax.grid(True, alpha=0.3)

        # 添加数值标签
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                   f'${value:.2f}', ha='center', va='bottom', fontweight='bold')

    def _plot_win_rate_pie(self, ax, win_rate):
        """绘制胜率饼图"""
        sizes = [win_rate * 100, (1 - win_rate) * 100]
        colors = [self.colors['success'], self.colors['danger']]
        labels = ['盈利交易', '亏损交易']
        explode = (0.1, 0)  # 突出显示盈利部分

        wedges, texts, autotexts = ax.pie(sizes, explode=explode, labels=labels, colors=colors,
                                          autopct='%1.1f%%', shadow=True, startangle=90)

        # 美化文字
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')

    def _plot_key_metrics_radar(self, ax, results):
        """绘制关键指标雷达图"""
        categories = ['收益率', '胜率', '交易频率', '风险控制', '稳定性']

        # 标准化指标到0-1范围
        normalized_values = [
            min(1.0, max(0, results['return_rate'] * 50)),  # 收益率标准化
            results['win_rate'],  # 胜率
            min(1.0, results['total_trades'] / 50),  # 交易频率
            1.0 - min(1.0, abs(results.get('max_loss', 0)) / 1000),  # 风险控制
            0.8  # 假设稳定性
        ]

        # 计算角度
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]  # 闭合图形
        normalized_values += normalized_values[:1]

        # 绘制雷达图
        ax = plt.subplot(2, 2, 4, projection='polar')
        ax.plot(angles, normalized_values, 'o-', linewidth=2, color=self.colors['primary'])
        ax.fill(angles, normalized_values, alpha=0.25, color=self.colors['primary'])

        # 设置标签
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        ax.set_ylim(0, 1)
        ax.grid(True)

    def plot_trading_history(self, trades: List[Dict], show=True):
        """
        绘制交易历史图表

        Args:
            trades: 交易记录列表
            show: 是否立即显示图表
        """
        if not trades:
            print("没有交易记录可显示")
            return

        df = pd.DataFrame(trades)
        df['exit_time'] = pd.to_datetime(df['exit_time'])
        df = df.sort_values('exit_time')
        df['cumulative_pnl'] = df['net_pnl'].cumsum()

        # 创建2个子图
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
        fig.suptitle('交易历史分析', fontsize=16, fontweight='bold')
        fig.patch.set_facecolor(self.colors['background'])

        # 1. 累计盈亏曲线
        ax1.plot(df['exit_time'], df['cumulative_pnl'],
                linewidth=2, color=self.colors['primary'], marker='o', markersize=4)
        ax1.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax1.set_title('累计盈亏曲线', fontweight='bold')
        ax1.set_ylabel('累计盈亏 (USDT)')
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

        # 2. 单笔交易盈亏
        colors = [self.colors['profit'] if pnl > 0 else self.colors['loss'] for pnl in df['net_pnl']]
        bars = ax2.bar(df['exit_time'], df['net_pnl'], color=colors, alpha=0.7, edgecolor='black')
        ax2.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        ax2.set_title('单笔交易盈亏', fontweight='bold')
        ax2.set_ylabel('盈亏 (USDT)')
        ax2.set_xlabel('时间')
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

        plt.tight_layout()

        if show:
            plt.show()
        else:
            self.figures['trading_history'] = fig

    def plot_price_analysis(self, df: pd.DataFrame, symbol: str, show=True):
        """
        绘制价格分析图表

        Args:
            df: 价格数据DataFrame
            symbol: 交易对符号
            show: 是否立即显示图表
        """
        # 创建3个子图
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 12))
        fig.suptitle(f'{symbol} 价格分析', fontsize=16, fontweight='bold')
        fig.patch.set_facecolor(self.colors['background'])

        # 1. 价格走势图
        ax1.plot(df.index, df['close_binance'], label='Binance', color=self.colors['primary'], linewidth=1.5)
        ax1.set_title('价格走势', fontweight='bold')
        ax1.set_ylabel('价格 (USDT)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. 成交量
        ax2.bar(df.index, df['volume_binance'], color=self.colors['info'], alpha=0.7)
        ax2.set_title('成交量', fontweight='bold')
        ax2.set_ylabel('成交量')
        ax2.grid(True, alpha=0.3)

        # 3. 价格波动率
        df['returns'] = df['close_binance'].pct_change()
        df['volatility'] = df['returns'].rolling(window=20).std() * np.sqrt(48)  # 30分钟转日化
        ax3.plot(df.index, df['volatility'], color=self.colors['warning'], linewidth=1.5)
        ax3.set_title('价格波动率 (20期滚动)', fontweight='bold')
        ax3.set_ylabel('波动率')
        ax3.set_xlabel('时间')
        ax3.grid(True, alpha=0.3)

        plt.tight_layout()

        if show:
            plt.show()
        else:
            self.figures['price_analysis'] = fig

    def plot_opportunities_analysis(self, opportunities: List[Dict], show=True):
        """
        绘制套利机会分析

        Args:
            opportunities: 套利机会列表
            show: 是否立即显示图表
        """
        if not opportunities:
            print("没有套利机会可分析")
            return

        df = pd.DataFrame(opportunities)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # 创建2x2子图
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('套利机会分析', fontsize=16, fontweight='bold')
        fig.patch.set_facecolor(self.colors['background'])

        # 1. 价差分布
        ax1.hist(df['price_diff_pct'] * 100, bins=20, color=self.colors['info'], alpha=0.7, edgecolor='black')
        ax1.set_title('价差分布 (%)', fontweight='bold')
        ax1.set_xlabel('价差百分比')
        ax1.set_ylabel('频次')
        ax1.grid(True, alpha=0.3)

        # 2. 预期利润分布
        ax2.hist(df['expected_profit_pct'] * 100, bins=20, color=self.colors['profit'], alpha=0.7, edgecolor='black')
        ax2.set_title('预期利润分布 (%)', fontweight='bold')
        ax2.set_xlabel('预期利润百分比')
        ax2.set_ylabel('频次')
        ax2.grid(True, alpha=0.3)

        # 3. 时间序列
        ax3.plot(df['timestamp'], df['price_diff_pct'] * 100,
                marker='o', linestyle='-', color=self.colors['primary'])
        ax3.set_title('价差时间序列分析', fontweight='bold')
        ax3.set_ylabel('价差百分比 (%)')
        ax3.set_xlabel('时间')
        ax3.grid(True, alpha=0.3)
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45)

        # 4. 交易所分布
        exchange_counts = pd.concat([df['exchange_high'], df['exchange_low']]).value_counts()
        ax4.pie(exchange_counts.values, labels=exchange_counts.index, autopct='%1.1f%%',
                colors=[self.colors['primary'], self.colors['success'], self.colors['warning']])
        ax4.set_title('交易所套利机会分布', fontweight='bold')

        plt.tight_layout()

        if show:
            plt.show()
        else:
            self.figures['opportunities_analysis'] = fig

    def plot_parameter_optimization(self, results_list: List[Dict], show=True):
        """
        绘制参数优化结果

        Args:
            results_list: 不同参数的测试结果列表
            show: 是否立即显示图表
        """
        df = pd.DataFrame(results_list)

        # 创建2x2子图
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('参数优化分析', fontsize=16, fontweight='bold')
        fig.patch.set_facecolor(self.colors['background'])

        # 1. 参数vs收益率
        ax1.plot(df['min_profit_threshold'], df['return_rate'] * 100,
                marker='o', linestyle='-', color=self.colors['primary'], linewidth=2)
        ax1.set_title('最小利润阈值 vs 收益率', fontweight='bold')
        ax1.set_xlabel('最小利润阈值')
        ax1.set_ylabel('收益率 (%)')
        ax1.grid(True, alpha=0.3)

        # 2. 参数vs胜率
        ax2.plot(df['min_profit_threshold'], df['win_rate'] * 100,
                marker='s', linestyle='-', color=self.colors['success'], linewidth=2)
        ax2.set_title('最小利润阈值 vs 胜率', fontweight='bold')
        ax2.set_xlabel('最小利润阈值')
        ax2.set_ylabel('胜率 (%)')
        ax2.grid(True, alpha=0.3)

        # 3. 参数vs交易次数
        ax3.plot(df['min_profit_threshold'], df['total_trades'],
                marker='^', linestyle='-', color=self.colors['warning'], linewidth=2)
        ax3.set_title('最小利润阈值 vs 交易次数', fontweight='bold')
        ax3.set_xlabel('最小利润阈值')
        ax3.set_ylabel('交易次数')
        ax3.grid(True, alpha=0.3)

        # 4. 综合评分
        # 计算综合评分 (收益率 * 胜率 * sqrt(交易次数/100))
        df['composite_score'] = df['return_rate'] * df['win_rate'] * np.sqrt(df['total_trades'] / 10)
        best_idx = df['composite_score'].idxmax()

        ax4.scatter(df['min_profit_threshold'], df['composite_score'] * 100,
                   c=df['return_rate'] * 100, cmap='viridis', s=100, alpha=0.7)
        ax4.scatter(df.loc[best_idx, 'min_profit_threshold'], df.loc[best_idx, 'composite_score'] * 100,
                   color='red', s=200, marker='*', label='最佳参数')
        ax4.set_title('参数综合评分分析', fontweight='bold')
        ax4.set_xlabel('最小利润阈值')
        ax4.set_ylabel('综合评分')
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()

        if show:
            plt.show()
        else:
            self.figures['parameter_optimization'] = fig

    def show_all_figures(self):
        """显示所有保存的图表"""
        for name, fig in self.figures.items():
            print(f"显示图表: {name}")
            plt.figure(fig.number)
            plt.show()

    def clear_figures(self):
        """清除所有保存的图表"""
        plt.close('all')
        self.figures.clear()

class RealTimePopupVisualizer:
    """实时弹窗可视化"""

    def __init__(self, update_interval=5):
        """
        初始化实时可视化器

        Args:
            update_interval: 更新间隔（秒）
        """
        self.update_interval = update_interval
        self.visualizer = PopupVisualizer()
        self.running = False
        self.current_data = {}

    def start_realtime_monitoring(self, data_source_func):
        """
        启动实时监控

        Args:
            data_source_func: 数据源函数，返回最新数据
        """
        self.running = True

        def monitor_loop():
            while self.running:
                try:
                    # 获取最新数据
                    data = data_source_func()
                    if data:
                        self.update_charts(data)
                    time.sleep(self.update_interval)
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"监控出错: {e}")
                    time.sleep(self.update_interval)

        # 在单独线程中运行
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()

        print("实时监控已启动 (按Ctrl+C停止)")
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.running = False
            print("监控已停止")

    def update_charts(self, data):
        """更新图表"""
        print(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if 'price_data' in data:
            # 更新价格图表
            self.visualizer.plot_price_analysis(data['price_data'], data.get('symbol', 'UNKNOWN'))

        if 'opportunities' in data:
            # 更新套利机会图表
            self.visualizer.plot_opportunities_analysis(data['opportunities'])

        plt.pause(0.1)  # 短暂暂停以显示图表

# 便利函数
def quick_backtest_visualization(arbitrage_system, results):
    """
    快速回测可视化

    Args:
        arbitrage_system: 套利系统实例
        results: 回测结果
    """
    visualizer = PopupVisualizer()

    print("生成回测结果可视化...")
    visualizer.plot_backtest_summary(results, arbitrage_system.closed_trades)

    if arbitrage_system.closed_trades:
        print("生成交易历史可视化...")
        visualizer.plot_trading_history(arbitrage_system.closed_trades)

    print("可视化完成！")

def create_demo_analysis():
    """创建演示分析"""
    visualizer = PopupVisualizer()

    # 模拟回测结果
    demo_results = {
        'total_trades': 25,
        'total_pnl': 342.67,
        'return_rate': 0.0068,
        'win_rate': 0.68,
        'max_profit': 28.50,
        'max_loss': -15.30,
        'avg_profit': 13.71
    }

    # 模拟交易记录
    demo_trades = []
    for i in range(25):
        demo_trades.append({
            'symbol': 'BTCUSDT',
            'net_pnl': np.random.normal(15, 20),
            'exit_time': datetime(2024, 1, 1) + timedelta(hours=i*12)
        })

    print("演示套利系统可视化分析")
    print("=" * 50)

    # 显示回测结果
    visualizer.plot_backtest_summary(demo_results, demo_trades)

    # 显示交易历史
    visualizer.plot_trading_history(demo_trades)

    print("演示完成！")

if __name__ == "__main__":
    # 运行演示
    create_demo_analysis()