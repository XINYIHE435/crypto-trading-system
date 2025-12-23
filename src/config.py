"""
配置文件管理
"""
import os
import configparser
from pathlib import Path

class Config:
    """配置管理类"""
    
    def __init__(self, config_path="config/config.ini"):
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_path):
            self.config.read(self.config_path, encoding='utf-8')
        else:
            print(f"警告: 配置文件不存在: {self.config_path}")
            self.create_default_config()
    
    def create_default_config(self):
        """创建默认配置文件"""
        default_config = """[DEFAULT]
# 默认交易对
symbols = BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,ADAUSDT

# 默认时间框架
timeframes = 30m,1h,4h

# 数据下载设置
start_date = 2025-11-01
end_date = 2025-12-12

[DOWNLOAD]
# 并发下载数
max_concurrent = 5

# 数据保存路径
data_dir = data/raw

[ARBITRAGE]
# 最小利润阈值
min_profit_threshold = 0.002

# 最大持仓数
max_positions = 5

# 持仓超时时间(秒)
position_timeout = 3600

# 最大回撤
risk_max_drawdown = 0.05

[EXCHANGES]
# 支持的交易所
supported_exchanges = binance,kucoin,okx,huobi,bybit
"""
        
        # 确保配置目录存在
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(default_config)
        
        print(f"已创建默认配置文件: {self.config_path}")
        self.config.read(self.config_path, encoding='utf-8')
    
    def get_symbols(self):
        """获取交易对列表"""
        symbols_str = self.config.get('DEFAULT', 'symbols', fallback='BTCUSDT,ETHUSDT')
        return [s.strip() for s in symbols_str.split(',')]
    
    def get_timeframes(self):
        """获取时间框架列表"""
        timeframes_str = self.config.get('DEFAULT', 'timeframes', fallback='30m,1h')
        return [t.strip() for t in timeframes_str.split(',')]
    
    def get_start_date(self):
        """获取开始日期"""
        return self.config.get('DEFAULT', 'start_date', fallback='2025-11-01')
    
    def get_end_date(self):
        """获取结束日期"""
        return self.config.get('DEFAULT', 'end_date', fallback='2025-12-12')
    
    def get_max_concurrent(self):
        """获取最大并发数"""
        return self.config.getint('DOWNLOAD', 'max_concurrent', fallback=5)
    
    def get_data_dir(self):
        """获取数据目录"""
        return self.config.get('DOWNLOAD', 'data_dir', fallback='data/raw')
    
    def get_arbitrage_config(self):
        """获取套利配置"""
        return {
            'min_profit_threshold': self.config.getfloat('ARBITRAGE', 'min_profit_threshold', fallback=0.002),
            'max_positions': self.config.getint('ARBITRAGE', 'max_positions', fallback=5),
            'position_timeout': self.config.getint('ARBITRAGE', 'position_timeout', fallback=3600),
            'risk_max_drawdown': self.config.getfloat('ARBITRAGE', 'risk_max_drawdown', fallback=0.05)
        }
    
    def get_supported_exchanges(self):
        """获取支持的交易所列表"""
        exchanges_str = self.config.get('EXCHANGES', 'supported_exchanges', fallback='binance,kucoin,okx,huobi,bybit')
        return [e.strip() for e in exchanges_str.split(',')]

# SSL验证配置
# 开发环境可以设为False以避免证书问题
# 生产环境应该设为True以确保安全
VERIFY_SSL = os.getenv('VERIFY_SSL', 'False').lower() == 'true'