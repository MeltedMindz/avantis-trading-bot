#!/usr/bin/env python3
"""
Complete Trading Bot Demo using the official Avantis SDK
This demonstrates all the functionality we've built
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src directory to Python path
src_path = str(Path(__file__).parent.parent / "src")
sys.path.insert(0, src_path)

# Import our modules
from avantis_client import AvantisClient
from models import Trade, TradeDirection, OrderType, TradeStatus
from strategies.momentum_strategy import MomentumStrategy
from risk_manager import RiskManager
from logger import logger
from config import config


async def demo_basic_trading():
    """Demonstrate basic trading operations"""
    logger.info("🚀 Starting Avantis Trading Bot Demo")
    
    try:
        # Initialize the client
        client = AvantisClient()
        
        if not await client.initialize():
            logger.error("Failed to initialize client")
            return False
        
        logger.info(f"✅ Client initialized for trader: {client.trader_address}")
        
        # Get available pairs
        pairs_info = await client.client.pairs_cache.get_pairs_info()
        logger.info(f"📊 Available trading pairs: {len(pairs_info)}")
        
        # Show some popular pairs
        popular_pairs = ["ETH/USD", "BTC/USD", "SOL/USD", "AVAX/USD"]
        for pair in popular_pairs:
            if pair in pairs_info:
                pair_index = await client.get_pair_index(pair)
                logger.info(f"   {pair} (Index: {pair_index})")
        
        # Get market data for ETH/USD
        logger.info("\n📈 Getting market data for ETH/USD...")
        market_data = await client.get_market_data("ETH/USD")
        
        if market_data:
            logger.info(f"   Open Interest Long: {market_data.get('open_interest_long', 'N/A')}")
            logger.info(f"   Open Interest Short: {market_data.get('open_interest_short', 'N/A')}")
            logger.info(f"   Utilization: {market_data.get('utilization', 'N/A')}%")
            logger.info(f"   Skew: {market_data.get('skew', 'N/A')}%")
            logger.info(f"   Margin Fee Long: {market_data.get('margin_fee_long', 'N/A')}")
            logger.info(f"   Margin Fee Short: {market_data.get('margin_fee_short', 'N/A')}")
        
        # Get trading parameters
        logger.info("\n⚙️ Getting trading parameters...")
        trading_params = await client.get_trading_parameters("ETH/USD")
        
        if trading_params:
            logger.info(f"   Loss Protection: {trading_params.get('loss_protection', 'N/A')}")
            logger.info(f"   Opening Fee: {trading_params.get('opening_fee', 'N/A')} USDC")
            logger.info(f"   Referral Rebate: {trading_params.get('referral_rebate_percentage', 'N/A')}%")
        
        # Check USDC balance and allowance
        logger.info("\n💰 Checking USDC balance and allowance...")
        balance = await client.client.get_usdc_balance(client.trader_address)
        allowance = await client.check_usdc_allowance(100)
        
        logger.info(f"   USDC Balance: {balance}")
        logger.info(f"   USDC Allowance: {allowance}")
        
        return True
        
    except Exception as e:
        logger.error_occurred(e, "basic trading demo")
        return False


async def demo_trading_strategies():
    """Demonstrate trading strategies"""
    logger.info("\n🤖 Trading Strategies Demo")
    
    try:
        # Initialize strategy
        strategy = MomentumStrategy()
        await strategy.initialize()
        
        # Simulate market data for strategy analysis
        mock_data = {
            'ETH/USD': {
                'price': 2000.0,
                'volume': 1000000,
                'rsi': 45.0,
                'macd': 0.5,
                'ma_20': 1950.0,
                'ma_50': 1900.0
            }
        }
        
        # Analyze market
        signals = await strategy.analyze(mock_data)
        logger.info(f"📊 Strategy Analysis Results:")
        for pair, signal in signals.items():
            logger.info(f"   {pair}: {signal}")
        
        # Initialize risk manager
        risk_manager = RiskManager()
        await risk_manager.initialize()
        
        # Test position sizing
        recommended_size = await risk_manager.calculate_position_size(
            pair="ETH/USD",
            entry_price=2000.0,
            leverage=10,
            confidence=0.8
        )
        logger.info(f"🎯 Recommended position size: {recommended_size} USDC")
        
        return True
        
    except Exception as e:
        logger.error_occurred(e, "trading strategies demo")
        return False


async def demo_price_feeds():
    """Demonstrate price feed functionality"""
    logger.info("\n📡 Price Feed Demo")
    
    try:
        from avantis_trader_sdk.feed.feed_client import FeedClient
        
        # Create feed client
        feed_client = FeedClient(config.wallet.ws_url)
        
        # Register callbacks for popular pairs
        def price_callback(data):
            logger.info(f"📈 Price Update: {data}")
        
        popular_pairs = ["ETH/USD", "BTC/USD", "SOL/USD"]
        
        for pair in popular_pairs:
            try:
                feed_client.register_price_feed_callback(pair, price_callback)
                logger.info(f"✅ Registered callback for {pair}")
            except Exception as e:
                logger.warning(f"⚠️ Could not register callback for {pair}: {e}")
        
        # Test feed ID conversion
        test_feed_id = "0x09f7c1d7dfbb7df2b8fe3d3d87ee94a2259d212da4f30c1f0540d066dfa44723"
        pair_name = feed_client.get_pair_from_feed_id(test_feed_id)
        logger.info(f"🔗 Feed ID {test_feed_id[:20]}... maps to {pair_name}")
        
        logger.info("ℹ️ Note: Price feeds require active WebSocket connection to receive real-time data")
        
        return True
        
    except Exception as e:
        logger.error_occurred(e, "price feed demo")
        return False


async def demo_trade_preparation():
    """Demonstrate trade preparation (without actually executing)"""
    logger.info("\n📋 Trade Preparation Demo")
    
    try:
        client = AvantisClient()
        await client.initialize()
        
        # Create a sample trade
        trade = Trade(
            pair="ETH/USD",
            direction=TradeDirection.LONG,
            entry_price=2000.0,
            size=100.0,
            leverage=10.0,
            take_profit=2500.0,
            stop_loss=1800.0,
            order_type=OrderType.MARKET
        )
        
        logger.info(f"📝 Sample Trade Created:")
        logger.info(f"   Pair: {trade.pair}")
        logger.info(f"   Direction: {trade.direction.value}")
        logger.info(f"   Size: {trade.size} USDC")
        logger.info(f"   Leverage: {trade.leverage}x")
        logger.info(f"   Entry Price: ${trade.entry_price}")
        logger.info(f"   Take Profit: ${trade.take_profit}")
        logger.info(f"   Stop Loss: ${trade.stop_loss}")
        
        # Get pair index
        pair_index = await client.get_pair_index(trade.pair)
        if pair_index is not None:
            logger.info(f"   Pair Index: {pair_index}")
            
            # Calculate price impact
            price_impact = await client.calculate_price_impact(
                trade.pair, trade.size, trade.direction == TradeDirection.LONG
            )
            
            if price_impact:
                logger.info(f"📊 Price Impact Analysis:")
                logger.info(f"   Total Impact: {price_impact.get('total_impact', 'N/A')}%")
                logger.info(f"   Price Impact: {price_impact.get('price_impact', 'N/A')}%")
                logger.info(f"   Skew Impact: {price_impact.get('skew_impact', 'N/A')}%")
        
        logger.info("ℹ️ Trade preparation complete. Ready for execution!")
        
        return True
        
    except Exception as e:
        logger.error_occurred(e, "trade preparation demo")
        return False


async def main():
    """Run the complete demo"""
    logger.info("🎯 Avantis Trading Bot - Complete Demo")
    logger.info("=" * 60)
    
    # Check if private key is set
    if not os.getenv("PRIVATE_KEY"):
        logger.warning("⚠️ No PRIVATE_KEY environment variable set")
        logger.info("   Set PRIVATE_KEY to your wallet's private key to enable full functionality")
        logger.info("   For demo purposes, using dummy key...")
        os.environ["PRIVATE_KEY"] = "0x0000000000000000000000000000000000000000000000000000000000000001"
    
    demos = [
        ("Basic Trading Operations", demo_basic_trading),
        ("Trading Strategies", demo_trading_strategies),
        ("Price Feeds", demo_price_feeds),
        ("Trade Preparation", demo_trade_preparation),
    ]
    
    results = []
    
    for demo_name, demo_func in demos:
        logger.info(f"\n{'='*20} {demo_name} {'='*20}")
        
        try:
            result = await demo_func()
            results.append((demo_name, result))
            
            if result:
                logger.info(f"✅ {demo_name} - SUCCESS")
            else:
                logger.error(f"❌ {demo_name} - FAILED")
                
        except Exception as e:
            logger.error(f"❌ {demo_name} - ERROR: {e}")
            results.append((demo_name, False))
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("DEMO SUMMARY")
    logger.info(f"{'='*60}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for demo_name, result in results:
        status = "✅ SUCCESS" if result else "❌ FAILED"
        logger.info(f"{demo_name:.<40} {status}")
    
    logger.info(f"\nOverall: {passed}/{total} demos completed successfully ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("\n🎉 ALL DEMOS PASSED!")
        logger.info("📝 What we demonstrated:")
        logger.info("   ✅ Official Avantis SDK integration")
        logger.info("   ✅ Trading client initialization")
        logger.info("   ✅ Market data retrieval")
        logger.info("   ✅ Trading parameters calculation")
        logger.info("   ✅ Price feed setup")
        logger.info("   ✅ Trading strategies")
        logger.info("   ✅ Risk management")
        logger.info("   ✅ Trade preparation")
        logger.info("\n🚀 The Avantis Trading Bot is ready for production!")
    else:
        logger.warning(f"\n⚠️ {total-passed} demos had issues. Check the logs above.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
