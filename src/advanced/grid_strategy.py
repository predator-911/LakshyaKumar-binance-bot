#!/usr/bin/env python3

import sys
import os
import click
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from colorama import init, Fore, Style

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils import BinanceBot

# Initialize colorama for colored output
init(autoreset=True)

# Load environment variables
load_dotenv()

def execute_grid_strategy(symbol: str, total_investment: float, price_range_pct: float, 
                         num_grids: int, simulate: bool = False, use_sentiment: bool = False):
    """Execute a grid trading strategy"""
    
    # Initialize bot
    api_key = os.getenv('BINANCE_API_KEY')
    secret_key = os.getenv('BINANCE_SECRET_KEY')
    testnet = os.getenv('TESTNET', 'True').lower() == 'true'
    
    bot = BinanceBot(api_key, secret_key, testnet)
    
    # Force simulation if requested or no API keys
    if simulate or bot.simulated_mode:
        bot.simulated_mode = True
        print(f"{Fore.YELLOW}Running in SIMULATION mode")
    
    # Validate inputs
    if not bot.validate_symbol(symbol):
        print(f"{Fore.RED}Error: Invalid symbol {symbol}")
        return False
        
    if total_investment <= 0:
        print(f"{Fore.RED}Error: Total investment must be positive")
        return False
        
    if price_range_pct <= 0 or price_range_pct > 50:
        print(f"{Fore.RED}Error: Price range percentage must be between 0 and 50")
        return False
        
    if num_grids < 2:
        print(f"{Fore.RED}Error: Number of grids must be at least 2")
        return False
    
    # Check sentiment if requested
    if use_sentiment:
        fear_greed = bot.get_fear_greed_index()
        if fear_greed > 70:
            print(f"{Fore.YELLOW}Grid strategy not recommended in extreme greed (Fear & Greed Index: {fear_greed})")
            if not click.confirm("Continue anyway?"):
                return False
        else:
            print(f"{Fore.GREEN}Market sentiment suitable for grid trading (Fear & Greed Index: {fear_greed})")
    
    # Get current price
    current_price = bot.get_current_price(symbol)
    print(f"{Fore.CYAN}Current price for {symbol}: ${current_price:,.2f}")
    
    # Calculate grid parameters
    price_range = current_price * (price_range_pct / 100)
    upper_price = current_price + (price_range / 2)
    lower_price = current_price - (price_range / 2)
    price_step = price_range / (num_grids - 1)
    
    # Calculate investment per grid
    investment_per_grid = total_investment / num_grids
    
    print(f"\n{Fore.CYAN}=== GRID STRATEGY PARAMETERS ===")
    print(f"Total Investment: ${total_investment:,.2f}")
    print(f"Current Price: ${current_price:,.2f}")
    print(f"Price Range: ±{price_range_pct}% (${price_range:,.2f})")
    print(f"Upper Bound: ${upper_price:,.2f}")
    print(f"Lower Bound: ${lower_price:,.2f}")
    print(f"Number of Grids: {num_grids}")
    print(f"Price Step: ${price_step:,.2f}")
    print(f"Investment per Grid: ${investment_per_grid:,.2f}")
    print("-" * 40)
    
    # Generate grid levels
    grid_levels = []
    for i in range(num_grids):
        grid_price = lower_price + (i * price_step)
        quantity = investment_per_grid / grid_price
        
        # Determine order type based on price relative to current
        if grid_price < current_price:
            order_side = 'BUY'
            order_type = 'LIMIT'
        elif grid_price > current_price:
            order_side = 'SELL'
            order_type = 'LIMIT'
        else:
            order_side = 'BUY'  # Default to buy at current price
            order_type = 'MARKET'
        
        grid_levels.append({
            'level': i + 1,
            'price': bot.format_price(grid_price, symbol),
            'quantity': bot.format_quantity(quantity, symbol),
            'side': order_side,
            'type': order_type,
            'investment': investment_per_grid,
            'status': 'PENDING'
        })
    
    # Display grid plan
    print(f"\n{Fore.BLUE}=== GRID TRADING PLAN ===")
    print("Level | Price      | Quantity   | Side | Type   | Investment")
    print("-" * 60)
    for grid in grid_levels:
        print(f"{grid['level']:5d} | ${grid['price']:9.2f} | {grid['quantity']:10.6f} | "
              f"{grid['side']:4s} | {grid['type']:6s} | ${grid['investment']:8.2f}")
    
    if not click.confirm(f"\nProceed with placing {len(grid_levels)} grid orders?"):
        print(f"{Fore.YELLOW}Grid strategy cancelled by user")
        return False
    
    # Execute grid orders
    placed_orders = []
    total_placed_value = 0
    
    print(f"\n{Fore.GREEN}=== EXECUTING GRID ORDERS ===")
    
    for grid in grid_levels:
        try:
            print(f"\nPlacing Grid Level {grid['level']}: {grid['side']} {grid['quantity']} @ ${grid['price']}")
            
            if bot.simulated_mode:
                # Simulate order placement
                order_result = {
                    'orderId': f'GRID_SIM_{grid["level"]}_{symbol}_{grid["side"]}',
                    'symbol': symbol,
                    'side': grid['side'],
                    'type': grid['type'],
                    'origQty': str(grid['quantity']),
                    'price': str(grid['price']),
                    'status': 'NEW' if grid['type'] == 'LIMIT' else 'FILLED'
                }
                print(f"{Fore.YELLOW}SIMULATED: Order placed")
            else:
                # Place real order
                if grid['type'] == 'MARKET':
                    order_result = bot.client.futures_create_order(
                        symbol=symbol,
                        side=grid['side'],
                        type='MARKET',
                        quantity=grid['quantity']
                    )
                else:  # LIMIT
                    order_result = bot.client.futures_create_order(
                        symbol=symbol,
                        side=grid['side'],
                        type='LIMIT',
                        quantity=grid['quantity'],
                        price=grid['price'],
                        timeInForce='GTC'
                    )
                print(f"{Fore.GREEN}✓ Order placed successfully")
            
            # Log the order
            bot.log_order(
                order_type=f'GRID_{grid["type"]}',
                symbol=symbol,
                side=grid['side'],
                quantity=grid['quantity'],
                price=grid['price'],
                order_id=order_result.get('orderId')
            )
            
            # Update grid status
            grid['status'] = order_result.get('status', 'UNKNOWN')
            grid['order_id'] = order_result.get('orderId')
            
            placed_orders.append({
                'level': grid['level'],
                'order_id': order_result.get('orderId'),
                'side': grid['side'],
                'price': grid['price'],
                'quantity': grid['quantity'],
                'status': grid['status']
            })
            
            total_placed_value += grid['investment']
            
        except Exception as e:
            print(f"{Fore.RED}✗ Error placing grid level {grid['level']}: {e}")
            bot.logger.error(f"Grid order error (level {grid['level']}): {e}")
            grid['status'] = 'FAILED'
            continue
    
    # Summary
    successful_orders = len([o for o in placed_orders if o['status'] not in ['FAILED', 'REJECTED']])
    success_rate = (successful_orders / len(grid_levels)) * 100
    
    print(f"\n{Fore.GREEN}=== GRID STRATEGY SUMMARY ===")
    print(f"Total Grids Planned: {len(grid_levels)}")
    print(f"Orders Placed Successfully: {successful_orders}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Total Value Committed: ${total_placed_value:,.2f}")
    
    # Risk analysis
    max_drawdown_pct = (current_price - lower_price) / current_price * 100
    max_profit_pct = (upper_price - current_price) / current_price * 100
    
    print(f"\n--- RISK ANALYSIS ---")
    print(f"Maximum Potential Drawdown: {max_drawdown_pct:.2f}%")
    print(f"Maximum Potential Profit: {max_profit_pct:.2f}%")
    print(f"Grid Density: {num_grids} levels in ±{price_range_pct}% range")
    
    # Show active orders
    if placed_orders:
        print(f"\n--- ACTIVE ORDERS ---")
        buy_orders = [o for o in placed_orders if o['side'] == 'BUY']
        sell_orders = [o for o in placed_orders if o['side'] == 'SELL']
        
        print(f"Buy Orders (Support): {len(buy_orders)}")
        for order in buy_orders:
            print(f"  Level {order['level']}: {order['quantity']} @ ${order['price']} [{order['status']}]")
            
        print(f"Sell Orders (Resistance): {len(sell_orders)}")
        for order in sell_orders:
            print(f"  Level {order['level']}: {order['quantity']} @ ${order['price']} [{order['status']}]")
    
    # Strategy tips
    print(f"\n{Fore.CYAN}--- GRID STRATEGY TIPS ---")
    print("• Monitor orders regularly and adjust if market moves outside range")
    print("• Consider taking profits if price oscillates within the grid")
    print("• Be prepared to add more capital if price breaks below the grid")
    print("• Grid trading works best in sideways/ranging markets")
    
    return successful_orders > 0

@click.command()
@click.argument('symbol')
@click.argument('investment', type=float)
@click.option('--range-pct', '-r', default=10.0, help='Price range percentage (default: 10%)')
@click.option('--grids', '-g', default=5, help='Number of grid levels (default: 5)')
@click.option('--simulate', is_flag=True, help='Run in simulation mode')
@click.option('--sentiment', is_flag=True, help='Use fear & greed index for strategy validation')
def main(symbol, investment, range_pct, grids, simulate, sentiment):
    """
    Execute a Grid Trading Strategy on Binance Futures
    
    SYMBOL: Trading pair (e.g., BTCUSDT)
    INVESTMENT: Total amount to invest in USD
    """
    print(f"{Fore.BLUE}=== Binance Futures Grid Trading Bot ===")
    print(f"Symbol: {symbol}")
    print(f"Total Investment: ${investment:,.2f}")
    print(f"Price Range: ±{range_pct}%")
    print(f"Grid Levels: {grids}")
    print(f"Simulation Mode: {'Enabled' if simulate else 'Disabled'}")
    print(f"Sentiment Analysis: {'Enabled' if sentiment else 'Disabled'}")
    print("-" * 40)
    
    success = execute_grid_strategy(symbol.upper(), investment, range_pct, 
                                  grids, simulate, sentiment)
    
    if success:
        print(f"\n{Fore.GREEN}Grid strategy setup completed!")
    else:
        print(f"\n{Fore.RED}Grid strategy setup failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
