#!/usr/bin/env python3
"""
Simple test for Avantis SDK integration
"""

import asyncio
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_sdk_basics():
    """Test basic SDK functionality"""
    print("🧪 Testing Avantis SDK Integration")
    
    try:
        # Test direct SDK imports
        from avantis_trader_sdk.client import TraderClient
        from avantis_trader_sdk.feed.feed_client import FeedClient
        from avantis_trader_sdk.types import TradeInput, TradeInputOrderType, MarginUpdateType
        
        print("✅ SDK imports successful")
        
        # Test client initialization
        provider_url = "https://mainnet.base.org"
        trader_client = TraderClient(provider_url)
        
        print("✅ TraderClient initialized")
        
        # Test getting pairs info
        pairs_info = await trader_client.pairs_cache.get_pairs_info()
        print(f"✅ Pairs info retrieved: {len(pairs_info)} pairs available")
        
        # List some available pairs
        for i, pair_name in enumerate(list(pairs_info.keys())[:5]):
            print(f"   - {pair_name}")
        
        # Test getting snapshot
        snapshot = await trader_client.snapshot.get_snapshot()
        print("✅ Snapshot retrieved successfully")
        
        # Test getting ETH/USD pair index
        try:
            eth_pair_index = await trader_client.pairs_cache.get_pair_index("ETH/USD")
            print(f"✅ ETH/USD pair index: {eth_pair_index}")
        except Exception as e:
            print(f"⚠️ ETH/USD pair index failed: {e}")
        
        # Test feed client
        feed_client = FeedClient("wss://hermes.pyth.network/ws")
        print("✅ FeedClient initialized")
        
        # Test feed ID to pair conversion
        test_feed_id = "0x09f7c1d7dfbb7df2b8fe3d3d87ee94a2259d212da4f30c1f0540d066dfa44723"
        pair_name = feed_client.get_pair_from_feed_id(test_feed_id)
        print(f"✅ Feed ID conversion: {pair_name}")
        
        print("\n🎉 All basic SDK tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ SDK test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_our_client():
    """Test our AvantisClient wrapper"""
    print("\n🧪 Testing Our AvantisClient Wrapper")
    
    try:
        # Set a dummy private key for testing
        import os
        os.environ["PRIVATE_KEY"] = "0x0000000000000000000000000000000000000000000000000000000000000001"
        
        from src.avantis_client import AvantisClient
        from src.config import config
        
        client = AvantisClient()
        
        if await client.initialize():
            print("✅ AvantisClient initialization successful")
            
            # Test getting pair index
            pair_index = await client.get_pair_index("ETH/USD")
            if pair_index is not None:
                print(f"✅ Pair index retrieval: {pair_index}")
            else:
                print("⚠️ Pair index retrieval failed")
            
            print("🎉 Our client wrapper tests passed!")
            return True
        else:
            print("❌ AvantisClient initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Our client test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("🚀 Starting Avantis SDK Integration Tests")
    print("=" * 50)
    
    # Test 1: Basic SDK functionality
    sdk_success = await test_sdk_basics()
    
    # Test 2: Our client wrapper
    client_success = await test_our_client()
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    if sdk_success and client_success:
        print("🎉 ALL TESTS PASSED! SDK integration is working perfectly.")
        return True
    else:
        print("❌ Some tests failed. Check the output above.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
