"""
加密货币套利系统主模块
包含数据下载、套利策略和可视化功能
"""

# 数据下载模块
from .data_downloader import DataDownloader

# 套利系统核心模块（重构后）
from .arbitrage_system import (
    ArbitrageSystem, 
    ArbitrageConfig,
    ArbitragePosition,
    ArbitrageType,
    OpenCondition,
    Direction,
    CloseReason
)

# 可视化模块
from .popup_visualization import PopupVisualizer, RealTimePopupVisualizer

__all__ = [
    'DataDownloader',
    'ArbitrageSystem', 'ArbitrageConfig', 'ArbitragePosition',
    'ArbitrageType', 'OpenCondition', 'Direction', 'CloseReason',
    'PopupVisualizer', 'RealTimePopupVisualizer'
]