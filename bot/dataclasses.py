from dataclasses import dataclass
from typing import List, Optional
from decimal import Decimal


@dataclass
class StopLimitOrder:
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    stop_price: Decimal
    time_in_force: str = "GTC"
    reduce_only: bool = False
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'side': self.side,
            'quantity': float(self.quantity),
            'price': float(self.price),
            'stopPrice': float(self.stop_price),
            'timeInForce': self.time_in_force,
            'reduceOnly': self.reduce_only
        }

@dataclass
class OCOOrder:
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    stop_price: Decimal
    stop_limit_price: Decimal
    time_in_force: str = "GTC"
    
    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'side': self.side,
            'quantity': float(self.quantity),
            'price': float(self.price),
            'stopPrice': float(self.stop_price),
            'stopLimitPrice': float(self.stop_limit_price),
            'timeInForce': self.time_in_force
        }
    
@dataclass
class OrderResponse:
    order_id: str
    symbol: str
    side: str
    type: str
    status: str
    price: Optional[str] = None
    orders: Optional[List[dict]] = None
    order_list_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'orderId': self.order_id,
            'symbol': self.symbol,
            'side': self.side,
            'type': self.type,
            'status': self.status,
            'price': self.price,
            'orders': self.orders,
            'orderListId': self.order_list_id
        }
