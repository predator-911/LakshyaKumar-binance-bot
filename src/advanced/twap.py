#!/usr/bin/env python3

import sys
import os
import time
import click
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from colorama import init, Fore, Style

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils import BinanceBot

# Initialize colorama for colored output
init(autoreset=True)

# Load environment variables
load_dotenv()

def execute_twap_order(symbol: str, side: str, total_quantity: float, duration_minutes: int, 
                      num_orders: int = 5, simulate: bool = False, use_sentiment: bool = False):
    """Execute a TWAP (Time Weighted Average Price) order"""
    
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
        
    if side.upper() not in ['BUY', 'SELL']:
        print(f"{Fore.RED}Error: Side must be BUY or SELL")
        return False
        
    if total_quantity <= 0:
        print(f"{Fore.RED}Error: Total quantity must be positive")
        return False
        
    if duration_minutes <= 0:
        print(f"{Fore.RED}Error: Duration must be positive")
        return False
        
    if num_orders <= 0:
        print(f"{Fore.RED}Error: Number of orders must be positive")
        return False
    
    # Check sentiment if requested
    if use_sentiment:
        fear_greed = bot.get_fear_greed_index()
        if not bot.should_trade_based_on_sentiment(side, fear_greed):
            print(f"{Fore.YELLOW}TWAP execution rejected due to market sentiment (Fear & Greed Index: {fear_greed})")
            return False
        else:
            print(f"{Fore.GREEN}Sentiment check passed (Fear & Greed Index: {fear_greed})")
    
    # Calculate TWAP parameters
    quantity_per_order = total_quantity / num_orders
    interval_seconds = (duration_minutes * 60) / num_orders
    
    print(f"\n{Fore.CYAN}=== TWAP EXECUTION PLAN ===")
    print(f"Total Quantity: {total_quantity}")
    print(f"Number of Orders: {num_orders}")
    print(f"Quantity per Order: {quantity_per_order:.6f}")
    print(f"Duration: {duration_minutes} minutes")
    print(f"Interval: {interval_seconds:.1f} seconds")
    print(f"Side: {side.upper()}")
    print("-" * 40)
    
    # Track execution statistics
    executed_orders = []
    total_executed_qty = 0
    total_cost = 0
    start_time = datetime.now()
    
    # Load historical data for simulation
    if bot.simulated_mode:
        try:
            df = pd.read_csv('data/historical_prices.csv')
            symbol_data = df[df['symbol'] == symbol].copy()
            if symbol_data.empty:
                print(f"{Fore.YELLOW}No historical data for {symbol}, using default prices")
                # Create dummy data
                base_price = 45000.0 if 'BTC' in symbol else 2500.0
                symbol_data = pd.DataFrame({
                    'timestamp': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')] * 10,
                    'close': [base_price + i * 10 for i in range(10)]
                })
            else:
                symbol_data['timestamp'] = pd.to_datetime(symbol_data['timestamp'])
        except Exception as e:
            print(f"{Fore.YELLOW}Error loading historical data: {e}")
            symbol_data = pd.DataFrame()
    
    # Execute orders
    for i in range(num_orders):
        try:
            order_start_time = datetime.now()
            
            # Get current price
            if bot.simulated_mode and not symbol_data.empty:
                # Use historical data with some variation
                idx = min(i, len(symbol_data) - 1)
                current_price = float(symbol_data.iloc[idx]['close'])
                # Add some realistic price movement
                import random
                price_variation = random.uniform(-0.002, 0.002)  # ±0.2% variation
                current_price *= (1 + price_variation)
            else:
                current_price = bot.get_current_price(symbol)
            
            # Format quantity
            order_quantity = bot.format_quantity(quantity_per_order, symbol)
            
            print(f"\n{Fore.BLUE}Executing Order {i+1}/{num_orders}")
            print(f"Time: {order_start_time.strftime('%H:%M:%S')}")
            print(f"Price: ${current_price:,.2f}")
            print(f"Quantity: {order_quantity}")
            
            if bot.simulated_mode:
                # Simulate order execution
                order_result = {
                    'orderId': f'TWAP_SIM_{i+1}_{symbol}_{side}_{order_quantity}',
                    'symbol': symbol,
                    'side': side,
                    'type': 'MARKET',
                    'origQty': str(order_quantity),
                    'executedQty': str(order_quantity),
                    'price': str(current_price),
                    'status': 'FILLED',
                    'transactTime': int(order_start_time.timestamp() * 1000)
                }
                execution_time = 0.1  # Simulate fast execution
            else:
                # Place real market order
                order_result = bot.client.futures_create_order(
                    symbol=symbol,
                    side=side,
                    type='MARKET',
                    quantity=order_quantity
                )
                execution_time = (datetime.now() - order_start_time).total_seconds()
            
            # Log the order
            bot.log_order(
                order_type='TWAP_MARKET',
                symbol=symbol,
                side=side,
                quantity=order_quantity,
                price=current_price,
                order_id=order_result.get('orderId')
            )
            
            # Update statistics
            executed_qty = float(order_result.get('executedQty', order_quantity))
            order_cost = executed_qty * current_price
            
            executed_orders.append({
                'order_num': i + 1,
                'time': order_start_time,
                'price': current_price,
                'quantity': executed_qty,
                'cost': order_cost,
                'execution_time': execution_time
            })
            
            total_executed_qty += executed_qty
            total_cost += order_cost
            
            print(f"{Fore.GREEN}✓ Order {i+1} filled at ${current_price:,.2f}")
            print(f"Execution time: {execution_time:.2f}s")
            
            # Wait for next interval (except for last order)
            if i < num_orders - 1:
                print(f"{Fore.YELLOW}Waiting {interval_seconds:.1f}s for next order...")
                if not bot.simulated_mode:
                    time.sleep(interval_seconds)
                else:
                    # Simulate time passage
                    time.sleep(0.1)  # Brief pause for simulation
                    
        except Exception as e:
            print(f"{Fore.RED}Error executing order {i+1}: {e}")
            bot.logger.error(f"TWAP order {i+1} error: {e}")
            continue
    
    # Calculate final statistics
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    
    if total_executed_qty > 0:
        avg_price = total_cost / total_executed_qty
        completion_rate = (total_executed_qty / total_quantity) * 100
        
        print(f"\n{Fore.GREEN}=== TWAP EXECUTION SUMMARY ===")
        print(f"Total Duration: {total_duration:.1f} seconds")
        print(f"Orders Executed: {len(executed_orders)}/{num_orders}")
        print(f"Total Quantity Executed: {total_executed_qty:.6f}")
        print(f"Completion Rate: {completion_rate:.1f}%")
        print(f"Average Execution Price: ${avg_price:,.2f}")
        print(f"Total Value: ${total_cost:,.2f}")
        
        # Price analysis
        if executed_orders:
            prices = [order['price'] for order in executed_orders]
            min_price = min(prices)
            max_price = max(prices)
            price_range = max_price - min_price
            price_std = pd.Series(prices).std()
            
            print(f"\n--- PRICE ANALYSIS ---")
            print(f"Price Range: ${min_price:,.2f} - ${max_price:,.2f}")
            print(f"Price Spread: ${price_range:,.2f} ({(price_range/avg_price)*100:.2f}%)")
            print(f"Price Volatility (Std Dev): ${price_std:.2f}")
            
        # Create execution report
        df_orders = pd.DataFrame(executed_orders)
        if not df_orders.empty:
            print(f"\n--- ORDER DETAILS ---")
            for _, order in df_orders.iterrows():
                print(f"Order {order['order_num']}: {order['quantity']:.6f} @ ${order['price']:,.2f} "
                      f"(${order['cost']:,.2f}) - {order['time'].strftime('%H:%M:%S')}")
        
        return True
    else:
        print(f"\n{Fore.RED}No orders were executed successfully")
        return False

@click.command()
@click.argument('symbol')
@click.argument('side')
@click.argument('quantity', type=float)
@click.option('--duration', '-d', default=60, help='Duration in minutes (default: 60)')
@click.option('--orders', '-n', default=5, help='Number of sub-orders (default: 5)')
@click.option('--simulate', is_flag=True, help='Run in simulation mode using historical data')
@click.option('--sentiment', is_flag=True, help='Use fear & greed index for trade decision')
def main(symbol, side, quantity, duration, orders, simulate, sentiment):
    """
    Execute a TWAP (Time Weighted Average Price) order on Binance Futures
    
    SYMBOL: Trading pair (e.g., BTCUSDT)
    SIDE: BUY or SELL
    QUANTITY: Total amount to trade
    """
    print(f"{Fore.BLUE}=== Binance Futures TWAP Order Bot ===")
    print(f"Symbol: {symbol}")
    print(f"Side: {side.upper()}")
    print(f"Total Quantity: {quantity}")
    print(f"Duration: {duration} minutes")
    print(f"Number of Orders: {orders}")
    print(f"Simulation Mode: {'Enabled' if simulate else 'Disabled'}")
    print(f"Sentiment Analysis: {'Enabled' if sentiment else 'Disabled'}")
    print("-" * 40)
    
    success = execute_twap_order(symbol.upper(), side.upper(), quantity, 
                               duration, orders, simulate, sentiment)
    
    if success:
        print(f"\n{Fore.GREEN}TWAP order execution completed!")
    else:
        print(f"\n{Fore.RED}TWAP order execution failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
