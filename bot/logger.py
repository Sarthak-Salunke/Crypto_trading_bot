import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Union
import json


class TradingBotLogger:
    
    _instance: Optional['TradingBotLogger'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'TradingBotLogger':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
            
        self.log_directory = Path("logs")
        self.loggers: Dict[str, logging.Logger] = {}
        self.formatters: Dict[str, logging.Formatter] = {}
        

        self.log_directory.mkdir(exist_ok=True)
        

        self._setup_formatters()
        

        self._setup_loggers()
        
        self._initialized = True
    
    def _setup_formatters(self) -> None:
        self.formatters['standard'] = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.formatters['detailed'] = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.formatters['json'] = JsonFormatter()
        self.formatters['trade'] = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | TRADE | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        

        self.formatters['api'] = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | API | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def _setup_loggers(self) -> None:
        self.loggers['system'] = self._create_logger(
            name='trading_bot.system',
            log_file='system.log',
            level=logging.INFO,
            formatter_name='detailed'
        )
        

        self.loggers['trade'] = self._create_logger(
            name='trading_bot.trade',
            log_file='trades.log',
            level=logging.INFO,
            formatter_name='trade',
            json_log=True
        )
        

        self.loggers['error'] = self._create_logger(
            name='trading_bot.error',
            log_file='errors.log',
            level=logging.ERROR,
            formatter_name='detailed',
            console_level=logging.ERROR
        )
        

        self.loggers['api'] = self._create_logger(
            name='trading_bot.api',
            log_file='api.log',
            level=logging.DEBUG,
            formatter_name='api',
            console_level=logging.WARNING
        )
        

        self.loggers['performance'] = self._create_logger(
            name='trading_bot.performance',
            log_file='performance.log',
            level=logging.INFO,
            formatter_name='detailed',
            console_level=logging.WARNING
        )
    
    def _create_logger(self, name: str, log_file: str, level: int,
                      formatter_name: str, console_level: Optional[int] = None,
                      json_log: bool = False) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        

        logger.handlers.clear()
        logger.propagate = False
        

        file_handler = logging.handlers.RotatingFileHandler(
            filename=self.log_directory / log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(self.formatters[formatter_name])
        logger.addHandler(file_handler)
        

        if json_log:
            json_file = log_file.replace('.log', '_structured.json')
            json_handler = logging.handlers.RotatingFileHandler(
                filename=self.log_directory / json_file,
                maxBytes=10 * 1024 * 1024,
                backupCount=3,
                encoding='utf-8'
            )
            json_handler.setLevel(level)
            json_handler.setFormatter(self.formatters['json'])
            logger.addHandler(json_handler)
        

        if console_level is not None:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(console_level)
            console_handler.setFormatter(self.formatters['standard'])
            logger.addHandler(console_handler)
        

        timed_handler = logging.handlers.TimedRotatingFileHandler(
            filename=self.log_directory / f"daily_{log_file}",
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        timed_handler.setLevel(level)
        timed_handler.setFormatter(self.formatters[formatter_name])
        timed_handler.suffix = "%Y%m%d"
        logger.addHandler(timed_handler)
        
        return logger
    
    def get_logger(self, logger_type: str) -> logging.Logger:
       
        if logger_type not in self.loggers:
            raise ValueError(f"Unknown logger type: {logger_type}. "
                           f"Available types: {list(self.loggers.keys())}")
        
        return self.loggers[logger_type]
    
    def log_trade(self, action: str, symbol: str, side: str, quantity: float,
                  price: Optional[float] = None, order_id: Optional[str] = None,
                  status: str = "PENDING", **kwargs) -> None:
        trade_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'order_id': order_id,
            'status': status,
            **kwargs
        }
        
        trade_logger = self.get_logger('trade')
        trade_logger.info(f"TRADE_EVENT", extra={'trade_data': trade_data})
    
    def log_api_call(self, endpoint: str, method: str, params: Dict[str, Any],
                     response_code: Optional[int] = None, response_time: Optional[float] = None,
                     error: Optional[str] = None) -> None:
        api_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'endpoint': endpoint,
            'method': method,
            'params': params,
            'response_code': response_code,
            'response_time': response_time,
            'error': error
        }
        
        api_logger = self.get_logger('api')
        level = logging.ERROR if error else logging.INFO
        api_logger.log(level, f"API_CALL: {method} {endpoint}", extra={'api_data': api_data})
    
    def log_performance(self, operation: str, duration: float, **kwargs) -> None:
        perf_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'operation': operation,
            'duration': duration,
            **kwargs
        }
        
        perf_logger = self.get_logger('performance')
        perf_logger.info(f"PERFORMANCE: {operation} took {duration:.3f}s", 
                        extra={'perf_data': perf_data})
    
    def log_error(self, error: Exception, context: Optional[Dict[str, Any]] = None,
                  logger_type: str = 'error') -> None:
        error_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {}
        }
        
        error_logger = self.get_logger(logger_type)
        error_logger.error(f"ERROR: {type(error).__name__}: {error}", 
                          extra={'error_data': error_data}, exc_info=True)
    
    def cleanup_old_logs(self, days_to_keep: int = 30) -> None:
       
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (days_to_keep * 24 * 60 * 60)
            
            deleted_count = 0
            for log_file in self.log_directory.glob("*.log*"):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    deleted_count += 1
            
            system_logger = self.get_logger('system')
            system_logger.info(f"Cleaned up {deleted_count} old log files (older than {days_to_keep} days)")
            
        except Exception as e:
            error_logger = self.get_logger('error')
            error_logger.error(f"Failed to cleanup old logs: {e}")


class JsonFormatter(logging.Formatter):
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
    
        if hasattr(record, 'trade_data'):
            log_data['trade_data'] = record.trade_data
        if hasattr(record, 'api_data'):
            log_data['api_data'] = record.api_data
        if hasattr(record, 'perf_data'):
            log_data['perf_data'] = record.perf_data
        if hasattr(record, 'error_data'):
            log_data['error_data'] = record.error_data
        

        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str, ensure_ascii=False)



_trading_logger: Optional[TradingBotLogger] = None


def get_trading_logger() -> TradingBotLogger:
    global _trading_logger
    if _trading_logger is None:
        _trading_logger = TradingBotLogger()
    return _trading_logger


def setup_logging(console_level: Union[str, int] = logging.INFO,
                 file_level: Union[str, int] = logging.DEBUG,
                 enable_console: bool = True) -> TradingBotLogger:
    if isinstance(console_level, str):
        console_level = getattr(logging, console_level.upper())
    if isinstance(file_level, str):
        file_level = getattr(logging, file_level.upper())
    

    trading_logger = get_trading_logger()
    

    if not enable_console:
        for logger in trading_logger.loggers.values():

            logger.handlers = [h for h in logger.handlers 
                             if not isinstance(h, logging.StreamHandler)]
    

    system_logger = trading_logger.get_logger('system')
    system_logger.info(f"Trading bot logging initialized - Console: {console_level}, File: {file_level}")
    
    return trading_logger


def get_logger(logger_type: str = 'system') -> logging.Logger:
   
    return get_trading_logger().get_logger(logger_type)



def log_trade(action: str, symbol: str, side: str, quantity: float, **kwargs) -> None:
    """Convenience function for trade logging."""
    get_trading_logger().log_trade(action, symbol, side, quantity, **kwargs)


def log_api_call(endpoint: str, method: str, params: Dict[str, Any], **kwargs) -> None:
    """Convenience function for API call logging."""
    get_trading_logger().log_api_call(endpoint, method, params, **kwargs)


def log_performance(operation: str, duration: float, **kwargs) -> None:
    """Convenience function for performance logging."""
    get_trading_logger().log_performance(operation, duration, **kwargs)


def log_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """Convenience function for error logging."""
    get_trading_logger().log_error(error, context)



class PerformanceLogger:
    
    def __init__(self, operation: str, **kwargs):
        self.operation = operation
        self.context = kwargs
        self.start_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration = time.time() - self.start_time
        log_performance(self.operation, duration, **self.context)


if __name__ == "__main__":

    print("Testing Trading Bot Logger...")
    

    logger = setup_logging(console_level=logging.INFO)
    

    system_logger = get_logger('system')
    system_logger.info("System logger test")
    
    trade_logger = get_logger('trade')
    trade_logger.info("Trade logger test")
    
    error_logger = get_logger('error')
    error_logger.error("Error logger test")
    
    api_logger = get_logger('api')
    api_logger.info("API logger test")
    

    log_trade(
        action="PLACE_ORDER",
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.001,
        price=45000.0,
        order_id="12345",
        status="NEW"
    )
    
    log_api_call(
        endpoint="/fapi/v1/order",
        method="POST",
        params={"symbol": "BTCUSDT", "side": "BUY"},
        response_code=200,
        response_time=0.5
    )
    

    with PerformanceLogger("test_operation", additional_info="test"):
        import time
        time.sleep(0.1)
    

    try:
        raise ValueError("Test error for logging")
    except Exception as e:
        log_error(e, context={"test_context": "example"})
    
    print("Logger testing completed. Check the 'logs' directory for output files.")
    

    log_dir = Path("logs")
    if log_dir.exists():
        print(f"\nLog files created in {log_dir.absolute()}:")
        for log_file in sorted(log_dir.glob("*.log*")):
            size = log_file.stat().st_size
            print(f"  {log_file.name} ({size} bytes)")