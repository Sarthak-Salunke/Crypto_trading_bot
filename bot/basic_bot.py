import logging
import time
from decimal import Decimal
from typing import Dict, Optional, Any, Union
import datetime

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
import requests

from .logger import log_trade, log_api_call, log_error


logger = logging.getLogger(__name__)


class BasicBot:
   
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True) -> None:
        if not api_key or not api_secret:
            raise ValueError("API key and secret cannot be empty")
            
        try:
            self.client = Client(api_key, api_secret, testnet=testnet)
            
            # Configure for Binance Futures testnet
            if testnet:
                self.client.API_URL = 'https://testnet.binancefuture.com/fapi'
                logger.info("Configured for Binance Futures testnet")
            
            self.exchange_info: Optional[Dict] = None
            self.symbol_filters: Dict[str, Dict] = {}
            self.time_offset = 0
            
            self._sync_time_with_binance()
            self._initialize_exchange_info()
            
            logger.info(f"BasicBot initialized successfully (testnet={testnet})")
            
        except BinanceAPIException as e:
            logger.error(f"Failed to initialize Binance client: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during initialization: {e}")
            raise
    
    def _initialize_exchange_info(self) -> None:
        try:
            self.exchange_info = self._make_api_call(self.client.futures_exchange_info)
            

            for symbol_info in self.exchange_info['symbols']:
                symbol = symbol_info['symbol']
                self.symbol_filters[symbol] = {
                    filter_info['filterType']: filter_info 
                    for filter_info in symbol_info['filters']
                }
                
            logger.info(f"Cached filters for {len(self.symbol_filters)} symbols")
            
        except BinanceAPIException as e:
            logger.error(f"Failed to retrieve exchange info: {e}")
            raise
    
    def _sync_time_with_binance(self) -> None:
        """Synchronize local time with Binance server time to prevent timestamp errors."""
        try:
            server_time = self.client.get_server_time()
            server_timestamp = server_time['serverTime']
            local_timestamp = int(time.time() * 1000)
            self.time_offset = server_timestamp - local_timestamp
            print(f"✅ Time synced with Binance (offset: {self.time_offset} ms)")
            logger.info(f"Time synchronized with Binance. Server Time: {server_timestamp}, Local Time: {local_timestamp}, Offset: {self.time_offset}ms")
        except Exception as e:
            print(f"⚠️ Failed to sync time: {e}")
            logger.warning(f"Failed to sync time with Binance: {e}")
            self.time_offset = 0

    def _get_synced_timestamp(self) -> int:
        """Get timestamp adjusted for Binance server time."""
        return int(time.time() * 1000) + self.time_offset

    def _make_api_call(self, func, *args, max_retries: int = 3, **kwargs) -> Any:
        for attempt in range(max_retries + 1):
            try:
                # Only add timestamp for methods that support it (like order creation)
                timestamp_methods = [
                    'futures_create_order',
                    'futures_cancel_order',
                    'futures_get_order',
                    'futures_account',
                    'futures_symbol_ticker'
                ]
                
                # Check if this is a method that needs timestamp
                func_name = str(func).split('.')[-1].split(' ')[0]
                if any(method in str(func) for method in timestamp_methods):
                    kwargs['timestamp'] = self._get_synced_timestamp()
                
                return func(*args, **kwargs)
                
            except BinanceAPIException as e:
                if e.code == -1021:  # Timestamp for this request was outside the recvWindow
                    if attempt < max_retries:
                        logger.warning(f"Timestamp error detected, resyncing time (attempt {attempt + 1})")
                        self._sync_time_with_binance()
                        wait_time = 2 ** attempt
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error("Max retries exceeded for timestamp sync")
                        raise
                elif e.code == -1003:
                    if attempt < max_retries:
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limit exceeded, waiting {wait_time}s (attempt {attempt + 1})")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error("Max retries exceeded for rate limit")
                        raise
                else:
                    logger.error(f"Binance API error: {e}")
                    raise
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Network error, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Network error after {max_retries} retries: {e}")
                    raise
                    
            except Exception as e:
                logger.error(f"Unexpected error in API call: {e}")
                raise
    
    def validate_symbol(self, symbol: str) -> bool:
        try:
            if not self.exchange_info:
                self._initialize_exchange_info()
                
            for symbol_info in self.exchange_info['symbols']:
                if (symbol_info['symbol'] == symbol.upper() and 
                    symbol_info['status'] == 'TRADING'):
                    return True
                    
            logger.warning(f"Symbol {symbol} not found or not tradeable")
            return False
            
        except Exception as e:
            logger.error(f"Error validating symbol {symbol}: {e}")
            return False
    
    def _validate_order_params(self, symbol: str, quantity: float, price: Optional[float] = None) -> bool:
        try:
            symbol = symbol.upper()
            if symbol not in self.symbol_filters:
                logger.error(f"No filters found for symbol {symbol}")
                return False
                
            filters = self.symbol_filters[symbol]
            

            if 'LOT_SIZE' in filters:
                lot_filter = filters['LOT_SIZE']
                min_qty = float(lot_filter['minQty'])
                max_qty = float(lot_filter['maxQty'])
                step_size = float(lot_filter['stepSize'])
                
                if quantity < min_qty or quantity > max_qty:
                    logger.error(f"Quantity {quantity} outside allowed range [{min_qty}, {max_qty}]")
                    return False
                    

                qty_decimal = Decimal(str(quantity))
                step_decimal = Decimal(str(step_size))
                if qty_decimal % step_decimal != 0:
                    logger.error(f"Quantity {quantity} doesn't comply with step size {step_size}")
                    return False
            

            if price is not None and 'PRICE_FILTER' in filters:
                price_filter = filters['PRICE_FILTER']
                min_price = float(price_filter['minPrice'])
                max_price = float(price_filter['maxPrice'])
                tick_size = float(price_filter['tickSize'])
                
                if price < min_price or price > max_price:
                    logger.error(f"Price {price} outside allowed range [{min_price}, {max_price}]")
                    return False
                    

                price_decimal = Decimal(str(price))
                tick_decimal = Decimal(str(tick_size))
                if price_decimal % tick_decimal != 0:
                    logger.error(f"Price {price} doesn't comply with tick size {tick_size}")
                    return False
            

            if 'MIN_NOTIONAL' in filters and 'minNotional' in filters['MIN_NOTIONAL']:
                try:
                    min_notional = float(filters['MIN_NOTIONAL']['minNotional'])
                    notional = quantity * (price if price else self.get_symbol_price(symbol))
                    
                    if notional < min_notional:
                        logger.error(f"Order notional {notional} below minimum {min_notional}")
                        return False
                except (KeyError, ValueError) as e:
                    logger.warning(f"MIN_NOTIONAL filter exists but has invalid format: {e}")

                    pass
            else:

                logger.debug(f"MIN_NOTIONAL filter not found for {symbol} - skipping notional validation")
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating order parameters: {e}")
            return False
    
    def get_symbol_price(self, symbol: str) -> float:
        try:
            ticker = self._make_api_call(self.client.futures_symbol_ticker, symbol=symbol.upper())
            return float(ticker['price'])
            
        except BinanceAPIException as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            raise
    
    def get_account_balance(self, asset: str = 'USDT') -> Dict[str, float]:
        try:
            account_info = self._make_api_call(self.client.futures_account)
            
            for balance in account_info['assets']:
                if balance['asset'] == asset.upper():
                    return {
                        'available': float(balance['availableBalance']),
                        'total': float(balance['walletBalance'])
                    }
            
            logger.warning(f"Asset {asset} not found in account")
            return {'available': 0.0, 'total': 0.0}
            
        except BinanceAPIException as e:
            logger.error(f"Failed to get account balance: {e}")
            raise
    
    def place_market_order(self, symbol: str, side: str, quantity: float) -> Dict[str, Any]:
        try:
            symbol = symbol.upper()
            side = side.upper()
            

            if side not in ['BUY', 'SELL']:
                raise ValueError(f"Invalid side: {side}. Must be 'BUY' or 'SELL'")
                
            if not self.validate_symbol(symbol):
                raise ValueError(f"Invalid or non-tradeable symbol: {symbol}")
                
            if not self._validate_order_params(symbol, quantity):
                raise ValueError("Order parameters failed validation")
            

            order = self._make_api_call(
                self.client.futures_create_order,
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            
            log_trade("PLACE_ORDER", symbol, side, quantity, order_type="MARKET")
            return order
            
        except Exception as e:
            log_error(e, {"symbol": symbol, "side": side, "quantity": quantity})
            raise
    
    def place_limit_order(self, symbol: str, side: str, quantity: float, price: float, 
                         time_in_force: str = 'GTC') -> Dict[str, Any]:
        try:
            symbol = symbol.upper()
            side = side.upper()
            time_in_force = time_in_force.upper()
            

            if side not in ['BUY', 'SELL']:
                raise ValueError(f"Invalid side: {side}. Must be 'BUY' or 'SELL'")
                
            if time_in_force not in ['GTC', 'IOC', 'FOK']:
                raise ValueError(f"Invalid time_in_force: {time_in_force}")
                
            if not self.validate_symbol(symbol):
                raise ValueError(f"Invalid or non-tradeable symbol: {symbol}")
                
            if not self._validate_order_params(symbol, quantity, price):
                raise ValueError("Order parameters failed validation")
            

            order = self._make_api_call(
                self.client.futures_create_order,
                symbol=symbol,
                side=side,
                type='LIMIT',
                quantity=quantity,
                price=price,
                timeInForce=time_in_force
            )
            
            logger.info(f"Limit order placed: {side} {quantity} {symbol} @ {price}")
            return order
            
        except (ValueError, BinanceOrderException) as e:
            logger.error(f"Failed to place limit order: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error placing limit order: {e}")
            raise
    
    def buy_market(self, symbol: str, quantity: float) -> Dict[str, Any]:
        return self.place_market_order(symbol, 'BUY', quantity)
    
    def sell_market(self, symbol: str, quantity: float) -> Dict[str, Any]:
        return self.place_market_order(symbol, 'SELL', quantity)
    
    def buy_limit(self, symbol: str, quantity: float, price: float, 
                  time_in_force: str = 'GTC') -> Dict[str, Any]:
        return self.place_limit_order(symbol, 'BUY', quantity, price, time_in_force)
    
    def sell_limit(self, symbol: str, quantity: float, price: float, 
                   time_in_force: str = 'GTC') -> Dict[str, Any]:
        return self.place_limit_order(symbol, 'SELL', quantity, price, time_in_force)

    def get_positions(self, symbol: str = None) -> list:
        """Get open futures positions.
        
        Args:
            symbol (str, optional): Filter positions by symbol
            
        Returns:
            list: List of open position dictionaries
        """
        try:
            account = self._make_api_call(self.client.futures_account)
            positions = account.get('positions', [])
            
            # Filter out positions with zero size
            open_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
            
            # Filter by symbol if provided
            if symbol:
                open_positions = [p for p in open_positions if p.get('symbol') == symbol.upper()]
                
            return open_positions
            
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []


if __name__ == "__main__":

    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:

        bot = BasicBot(
            api_key=os.getenv('BINANCE_API_KEY', ''),
            api_secret=os.getenv('BINANCE_API_SECRET', ''),
            testnet=True
        )
        

        print("Bot initialized successfully!")
        

        is_valid = bot.validate_symbol('BTCUSDT')
        print(f"BTCUSDT is valid: {is_valid}")
        

        balance = bot.get_account_balance('USDT')
        print(f"USDT Balance: {balance}")
        

        if is_valid:
            price = bot.get_symbol_price('BTCUSDT')
            print(f"Current BTCUSDT price: {price}")
        
    except Exception as e:
        logger.error(f"Error in example usage: {e}")
