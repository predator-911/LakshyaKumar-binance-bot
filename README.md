# Binance USDT-M Futures Trading Bot

A comprehensive CLI-based trading bot for Binance USDT-M Futures with advanced order types and risk management features.

## 🚀 Features

### Core Functionality
- **Market Orders**: Execute immediate buy/sell orders at current market price
- **Limit Orders**: Place orders at specific price levels with GTC (Good Till Cancelled) support
- **Stop-Limit Orders**: Advanced stop-loss and take-profit functionality
- **OCO Orders**: One-Cancels-Other orders for simultaneous take-profit and stop-loss
- **TWAP Orders**: Time-Weighted Average Price execution for large orders
- **Grid Trading**: Automated grid strategy for range-bound markets

### Advanced Features
- **Market Sentiment Integration**: Uses Fear & Greed Index for trade decisions
- **Simulation Mode**: Test strategies with historical data without real trading
- **Comprehensive Logging**: All orders and actions logged to `bot.log`
- **Risk Management**: Built-in validation and risk assessment
- **Colorized CLI**: User-friendly interface with colored output

## 📁 Project Structure

```
binance_bot/
│
├── src/
│   ├── utils.py              # Core bot utilities and Binance client wrapper
│   ├── market_orders.py      # Market order execution
│   ├── limit_orders.py       # Limit order placement
│   └── advanced/
│       ├── oco.py           # OCO (One-Cancels-Other) orders
│       ├── stop_limit.py    # Stop-limit order logic
│       ├── twap.py          # TWAP (Time-Weighted Average Price)
│       └── grid_strategy.py # Grid trading strategy
│
├── data/
│   ├── historical_prices.csv # Sample OHLC price data for simulation
│   └── fear_greed.csv        # Market sentiment index data
│
├── bot.log                   # Trading activity log (auto-generated)
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
└── README.md               # This file
```

## 🛠 Installation & Setup

### 1. Clone the Repository
```bash
git clone <https://github.com/predator-911/LakshyaKumar-binance-bot>
cd binance_bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your Binance API credentials
nano .env
```

### 4. Configure API Keys
Edit `.env` file with your Binance API credentials:
```env
BINANCE_API_KEY=your_api_key_here
BINANCE_SECRET_KEY=your_secret_key_here
TESTNET=True
```

**Important**: 
- Set `TESTNET=True` for testing on Binance Testnet
- Set `TESTNET=False` for live trading (use with caution!)
- If no API keys are provided, the bot runs in simulation mode

## 📈 Usage Examples

### Market Orders
```bash
# Buy 0.05 BTC at market price
python src/market_orders.py BTCUSDT BUY 0.05

# Sell 1.0 ETH with sentiment analysis
python src/market_orders.py ETHUSDT SELL 1.0 --sentiment
```

### Limit Orders
```bash
# Buy 0.1 BTC at $44,000
python src/limit_orders.py BTCUSDT BUY 0.1 44000

# Sell 2.0 ETH at $2,600 with sentiment check
python src/limit_orders.py ETHUSDT SELL 2.0 2600 --sentiment
```

### Advanced Orders

#### Stop-Limit Orders
```bash
# Stop-loss: Sell 0.05 BTC if price drops to $43,000, limit at $42,800
python src/advanced/stop_limit.py BTCUSDT SELL 0.05 43000 42800

# Stop-buy: Buy 0.1 BTC if price rises to $46,000, limit at $46,200
python src/advanced/stop_limit.py BTCUSDT BUY 0.1 46000 46200
```

#### OCO Orders
```bash
# OCO: Take profit at $47,000, stop loss at $43,000 (limit $42,800)
python src/advanced/oco.py BTCUSDT SELL 0.05 47000 43000 42800
```

#### TWAP Orders
```bash
# Execute 0.3 BTC buy over 30 minutes in 6 orders
python src/advanced/twap.py BTCUSDT BUY 0.3 --duration 30 --orders 6

# TWAP with simulation mode
python src/advanced/twap.py BTCUSDT BUY 0.5 --simulate --sentiment
```

#### Grid Trading Strategy
```bash
# Grid strategy: $10,000 investment, ±8% range, 7 grid levels
python src/advanced/grid_strategy.py BTCUSDT 10000 --range-pct 8.0 --grids 7

# Grid with simulation and sentiment analysis
python src/advanced/grid_strategy.py ETHUSDT 5000 --simulate --sentiment
```

## 🎯 Order Types Explained

### 1. Market Orders
- Execute immediately at current market price
- Best for quick entry/exit
- No price guarantee but guaranteed execution

### 2. Limit Orders
- Execute only at specified price or better
- Good for precise entry/exit points
- May not execute if price doesn't reach limit

### 3. Stop-Limit Orders
- Triggers a limit order when stop price is reached
- Combines stop-loss protection with price control
- Useful for risk management

### 4. OCO (One-Cancels-Other)
- Places two orders simultaneously
- When one executes, the other is cancelled
- Perfect for take-profit + stop-loss scenarios

### 5. TWAP (Time-Weighted Average Price)
- Splits large orders into smaller chunks over time
- Reduces market impact
- Better average price for large positions

### 6. Grid Trading
- Places multiple buy/sell orders in a price range
- Profits from price oscillations
- Best for sideways/ranging markets

## 📊 Market Sentiment Integration

The bot integrates a Fear & Greed Index for enhanced decision making:

- **Extreme Fear (0-25)**: Optimal buying opportunities
- **Fear (25-45)**: Good for buying, caution on selling
- **Neutral (45-55)**: Normal trading conditions
- **Greed (55-75)**: Good for selling, caution on buying
- **Extreme Greed (75-100)**: Optimal selling opportunities

Enable sentiment analysis with the `--sentiment` flag:
```bash
python src/market_orders.py BTCUSDT BUY 0.1 --sentiment
```

## 🔍 Simulation Mode

Test strategies risk-free using historical data:

### Automatic Simulation
- Runs automatically if no API keys are provided
- Uses data from `data/historical_prices.csv`
- All logs saved to `bot.log` with "SIMULATED" marker

### Manual Simulation
```bash
# Force simulation mode
python src/advanced/twap.py BTCUSDT BUY 0.5 --simulate
python src/advanced/grid_strategy.py BTCUSDT 10000 --simulate
```

## 📝 Logging & Monitoring

All trading activity is logged to `bot.log`:

```json
{
  "timestamp": "2024-01-15T10:30:45",
  "order_id": "12345678",
  "symbol": "BTCUSDT",
  "side": "BUY",
  "type": "MARKET",
  "quantity": 0.05,
  "price": 45000.0,
  "status": "FILLED",
  "mode": "LIVE"
}
```

## ⚠️ Risk Management

### Built-in Safety Features
- Input validation for all parameters
- Price range validation for stop orders
- Quantity and price formatting per symbol
- Sentiment-based trade filtering
- Simulation mode for testing

### Best Practices
1. **Start Small**: Begin with small amounts to test strategies
2. **Use Testnet**: Always test on Binance Testnet first
3. **Set Stop Losses**: Use stop-limit orders for risk management
4. **Monitor Positions**: Regularly check open orders and positions
5. **Diversify**: Don't put all capital in one strategy
6. **Keep Records**: Review `bot.log` regularly for performance analysis

## 🔧 Configuration Options

### Environment Variables (.env)
```env
# API Configuration
BINANCE_API_KEY=your_api_key
BINANCE_SECRET_KEY=your_secret_key
TESTNET=True

# Bot Settings
LOG_LEVEL=INFO
MAX_RETRY_ATTEMPTS=3

# Trading Parameters
DEFAULT_LEVERAGE=1
RISK_PERCENTAGE=2
MIN_ORDER_SIZE=0.001
```

### Command Line Options
Most scripts support these common options:
- `--sentiment`: Enable sentiment-based filtering
- `--simulate`: Force simulation mode
- `--help`: Show detailed help for each command

## 🐛 Troubleshooting

### Common Issues

#### 1. API Connection Errors
```bash
# Check API credentials in .env
# Verify IP whitelisting on Binance
# Ensure testnet setting matches your keys
```

#### 2. Invalid Symbol Errors
```bash
# Use correct symbol format: BTCUSDT, ETHUSDT
# Check if symbol exists on Binance Futures
```

#### 3. Insufficient Balance
```bash
# Check account balance
# Reduce order quantity
# Use simulation mode for testing
```

#### 4. Price Precision Errors
```bash
# Bot automatically formats prices per symbol
# Check Binance symbol info for requirements
```

### Debug Mode
Enable detailed logging:
```bash
export LOG_LEVEL=DEBUG
python src/market_orders.py BTCUSDT BUY 0.01
```

## 🔄 Development

### Adding New Strategies
1. Create new file in `src/advanced/`
2. Import `BinanceBot` from `src.utils`
3. Follow existing patterns for CLI and logging
4. Add comprehensive error handling
5. Include simulation mode support

### Testing
```bash
# Test all order types in simulation
python src/market_orders.py BTCUSDT BUY 0.01 --simulate
python src/limit_orders.py BTCUSDT BUY 0.01 40000 --simulate
python src/advanced/twap.py BTCUSDT BUY 0.1 --simulate
```

## 📜 License

This project is for educational purposes. Use at your own risk. The authors are not responsible for any financial losses.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📞 Support

For issues and questions:
1. Check the troubleshooting section
2. Review `bot.log` for error details
3. Ensure you're using the latest version
4. Test in simulation mode first

---

**⚠️ DISCLAIMER**: Cryptocurrency trading involves substantial risk of loss. This bot is provided for educational purposes only. Always test thoroughly in simulation mode before using real funds. The developers assume no responsibility for trading losses.
