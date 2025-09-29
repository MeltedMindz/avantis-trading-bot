# Avantis Trading Bot

A comprehensive trading bot for the Avantis decentralized exchange, built with their official SDK.

## 🚀 Features

- **📦 Complete SDK Integration**: Includes the official [Avantis Trader SDK](https://github.com/Avantis-Labs/avantis_trader_sdk) as a submodule - no separate installation needed!
- **🎯 10% Daily Returns Mode**: Aggressive compound growth system designed for consistent daily profits
- **Multiple Trading Strategies**: DCA, Momentum, Mean Reversion, Grid Trading, Breakout
- **Advanced Risk Management**: Position sizing, drawdown limits, leverage control
- **Real-time Price Feeds**: WebSocket integration with Pyth Network
- **Comprehensive Logging**: Rich console output with performance metrics
- **CLI Interface**: Command-line management with live dashboard
- **Backtesting**: Historical strategy testing capabilities
- **Compound Growth Tracking**: Automatic reinvestment and compound growth calculation
- **One-Command Setup**: Automated setup script for easy installation

## 📋 Requirements

- Python 3.8+
- Private key for your Ethereum wallet
- USDC balance for trading

## 🛠️ Installation

1. **Clone the repository with submodules:**
   ```bash
   git clone --recurse-submodules https://github.com/MeltedMindz/avantis-trading-bot.git
   cd avantis-trading-bot
   ```

2. **Run the setup script:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

   **OR manually:**
   ```bash
   # Initialize SDK submodule
   git submodule update --init --recursive
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Set up configuration
   cp config.env.example .env
   cp config_aggressive.env.example config_aggressive.env
   ```

3. **Configure your settings:**
   ```bash
   # Edit .env with your private key
   nano .env
   
   # Edit aggressive trading settings
   nano config_aggressive.env
   ```

## ⚙️ Configuration

Create a `.env` file with the following variables:

```env
# Required
PRIVATE_KEY=0x your_private_key_here

# Optional (defaults provided)
PROVIDER_URL=https://mainnet.base.org
WS_URL=wss://hermes.pyth.network/ws
DEFAULT_LEVERAGE=10
MAX_POSITION_SIZE=100.0
```

## 🎯 Quick Start

### 🚀 Aggressive 10% Daily Returns Mode

**NEW!** The bot now includes an aggressive mode designed to achieve 10% daily returns through compound growth:

```bash
# Start aggressive trading bot
python run_aggressive_bot.py

# Start with custom capital
python run_aggressive_bot.py --capital 5000

# Test mode (no actual trades)
python run_aggressive_bot.py --dry-run

# Show compound growth projections
python run_aggressive_bot.py --projections

# Check daily status
python run_aggressive_bot.py --status
```

### Basic Usage

```python
import asyncio
import os
from src.avantis_client import AvantisClient
from src.models import Trade, TradeDirection, OrderType

async def main():
    # Set your private key
    os.environ["PRIVATE_KEY"] = "0x your_private_key_here"
    
    # Initialize client
    client = AvantisClient()
    await client.initialize()
    
    # Create a trade
    trade = Trade(
        pair="ETH/USD",
        direction=TradeDirection.LONG,
        entry_price=2000.0,
        size=100.0,
        leverage=10.0,
        take_profit=2500.0,
        stop_loss=1800.0
    )
    
    # Open the trade
    success = await client.open_trade(trade)
    if success:
        print("Trade opened successfully!")
    
    # Get open trades
    trades = await client.get_open_trades()
    print(f"Open trades: {len(trades)}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Using Trading Strategies

```python
from src.strategies.momentum_strategy import MomentumStrategy

async def run_strategy():
    strategy = MomentumStrategy()
    await strategy.initialize()
    
    # Get market data
    market_data = {
        'ETH/USD': {
            'price': 2000.0,
            'rsi': 45.0,
            'macd': 0.5,
            'volume': 1000000
        }
    }
    
    # Analyze and get trading signals
    signals = await strategy.analyze(market_data)
    print(f"Trading signals: {signals}")

asyncio.run(run_strategy())
```

## 📊 Available Trading Pairs

The bot supports all pairs available on Avantis, including:

- **Crypto**: ETH/USD, BTC/USD, SOL/USD, AVAX/USD, MATIC/USD
- **Forex**: EUR/USD, GBP/USD, JPY/USD
- **Commodities**: GOLD/USD, SILVER/USD, OIL/USD
- **And many more...**

## 🎛️ Trading Strategies

### 1. Momentum Strategy
- Uses RSI, MACD, and moving averages
- Identifies trend continuation opportunities
- Configurable parameters for sensitivity

### 2. Mean Reversion Strategy
- Bollinger Bands and Z-score analysis
- Identifies oversold/overbought conditions
- Suitable for range-bound markets

### 3. Grid Trading Strategy
- Places buy/sell orders at predetermined levels
- Profits from price oscillations
- Risk management through position sizing

### 4. DCA (Dollar Cost Averaging)
- Regular interval trading
- Reduces impact of market volatility
- Configurable intervals and amounts

### 5. Breakout Strategy
- Identifies support/resistance breakouts
- Volume confirmation
- Dynamic stop-loss management

## 🛡️ Risk Management

- **Position Sizing**: Automatic calculation based on account balance
- **Leverage Control**: Configurable maximum leverage limits (up to 50x in aggressive mode)
- **Stop Loss**: Automatic stop-loss placement (1.5% in aggressive mode)
- **Daily Loss Limits**: Prevents excessive daily losses (5% safety net)
- **Drawdown Protection**: Pauses trading during high drawdown
- **Quick Profit Taking**: Takes profits at 3% to compound gains

## 🎯 Compound Growth System

### 10% Daily Returns Mode

The bot includes an advanced compound growth system designed to achieve consistent 10% daily returns:

#### **Key Features:**
- **Daily Target Tracking**: Monitors progress toward 10% daily profit target
- **Compound Growth Calculator**: Projects exponential growth over time
- **Dynamic Position Sizing**: Adjusts position sizes based on daily progress
- **Risk-Adjusted Leverage**: Increases leverage when behind target, reduces when ahead
- **Trading Phases**: Different strategies for different times of day

#### **Projected Growth:**
- **30 days**: ~17x return (1,700%)
- **90 days**: ~5,000x return (500,000%)
- **1 year**: ~13,000,000x return (1.3 billion %)

#### **Trading Phases:**
1. **Morning Aggressive (6-10 AM)**: High leverage, high frequency
2. **Midday Balanced (10 AM-2 PM)**: Moderate risk approach
3. **Afternoon Momentum (2-6 PM)**: Momentum following strategies
4. **Evening Consolidation (6-10 PM)**: Profit taking and consolidation
5. **Night Defensive (10 PM-6 AM)**: Low risk, defensive positions

#### **Risk Controls:**
- Maximum 50x leverage
- 1.5% stop loss
- 3% profit taking
- 5% daily loss limit
- Automatic trading pause after 3 consecutive losses

## 📈 Monitoring & Logging

The bot provides comprehensive logging:

- **Trade Events**: Open, close, modify trades
- **Performance Metrics**: PnL, win rate, Sharpe ratio
- **Risk Alerts**: Drawdown warnings, position limits
- **System Status**: Connection health, error tracking

## 🔧 CLI Interface

```bash
# Start the trading bot
python main.py --strategy momentum --pair ETH/USD

# View live dashboard
python src/cli.py dashboard

# Run backtesting
python src/cli.py backtest --strategy momentum --start-date 2024-01-01

# Check open positions
python src/cli.py positions
```

## 🧪 Testing

Run the test suite:

```bash
# Test SDK integration
python test_sdk_only.py

# Test all components
python final_test.py
```

## 📚 Examples

Check the `examples/` directory for:

- `basic_trading.py` - Simple trade execution
- `backtesting_example.py` - Strategy backtesting
- `integrated_trading_bot.py` - Full bot integration

## ⚠️ Important Notes

1. **Private Keys**: Never commit your private key to version control
2. **Testnet First**: Test with small amounts before using significant capital
3. **Rate Limits**: The bot respects Avantis rate limits
4. **Network Fees**: Consider gas costs for transactions
5. **Market Risk**: Trading involves risk of loss

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Links

- [Avantis Documentation](https://docs.avantisfi.com/)
- [Avantis SDK Documentation](https://sdk.avantisfi.com/)
- [Avantis Discord](https://discord.gg/avantis)

## 🆘 Support

For support and questions:

1. Check the documentation
2. Review the examples
3. Open an issue on GitHub
4. Join the Avantis Discord

---

**Disclaimer**: This software is for educational purposes. Trading cryptocurrencies involves substantial risk of loss. Use at your own risk.
