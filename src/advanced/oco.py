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

def place_oco_order(symbol: str, side: str, quantity: float, price: float, 
                   stop_price: float, stop_limit_price: float, use_sentiment: bool = False):
    """Place an OCO (One-Cancels-Other) order"""
    
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
        
    if price <= 0 or stop_price <= 0 or stop_limit_price <= 0:
        print(f"{Fore.RED}Error: All prices must be positive")
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
    
    # Validate OCO logic based on side
    if side.upper() == 'SELL':
        # For SELL OCO: price > current_price (take profit) and stop_price < current_price (stop loss)
        if price <= current_price:
            print(f"{Fore.RED}Error: Take-profit price (${price:,.2f}) must be above current price for SELL")
            return False
        if stop_price >= current_price:
            print(f"{Fore.RED}Error: Stop price (${stop_price:,.2f}) must be below current price for SELL")
            return False
        if stop_limit_price > stop_price:
            print(f"{Fore.YELLOW}Warning: Stop-limit price (${stop_limit_price:,.2f}) is above stop price")
    else:  # BUY
        # For BUY OCO: price < current_price (take profit) and stop_price > current_price (stop loss)
        if price >= current_price:
            print(f"{Fore.RED}Error: Take-profit price (${price:,.2f}) must be below current price for BUY")
            return False
        if stop_price <= current_price:
            print(f"{Fore.RED}Error: Stop price (${stop_price:,.2f}) must be above current price for BUY")
            return False
        if stop_limit_price < stop_price:
            print(f"{Fore.YELLOW}Warning: Stop-limit price (${stop_limit_price:,.2f}) is below stop price")
    
    # Format values
    quantity = bot.format_quantity(quantity, symbol)
    price = bot.format_price(price, symbol)
    stop_price = bot.format_price(stop_price, symbol)
    stop_limit_price = bot.format_price(stop_limit_price, symbol)
    
    try:
        if bot.simulated_mode:
            # Simulate the OCO order
            order_result = {
                'orderListId': f'SIM_OCO_{symbol}_{side}_{quantity}',
                'symbol': symbol,
                'side': side,
                'orders': [
                    {
                        'orderId': f'SIM_OCO_LIMIT_{symbol}_{side}_{quantity}',
                        'type': 'LIMIT_MAKER',
                        'price': str(price),
                        'origQty': str(quantity)
                    },
                    {
                        'orderId': f'SIM_OCO_STOP_{symbol}_{side}_{quantity}',
                        'type': 'STOP_LOSS_LIMIT',
                        'stopPrice': str(stop_price),
                        'price': str(stop_limit_price),
                        'origQty': str(quantity)
                    }
                ],
                'status': 'EXECUTING'
            }
            print(f"{Fore.YELLOW}SIMULATED MODE - OCO order would be placed")
        else:
            # Place real OCO order
            # Note: Binance Futures may not support OCO orders directly
            # In that case, we simulate by placing two separate orders
            print(f"{Fore.YELLOW}Note: Placing two separate orders to simulate OCO behavior")
            
            # Place limit order (take profit)
            limit_order = bot.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='LIMIT',
                quantity=quantity,
                price=price,
                timeInForce='GTC'
            )
            
            # Place stop-limit order (stop loss)
            stop_order = bot.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='STOP',
                quantity=quantity,
                price=stop_limit_price,
                stopPrice=stop_price,
                timeInForce='GTC'
            )
            
            order_result = {
                'orderListId': f'MANUAL_OCO_{limit_order["orderId"]}_{stop_order["orderId"]}',
                'symbol': symbol,
                'side': side,
                'orders': [limit_order, stop_order],
                'status': 'EXECUTING'
            }
            
            print(f"{Fore.GREEN}OCO-style orders placed successfully")
            
        # Log both orders
        bot.log_order(
            order_type='OCO_LIMIT',
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            order_id=order_result['orders'][0].get('orderId') if 'orders' in order_result else order_result.get('orderListId')
        )
        
        bot.log_order(
            order_type='OCO_STOP',
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=stop_limit_price,
            order_id=order_result['orders'][1].get('orderId') if 'orders' in order_result else f"{order_result.get('orderListId')}_STOP"
        )
        
        # Display order summary
        limit_value = quantity * price
        stop_value = quantity * stop_limit_price
        
        # Calculate profit/loss potential
        if side.upper() == 'SELL':
            profit_pct = ((price - current_price) / current_price) * 100
            loss_pct = ((stop_limit_price - current_price) / current_price) * 100
        else:  # BUY
            profit_pct = ((current_price - price) / current_price) * 100
            loss_pct = ((current_price - stop_limit_price) / current_price) * 100
        
        print(f"\n{Fore.GREEN}=== OCO ORDER SUMMARY ===")
        print(f"Order List ID: {order_result.get('orderListId')}")
        print(f"Symbol: {symbol}")
        print(f"Side: {side}")
        print(f"Quantity: {quantity}")
        print(f"Current Price: ${current_price:,.2f}")
        print(f"\n--- TAKE PROFIT ORDER ---")
        print(f"Type: LIMIT")
        print(f"Price: ${price:,.2f}")
        print(f"Value: ${limit_value:,.2f}")
        print(f"Potential Profit: {profit_pct:.2f}%")
        print(f"\n--- STOP LOSS ORDER ---")
        print(f"Type: STOP-LIMIT")
        print(f"Stop Price: ${stop_price:,.2f}")
        print(f"Limit Price: ${stop_limit_price:,.2f}")
        print(f"Value: ${stop_value:,.2f}")
        print(f"Potential Loss: {loss_pct:.2f}%")
        print(f"\nRisk/Reward Ratio: 1:{abs(profit_pct/loss_pct):.2f}")
        print(f"Status: {order_result.get('status', 'UNKNOWN')}")
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}Error placing OCO order: {e}")
        bot.logger.error(f"OCO order error: {e}")
        return False

@click.command()
@click.argument('symbol')
@click.argument('side')
@click.argument('quantity', type=float)
@click.argument('price', type=float)
@click.argument('stop_price', type=float)
@click.argument('stop_limit_price', type=float)
@click.option('--sentiment', is_flag=True, help='Use fear & greed index for trade decision')
def main(symbol, side, quantity, price, stop_price, stop_limit_price, sentiment):
    """
    Place an OCO (One-Cancels-Other) order on Binance Futures
    
    SYMBOL: Trading pair (e.g., BTCUSDT)
    SIDE: BUY or SELL
    QUANTITY: Amount to trade
    PRICE: Take-profit limit price
    STOP_PRICE: Stop-loss trigger price
    STOP_LIMIT_PRICE: Stop-loss limit price
    """
    print(f"{Fore.BLUE}=== Binance Futures OCO Order Bot ===")
    print(f"Symbol: {symbol}")
    print(f"Side: {side.upper()}")
    print(f"Quantity: {quantity}")
    print(f"Take-Profit Price: ${price:,.2f}")
    print(f"Stop Price: ${stop_price:,.2f}")
    print(f"Stop-Limit Price: ${stop_limit_price:,.2f}")
    print(f"Sentiment Analysis: {'Enabled' if sentiment else 'Disabled'}")
    print("-" * 40)
    
    success = place_oco_order(symbol.upper(), side.upper(), quantity, 
                             price, stop_price, stop_limit_price, sentiment)
    
    if success:
        print(f"\n{Fore.GREEN}OCO order placed successfully!")
    else:
        print(f"\n{Fore.RED}OCO order failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
