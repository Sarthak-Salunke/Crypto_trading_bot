from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal

from binance.exceptions import BinanceAPIException, BinanceOrderException
from .basic_bot import BasicBot
from .dataclasses import OCOOrder, OrderResponse


logger = logging.getLogger(__name__)


class OrderManager:
    
    def __init__(self, bot: BasicBot) -> None:
       
        if not hasattr(bot, 'client') or bot.client is None:
            raise ValueError("bot must be properly initialized with valid client")
            
        self.bot = bot
        self.active_orders: Dict[str, Dict[str, Any]] = {}
        
        logger.info("OrderManager initialized successfully")
    
    def _validate_stop_limit_params(self, symbol: str, side: str, quantity: float,
                                  price: float, stop_price: float) -> bool:
       
        try:
            if not self.bot._validate_order_params(symbol, quantity, price):
                raise ValueError("Basic order parameters failed validation")
            
            if not self.bot._validate_order_params(symbol, quantity, stop_price):
                raise ValueError("Stop price failed validation against price filters")
            
            current_price = self.bot.get_symbol_price(symbol)
            
            if side.upper() == 'BUY':
                if stop_price <= current_price:
                    raise ValueError(
                        f"Buy stop price ({stop_price}) must be above current price ({current_price})"
                    )
                if price < stop_price:
                    raise ValueError(
                        f"Buy limit price ({price}) should be >= stop price ({stop_price})"
                    )
            else: 
                if stop_price >= current_price:
                    raise ValueError(
                        f"Sell stop price ({stop_price}) must be below current price ({current_price})"
                    )
                if price > stop_price:
                    raise ValueError(
                        f"Sell limit price ({price}) should be <= stop price ({stop_price})"
                    )
            
            min_price_diff = current_price * 0.001  # 0.1%
            price_diff = abs(stop_price - current_price)
            
            if price_diff < min_price_diff:
                logger.warning(
                    f"Stop price very close to current price. "
                    f"Difference: {price_diff}, minimum recommended: {min_price_diff}"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Stop-Limit parameter validation failed: {e}")
            raise
    
    def place_stop_limit_order(self, symbol: str, side: str, quantity: float,
                             price: float, stop_price: float,
                             time_in_force: str = 'GTC',
                             reduce_only: bool = False) -> Dict[str, Any]:
        try:
            symbol = symbol.upper()
            side = side.upper()
            time_in_force = time_in_force.upper()
            
            if side not in ['BUY', 'SELL']:
                raise ValueError(f"Invalid side: {side}. Must be 'BUY' or 'SELL'")
                
            if time_in_force not in ['GTC', 'IOC', 'FOK']:
                raise ValueError(f"Invalid time_in_force: {time_in_force}")
                
            if quantity <= 0:
                raise ValueError(f"Quantity must be positive, got: {quantity}")
                
            if price <= 0 or stop_price <= 0:
                raise ValueError("Price and stop_price must be positive")
            
            if not self.bot.validate_symbol(symbol):
                raise ValueError(f"Invalid or non-tradeable symbol: {symbol}")
        
            self._validate_stop_limit_params(symbol, side, quantity, price, stop_price)
            
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': 'STOP',
                'quantity': quantity,
                'price': price,
                'stopPrice': stop_price,
                'timeInForce': time_in_force
            }
            
            if reduce_only:
                order_params['reduceOnly'] = reduce_only
            
            order = self.bot._make_api_call(
                self.bot.client.futures_create_order,
                **order_params
            )
            order_id = str(order['orderId'])
            self.active_orders[order_id] = {
                'symbol': symbol,
                'side': side,
                'type': 'STOP_LIMIT',
                'quantity': float(quantity),
                'price': float(price),
                'stop_price': float(stop_price),
                'status': order['status'],
                'time_in_force': time_in_force,
                'reduce_only': reduce_only
            }
            
            logger.info(
                f"Stop-Limit order placed: {side} {quantity} {symbol} "
                f"@ {price} (stop: {stop_price}) - Order ID: {order_id}"
            )
            
            return OrderResponse(
                order_id=order_id,
                symbol=symbol,
                side=side,
                type='STOP_LIMIT',
                status=order['status'],
                price=str(price)
            )
            
        except (ValueError, BinanceOrderException) as e:
            logger.error(f"Failed to place stop-limit order: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error placing stop-limit order: {e}")
            raise
    
    def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        try:
            symbol = symbol.upper()
            
            if not self.bot.validate_symbol(symbol):
                raise ValueError(f"Invalid symbol: {symbol}")
                
            if order_id <= 0:
                raise ValueError(f"Invalid order_id: {order_id}")
            

            cancel_response = self.bot._make_api_call(
                self.bot.client.futures_cancel_order,
                symbol=symbol,
                orderId=order_id
            )
            
            order_id_str = str(order_id)
            if order_id_str in self.active_orders:
                del self.active_orders[order_id_str]
                logger.info(f"Removed order {order_id} from active orders cache")
            
            logger.info(f"Order canceled: {symbol} - Order ID: {order_id}")
            
            return cancel_response
            
        except (ValueError, BinanceOrderException) as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error canceling order {order_id}: {e}")
            raise
    
    def cancel_all_orders(self, symbol: str) -> List[Dict[str, Any]]:
        try:
            symbol = symbol.upper()
            
            if not self.bot.validate_symbol(symbol):
                raise ValueError(f"Invalid symbol: {symbol}")
          
            cancel_response = self.bot._make_api_call(
                self.bot.client.futures_cancel_all_open_orders,
                symbol=symbol
            )
            
            orders_to_remove = [
                order_id for order_id, order_data in self.active_orders.items()
                if order_data['symbol'] == symbol
            ]
            
            for order_id in orders_to_remove:
                del self.active_orders[order_id]
            
            logger.info(
                f"All orders canceled for {symbol}. "
                f"Removed {len(orders_to_remove)} orders from cache"
            )
            
            return cancel_response
            
        except (ValueError, BinanceOrderException) as e:
            logger.error(f"Failed to cancel all orders for {symbol}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error canceling all orders for {symbol}: {e}")
            raise
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            if symbol:
                symbol = symbol.upper()
                if not self.bot.validate_symbol(symbol):
                    raise ValueError(f"Invalid symbol: {symbol}")
                    
                orders = self.bot._make_api_call(
                    self.bot.client.futures_get_open_orders,
                    symbol=symbol
                )
                logger.info(f"Retrieved {len(orders)} open orders for {symbol}")
            else:
                orders = self.bot._make_api_call(
                    self.bot.client.futures_get_open_orders
                )
                logger.info(f"Retrieved {len(orders)} open orders for all symbols")
            
            return orders
            
        except (ValueError, BinanceAPIException) as e:
            logger.error(f"Failed to get open orders: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting open orders: {e}")
            raise
    
    def get_order_status(self, symbol: str, order_id: int) -> Dict[str, Any]:
        try:
            symbol = symbol.upper()
            
            if not self.bot.validate_symbol(symbol):
                raise ValueError(f"Invalid symbol: {symbol}")
                
            if order_id <= 0:
                raise ValueError(f"Invalid order_id: {order_id}")
            
            order_status = self.bot._make_api_call(
                self.bot.client.futures_get_order,
                symbol=symbol,
                orderId=order_id
            )
            
            order_id_str = str(order_id)
            if order_id_str in self.active_orders:
                self.active_orders[order_id_str]['status'] = order_status['status']
            
            logger.info(f"Order status retrieved: {symbol} - Order ID: {order_id}")
            
            return order_status
            
        except (ValueError, BinanceAPIException) as e:
            logger.error(f"Failed to get order status for {order_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting order status for {order_id}: {e}")
            raise
    
    def buy_stop_limit(self, symbol: str, quantity: float, price: float,
                      stop_price: float, time_in_force: str = 'GTC',
                      reduce_only: bool = False) -> Dict[str, Any]:
        return self.place_stop_limit_order(
            symbol, 'BUY', quantity, price, stop_price, time_in_force, reduce_only
        )
    
    def sell_stop_limit(self, symbol: str, quantity: float, price: float,
                       stop_price: float, time_in_force: str = 'GTC',
                       reduce_only: bool = False) -> Dict[str, Any]:
        return self.place_stop_limit_order(
            symbol, 'SELL', quantity, price, stop_price, time_in_force, reduce_only
        )
    
    def get_cached_orders(self, symbol: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        if symbol:
            symbol = symbol.upper()
            filtered_orders = {
                order_id: order_data 
                for order_id, order_data in self.active_orders.items()
                if order_data['symbol'] == symbol
            }
            logger.info(f"Retrieved {len(filtered_orders)} cached orders for {symbol}")
            return filtered_orders
        else:
            logger.info(f"Retrieved {len(self.active_orders)} cached orders")
            return self.active_orders.copy()
    
    def place_oco_order(self, oco_order: OCOOrder) -> Dict[str, Any]:
        try:
            self._validate_oco_order(oco_order)
            
            tp_order = self.place_limit_order(
                symbol=oco_order.symbol,
                side='SELL' if oco_order.side.upper() == 'BUY' else 'BUY',
                quantity=oco_order.quantity,
                price=oco_order.price,
                reduce_only=True
            )
            
            sl_order = self.place_stop_limit_order(
                symbol=oco_order.symbol,
                side='SELL' if oco_order.side.upper() == 'BUY' else 'BUY',
                quantity=oco_order.quantity,
                price=oco_order.stop_limit_price,
                stop_price=oco_order.stop_price,
                reduce_only=True
            )
            
            oco_response = {
                'take_profit_order': tp_order,
                'stop_loss_order': sl_order,
                'oco_order_id': f"{tp_order['orderId']}_{sl_order['orderId']}",
                'symbol': oco_order.symbol,
                'quantity': oco_order.quantity,
                'side': oco_order.side
            }
            
            logger.info(
                f"OCO order placed: {oco_order.symbol} - "
                f"TP: {oco_order.price}, SL: {oco_order.stop_price}"
            )
            
            return oco_response
            
        except Exception as e:
            logger.error(f"Failed to place OCO order: {e}")
            raise
    
    def _validate_oco_order(self, oco_order: OCOOrder) -> bool:
        if not oco_order.symbol or not oco_order.symbol.upper():
            raise ValueError("Symbol is required")
            
        if oco_order.quantity <= 0:
            raise ValueError("Quantity must be positive")
            
        if oco_order.price <= 0:
            raise ValueError("Take profit price must be positive")
            
        if oco_order.stop_price <= 0:
            raise ValueError("Stop price must be positive")
            
        if oco_order.stop_limit_price <= 0:
            raise ValueError("Stop limit price must be positive")
            
        current_price = self.bot.get_symbol_price(oco_order.symbol)
        
        if oco_order.side.upper() == 'BUY':
            if oco_order.price <= current_price:
                raise ValueError("Take profit price must be above current price for BUY orders")
            if oco_order.stop_price >= current_price:
                raise ValueError("Stop price must be below current price for BUY orders")
        else:  
            if oco_order.price >= current_price:
                raise ValueError("Take profit price must be below current price for SELL orders")
            if oco_order.stop_price <= current_price:
                raise ValueError("Stop price must be above current price for SELL orders")
                
        return True
    
    def sync_cached_orders(self) -> None:
        try:
            all_open_orders = self.get_open_orders()
            active_order_ids = {str(order['orderId']) for order in all_open_orders}
            
            inactive_orders = [
                order_id for order_id in self.active_orders.keys()
                if order_id not in active_order_ids
            ]
            
            for order_id in inactive_orders:
                del self.active_orders[order_id]
            
            logger.info(
                f"Synchronized cached orders. Removed {len(inactive_orders)} "
                f"inactive orders. {len(self.active_orders)} orders remain cached."
            )
            
        except Exception as e:
            logger.error(f"Failed to synchronize cached orders: {e}")


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
        order_manager = OrderManager(bot)
        
        print("OrderManager initialized successfully!")
        
        if bot.validate_symbol('BTCUSDT'):
            current_price = bot.get_symbol_price('BTCUSDT')
            print(f"Current BTCUSDT price: {current_price}")
            stop_price = current_price * 0.95  
            limit_price = stop_price * 0.99  
            
            print(f"Example sell stop-limit order would be:")
            print(f"Stop Price: {stop_price}")
            print(f"Limit Price: {limit_price}")
            
        open_orders = order_manager.get_open_orders('BTCUSDT')
        print(f"Open orders for BTCUSDT: {len(open_orders)}")
        
        cached_orders = order_manager.get_cached_orders()
        print(f"Cached orders: {len(cached_orders)}")
        
    except Exception as e:
        logger.error(f"Error in example usage: {e}")
