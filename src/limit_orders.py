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

def place_limit_order(symbol: str, side: str, quantity: float, price: float, use_sentiment: bool = False):
    """Place a limit order"""
    
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
        
    if price <= 0:
        print(f"{Fore.RED}Error: Price must be positive")
        return False
        
    # Check sentiment if requested
    if use_sentiment:
        fear_greed = bot.get_fear_greed_index()
        if not bot.should_trade_based_on_sentiment(side, fear_greed):
            print(f"{Fore.YELLOW}Trade rejected due to market sentiment (Fear & Greed Index: {fear_greed})")
            return False
        else:
            print(f"{Fore.GREEN}Sentiment check passed (Fear & Greed Index: {fear_greed})")
    
    # Get current price for comparison
    current_price = bot.get_current_price(symbol)
    print(f"{Fore.CYAN}Current market price: ${current_price:,.2f}")
    
    # Validate limit price logic
    if side.upper() == 'BUY' and price >= current_price:
        print(f"{Fore.YELLOW}Warning: Buy limit price (${price:,.2f}) is at or above market price")
        print(f"{Fore.YELLOW}This will execute immediately as a market order")
    elif side.upper() == 'SELL' and price <= current_price:
        print(f"{Fore.YELLOW}Warning: Sell limit price (${price:,.2f}) is at or below market price")
        print(f"{Fore.YELLOW}This will execute immediately as a market order")
    
    # Format values
    quantity = bot.format_quantity(quantity, symbol)
    price = bot.format_price(price, symbol)
    
    try:
        if bot.simulated_mode:
            # Simulate the order
            order_result = {
                'orderId': f'SIM_LIMIT_{symbol}_{side}_{quantity}_{price}',
                'symbol': symbol,
                'side': side,
                'type': 'LIMIT',
                'origQty': str(quantity),
                'price': str(price),
                'status': 'NEW'
            }
            print(f"{Fore.YELLOW}SIMULATED MODE - Limit order would be placed")
        else:
            # Place real order
            order_result = bot.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='LIMIT',
                quantity=quantity,
                price=price,
                timeInForce='GTC'  # Good Till Cancelled
            )
            print(f"{Fore.GREEN}Limit order placed successfully")
            
        # Log the order
        bot.log_order(
            order_type='LIMIT',
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            status=order_result.get('status', 'NEW'),
            order_id=order_result.get('orderId')
        )
        
        # Display order summary
        total_value = quantity * price
        price_diff = price - current_price
        price_diff_pct = (price_diff / current_price) * 100
        
        print(f"\n{Fore.GREEN}=== LIMIT ORDER SUMMARY ===")
        print(f"Order ID: {order_result.get('orderId')}")
        print(f"Symbol: {symbol}")
        print(f"Side: {side}")
        print(f"Type: LIMIT")
        print(f"Quantity: {quantity}")
        print(f"Limit Price: ${price:,.2f}")
        print(f"Current Price: ${current_price:,.2f}")
        print(f"Price Difference: ${price_diff:+.2f} ({price_diff_pct:+.2f}%)")
        print(f"Total Value: ${total_value:,.2f}")
        print(f"Status: {order_result.get('status', 'UNKNOWN')}")
        print(f"Time in Force: GTC (Good Till Cancelled)")
        
        # Execution probability estimate
        if side.upper() == 'BUY':
            if price < current_price * 0.95:
                prob = "High"
            elif price < current_price * 0.98:
                prob = "Medium"
            else:
                prob = "Low"
        else:  # SELL
            if price > current_price * 1.05:
                prob = "High"
            elif price > current_price * 1.02:
                prob = "Medium"
            else:
                prob = "Low"
                
        print(f"Execution Probability: {prob}")
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}Error placing limit order: {e}")
        bot.logger.error(f"Limit order error: {e}")
        return False

@click.command()
@click.argument('symbol')
@click.argument('side')
@click.argument('quantity', type=float)
@click.argument('price', type=float)
@click.option('--sentiment', is_flag=True, help='Use fear & greed index for trade decision')
def main(symbol, side, quantity, price, sentiment):
    """
    Place a limit order on Binance Futures
    
    SYMBOL: Trading pair (e.g., BTCUSDT)
    SIDE: BUY or SELL
    QUANTITY: Amount to trade
    PRICE: Limit price for the order
    """
    print(f"{Fore.BLUE}=== Binance Futures Limit Order Bot ===")
    print(f"Symbol: {symbol}")
    print(f"Side: {side.upper()}")
    print(f"Quantity: {quantity}")
    print(f"Limit Price: ${price:,.2f}")
    print(f"Sentiment Analysis: {'Enabled' if sentiment else 'Disabled'}")
    print("-" * 40)
    
    success = place_limit_order(symbol.upper(), side.upper(), quantity, price, sentiment)
    
    if success:
        print(f"\n{Fore.GREEN}Limit order placed successfully!")
    else:
        print(f"\n{Fore.RED}Limit order failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
