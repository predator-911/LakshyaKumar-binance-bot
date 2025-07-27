"""
Binance USDT-M Futures Trading Bot

A comprehensive CLI-based trading bot for Binance USDT-M Futures with advanced 
order types and risk management features.

Author: Lakshya Kumar
Version: 1.0
"""

__version__ = "1.0.0"
__author__ = "LakshyaKumar"
__email__ = "pushpalakshay2003@gmail.com"

# Import main components for easy access
from .utils import BinanceBot

__all__ = ['BinanceBot']
