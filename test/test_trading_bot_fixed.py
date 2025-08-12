import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from decimal import Decimal
import os
import time
from typing import Dict, Any

from bot.utils import (
    exponential_backoff, validate_order_parameters, format_quantity,
    format_price, load_environment_variables, ValidationError,
    RetryExhaustedError, validate_filters, RateLimiter
)
from bot.basic_bot import BasicBot


class TestUtils:
    
    def test_validate_order_parameters_valid(self):
        params = validate_order_parameters(
            symbol='BTCUSDT',
            side='BUY',
            order_type='LIMIT',
            quantity='0.001',
            price='50000.00',
            time_in_force='GTC'
        )
        
        assert params['symbol'] == 'BTCUSDT'
        assert params['side'] == 'BUY'
        assert params['type'] == 'LIMIT'
        assert params['quantity'] == '0.001'
        assert params['price'] == '50000.00'
        assert params['timeInForce'] == 'GTC'
    
    def test_validate_order_parameters_invalid_side(self):
        """Test invalid side parameter."""
        with pytest.raises(ValidationError) as excinfo:
            validate_order_parameters(
                symbol='BTCUSDT',
                side='INVALID',
                order_type='LIMIT',
                quantity='0.001'
            )
        assert "Side must be one of" in str(excinfo.value)
    
    def test_validate_order_parameters_invalid_quantity(self):
        with pytest.raises(ValidationError) as excinfo:
            validate_order_parameters(
                symbol='BTCUSDT',
                side='BUY',
                order_type='LIMIT',
                quantity='-0.001'
            )
        assert "Quantity must be positive" in str(excinfo.value)
    
    def test_validate_order_parameters_market_order(self):
        params = validate_order_parameters(
            symbol='BTCUSDT',
            side='BUY',
            order_type='MARKET',
            quantity='0.001'
        )
        
        assert 'price' not in params
        assert 'timeInForce' not in params
    
    def test_validate_order_parameters_stop_order(self):
        params = validate_order_parameters(
            symbol='BTCUSDT',
            side='BUY',
            order_type='STOP_MARKET',
            quantity='0.001',
            stop_price='49000.00'
        )
        
        assert params['stopPrice'] == '49000.00'
    
    def test_format_quantity(self):
        assert format_quantity(0.123456789, 3) == "0.123"
        assert format_quantity("0.123456789", 5) == "0.12345"
        assert format_quantity(Decimal("0.123456789"), 2) == "0.12"
    
    def test_format_price(self):
        assert format_price(50000.123, "0.01") == "50000.12"
        assert format_price("50000.999", "0.1") == "50000.9"
        assert format_price(Decimal("50000.555"), Decimal("0.001")) == "50000.555"
    
    def test_validate_filters_lot_size(self):
        symbol_info = {
            'filters': [
                {
                    'filterType': 'LOT_SIZE',
                    'minQty': '0.001',
                    'maxQty': '10.0',
                    'stepSize': '0.001'
                }
            ]
        }
        
        params = {'quantity': '0.005'}
        is_valid, error = validate_filters(params, symbol_info)
        assert is_valid is True
        assert error is None
        
        params = {'quantity': '0.0005'}
        is_valid, error = validate_filters(params, symbol_info)
        assert is_valid is False
        assert "below minimum" in error
    
    def test_exponential_backoff_decorator(self):
        call_count = 0
        
        @exponential_backoff(max_retries=2, base_delay=0.1)
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Test error")
            return "success"
        
        result = failing_function()
        assert result == "success"
        assert call_count == 3
    
    def test_exponential_backoff_exhausted(self):
        @exponential_backoff(max_retries=1, base_delay=0.1)
        def always_failing_function():
            raise Exception("Always fails")
        
        with pytest.raises(RetryExhaustedError):
            always_failing_function()
    
    def test_rate_limiter(self):
        limiter = RateLimiter(max_requests=2, time_window=1.0)
        
        assert limiter.acquire() is True
        assert limiter.acquire() is True
        
        assert limiter.acquire() is False
        
        wait_time = limiter.wait_time()
        assert wait_time > 0
    
    @patch.dict(os.environ, {
        'BINANCE_API_KEY': 'test_key',
        'BINANCE_SECRET_KEY': 'test_secret',
        'BINANCE_TESTNET': 'true'
    })
    def test_load_environment_variables(self):
        """Test environment variable loading."""
        env_vars = load_environment_variables()
        
        assert env_vars['BINANCE_API_KEY'] == 'test_key'
        assert env_vars['BINANCE_SECRET_KEY'] == 'test_secret'
        assert env_vars['BINANCE_TESTNET'] == 'true'
        assert 'LOG_LEVEL' in env_vars
        assert 'MAX_RETRIES' in env_vars


class TestBasicBot:
    @pytest.fixture
    def mock_client(self):
        return Mock()
    
    @pytest.fixture
    def basic_bot(self, mock_client):
        bot = BasicBot('test_key', 'test_secret', testnet=True)
        bot.client = mock_client
        return bot
    
    def test_init_valid_credentials(self):
        bot = BasicBot('test_key', 'test_secret', testnet=True)
        assert bot.client is not None
    
    def test_init_empty_credentials(self):
        with pytest.raises(ValueError):
            BasicBot('', '', testnet=True)
    
    def test_validate_symbol_valid(self, basic_bot, mock_client):
        mock_client.futures_exchange_info.return_value = {
            'symbols': [
                {
                    'symbol': 'BTCUSDT',
                    'status': 'TRADING',
                    'filters': []
                }
            ]
        }
        
        result = basic_bot.validate_symbol('BTCUSDT')
        assert result is True
    
    def test_get_symbol_price(self, basic_bot, mock_client):
        mock_client.futures_symbol_ticker.return_value = {'price': '50000.0'}
        
        price = basic_bot.get_symbol_price('BTCUSDT')
        assert price == 50000.0
    
    def test_get_account_balance(self, basic_bot, mock_client):
        mock_client.futures_account.return_value = {
            'assets': [
                {
                    'asset': 'USDT',
                    'availableBalance': '1000.0',
                    'walletBalance': '1500.0'
                }
            ]
        }
        
        balance = basic_bot.get_account_balance('USDT')
        assert balance['available'] == 1000.0
        assert balance['total'] == 1500.0
    
    def test_place_market_order_success(self, basic_bot, mock_client):
        mock_client.futures_create_order.return_value = {
            'orderId': 12345,
            'symbol': 'BTCUSDT',
            'status': 'FILLED',
            'executedQty': '0.001',
            'side': 'BUY',
            'type': 'MARKET'
        }
        
        order = basic_bot.place_market_order('BTCUSDT', 'BUY', 0.001)
        assert order['orderId'] == 12345
        assert order['status'] == 'FILLED'
    
    def test_place_limit_order_success(self, basic_bot, mock_client):
        mock_client.futures_create_order.return_value = {
            'orderId': 12346,
            'symbol': 'BTCUSDT',
            'status': 'NEW',
            'side': 'SELL',
            'type': 'LIMIT',
            'price': '51000.0'
        }
        
        order = basic_bot.place_limit_order('BTCUSDT', 'SELL', 0.001, 51000.0)
        assert order['orderId'] == 12346
        assert order['status'] == 'NEW'
    
    def test_buy_market_convenience(self, basic_bot, mock_client):
        mock_client.futures_create_order.return_value = {'orderId': 12347}
        
        order = basic_bot.buy_market('BTCUSDT', 0.001)
        assert order['orderId'] == 12347
    
    def test_sell_market_convenience(self, basic_bot, mock_client):
        mock_client.futures_create_order.return_value = {'orderId': 12348}
        
        order = basic_bot.sell_market('BTCUSDT', 0.001)
        assert order['orderId'] == 12348
    
    def test_buy_limit_convenience(self, basic_bot, mock_client):
        mock_client.futures_create_order.return_value = {'orderId': 12349}
        
        order = basic_bot.buy_limit('BTCUSDT', 0.001, 50000.0)
        assert order['orderId'] == 12349
    
    def test_sell_limit_convenience(self, basic_bot, mock_client):
        mock_client.futures_create_order.return_value = {'orderId': 12350}
        
        order = basic_bot.sell_limit('BTCUSDT', 0.001, 50000.0)
        assert order['orderId'] == 12350


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )

@pytest.fixture
def sample_exchange_info():
    return {
        'symbols': [
            {
                'symbol': 'BTCUSDT',
                'status': 'TRADING',
                'baseAsset': 'BTC',
                'quoteAsset': 'USDT',
                'filters': [
                    {
                        'filterType': 'LOT_SIZE',
                        'minQty': '0.00100000',
                        'maxQty': '100.00000000',
                        'stepSize': '0.00100000'
                    },
                    {
                        'filterType': 'PRICE_FILTER',
                        'minPrice': '0.01000000',
                        'maxPrice': '100000.00000000',
                        'tickSize': '0.01000000'
                    },
                    {
                        'filterType': 'MIN_NOTIONAL',
                        'minNotional': '10.00000000'
                    }
                ]
            }
        ]
    }


@pytest.fixture
def sample_account_info():
    return {
        'accountType': 'FUTURES',
        'canTrade': True,
        'canWithdraw': False,
        'canDeposit': False,
        'balances': [
            {
                'asset': 'USDT',
                'balance': '1000.00000000',
                'crossWalletBalance': '1000.00000000'
            },
            {
                'asset': 'BTC',
                'balance': '0.10000000',
                'crossWalletBalance': '0.10000000'
            }
        ]
    }


if __name__ == "__main__":
    pytest.main([__file__])
