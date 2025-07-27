#!/usr/bin/env python3

import sys
import os
import click
from dotenv import load_dotenv
from colorama import init, Fore, Style

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils import BinanceBot

# Initialize colorama for colored output
init(autoreset=True)

# Load environment variables
load_dotenv()

def place_market_order(symbol: str, side: str, quantity: float, use_sentiment: bool = False):
    """Place a market order"""
    
    # Initialize bot
    api_key = os.getenv('BINANCE_API_KEY')
    secret_key = os.getenv('BINANCE_SECRET_KEY')
    testnet = os.getenv('TESTNET', 'True').lower() == 'true'
    
    bot = BinanceBot(api_key, secret_key, testnet)
    
    # Validate inputs
    if not bot.validate_symbol(symbol):
        print(f"{Fore.RED}Error: Invalid symbol {symbol}")
        return False
        
    if side.upper() not in ['BUY', 'SELL']:
        print(f"{Fore.RED}Error: Side must be BUY or SELL")
        return False
        
    if quantity <= 0:
        print(f"{Fore.RED}Error: Quantity must be positive")
        return False
        
    # Check sentiment if requested
    if use_sentiment:
        fear_greed = bot.get_fear_greed_index()
        if not bot.should_trade_based_on_sentiment(side, fear_greed):
            print(f"{Fore.YELLOW}Trade rejected due to market sentiment (Fear & Greed Index: {fear_greed})")
            return False
        else:
            print(f"{Fore.GREEN}Sentiment check passed (Fear & Greed Index: {fear_greed})")
    
    # Get current price
    current_price = bot.get_current_price(symbol)
    print(f"{Fore.CYAN}Current price for {symbol}: ${current_price:,.2f}")
    
    # Format values
    quantity = bot.format_quantity(quantity, symbol)
    
    try:
        if bot.simulated_mode:
            # Simulate the order
            order_result = {
                'orderId': f'SIM_{symbol}_{side}_{quantity}',
                'symbol': symbol,
                'side': side,
                'type': 'MARKET',
                'origQty': str(quantity),
                'price': str(current_price),
                'status': 'FILLED'
            }
            print(f"{Fore.YELLOW}SIMULATED MODE - Order would be placed")
        else:
            # Place real order
            order_result = bot.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            print(f"{Fore.GREEN}Order placed successfully")
            
        # Log the order
        bot.log_order(
            order_type='MARKET',
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=current_price,
            order_id=order_result.get('orderId')
        )
        
        # Display order summary
        total_value = quantity * current_price
        print(f"\n{Fore.GREEN}=== ORDER SUMMARY ===")
        print(f"Order ID: {order_result.get('orderId')}")
        print(f"Symbol: {symbol}")
        print(f"Side: {side}")
        print(f"Type: MARKET")
        print(f"Quantity: {quantity}")
        print(f"Price: ${current_price:,.2f}")
        print(f"Total Value: ${total_value:,.2f}")
        print(f"Status: {order_result.get('status', 'UNKNOWN')}")
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}Error placing order: {e}")
        bot.logger.error(f"Market order error: {e}")
        return False

@click.command()
@click.argument('symbol')
@click.argument('side')
@click.argument('quantity', type=float)
@click.option('--sentiment', is_flag=True, help='Use fear & greed index for trade decision')
def main(symbol, side, quantity, sentiment):
    """
    Place a market order on Binance Futures
    
    SYMBOL: Trading pair (e.g., BTCUSDT)
    SIDE: BUY or SELL
    QUANTITY: Amount to trade
    """
    print(f"{Fore.BLUE}=== Binance Futures Market Order Bot ===")
    print(f"Symbol: {symbol}")
    print(f"Side: {side.upper()}")
    print(f"Quantity: {quantity}")
    print(f"Sentiment Analysis: {'Enabled' if sentiment else 'Disabled'}")
    print("-" * 40)
    
    success = place_market_order(symbol.upper(), side.upper(), quantity, sentiment)
    
    if success:
        print(f"\n{Fore.GREEN}Market order completed successfully!")
    else:
        print(f"\n{Fore.RED}Market order failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
