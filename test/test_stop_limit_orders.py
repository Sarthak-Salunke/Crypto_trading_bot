"""
Comprehensive test suite for Stop-Limit order functionality.

This test file specifically tests the stop-limit command functionality
as requested in the testing recommendations.

Test Categories:
1. Parameter Validation Tests
2. Order Placement Tests
3. Order Cancellation Tests
4. Edge Case Tests
5. Integration Tests
"""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
import os
import time
from typing import Dict, Any


from bot.orders import OrderManager
from bot.basic_bot import BasicBot
from bot.dataclasses import StopLimitOrder


class TestStopLimitParameterValidation:
    
    @pytest.fixture
    def mock_bot(self):
        from bot.basic_bot import BasicBot
        mock_client = Mock()
        mock_client.futures_create_order = Mock()
        mock_client.futures_cancel_order = Mock()
        mock_client.futures_cancel_all_open_orders = Mock()
        mock_client.futures_get_open_orders = Mock()
        mock_client.futures_get_order = Mock()
        mock_bot = BasicBot(api_key="test", api_secret="test", testnet=True)
        mock_bot.client = mock_client

        mock_bot.validate_symbol = Mock(return_value=True)
        mock_bot._validate_order_params = Mock(return_value=True)
        mock_bot.get_symbol_price = Mock(return_value=50000.0)
        mock_bot._make_api_call = Mock(side_effect=lambda func, **kwargs: func(**kwargs))
        return mock_bot
    
    @pytest.fixture
    def order_manager(self, mock_bot):
        return OrderManager(mock_bot)
    
    def test_valid_stop_limit_parameters(self, order_manager):
        result = order_manager._validate_stop_limit_params(
            symbol="BTCUSDT",
            side="BUY",
            quantity=0.001,
            price=51000.0,
            stop_price=50000.0
        )
        assert result is True
    
    def test_invalid_side_parameter(self, order_manager):
        with pytest.raises(ValueError, match="Invalid side"):
            order_manager._validate_stop_limit_params(
                symbol="BTCUSDT",
                side="INVALID",
                quantity=0.001,
                price=51000.0,
                stop_price=50000.0
            )
    
    def test_negative_quantity(self, order_manager):
        with pytest.raises(ValueError, match="Quantity must be positive"):
            order_manager._validate_stop_limit_params(
                symbol="BTCUSDT",
                side="BUY",
                quantity=-0.001,
                price=51000.0,
                stop_price=50000.0
            )
    
    def test_buy_stop_price_validation(self, order_manager):
        with pytest.raises(ValueError, match="Buy stop price.*must be above current price"):
            order_manager._validate_stop_limit_params(
                symbol="BTCUSDT",
                side="BUY",
                quantity=0.001,
                price=51000.0,
                stop_price=40000.0
            )
    
    def test_sell_stop_price_validation(self, order_manager):
        with pytest.raises(ValueError, match="Sell stop price.*must be below current price"):
            order_manager._validate_stop_limit_params(
                symbol="BTCUSDT",
                side="SELL",
                quantity=0.001,
                price=49000.0,
                stop_price=60000.0
            )
    
    def test_buy_limit_price_validation(self, order_manager):
        with pytest.raises(ValueError, match="Buy limit price.*should be >= stop price"):
            order_manager._validate_stop_limit_params(
                symbol="BTCUSDT",
                side="BUY",
                quantity=0.001,
                price=49000.0,
                stop_price=50000.0
            )
    
    def test_sell_limit_price_validation(self, order_manager):
        with pytest.raises(ValueError, match="Sell limit price.*should be <= stop price"):
            order_manager._validate_stop_limit_params(
                symbol="BTCUSDT",
                side="SELL",
                quantity=0.001,
                price=51000.0,
                stop_price=50000.0
            )


class TestStopLimitOrderPlacement:
    
    @pytest.fixture
    def mock_bot(self):
        mock_bot = Mock()
        mock_bot.validate_symbol.return_value = True
        mock_bot._validate_order_params.return_value = True
        mock_bot.get_symbol_price.return_value = 50000.0
        mock_bot._make_api_call = Mock()
        mock_bot.client = Mock()
        mock_bot.client.futures_create_order = Mock()
        return mock_bot
    
    @pytest.fixture
    def order_manager(self, mock_bot):
        return OrderManager(mock_bot)
    
    def test_place_buy_stop_limit_order(self, order_manager, mock_bot):
        mock_response = {
            'orderId': 12345,
            'symbol': 'BTCUSDT',
            'status': 'NEW',
            'side': 'BUY',
            'type': 'STOP',
            'price': '51000.0',
            'stopPrice': '50000.0',
            'origQty': '0.001'
        }
        mock_bot._make_api_call.return_value = mock_response
        
        result = order_manager.place_stop_limit_order(
            symbol='BTCUSDT',
            side='BUY',
            quantity=0.001,
            price=51000.0,
            stop_price=50000.0
        )
        
        assert result['orderId'] == 12345
        assert result['symbol'] == 'BTCUSDT'
        assert result['side'] == 'BUY'
        assert result['type'] == 'STOP'
        

        mock_bot._make_api_call.assert_called_once()
        call_args = mock_bot._make_api_call.call_args
        assert call_args[1]['symbol'] == 'BTCUSDT'
        assert call_args[1]['side'] == 'BUY'
        assert call_args[1]['type'] == 'STOP'
        assert call_args[1]['quantity'] == 0.001
        assert call_args[1]['price'] == 51000.0
        assert call_args[1]['stopPrice'] == 50000.0
    
    def test_place_sell_stop_limit_order(self, order_manager, mock_bot):
        mock_response = {
            'orderId': 12346,
            'symbol': 'BTCUSDT',
            'status': 'NEW',
            'side': 'SELL',
            'type': 'STOP',
            'price': '49000.0',
            'stopPrice': '50000.0',
            'origQty': '0.001'
        }
        mock_bot._make_api_call.return_value = mock_response
        
        result = order_manager.place_stop_limit_order(
            symbol='BTCUSDT',
            side='SELL',
            quantity=0.001,
            price=49000.0,
            stop_price=50000.0
        )
        
        assert result['orderId'] == 12346
        assert result['symbol'] == 'BTCUSDT'
        assert result['side'] == 'SELL'
        assert result['type'] == 'STOP'
    
    def test_buy_stop_limit_convenience_method(self, order_manager, mock_bot):
        mock_response = {
            'orderId': 12347,
            'symbol': 'BTCUSDT',
            'status': 'NEW',
            'side': 'BUY',
            'type': 'STOP'
        }
        mock_bot._make_api_call.return_value = mock_response
        
        result = order_manager.buy_stop_limit(
            symbol='BTCUSDT',
            quantity=0.001,
            price=51000.0,
            stop_price=50000.0
        )
        
        assert result['orderId'] == 12347
        assert result['side'] == 'BUY'
    
    def test_sell_stop_limit_convenience_method(self, order_manager, mock_bot):
        mock_response = {
            'orderId': 12348,
            'symbol': 'BTCUSDT',
            'status': 'NEW',
            'side': 'SELL',
            'type': 'STOP'
        }
        mock_bot._make_api_call.return_value = mock_response
        
        result = order_manager.sell_stop_limit(
            symbol='BTCUSDT',
            quantity=0.001,
            price=49000.0,
            stop_price=50000.0
        )
        
        assert result['orderId'] == 12348
        assert result['side'] == 'SELL'


class TestStopLimitOrderCancellation:
    @pytest.fixture
    def mock_bot(self):
        mock_bot = Mock()
        mock_bot.validate_symbol.return_value = True
        mock_bot._make_api_call = Mock()
        mock_bot.client = Mock()
        mock_bot.client.futures_cancel_order = Mock()
        mock_bot.client.futures_cancel_all_open_orders = Mock()
        mock_bot.client.futures_get_open_orders = Mock()
        return mock_bot
    
    @pytest.fixture
    def order_manager(self, mock_bot):
        return OrderManager(mock_bot)
    
    def test_cancel_single_order(self, order_manager, mock_bot):
        mock_response = {
            'orderId': 12345,
            'symbol': 'BTCUSDT',
            'status': 'CANCELED'
        }
        mock_bot._make_api_call.return_value = mock_response
        
        result = order_manager.cancel_order('BTCUSDT', 12345)
        
        assert result['orderId'] == 12345
        assert result['status'] == 'CANCELED'
        

        mock_bot._make_api_call.assert_called_once()
        call_args = mock_bot._make_api_call.call_args
        assert call_args[1]['symbol'] == 'BTCUSDT'
        assert call_args[1]['orderId'] == 12345
    
    def test_cancel_all_orders(self, order_manager, mock_bot):
        """Test canceling all orders for a symbol."""
        mock_response = {
            'code': 200,
            'msg': 'success'
        }
        mock_bot._make_api_call.return_value = mock_response
        
        result = order_manager.cancel_all_orders('BTCUSDT')
        
        assert result['code'] == 200
        assert result['msg'] == 'success'
    
    def test_get_open_orders(self, order_manager, mock_bot):
        mock_response = [
            {
                'orderId': 12345,
                'symbol': 'BTCUSDT',
                'status': 'NEW',
                'side': 'BUY',
                'type': 'STOP'
            },
            {
                'orderId': 12346,
                'symbol': 'BTCUSDT',
                'status': 'NEW',
                'side': 'SELL',
                'type': 'STOP'
            }
        ]
        mock_bot._make_api_call.return_value = mock_response
        
        result = order_manager.get_open_orders('BTCUSDT')
        
        assert len(result) == 2
        assert result[0]['symbol'] == 'BTCUSDT'
        assert result[0]['type'] == 'STOP'


class TestStopLimitEdgeCases:
    
    @pytest.fixture
    def mock_bot(self):
        mock_bot = Mock()
        mock_bot.validate_symbol.return_value = True
        mock_bot._validate_order_params.return_value = True
        mock_bot.get_symbol_price.return_value = 50000.0
        mock_bot._make_api_call = Mock()
        mock_bot.client = Mock()
        mock_bot.client.futures_create_order = Mock()
        return mock_bot
    
    @pytest.fixture
    def order_manager(self, mock_bot):
        return OrderManager(mock_bot)
    
    def test_zero_quantity(self, order_manager):
        with pytest.raises(ValueError, match="Quantity must be positive"):
            order_manager.place_stop_limit_order(
                symbol='BTCUSDT',
                side='BUY',
                quantity=0.0,
                price=51000.0,
                stop_price=50000.0
            )
    
    def test_negative_price(self, order_manager):
        with pytest.raises(ValueError, match="Price and stop_price must be positive"):
            order_manager.place_stop_limit_order(
                symbol='BTCUSDT',
                side='BUY',
                quantity=0.001,
                price=-51000.0,
                stop_price=50000.0
            )
    
    def test_invalid_symbol(self, order_manager, mock_bot):
        mock_bot.validate_symbol.return_value = False
        
        with pytest.raises(ValueError, match="Invalid symbol"):
            order_manager.place_stop_limit_order(
                symbol='INVALID',
                side='BUY',
                quantity=0.001,
                price=51000.0,
                stop_price=50000.0
            )
    
    def test_very_small_quantity(self, order_manager):
        mock_response = {
            'orderId': 12349,
            'symbol': 'BTCUSDT',
            'status': 'NEW',
            'side': 'BUY',
            'type': 'STOP'
        }
        mock_bot._make_api_call.return_value = mock_response
        
        result = order_manager.place_stop_limit_order(
            symbol='BTCUSDT',
            side='BUY',
            quantity=0.000001,
            price=51000.0,
            stop_price=50000.0
        )
        
        assert result['orderId'] == 12349


class TestStopLimitIntegration:
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_stop_limit_order_lifecycle(self):

        pytest.skip("Integration test requires actual API credentials")
    
    def test_stop_limit_with_different_symbols(self, order_manager, mock_bot):
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
        
        for symbol in symbols:
            mock_response = {
                'orderId': 12345,
                'symbol': symbol,
                'status': 'NEW',
                'side': 'BUY',
                'type': 'STOP'
            }
            mock_bot._make_api_call.return_value = mock_response
            
            result = order_manager.place_stop_limit_order(
                symbol=symbol,
                side='BUY',
                quantity=0.001,
                price=51000.0,
                stop_price=50000.0
            )
            
            assert result['symbol'] == symbol
    
    def test_stop_limit_with_different_quantities(self, order_manager, mock_bot):
        quantities = [0.001, 0.01, 0.1, 1.0]
        
        for qty in quantities:
            mock_response = {
                'orderId': 12345,
                'symbol': 'BTCUSDT',
                'status': 'NEW',
                'side': 'BUY',
                'type': 'STOP',
                'origQty': str(qty)
            }
            mock_bot._make_api_call.return_value = mock_response
            
            result = order_manager.place_stop_limit_order(
                symbol='BTCUSDT',
                side='BUY',
                quantity=qty,
                price=51000.0,
                stop_price=50000.0
            )
            
            assert float(result['origQty']) == qty


class TestStopLimitCLI:
    @pytest.fixture
    def mock_cli(self):
        """Create mock CLI."""
        mock_cli = Mock()
        mock_cli.order_manager = Mock()
        return mock_cli
    
    def test_cli_stop_limit_command(self, mock_cli):
        from bot.cli import handle_stop_limit_command
        
        args = Mock()
        args.symbol = 'BTCUSDT'
        args.side = 'BUY'
        args.quantity = 0.001
        args.price = 51000.0
        args.stop_price = 50000.0
        
        mock_cli.order_manager.place_stop_limit_order.return_value = {
            'orderId': 12345,
            'status': 'NEW'
        }
        
        handle_stop_limit_command(mock_cli, args)
        
        mock_cli.order_manager.place_stop_limit_order.assert_called_once_with(
            'BTCUSDT', 'BUY', 0.001, 51000.0, 50000.0
        )



pytestmark = pytest.mark.asyncio


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "stop_limit: marks tests as stop-limit specific tests"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])