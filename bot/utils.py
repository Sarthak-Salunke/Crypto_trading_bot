import os
import time
import logging
import functools
from typing import Any, Callable, Dict, Optional, Union, Tuple
from decimal import Decimal, ROUND_DOWN, ROUND_UP
import asyncio
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class RetryExhaustedError(Exception):
    pass


class ValidationError(Exception):
    pass


def load_environment_variables() -> Dict[str, str]:
    load_dotenv()
    
    required_vars = [
        'BINANCE_API_KEY',
        'BINANCE_SECRET_KEY',
        'BINANCE_TESTNET'
    ]
    
    env_vars = {}
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            env_vars[var] = value
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    

    env_vars['LOG_LEVEL'] = os.getenv('LOG_LEVEL', 'INFO')
    env_vars['MAX_RETRIES'] = int(os.getenv('MAX_RETRIES', '3'))
    env_vars['BASE_DELAY'] = float(os.getenv('BASE_DELAY', '1.0'))
    env_vars['MAX_DELAY'] = float(os.getenv('MAX_DELAY', '60.0'))
    
    logger.info(f"Environment variables loaded successfully. Testnet: {env_vars['BINANCE_TESTNET']}")
    return env_vars


def exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True
) -> Callable:
   
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    

                    if hasattr(e, 'code'):

                        no_retry_codes = [-1021, -1022, -2010, -2011, -2013, -2014, -2015]
                        if getattr(e, 'code', None) in no_retry_codes:
                            logger.error(f"Non-retryable error {e.code}: {e}")
                            raise e
                    
                    if attempt == max_retries:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
                        break
                    

                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    

                    if jitter:
                        import random
                        delay *= (0.5 + random.random() * 0.5)
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    time.sleep(delay)
            
            raise RetryExhaustedError(f"Failed after {max_retries + 1} attempts: {last_exception}")
        
        return wrapper
    return decorator


async def async_exponential_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True
) -> Callable:
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    

                    if hasattr(e, 'code'):
                        no_retry_codes = [-1021, -1022, -2010, -2011, -2013, -2014, -2015]
                        if getattr(e, 'code', None) in no_retry_codes:
                            logger.error(f"Non-retryable error {e.code}: {e}")
                            raise e
                    
                    if attempt == max_retries:
                        logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
                        break
                    

                    delay = min(base_delay * (backoff_factor ** attempt), max_delay)
                    

                    if jitter:
                        import random
                        delay *= (0.5 + random.random() * 0.5)
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    await asyncio.sleep(delay)
            
            raise RetryExhaustedError(f"Failed after {max_retries + 1} attempts: {last_exception}")
        
        return wrapper
    return decorator


def safe_api_call(func: Callable) -> Callable:
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            logger.debug(f"API call {func.__name__} successful")
            return result
        except Exception as e:
            logger.error(f"API call {func.__name__} failed: {type(e).__name__}: {e}")
            

            if hasattr(e, 'response'):
                logger.error(f"Response status: {getattr(e.response, 'status_code', 'Unknown')}")
                logger.error(f"Response text: {getattr(e.response, 'text', 'Unknown')}")
            
            raise e
    
    return wrapper


def format_quantity(quantity: Union[str, float, Decimal], precision: int) -> str:
   
    decimal_quantity = Decimal(str(quantity))
    

    format_str = f"{{:.{precision}f}}"
    

    multiplier = Decimal(10) ** precision
    rounded_quantity = decimal_quantity.quantize(Decimal('1') / multiplier, rounding=ROUND_DOWN)
    
    return format_str.format(float(rounded_quantity))


def format_price(price: Union[str, float, Decimal], tick_size: Union[str, float, Decimal]) -> str:
    
    decimal_price = Decimal(str(price))
    decimal_tick_size = Decimal(str(tick_size))
    

    rounded_price = (decimal_price / decimal_tick_size).quantize(Decimal('1'), rounding=ROUND_DOWN) * decimal_tick_size
    

    tick_str = str(decimal_tick_size)
    if '.' in tick_str:
        precision = len(tick_str.split('.')[1].rstrip('0'))
    else:
        precision = 0
    
    format_str = f"{{:.{precision}f}}"
    return format_str.format(float(rounded_price))


def validate_order_parameters(
    symbol: str,
    side: str,
    order_type: str,
    quantity: Optional[Union[str, float]] = None,
    price: Optional[Union[str, float]] = None,
    time_in_force: Optional[str] = None,
    stop_price: Optional[Union[str, float]] = None,
    **kwargs
) -> Dict[str, Any]:
    
    if not symbol or not isinstance(symbol, str):
        raise ValidationError("Symbol must be a non-empty string")
    
    valid_sides = ['BUY', 'SELL']
    if side not in valid_sides:
        raise ValidationError(f"Side must be one of {valid_sides}")
    
    valid_order_types = [
        'MARKET', 'LIMIT', 'STOP_MARKET', 'STOP', 'TAKE_PROFIT_MARKET',
        'TAKE_PROFIT', 'TRAILING_STOP_MARKET'
    ]
    if order_type not in valid_order_types:
        raise ValidationError(f"Order type must be one of {valid_order_types}")
    

    params = {
        'symbol': symbol.upper(),
        'side': side.upper(),
        'type': order_type.upper()
    }
    

    if quantity is not None:
        try:
            quantity_decimal = Decimal(str(quantity))
            if quantity_decimal <= 0:
                raise ValidationError("Quantity must be positive")
            params['quantity'] = str(quantity)
        except (ValueError, TypeError):
            raise ValidationError("Quantity must be a valid number")
    

    if price is not None:
        try:
            price_decimal = Decimal(str(price))
            if price_decimal <= 0:
                raise ValidationError("Price must be positive")
            params['price'] = str(price)
        except (ValueError, TypeError):
            raise ValidationError("Price must be a valid number")
    

    if stop_price is not None:
        try:
            stop_price_decimal = Decimal(str(stop_price))
            if stop_price_decimal <= 0:
                raise ValidationError("Stop price must be positive")
            params['stopPrice'] = str(stop_price)
        except (ValueError, TypeError):
            raise ValidationError("Stop price must be a valid number")
    

    if time_in_force is not None:
        valid_tif = ['GTC', 'IOC', 'FOK', 'GTX']
        if time_in_force not in valid_tif:
            raise ValidationError(f"Time in force must be one of {valid_tif}")
        params['timeInForce'] = time_in_force
    

    for key, value in kwargs.items():
        if value is not None:
            params[key] = value
    

    if order_type in ['LIMIT', 'STOP', 'TAKE_PROFIT']:
        if price is None:
            raise ValidationError(f"{order_type} orders require price")
        if time_in_force is None:
            params['timeInForce'] = 'GTC'
    
    if order_type in ['STOP_MARKET', 'STOP', 'TAKE_PROFIT_MARKET', 'TAKE_PROFIT']:
        if stop_price is None:
            raise ValidationError(f"{order_type} orders require stop price")
    
    if order_type == 'MARKET':

        params.pop('price', None)
        params.pop('timeInForce', None)
    
    logger.debug(f"Validated order parameters: {params}")
    return params


def calculate_notional_value(quantity: Union[str, float, Decimal], price: Union[str, float, Decimal]) -> Decimal:
    
    return Decimal(str(quantity)) * Decimal(str(price))


def validate_filters(
    params: Dict[str, Any],
    symbol_info: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    
    try:
        filters = {f['filterType']: f for f in symbol_info.get('filters', [])}
        quantity = Decimal(str(params.get('quantity', 0)))
        price = Decimal(str(params.get('price', 0))) if params.get('price') else None
        

        if 'LOT_SIZE' in filters:
            lot_filter = filters['LOT_SIZE']
            min_qty = Decimal(lot_filter['minQty'])
            max_qty = Decimal(lot_filter['maxQty'])
            step_size = Decimal(lot_filter['stepSize'])
            
            if quantity < min_qty:
                return False, f"Quantity {quantity} below minimum {min_qty}"
            if quantity > max_qty:
                return False, f"Quantity {quantity} above maximum {max_qty}"
            if (quantity - min_qty) % step_size != 0:
                return False, f"Quantity {quantity} not aligned with step size {step_size}"
        

        if price and 'PRICE_FILTER' in filters:
            price_filter = filters['PRICE_FILTER']
            min_price = Decimal(price_filter['minPrice'])
            max_price = Decimal(price_filter['maxPrice'])
            tick_size = Decimal(price_filter['tickSize'])
            
            if price < min_price:
                return False, f"Price {price} below minimum {min_price}"
            if price > max_price:
                return False, f"Price {price} above maximum {max_price}"
            if (price - min_price) % tick_size != 0:
                return False, f"Price {price} not aligned with tick size {tick_size}"
        

        if 'MIN_NOTIONAL' in filters and price:
            min_notional = Decimal(filters['MIN_NOTIONAL']['minNotional'])
            notional = calculate_notional_value(quantity, price)
            if notional < min_notional:
                return False, f"Notional value {notional} below minimum {min_notional}"
        
        return True, None
        
    except Exception as e:
        return False, f"Filter validation error: {e}"


def get_precision_from_step_size(step_size: Union[str, float, Decimal]) -> int:
   
    step_str = str(Decimal(str(step_size)))
    if '.' in step_str:
        return len(step_str.split('.')[1].rstrip('0'))
    return 0


def truncate_to_precision(value: Union[str, float, Decimal], precision: int) -> str:
    
    decimal_value = Decimal(str(value))
    multiplier = Decimal(10) ** precision
    truncated = int(decimal_value * multiplier) / multiplier
    
    format_str = f"{{:.{precision}f}}"
    return format_str.format(truncated)



class RateLimiter:
    
    def __init__(self, max_requests: int = 10, time_window: float = 60.0):
    
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def acquire(self) -> bool:
       
        now = time.time()
        

        self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
        
        if len(self.requests) >= self.max_requests:
            return False
        
        self.requests.append(now)
        return True
    
    def wait_time(self) -> float:
        
        if len(self.requests) < self.max_requests:
            return 0.0
        
        oldest_request = min(self.requests)
        return self.time_window - (time.time() - oldest_request)