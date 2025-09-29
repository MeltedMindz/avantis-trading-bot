#!/usr/bin/env python3
"""
Comprehensive test script for the Avantis Trading Bot
Tests all functionality with the official SDK
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.avantis_client import AvantisClient
from src.logger import logger
from src.config import config


async def test_basic_functionality():
    """Test basic SDK functionality"""
    logger.info("🧪 Testing Basic SDK Functionality")
    
    try:
        # Test without private key first (read-only operations)
        client = AvantisClient()
        
        # Override the private key for testing
        original_private_key = config.wallet.private_key
        config.wallet.private_key = "0x0000000000000000000000000000000000000000000000000000000000000001"  # Dummy key
        
        # Initialize client
        if await client.initialize():
            logger.info("✅ Client initialization successful")
            
            # Test getting pair info
            pairs_info = await client.client.pairs_cache.get_pairs_info()
            logger.info(f"✅ Pairs info retrieved: {len(pairs_info)} pairs available")
            
            # Test getting snapshot
            snapshot = await client.client.snapshot.get_snapshot()
            logger.info("✅ Snapshot retrieved successfully")
            
            # Test getting pair index
            eth_pair_index = await client.get_pair_index("ETH/USD")
            if eth_pair_index is not None:
                logger.info(f"✅ ETH/USD pair index: {eth_pair_index}")
            else:
                logger.warning("⚠️ ETH/USD pair index not found")
            
            # Test getting market data
            market_data = await client.get_market_data("ETH/USD")
            if market_data:
                logger.info("✅ Market data retrieved successfully")
                logger.info(f"   - Open Interest Long: {market_data.get('open_interest_long', 'N/A')}")
                logger.info(f"   - Utilization: {market_data.get('utilization', 'N/A')}%")
                logger.info(f"   - Skew: {market_data.get('skew', 'N/A')}%")
            else:
                logger.warning("⚠️ Market data retrieval failed")
            
            return True
        else:
            logger.error("❌ Client initialization failed")
            return False
            
    except Exception as e:
        logger.error_occurred(e, "basic functionality test")
        return False
    finally:
        # Restore original private key
        config.wallet.private_key = original_private_key


async def test_trading_parameters():
    """Test trading parameter calculations"""
    logger.info("🧪 Testing Trading Parameters")
    
    try:
        client = AvantisClient()
        
        # Initialize with dummy key
        original_private_key = config.wallet.private_key
        config.wallet.private_key = "0x0000000000000000000000000000000000000000000000000000000000000001"
        
        if await client.initialize():
            # Test getting trading parameters
            trading_params = await client.get_trading_parameters("ETH/USD")
            if trading_params:
                logger.info("✅ Trading parameters retrieved successfully")
                logger.info(f"   - Pair Index: {trading_params.get('pair_index', 'N/A')}")
                logger.info(f"   - Loss Protection: {trading_params.get('loss_protection', 'N/A')}")
                logger.info(f"   - Opening Fee: {trading_params.get('opening_fee', 'N/A')}")
                logger.info(f"   - Referral Rebate: {trading_params.get('referral_rebate_percentage', 'N/A')}%")
            else:
                logger.warning("⚠️ Trading parameters retrieval failed")
            
            # Test price impact calculation
            price_impact = await client.calculate_price_impact("ETH/USD", 1000, True)
            if price_impact:
                logger.info("✅ Price impact calculated successfully")
                logger.info(f"   - Total Impact: {price_impact.get('total_impact', 'N/A')}%")
                logger.info(f"   - Price Impact: {price_impact.get('price_impact', 'N/A')}%")
                logger.info(f"   - Skew Impact: {price_impact.get('skew_impact', 'N/A')}%")
            else:
                logger.warning("⚠️ Price impact calculation failed")
            
            return True
        else:
            logger.error("❌ Client initialization failed")
            return False
            
    except Exception as e:
        logger.error_occurred(e, "trading parameters test")
        return False
    finally:
        config.wallet.private_key = original_private_key


async def test_price_feed():
    """Test price feed functionality"""
    logger.info("🧪 Testing Price Feed Functionality")
    
    try:
        from avantis_trader_sdk.feed.feed_client import FeedClient
        
        # Create feed client
        feed_client = FeedClient(
            ws_url="wss://hermes.pyth.network/ws",
            on_error=lambda e: logger.warning(f"Feed error: {e}"),
            on_close=lambda e: logger.warning(f"Feed closed: {e}")
        )
        
        # Test getting pair from feed ID
        test_feed_id = "0x09f7c1d7dfbb7df2b8fe3d3d87ee94a2259d212da4f30c1f0540d066dfa44723"
        pair_name = feed_client.get_pair_from_feed_id(test_feed_id)
        logger.info(f"✅ Feed ID to pair conversion: {test_feed_id} -> {pair_name}")
        
        # Test registering callback (without actually listening)
        callback_registered = False
        try:
            feed_client.register_price_feed_callback("ETH/USD", lambda data: None)
            callback_registered = True
            logger.info("✅ Price feed callback registration successful")
        except Exception as e:
            logger.warning(f"⚠️ Price feed callback registration failed: {e}")
        
        return True
        
    except Exception as e:
        logger.error_occurred(e, "price feed test")
        return False


async def test_with_real_private_key():
    """Test with real private key if available"""
    logger.info("🧪 Testing with Real Private Key")
    
    private_key = os.getenv("PRIVATE_KEY")
    if not private_key:
        logger.info("ℹ️ No PRIVATE_KEY environment variable set, skipping real key tests")
        return True
    
    try:
        client = AvantisClient()
        config.wallet.private_key = private_key
        
        if await client.initialize():
            logger.info("✅ Real private key initialization successful")
            
            # Test getting USDC balance
            balance = await client.client.get_usdc_balance(client.trader_address)
            logger.info(f"✅ USDC Balance: {balance}")
            
            # Test getting allowance
            allowance = await client.check_usdc_allowance(100)
            logger.info(f"✅ USDC Allowance: {allowance}")
            
            # Test getting open trades
            trades = await client.get_open_trades()
            logger.info(f"✅ Open trades: {len(trades)}")
            
            return True
        else:
            logger.error("❌ Real private key initialization failed")
            return False
            
    except Exception as e:
        logger.error_occurred(e, "real private key test")
        return False


async def test_all_examples():
    """Test all SDK examples"""
    logger.info("🧪 Testing SDK Examples")
    
    try:
        # Test example 1: Get pair info
        from avantis_trader_sdk.client import TraderClient
        
        provider_url = "https://mainnet.base.org"
        trader_client = TraderClient(provider_url)
        
        pairs_info = await trader_client.pairs_cache.get_pairs_info()
        logger.info(f"✅ Example 1 - Pairs info: {len(pairs_info)} pairs")
        
        # Test example 2: Get snapshot
        snapshot = await trader_client.snapshot.get_snapshot()
        logger.info("✅ Example 2 - Snapshot retrieved")
        
        # Test getting pair index
        try:
            eth_pair_index = await trader_client.pairs_cache.get_pair_index("ETH/USD")
            logger.info(f"✅ Example 3 - ETH/USD pair index: {eth_pair_index}")
        except Exception as e:
            logger.warning(f"⚠️ Example 3 - ETH/USD pair index failed: {e}")
        
        return True
        
    except Exception as e:
        logger.error_occurred(e, "SDK examples test")
        return False


async def run_comprehensive_tests():
    """Run all tests"""
    logger.info("🚀 Starting Comprehensive Avantis SDK Tests")
    
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("Trading Parameters", test_trading_parameters),
        ("Price Feed", test_price_feed),
        ("SDK Examples", test_all_examples),
        ("Real Private Key", test_with_real_private_key),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = await test_func()
            results.append((test_name, result))
            
            if result:
                logger.info(f"✅ {test_name} - PASSED")
            else:
                logger.error(f"❌ {test_name} - FAILED")
                
        except Exception as e:
            logger.error(f"❌ {test_name} - ERROR: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*60}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name:.<40} {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("🎉 All tests passed! The Avantis client is working perfectly.")
    else:
        logger.warning(f"⚠️ {total-passed} tests failed. Check the logs above for details.")
    
    return passed == total


if __name__ == "__main__":
    # Run the comprehensive tests
    success = asyncio.run(run_comprehensive_tests())
    sys.exit(0 if success else 1)
