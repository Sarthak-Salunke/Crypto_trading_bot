import os
from typing import Dict, Any

class APIConfig:                                                                                     
    
    API_KEY = os.getenv('BINANCE_API_KEY', '')
    API_SECRET = os.getenv('BINANCE_API_SECRET', '')
    
    TESTNET = os.getenv('USE_TESTNET', 'true').lower() == 'true'
    TESTNET_URL = 'https://testnet.binancefuture.com'
    MAINNET_URL = 'ht             tps://fapi.binance.com'
    
    MAX_REQUESTS_PER_SECOND = 10
    MAX_REQUESTS_PER_MINUTE = 1200

class TradingConfig:
    
    DEFAULT_SYMBOL = 'BTCUSDT'
    DEFAULT_QUANTITY = 0.001
    DEFAULT_LEVERAGE = 10
    
    MAX_POSITION_SIZE = 0.1  
    MAX_DAILY_LOSS = 0.05    
    STOP_LOSS_PERCENTAGE = 0.02  
    TAKE_PROFIT_PERCENTAGE = 0.04 
    
    MIN_ORDER_SIZE = 0.001
    MAX_ORDER_SIZE = 100.0
    PRICE_PRECISION = 2
    QUANTITY_PRECISION = 3

class SystemConfig:
    
    
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///trading_bot.db')
    
    CACHE_TTL = 300  
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    ENABLE_MONITORING = os.getenv('ENABLE_MONITORING', 'true').lower() == 'true'
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')

class BotConfig:
    
    BOT_NAME = 'BinanceTradingBot'
    VERSION = '1.0.0'
    
    ENABLE_STOP_LOSS = True
    ENABLE_TAKE_PROFIT = True
    ENABLE_TRAILING_STOP = False
    
    ENABLE_NOTIFICATIONS = True
    NOTIFICATION_CHANNELS = ['email', 'webhook']
    
    PAPER_TRADING = os.getenv('PAPER_TRADING', 'true').lower() == 'true'
    LIVE_TRADING = os.getenv('LIVE_TRADING', 'false').lower() == 'true'

CONFIG: Dict[str, Any] = {
    'api': APIConfig,
    'trading': TradingConfig,
    'system': SystemConfig,
    'bot': BotConfig,
}

def get_config(section: str = None) -> Any:
    if section:
        return CONFIG.get(section)
    return CONFIG

def load_config_from_file(config_path: str = None) -> Dict[str, Any]:
    import json
    
    if not config_path:
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    
    return {}

config = get_config()
