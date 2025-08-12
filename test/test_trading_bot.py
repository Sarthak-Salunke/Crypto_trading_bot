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
from bot.config import BotConfig
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from decimal import Decimal
import pytest
import asyncio
import os
import time
from typing import Dict, Any


class TestUtils:
    """Test utility functions."""
    
    def test_validate_order_parameters_valid(self):
        """Test valid order parameter validation."""
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
        """Test invalid quantity parameter."""
        with pytest.raises(ValidationError) as excinfo:
            validate_order_parameters(
                symbol='BTCUSDT',
                side='BUY',
                order_type='LIMIT',
                quantity='-0.001'
            )
        assert "Quantity must be positive" in str(excinfo.value)
    
    def test_validate_order_parameters_market_order(self):
        """Test market order validation."""
        params = validate_order_parameters(
            symbol='BTCUSDT',
            side='BUY',
            order_type='MARKET',
            quantity='0.001'
        )
        
        assert 'price' not in params
        assert 'timeInForce' not in params
    
    def test_validate_order_parameters_stop_order(self):
        """Test stop order validation."""
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
    def mock_config(self):
        """Mock configuration."""
        config = Mock(spec=BotConfig)
        config.api_key = 'test_key'
        config.secret_key = 'test_secret'
        config.testnet = True
        config.max_retries = 3
        config.base_delay = 1.0
        return config
    
    @pytest.fixture
    def mock_client(self):
        client = Mock(spec=BinanceClient)
        return client
    
    @pytest.fixture
    def basic_bot(self, mock_config, mock_client):
        with patch('bot.BinanceClient', return_value=mock_client):
            bot = BasicBot(mock_config)
            bot.client = mock_client
            return bot
    
    def test_get_account_info(self, basic_bot, mock_client):
        mock_account_info = {
            'accountType': 'FUTURES',
            'balances': [
                {'asset': 'USDT', 'balance': '1000.0'},
                {'asset': 'BTC', 'balance': '0.1'}
            ]
        }
        mock_client.get_account.return_value = mock_account_info
        
        account_info = basic_bot.get_account_info()
        
        assert account_info == mock_account_info
        mock_client.get_account.assert_called_once()
    
    def test_get_symbol_info(self, basic_bot, mock_client):
        mock_exchange_info = {
            'symbols': [
                {
                    'symbol': 'BTCUSDT',
                    'status': 'TRADING',
                    'filters': [
                        {
                            'filterType': 'LOT_SIZE',
                            'minQty': '0.001',
                            'maxQty': '10.0',
                            'stepSize': '0.001'
                        }
                    ]
                }
            ]
        }
        mock_client.get_exchange_info.return_value = mock_exchange_info
        
        symbol_info = basic_bot.get_symbol_info('BTCUSDT')
        
        assert symbol_info['symbol'] == 'BTCUSDT'
        assert symbol_info['status'] == 'TRADING'
        mock_client.get_exchange_info.assert_called_once()
    
    def test_place_market_order(self, basic_bot, mock_client):
        mock_order_response = {
            'orderId': 12345,
            'symbol': 'BTCUSDT',
            'status': 'FILLED',
            'executedQty': '0.001',
            'side': 'BUY',
            'type': 'MARKET'
        }
        mock_client.new_order.return_value = mock_order_response
        
        order = basic_bot.place_market_order('BTCUSDT', 'BUY', '0.001')
        
        assert order['orderId'] == 12345
        assert order['status'] == 'FILLED'
        mock_client.new_order.assert_called_once()
        

        call_args = mock_client.new_order.call_args[1]
        assert call_args['symbol'] == 'BTCUSDT'
        assert call_args['side'] == 'BUY'
        assert call_args['type'] == 'MARKET'
        assert call_args['quantity'] == '0.001'
    
    def test_place_limit_order(self, basic_bot, mock_client):
        mock_order_response = {
            'orderId': 12346,
            'symbol': 'BTCUSDT',
            'status': 'NEW',
            'side': 'SELL',
            'type': 'LIMIT',
            'price': '51000.00'
        }
        mock_client.new_order.return_value = mock_order_response
        
        order = basic_bot.place_limit_order('BTCUSDT', 'SELL', '0.001', '51000.00')
        
        assert order['orderId'] == 12346
        assert order['status'] == 'NEW'
        mock_client.new_order.assert_called_once()
        
        call_args = mock_client.new_order.call_args[1]
        assert call_args['price'] == '51000.00'
        assert call_args['timeInForce'] == 'GTC'
    
    def test_get_order_status(self, basic_bot, mock_client):
        mock_order_status = {
            'orderId': 12345,
            'status': 'FILLED',
            'executedQty': '0.001'
        }
        mock_client.get_order.return_value = mock_order_status
        
        status = basic_bot.get_order_status('BTCUSDT', 12345)
        
        assert status['status'] == 'FILLED'
        mock_client.get_order.assert_called_once_with(symbol='BTCUSDT', orderId=12345)
    
    def test_cancel_order(self, basic_bot, mock_client):
        mock_cancel_response = {
            'orderId': 12345,
            'status': 'CANCELED'
        }
        mock_client.cancel_order.return_value = mock_cancel_response
        
        result = basic_bot.cancel_order('BTCUSDT', 12345)
        
        assert result['status'] == 'CANCELED'
        mock_client.cancel_order.assert_called_once_with(symbol='BTCUSDT', orderId=12345)
    
    def test_api_error_handling(self, basic_bot, mock_client):
        mock_client.get_account.side_effect = Exception("API Error")
        
        with pytest.raises(Exception) as excinfo:
            basic_bot.get_account_info()
        
        assert "API Error" in str(excinfo.value)


class TestOrderManager:
    @pytest.fixture
    def mock_client(self):
        """Mock Binance client."""
        return Mock(spec=BinanceClient)
    
    @pytest.fixture
    def order_manager(self, mock_client):
        return OrderManager(mock_client)
    
    def test_stop_limit_order_creation(self, order_manager, mock_client):
        mock_order_response = {
            'orderId': 12347,
            'symbol': 'BTCUSDT',
            'status': 'NEW',
            'type': 'STOP'
        }
        mock_client.new_order.return_value = mock_order_response
        
        stop_limit = StopLimitOrder(
            symbol='BTCUSDT',
            side='BUY',
            quantity='0.001',
            price='51000.00',
            stop_price='50000.00'
        )
        
        order = order_manager.place_stop_limit_order(stop_limit)
        
        assert order['orderId'] == 12347
        assert order['type'] == 'STOP'
    
    def test_oco_order_creation(self, order_manager, mock_client):
        mock_oco_response = {
            'orderListId': 789,
            'orders': [
                {'orderId': 12348, 'symbol': 'BTCUSDT'},
                {'orderId': 12349, 'symbol': 'BTCUSDT'}
            ]
        }
        mock_client.new_oco_order.return_value = mock_oco_response
        
        oco_order = OCOOrder(
            symbol='BTCUSDT',
            side='SELL',
            quantity='0.001',
            price='52000.00',
            stop_price='48000.00',
            stop_limit_price='47500.00'
        )
        
        order = order_manager.place_oco_order(oco_order)
        
        assert order['orderListId'] == 789
        assert len(order['orders']) == 2
    
    def test_twap_order_creation(self, order_manager):
        twap_order = TWAPOrder(
            symbol='BTCUSDT',
            side='BUY',
            total_quantity='0.01',
            duration_minutes=60,
            interval_minutes=5
        )
        

        sub_orders = twap_order.calculate_sub_orders()
        
        expected_sub_orders = 12
        expected_quantity_per_order = '0.00083333'
        
        assert len(sub_orders) == expected_sub_orders

        total_qty = sum(Decimal(order['quantity']) for order in sub_orders)
        assert abs(total_qty - Decimal('0.01')) < Decimal('0.00001')
    
    @pytest.mark.asyncio
    async def test_twap_order_execution(self, order_manager, mock_client):
        """Test TWAP order execution."""
        mock_client.new_order = AsyncMock()
        mock_client.new_order.return_value = {
            'orderId': 12350,
            'status': 'FILLED'
        }
        
        twap_order = TWAPOrder(
            symbol='BTCUSDT',
            side='BUY',
            total_quantity='0.006',
            duration_minutes=1,
            interval_minutes=0.5
        )
        

        with patch('asyncio.sleep', return_value=None):
            results = await order_manager.execute_twap_order(twap_order)
        
        assert len(results) == 2
        assert all(result['status'] == 'FILLED' for result in results)
    
    def test_order_validation_error(self, order_manager):
        """Test order validation errors."""
        with pytest.raises(ValidationError):
            StopLimitOrder(
                symbol='',
                side='BUY',
                quantity='0.001',
                price='51000.00',
                stop_price='50000.00'
            )
    
    def test_order_parameter_formatting(self, order_manager):
        stop_limit = StopLimitOrder(
            symbol='btcusdt',
            side='buy',
            quantity=0.001,
            price=51000.00,
            stop_price=50000.00
        )
        
        params = stop_limit.to_params()
        
        assert params['symbol'] == 'BTCUSDT'
        assert params['side'] == 'BUY'
        assert isinstance(params['quantity'], str)
        assert isinstance(params['price'], str)
        assert isinstance(params['stopPrice'], str)


class TestIntegration:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_testnet_market_order_integration(self):
        if not os.getenv('INTEGRATION_TEST'):
            pytest.skip("Integration test skipped - set INTEGRATION_TEST=true to run")
        
        try:

            env_vars = load_environment_variables()
            

            config = BotConfig()
            config.load_from_env()
            

            assert config.testnet is True, "Integration tests must use testnet"
            

            bot = BasicBot(config)
            

            test_symbol = 'BTCUSDT'
            test_quantity = '0.001'
            

            account_info = bot.get_account_info()
            assert 'balances' in account_info
            

            symbol_info = bot.get_symbol_info(test_symbol)
            assert symbol_info['symbol'] == test_symbol
            order = bot.place_market_order(test_symbol, 'BUY', test_quantity)
            

            assert 'orderId' in order
            assert order['symbol'] == test_symbol
            assert order['side'] == 'BUY'
            assert order['type'] == 'MARKET'
            

            order_status = bot.get_order_status(test_symbol, order['orderId'])
            assert order_status['orderId'] == order['orderId']
            

            if order_status['status'] == 'FILLED':
                executed_qty = order_status['executedQty']
                

                sell_order = bot.place_market_order(test_symbol, 'SELL', executed_qty)
                assert sell_order['side'] == 'SELL'
                
                print(f"Integration test completed successfully!")
                print(f"Buy order: {order['orderId']}, Sell order: {sell_order['orderId']}")
            
        except Exception as e:
            pytest.fail(f"Integration test failed: {e}")
    
    @pytest.mark.integration
    def test_testnet_limit_order_integration(self):
        if not os.getenv('INTEGRATION_TEST'):
            pytest.skip("Integration test skipped - set INTEGRATION_TEST=true to run")
        
        try:
            config = BotConfig()
            config.load_from_env()
            assert config.testnet is True
            
            bot = BasicBot(config)
            
            test_symbol = 'BTCUSDT'
            test_quantity = '0.001'
            

            ticker = bot.client.get_symbol_ticker(symbol=test_symbol)
            current_price = float(ticker['price'])
            

            limit_price = str(current_price * 0.8)
            
            order = bot.place_limit_order(
                test_symbol, 'BUY', test_quantity, limit_price
            )
            
            assert order['type'] == 'LIMIT'
            assert order['status'] == 'NEW'
            

            time.sleep(1)
            
            cancel_result = bot.cancel_order(test_symbol, order['orderId'])
            assert cancel_result['status'] == 'CANCELED'
            
            print(f"Limit order integration test completed successfully!")
            
        except Exception as e:
            pytest.fail(f"Limit order integration test failed: {e}")


class TestErrorHandling:
    
    def test_network_error_retry(self):
        call_count = 0
        
        @exponential_backoff(max_retries=2, base_delay=0.1)
        def network_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network error")
            return {"status": "success"}
        
        result = network_call()
        assert result["status"] == "success"
        assert call_count == 2
    
    def test_binance_api_error_no_retry(self):
        @exponential_backoff(max_retries=2, base_delay=0.1)
        def api_call():
            error = Exception("Insufficient balance")
            error.code = -2010
            raise error
        
        with pytest.raises(Exception) as excinfo:
            api_call()
        
        assert "Insufficient balance" in str(excinfo.value)
    
    def test_malformed_order_parameters(self):
        with pytest.raises(ValidationError):
            validate_order_parameters(
                symbol=None,
                side='BUY',
                order_type='LIMIT'
            )
        
        with pytest.raises(ValidationError):
            validate_order_parameters(
                symbol='BTCUSDT',
                side='INVALID_SIDE',
                order_type='LIMIT'
            )
    
    def test_precision_edge_cases(self):
        assert format_quantity(0.00000001, 8) == "0.00000001"
        

        assert format_quantity(0.999999, 2) == "0.99"
        

        assert format_price(50000.555, "0.01") == "50000.55"



pytestmark = pytest.mark.asyncio


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



def assert_order_params(params, expected_symbol, expected_side, expected_type):
    assert params['symbol'] == expected_symbol
    assert params['side'] == expected_side
    assert params['type'] == expected_type

def create_mock_order_response(order_id, symbol, side, order_type, status='NEW'):
    return {
        'orderId': order_id,
        'symbol': symbol,
        'side': side,
        'type': order_type,
        'status': status,
        'timeInForce': 'GTC',
        'origQty': '0.001',
        'executedQty': '0.000' if status == 'NEW' else '0.001',
        'price': '50000.00' if order_type != 'MARKET' else '0.00000000',
        'transactTime': int(time.time() * 1000)
    }


if __name__ == "__main__":
    pytest.main([__file__])