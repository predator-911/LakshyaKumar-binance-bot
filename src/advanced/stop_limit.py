#!/usr/bin/env python3

import sys
import os
import click
from dotenv import load_dotenv
from colorama import init, Fore, Style

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils import BinanceBot

# Initialize colorama for colored output
init(autoreset=True)

# Load environment variables
load_dotenv()

def place_stop_limit_order(symbol: str, side: str, quantity: float, stop_price: float, 
                          limit_price: float, use_sentiment: bool = False):
    """Place a stop-limit order"""
    
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
        
    if stop_price <= 0 or limit_price <= 0:
        print(f"{Fore.RED}Error: Stop price and limit price must be positive")
        return False
        
    # Check sentiment if requested
    if use_sentiment:
        fear_greed = bot.get_fear_greed_index()
        if not bot.should_trade_based_on_sentiment(side, fear_greed):
            print(f"{Fore.YELLOW}Trade rejected due to market sentiment (Fear & Greed Index: {fear_greed})")
            return False
        else:
            print(f"{Fore.GREEN}Sentiment check passed (Fear & Greed Index: {fear_greed})")
    
    # Get current price for validation
    current_price = bot.get_current_price(symbol)
    print(f"{Fore.CYAN}Current market price: ${current_price:,.2f}")
    
    # Validate stop-limit logic
    if side.upper() == 'BUY':
        if stop_price <= current_price:
            print(f"{Fore.RED}Error: Buy stop price (${stop_price:,.2f}) must be above current price")
            return False
        if limit_price < stop_price:
            print(f"{Fore.YELLOW}Warning: Limit price (${limit_price:,.2f}) is below stop price")
            print(f"{Fore.YELLOW}This may result in immediate execution or no execution")
    else:  # SELL
        if stop_price >= current_price:
            print(f"{Fore.RED}Error: Sell stop price (${stop_price:,.2f}) must be below current price")
            return False
        if limit_price > stop_price:
            print(f"{Fore.YELLOW}Warning: Limit price (${limit_price:,.2f}) is above stop price")
            print(f"{Fore.YELLOW}This may result in immediate execution or no execution")
    
    # Format values
    quantity = bot.format_quantity(quantity, symbol)
    stop_price = bot.format_price(stop_price, symbol)
    limit_price = bot.format_price(limit_price, symbol)
    
    try:
        if bot.simulated_mode:
            # Simulate the order
            order_result = {
                'orderId': f'SIM_STOP_LIMIT_{symbol}_{side}_{quantity}_{stop_price}_{limit_price}',
                'symbol': symbol,
                'side': side,
                'type': 'STOP_MARKET',
                'origQty': str(quantity),
                'stopPrice': str(stop_price),
                'price': str(limit_price),
                'status': 'NEW'
            }
            print(f"{Fore.YELLOW}SIMULATED MODE - Stop-limit order would be placed")
        else:
            # Place real order
            order_result = bot.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='STOP',
                quantity=quantity,
                price=limit_price,
                stopPrice=stop_price,
                timeInForce='GTC'
            )
            print(f"{Fore.GREEN}Stop-limit order placed successfully")
            
        # Log the order
        bot.log_order(
            order_type='STOP_LIMIT',
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=limit_price,
            status=order_result.get('status', 'NEW'),
            order_id=order_result.get('orderId')
        )
        
        # Display order summary
        total_value = quantity * limit_price
        stop_diff = stop_price - current_price
        stop_diff_pct = (stop_diff / current_price) * 100
        limit_diff = limit_price - current_price
        limit_diff_pct = (limit_diff / current_price) * 100
        
        print(f"\n{Fore.GREEN}=== STOP-LIMIT ORDER SUMMARY ===")
        print(f"Order ID: {order_result.get('orderId')}")
        print(f"Symbol: {symbol}")
        print(f"Side: {side}")
        print(f"Type: STOP-LIMIT")
        print(f"Quantity: {quantity}")
        print(f"Stop Price: ${stop_price:,.2f} ({stop_diff_pct:+.2f}% from current)")
        print(f"Limit Price: ${limit_price:,.2f} ({limit_diff_pct:+.2f}% from current)")
        print(f"Current Price: ${current_price:,.2f}")
        print(f"Estimated Value: ${total_value:,.2f}")
        print(f"Status: {order_result.get('status', 'UNKNOWN')}")
        print(f"Time in Force: GTC (Good Till Cancelled)")
        
        # Risk assessment
        risk_pct = abs(stop_diff_pct)
        if risk_pct < 2:
            risk_level = "Low"
        elif risk_pct < 5:
            risk_level = "Medium"
        else:
            risk_level = "High"
            
        print(f"Risk Level: {risk_level} ({risk_pct:.2f}% from current price)")
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}Error placing stop-limit order: {e}")
        bot.logger.error(f"Stop-limit order error: {e}")
        return False

@click.command()
@click.argument('symbol')
@click.argument('side')
@click.argument('quantity', type=float)
@click.argument('stop_price', type=float)
@click.argument('limit_price', type=float)
@click.option('--sentiment', is_flag=True, help='Use fear & greed index for trade decision')
def main(symbol, side, quantity, stop_price, limit_price, sentiment):
    """
    Place a stop-limit order on Binance Futures
    
    SYMBOL: Trading pair (e.g., BTCUSDT)
    SIDE: BUY or SELL
    QUANTITY: Amount to trade
    STOP_PRICE: Price that triggers the limit order
    LIMIT_PRICE: Limit price for execution after trigger
    """
    print(f"{Fore.BLUE}=== Binance Futures Stop-Limit Order Bot ===")
    print(f"Symbol: {symbol}")
    print(f"Side: {side.upper()}")
    print(f"Quantity: {quantity}")
    print(f"Stop Price: ${stop_price:,.2f}")
    print(f"Limit Price: ${limit_price:,.2f}")
    print(f"Sentiment Analysis: {'Enabled' if sentiment else 'Disabled'}")
    print("-" * 40)
    
    success = place_stop_limit_order(symbol.upper(), side.upper(), quantity, 
                                   stop_price, limit_price, sentiment)
    
    if success:
        print(f"\n{Fore.GREEN}Stop-limit order placed successfully!")
    else:
        print(f"\n{Fore.RED}Stop-limit order failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
