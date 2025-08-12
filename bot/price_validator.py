import logging
from decimal import Decimal
from typing import Dict, Optional, Tuple
from binance.exceptions import BinanceAPIException

from .basic_bot import BasicBot

logger = logging.getLogger(__name__)


class PriceValidator:
    
    def __init__(self, bot: BasicBot):
        self.bot = bot
    
    def get_current_market_price(self, symbol: str) -> Decimal:
        try:
            price = self.bot.get_symbol_price(symbol)
            return Decimal(str(price))
        except Exception as e:
            logger.error(f"Failed to get current price for {symbol}: {e}")
            raise
    
    def validate_limit_price(
        self, 
        symbol: str, 
        side: str, 
        proposed_price: Decimal
    ) -> Tuple[bool, str]:
        try:
            current_price = self.get_current_market_price(symbol)
            
            if side.upper() == 'SELL':

                if proposed_price < current_price:
                    return False, (
                        f"SELL limit price {proposed_price} cannot be lower than "
                        f"current market price {current_price}"
                    )
            elif side.upper() == 'BUY':

                if proposed_price > current_price:
                    return False, (
                        f"BUY limit price {proposed_price} cannot be higher than "
                        f"current market price {current_price}"
                    )
            
            return True, ""
            
        except Exception as e:
            return False, f"Error validating price: {e}"
    
    def get_price_bounds(self, symbol: str) -> Dict[str, Decimal]:
        try:
            current_price = self.get_current_market_price(symbol)
            return {
                'current_price': current_price,
                'min_sell_price': current_price,
                'max_buy_price': current_price
            }
        except Exception as e:
            logger.error(f"Failed to get price bounds for {symbol}: {e}")
            raise
    
    def suggest_reasonable_price(
        self, 
        symbol: str, 
        side: str, 
        offset_percent: Decimal = Decimal('0.1')
    ) -> Decimal:
        try:
            current_price = self.get_current_market_price(symbol)
            
            if side.upper() == 'SELL':

                suggested = current_price * (Decimal('1') + offset_percent / Decimal('100'))
            else:

                suggested = current_price * (Decimal('1') - offset_percent / Decimal('100'))
            
            return suggested.quantize(Decimal('0.01'))
            
        except Exception as e:
            logger.error(f"Failed to suggest price for {symbol}: {e}")
            raise