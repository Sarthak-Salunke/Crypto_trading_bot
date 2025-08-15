import argparse
import sys
import os
from typing import Optional, Dict, Any
from decimal import Decimal


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .basic_bot import BasicBot
from .orders import OrderManager
from .logger import get_logger
from .utils import load_environment_variables, validate_order_parameters

logger = get_logger('system')


class TradingBotCLI:
    def __init__(self):
        self.bot: Optional[BasicBot] = None
        
    def initialize_bot(self) -> bool:
        try:
            env_vars = load_environment_variables()
            api_key = env_vars.get('BINANCE_API_KEY')
            api_secret = env_vars.get('BINANCE_SECRET_KEY')
            
            if not api_key or not api_secret:
                logger.error("API credentials not found in environment variables")
                print("Error: Please set BINANCE_API_KEY and BINANCE_SECRET_KEY in your .env file")
                return False
                
            self.bot = BasicBot(api_key, api_secret)
            self.order_manager = OrderManager(self.bot)
            logger.info("Bot initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            print(f"Error initializing bot: {e}")
            return False


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='python -m bot.cli',
        description='Binance Futures Trading Bot CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m bot.cli account
  python -m bot.cli market --symbol BTCUSDT --side BUY --quantity 0.001
  python -m bot.cli limit --symbol BTCUSDT --side SELL --quantity 0.001 --price 45000
  python -m bot.cli stop-limit --symbol BTCUSDT --side BUY --quantity 0.001 --price 45000 --stop-price 46000
  python -m bot.cli cancel --symbol BTCUSDT --order-id 12345678
  python -m bot.cli interactive
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    

    account_parser = subparsers.add_parser(
        'account', 
        help='Show account balance and information'
    )
    
    balance_parser = subparsers.add_parser(
        'balance', 
        help='Show account balance and information (alias for account)'
    )
    

    market_parser = subparsers.add_parser(
        'market', 
        help='Place a market order'
    )
    market_parser.add_argument('--symbol', required=True, help='Trading symbol (e.g., BTCUSDT)')
    market_parser.add_argument('--side', required=True, choices=['BUY', 'SELL'], help='Order side')
    market_parser.add_argument('--quantity', required=True, type=float, help='Order quantity')
    

    limit_parser = subparsers.add_parser(
        'limit',
        help='Place a limit order'
    )
    limit_parser.add_argument('--symbol', required=True, help='Trading symbol (e.g., BTCUSDT)')
    limit_parser.add_argument('--side', required=True, choices=['BUY', 'SELL'], help='Order side')
    limit_parser.add_argument('--quantity', required=True, type=float, help='Order quantity')
    limit_parser.add_argument('--price', required=True, type=float, help='Order price')
    

    stop_limit_parser = subparsers.add_parser(
        'stop-limit',
        help='Place a stop-limit order'
    )
    stop_limit_parser.add_argument('--symbol', required=True, help='Trading symbol (e.g., BTCUSDT)')
    stop_limit_parser.add_argument('--side', required=True, choices=['BUY', 'SELL'], help='Order side')
    stop_limit_parser.add_argument('--quantity', required=True, type=float, help='Order quantity')
    stop_limit_parser.add_argument('--price', required=True, type=float, help='Limit price')
    stop_limit_parser.add_argument('--stop-price', required=True, type=float, help='Stop price')
    

    cancel_parser = subparsers.add_parser(
        'cancel',
        help='Cancel an existing order'
    )
    cancel_parser.add_argument('--symbol', required=True, help='Trading symbol (e.g., BTCUSDT)')
    cancel_parser.add_argument('--order-id', required=True, type=int, help='Order ID to cancel')
    

    interactive_parser = subparsers.add_parser(
        'interactive',
        help='Enter interactive mode'
    )
    
    return parser


def handle_account_command(cli: TradingBotCLI) -> None:
    """Handle account balance command."""
    try:
        balance = cli.bot.get_account_balance('USDT')
        print("\n=== Account Balance ===")
        print(f"USDT Available: {balance['available']}")
        print(f"USDT Total: {balance['total']}")
        print("=" * 23)
        
    except Exception as e:
        logger.error(f"Error checking account balance: {e}")
        print(f"Error: {e}")


def handle_market_command(cli: TradingBotCLI, args: argparse.Namespace) -> None:
    """Handle market order command."""
    try:
        params = {
            'symbol': args.symbol,
            'side': args.side,
            'quantity': args.quantity
        }
        
        try:
            params = validate_order_parameters(
                symbol=args.symbol,
                side=args.side,
                order_type='MARKET',
                quantity=args.quantity
            )
        except Exception as e:
            print(f"Error: Invalid order parameters - {e}")
            return
            
        result = cli.bot.place_market_order(args.symbol, args.side, args.quantity)
        if result:
            print(f"Market order placed successfully:")
            print(f"Symbol: {result.get('symbol')}")
            print(f"Order ID: {result.get('orderId')}")
            print(f"Status: {result.get('status')}")
        else:
            print("Failed to place market order")
            
    except Exception as e:
        logger.error(f"Error placing market order: {e}")
        print(f"Error: {e}")


def handle_limit_command(cli: TradingBotCLI, args: argparse.Namespace) -> None:
    """Handle limit order command with price validation."""
    try:
        from .price_validator import PriceValidator
        
        validator = PriceValidator(cli.bot)
        

        is_valid, error_msg = validator.validate_limit_price(
            args.symbol, 
            args.side, 
            Decimal(str(args.price))
        )
        
        if not is_valid:
            print(f"❌ Price validation failed: {error_msg}")
            

            try:
                suggested = validator.suggest_reasonable_price(
                    args.symbol, 
                    args.side, 
                    Decimal('0.1')
                )
                print(f"💡 Suggested price: {suggested}")
            except Exception as e:
                logger.warning(f"Could not suggest price: {e}")
            
            return
        

        try:
            params = validate_order_parameters(
                symbol=args.symbol,
                side=args.side,
                order_type='LIMIT',
                quantity=args.quantity,
                price=args.price
            )
        except Exception as e:
            print(f"❌ Invalid order parameters: {e}")
            return
            

        result = cli.bot.place_limit_order(args.symbol, args.side, args.quantity, args.price)
        if result:
            print(f"✅ Limit order placed successfully:")
            print(f"   Symbol: {result.get('symbol')}")
            print(f"   Order ID: {result.get('orderId')}")
            print(f"   Status: {result.get('status')}")
            print(f"   Price: {result.get('price')}")
            print(f"   Side: {result.get('side')}")
            print(f"   Quantity: {result.get('origQty')}")
        else:
            print("❌ Failed to place limit order")
            
    except Exception as e:
        logger.error(f"Error placing limit order: {e}")
        print(f"Error: {e}")


def handle_stop_limit_command(cli: TradingBotCLI, args: argparse.Namespace) -> None:
    """Handle stop-limit order command."""
    try:

        notional = args.quantity * args.price
        

        if notional < 100:
            print(f"❌ Order notional must be >= 100 USDT. Current: ${notional:.2f}")
            print(f"💡 Increase quantity or price to meet minimum requirement")
            

            min_quantity = 100 / args.price
            print(f"💡 Minimum quantity at ${args.price}: {min_quantity:.4f}")
            return
        
        params = {
            'symbol': args.symbol,
            'side': args.side,
            'quantity': args.quantity,
            'price': args.price,
            'stopPrice': args.stop_price
        }
        
        try:
            params = validate_order_parameters(
                symbol=args.symbol,
                side=args.side,
                order_type='STOP',
                quantity=args.quantity,
                price=args.price,
                stop_price=args.stop_price
            )
        except Exception as e:
            print(f"Error: Invalid order parameters - {e}")
            return
            
        result = cli.order_manager.place_stop_limit_order(
            args.symbol,
            args.side,
            args.quantity,
            args.price,
            args.stop_price
        )
        
        if result:
            print(f"✅ Stop-limit order placed successfully:")
            print(f"   Symbol: {result.get('symbol')}")
            print(f"   Order ID: {result.get('orderId')}")
            print(f"   Status: {result.get('status')}")
            print(f"   Price: {result.get('price')}")
            print(f"   Stop Price: {result.get('stopPrice')}")
            print(f"   Notional: ${notional:.2f}")
        else:
            print("❌ Failed to place stop-limit order")
            
    except Exception as e:
        logger.error(f"Error placing stop-limit order: {e}")
        print(f"Error: {e}")


def handle_cancel_command(cli: TradingBotCLI, args: argparse.Namespace) -> None:
    """Handle cancel order command."""
    try:
        result = cli.bot.client.futures_cancel_order(symbol=args.symbol, orderId=args.order_id)
        if result:
            print(f"Order cancelled successfully:")
            print(f"Symbol: {result.get('symbol')}")
            print(f"Order ID: {result.get('orderId')}")
            print(f"Status: {result.get('status')}")
        else:
            print("Failed to cancel order")
            
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        print(f"Error: {e}")


def interactive_mode(cli: TradingBotCLI) -> None:
    """Run the CLI in interactive mode."""
    print("\n=== Binance Futures Trading Bot - Interactive Mode ===")
    print("Type 'help' for available commands or 'quit' to exit")
    
    while True:
        try:
            user_input = input("\nbot> ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
                
            if user_input.lower() == 'help':
                print_interactive_help()
                continue
                

            args = user_input.split()
            if not args:
                continue
                
            command = args[0].lower()
            
            if command == 'account':
                handle_account_command(cli)
                
            elif command == 'market':
                if len(args) < 4:
                    print("Usage: market <symbol> <side> <quantity>")
                    continue

                mock_args = argparse.Namespace()
                mock_args.symbol = args[1]
                mock_args.side = args[2].upper()
                try:
                    mock_args.quantity = float(args[3])
                    handle_market_command(cli, mock_args)
                except ValueError:
                    print("Error: Invalid quantity")
                    
            elif command == 'limit':
                if len(args) < 5:
                    print("Usage: limit <symbol> <side> <quantity> <price>")
                    continue
                mock_args = argparse.Namespace()
                mock_args.symbol = args[1]
                mock_args.side = args[2].upper()
                try:
                    mock_args.quantity = float(args[3])
                    mock_args.price = float(args[4])
                    handle_limit_command(cli, mock_args)
                except ValueError:
                    print("Error: Invalid quantity or price")
                    
            elif command == 'cancel':
                if len(args) < 3:
                    print("Usage: cancel <symbol> <order_id>")
                    continue
                mock_args = argparse.Namespace()
                mock_args.symbol = args[1]
                try:
                    mock_args.order_id = int(args[2])
                    handle_cancel_command(cli, mock_args)
                except ValueError:
                    print("Error: Invalid order ID")
                    
            else:
                print(f"Unknown command: {command}")
                print("Type 'help' for available commands")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            logger.error(f"Error in interactive mode: {e}")
            print(f"Error: {e}")


def print_interactive_help() -> None:
    """Print help for interactive mode."""
    help_text = """
Available commands in interactive mode:

  account                           - Show account balance
  market <symbol> <side> <quantity> - Place market order
  limit <symbol> <side> <quantity> <price> - Place limit order
  cancel <symbol> <order_id>        - Cancel order
  help                             - Show this help
  quit/exit/q                      - Exit interactive mode

Examples:
  account
  market BTCUSDT BUY 0.001
  limit BTCUSDT SELL 0.001 45000
  cancel BTCUSDT 12345678
"""
    print(help_text)


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    

    if len(sys.argv) == 1:
        parser.print_help()
        return
        
    args = parser.parse_args()
    

    cli = TradingBotCLI()
    if not cli.initialize_bot():
        sys.exit(1)
    

    try:
        if args.command == 'account':
            handle_account_command(cli)
            
        elif args.command == 'market':
            handle_market_command(cli, args)
            
        elif args.command == 'limit':
            handle_limit_command(cli, args)
            
        elif args.command == 'stop-limit':
            handle_stop_limit_command(cli, args)
            
        elif args.command == 'cancel':
            handle_cancel_command(cli, args)
            
        elif args.command == 'interactive':
            interactive_mode(cli)
            
        else:
            print(f"Unknown command: {args.command}")
            parser.print_help()
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"CLI error: {e}")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
