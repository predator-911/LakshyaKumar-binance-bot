import os
import logging
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any
from binance.client import Client
from binance.exceptions import BinanceAPIException
import json

class BinanceBot:
    def __init__(self, api_key: str = None, secret_key: str = None, testnet: bool = True):
        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet
        self.client = None
        self.simulated_mode = False
        
        # Setup logging
        self.setup_logging()
        
        # Initialize client if API keys are provided
        if api_key and secret_key:
            try:
                self.client = Client(api_key, secret_key, testnet=testnet)
                self.logger.info("Binance client initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize Binance client: {e}")
                self.simulated_mode = True
        else:
            self.logger.info("No API keys provided, running in simulated mode")
            self.simulated_mode = True
            
    def setup_logging(self):
        """Setup logging configuration"""
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler('bot.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        if self.simulated_mode:
            return self.get_simulated_price(symbol)
        
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except BinanceAPIException as e:
            self.logger.error(f"Error getting price for {symbol}: {e}")
            return self.get_simulated_price(symbol)
            
    def get_simulated_price(self, symbol: str) -> float:
        """Get simulated price from historical data"""
        try:
            df = pd.read_csv('data/historical_prices.csv')
            symbol_data = df[df['symbol'] == symbol]
            if not symbol_data.empty:
                return float(symbol_data.iloc[-1]['close'])
            else:
                # Default prices for common symbols
                default_prices = {
                    'BTCUSDT': 45000.0,
                    'ETHUSDT': 2500.0,
                    'ADAUSDT': 0.5,
                    'DOTUSDT': 7.0
                }
                return default_prices.get(symbol, 100.0)
        except Exception as e:
            self.logger.error(f"Error getting simulated price: {e}")
            return 100.0
            
    def validate_symbol(self, symbol: str) -> bool:
        """Validate if symbol exists"""
        if self.simulated_mode:
            valid_symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT']
            return symbol in valid_symbols
            
        try:
            self.client.futures_exchange_info()
            return True
        except:
            return False
            
    def log_order(self, order_type: str, symbol: str, side: str, quantity: float, 
                  price: float = None, status: str = "FILLED", order_id: str = None):
        """Log order details"""
        if not order_id:
            order_id = f"SIM_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
        order_log = {
            'timestamp': datetime.now().isoformat(),
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity,
            'price': price,
            'status': status,
            'mode': 'SIMULATED' if self.simulated_mode else 'LIVE'
        }
        
        self.logger.info(f"ORDER: {json.dumps(order_log)}")
        return order_log
        
    def get_fear_greed_index(self, date: str = None) -> int:
        """Get fear and greed index for a given date"""
        try:
            df = pd.read_csv('data/fear_greed.csv')
            if date:
                row = df[df['date'] == date]
                if not row.empty:
                    return int(row.iloc[0]['fear_greed_index'])
            return int(df.iloc[-1]['fear_greed_index'])  # Return latest
        except Exception as e:
            self.logger.error(f"Error getting fear greed index: {e}")
            return 50  # Neutral default
            
    def should_trade_based_on_sentiment(self, side: str, fear_greed_index: int = None) -> bool:
        """Determine if we should trade based on market sentiment"""
        if fear_greed_index is None:
            fear_greed_index = self.get_fear_greed_index()
            
        if side.upper() == 'BUY':
            # Only buy in extreme fear or fear (< 40)
            return fear_greed_index < 40
        elif side.upper() == 'SELL':
            # Only sell in greed or extreme greed (> 60)
            return fear_greed_index > 60
            
        return True  # Allow trade if no specific sentiment rule
        
    def format_price(self, price: float, symbol: str) -> float:
        """Format price according to symbol precision"""
        if 'BTC' in symbol:
            return round(price, 2)
        elif 'ETH' in symbol:
            return round(price, 2)
        else:
            return round(price, 4)
            
    def format_quantity(self, quantity: float, symbol: str) -> float:
        """Format quantity according to symbol precision"""
        if 'BTC' in symbol:
            return round(quantity, 3)
        elif 'ETH' in symbol:
            return round(quantity, 2)
        else:
            return round(quantity, 1)
