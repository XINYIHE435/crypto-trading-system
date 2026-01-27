"""
加密货币套利系统主模块
包含套利策略和数据聚合功能
"""

# 套利系统核心模块
from .arbitrage_system import (
    ArbitrageSystem, 
    ArbitrageConfig,
    ArbitragePosition,
    ArbitrageType,
    OpenCondition,
    Direction,
    CloseReason
)

__all__ = [
    'ArbitrageSystem', 'ArbitrageConfig', 'ArbitragePosition',
    'ArbitrageType', 'OpenCondition', 'Direction', 'CloseReason',
]