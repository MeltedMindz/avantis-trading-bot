"""
Basic Trading Example for Avantis

This example demonstrates how to use the Avantis Trading Bot
for basic trading operations.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the trading bot components
from src.trading_bot import AvantisTradingBot
from src.strategies import DCAStrategy, MomentumStrategy
from src.logger import logger


async def basic_trading_example():
    """Basic trading example"""
    logger.info("🚀 Starting Basic Trading Example")
    
    # Create and initialize the trading bot
    bot = AvantisTradingBot()
    
    if not await bot.initialize():
        logger.error("Failed to initialize trading bot")
        return
    
    # Configure strategies
    dca_config = {
        'enabled': True,
        'pairs': ['ETH/USD'],
        'leverage': 5,
        'position_size': 10.0,
        'interval_minutes': 60,
        'direction': 'long'
    }
    
    momentum_config = {
        'enabled': True,
        'pairs': ['ETH/USD'],
        'leverage': 10,
        'position_size': 15.0,
        'rsi_period': 14,
        'min_signal_strength': 0.7
    }
    
    # Add strategies to bot
    bot.strategies['dca'] = DCAStrategy(dca_config)
    bot.strategies['momentum'] = MomentumStrategy(momentum_config)
    
    logger.info("✅ Bot initialized with strategies")
    
    # Run for a short period (in real usage, you'd run indefinitely)
    logger.info("📊 Running bot for 5 minutes...")
    await asyncio.sleep(300)  # Run for 5 minutes
    
    # Stop the bot
    await bot.stop()
    logger.info("🛑 Bot stopped")


async def manual_trade_example():
    """Example of manual trade execution"""
    logger.info("📈 Manual Trade Example")
    
    bot = AvantisTradingBot()
    
    if not await bot.initialize():
        logger.error("Failed to initialize trading bot")
        return
    
    # Get market data for ETH/USD
    market_data = await bot.avantis_client.get_market_data("ETH/USD")
    if market_data:
        logger.info(f"ETH/USD Market Data: {market_data}")
    
    # Calculate price impact for a potential trade
    price_impact = await bot.avantis_client.calculate_price_impact(
        "ETH/USD", 
        position_size=1000, 
        is_long=True
    )
    
    if price_impact:
        logger.info(f"Price Impact: {price_impact}")
    
    # Get trading parameters
    trading_params = await bot.avantis_client.get_trading_parameters("ETH/USD")
    if trading_params:
        logger.info(f"Trading Parameters: {trading_params}")


if __name__ == "__main__":
    # Check if private key is set
    if not os.getenv("PRIVATE_KEY"):
        print("❌ Please set PRIVATE_KEY in your environment variables")
        print("   Example: export PRIVATE_KEY='0x...'")
        sys.exit(1)
    
    # Run the example
    asyncio.run(basic_trading_example())
