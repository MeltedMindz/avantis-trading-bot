"""
Integrated Trading Bot using Official Avantis SDK

This example demonstrates how to create a comprehensive trading bot
using the official Avantis Trader SDK with multiple strategies.
"""

import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the official Avantis SDK
from avantis_trader_sdk import TraderClient, FeedClient
from avantis_trader_sdk.types import TradeInput, TradeInputOrderType

# Import our custom components
from src.strategies import DCAStrategy, MomentumStrategy
from src.risk_manager import RiskManager
from src.logger import logger
from src.config import config


class IntegratedAvantisBot:
    """Integrated trading bot using official Avantis SDK"""
    
    def __init__(self):
        self.trader_client: Optional[TraderClient] = None
        self.feed_client: Optional[FeedClient] = None
        self.risk_manager = RiskManager()
        self.strategies = {}
        self.is_running = False
        
    async def initialize(self):
        """Initialize the bot with official SDK"""
        try:
            logger.info("🚀 Initializing Integrated Avantis Bot...")
            
            # Initialize TraderClient
            provider_url = config.wallet.provider_url
            self.trader_client = TraderClient(provider_url)
            
            # Set local signer
            self.trader_client.set_local_signer(config.wallet.private_key)
            
            # Get trader address
            trader_address = self.trader_client.get_signer().get_ethereum_address()
            logger.info(f"Trader address: {trader_address}")
            
            # Check USDC balance and allowance
            balance = await self.trader_client.get_usdc_balance(trader_address)
            allowance = await self.trader_client.get_usdc_allowance_for_trading(trader_address)
            
            logger.info(f"USDC Balance: {balance}")
            logger.info(f"USDC Allowance: {allowance}")
            
            # Initialize price feed client (optional)
            try:
                self.feed_client = FeedClient(
                    ws_url="wss://hermes.pyth.network/ws",
                    on_error=self._on_ws_error,
                    on_close=self._on_ws_close
                )
                logger.info("Price feed client initialized")
            except Exception as e:
                logger.warning(f"Could not initialize price feed client: {e}")
            
            # Load strategies
            self._load_strategies()
            
            logger.info("✅ Bot initialized successfully")
            return True
            
        except Exception as e:
            logger.error_occurred(e, "bot initialization")
            return False
    
    def _load_strategies(self):
        """Load trading strategies"""
        # DCA Strategy
        dca_config = {
            'enabled': True,
            'pairs': ['ETH/USD', 'BTC/USD'],
            'leverage': 5,
            'position_size': 10.0,
            'interval_minutes': 120,  # 2 hours
            'direction': 'long'
        }
        self.strategies['dca'] = DCAStrategy(dca_config)
        
        # Momentum Strategy
        momentum_config = {
            'enabled': True,
            'pairs': ['ETH/USD'],
            'leverage': 10,
            'position_size': 15.0,
            'rsi_period': 14,
            'min_signal_strength': 0.7
        }
        self.strategies['momentum'] = MomentumStrategy(momentum_config)
        
        logger.info(f"Loaded {len(self.strategies)} strategies")
    
    async def get_market_data(self, pair: str) -> Optional[Dict]:
        """Get comprehensive market data using official SDK"""
        try:
            # Get pairs info
            pairs_info = await self.trader_client.pairs_cache.get_pairs_info()
            
            # Get snapshot data
            snapshot = await self.trader_client.snapshot.get_snapshot()
            
            # Get asset parameters
            oi_limits = await self.trader_client.asset_parameters.get_oi_limits()
            oi = await self.trader_client.asset_parameters.get_oi()
            utilization = await self.trader_client.asset_parameters.get_utilization()
            skew = await self.trader_client.asset_parameters.get_asset_skew()
            
            # Get fee parameters
            margin_fee = await self.trader_client.fee_parameters.get_margin_fee()
            pair_spread = await self.trader_client.fee_parameters.get_pair_spread()
            
            market_data = {
                'pair': pair,
                'pairs_info': pairs_info,
                'snapshot': snapshot,
                'open_interest_limits': oi_limits,
                'open_interest': oi,
                'utilization': utilization,
                'skew': skew,
                'margin_fee': margin_fee,
                'pair_spread': pair_spread
            }
            
            return market_data
            
        except Exception as e:
            logger.error_occurred(e, f"getting market data for {pair}")
            return None
    
    async def open_trade(self, pair: str, is_long: bool, collateral: float, leverage: int) -> bool:
        """Open a trade using official SDK"""
        try:
            trader = self.trader_client.get_signer().get_ethereum_address()
            
            # Check allowance
            allowance = await self.trader_client.get_usdc_allowance_for_trading(trader)
            if allowance < collateral:
                logger.info(f"Approving {collateral} USDC for trading...")
                await self.trader_client.approve_usdc_for_trading(collateral)
            
            # Get pair index
            pair_index = await self.trader_client.pairs_cache.get_pair_index(pair)
            
            # Create trade input
            trade_input = TradeInput(
                trader=trader,
                open_price=None,  # Market order
                pair_index=pair_index,
                collateral_in_trade=collateral,
                is_long=is_long,
                leverage=leverage,
                index=0,  # First trade for this pair
                tp=0,  # No take profit
                sl=0,  # No stop loss
                timestamp=0
            )
            
            # Get opening fee and loss protection
            opening_fee = await self.trader_client.fee_parameters.get_new_trade_opening_fee(trade_input)
            loss_protection = await self.trader_client.trading_parameters.get_loss_protection_for_trade_input(
                trade_input, opening_fee_usdc=opening_fee
            )
            
            logger.info(f"Opening fee: {opening_fee} USDC")
            logger.info(f"Loss protection: {loss_protection.percentage}% (up to ${loss_protection.amount})")
            
            # Build and execute trade
            open_transaction = await self.trader_client.trade.build_trade_open_tx(
                trade_input, TradeInputOrderType.MARKET, 1.0  # 1% slippage
            )
            
            receipt = await self.trader_client.sign_and_get_receipt(open_transaction)
            
            logger.info(f"Trade opened successfully! Transaction: {receipt.get('transactionHash', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error_occurred(e, f"opening trade for {pair}")
            return False
    
    async def get_open_trades(self) -> List[Dict]:
        """Get all open trades using official SDK"""
        try:
            trader = self.trader_client.get_signer().get_ethereum_address()
            trades, pending_orders = await self.trader_client.trade.get_trades(trader)
            
            logger.info(f"Found {len(trades)} open trades and {len(pending_orders)} pending orders")
            
            return {
                'trades': trades,
                'pending_orders': pending_orders
            }
            
        except Exception as e:
            logger.error_occurred(e, "getting open trades")
            return {'trades': [], 'pending_orders': []}
    
    async def close_trade(self, pair_index: int, trade_index: int, collateral_to_close: Optional[float] = None) -> bool:
        """Close a trade using official SDK"""
        try:
            trader = self.trader_client.get_signer().get_ethereum_address()
            
            # Build close transaction
            close_transaction = await self.trader_client.trade.build_trade_close_tx(
                pair_index=pair_index,
                trade_index=trade_index,
                collateral_to_close=collateral_to_close or 0,  # 0 = close entire trade
                trader=trader
            )
            
            receipt = await self.trader_client.sign_and_get_receipt(close_transaction)
            
            logger.info(f"Trade closed successfully! Transaction: {receipt.get('transactionHash', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error_occurred(e, f"closing trade {pair_index}:{trade_index}")
            return False
    
    async def run_trading_loop(self):
        """Main trading loop"""
        try:
            logger.info("🔄 Starting trading loop...")
            self.is_running = True
            
            while self.is_running:
                try:
                    # Get current trades
                    trades_data = await self.get_open_trades()
                    
                    # Get market data for analysis
                    eth_market_data = await self.get_market_data("ETH/USD")
                    
                    if eth_market_data:
                        logger.debug("Market data retrieved successfully")
                    
                    # Run strategy analysis (simplified)
                    for strategy_name, strategy in self.strategies.items():
                        if strategy.enabled:
                            logger.debug(f"Running {strategy_name} strategy analysis")
                            # Here you would implement the actual strategy logic
                    
                    # Wait before next iteration
                    await asyncio.sleep(30)  # 30 second intervals
                    
                except Exception as e:
                    logger.error_occurred(e, "trading loop iteration")
                    await asyncio.sleep(60)  # Wait longer on error
                    
        except Exception as e:
            logger.error_occurred(e, "trading loop")
        finally:
            logger.info("🛑 Trading loop stopped")
    
    def _on_ws_error(self, error):
        """Handle WebSocket errors"""
        logger.error(f"WebSocket error: {error}")
    
    def _on_ws_close(self, error):
        """Handle WebSocket close"""
        logger.warning(f"WebSocket closed: {error}")
    
    async def stop(self):
        """Stop the bot"""
        self.is_running = False
        logger.info("Bot stopped")


async def main():
    """Main function to run the integrated bot"""
    # Check if private key is set
    if not os.getenv("PRIVATE_KEY"):
        print("❌ Please set PRIVATE_KEY in your environment variables")
        print("   Example: export PRIVATE_KEY='0x...'")
        return
    
    # Create and initialize bot
    bot = IntegratedAvantisBot()
    
    if not await bot.initialize():
        logger.error("Failed to initialize bot")
        return
    
    try:
        # Example: Open a small test trade
        logger.info("Opening test trade...")
        success = await bot.open_trade("ETH/USD", True, 5.0, 5)  # $5 collateral, 5x leverage
        
        if success:
            logger.info("Test trade opened successfully!")
            
            # Get open trades
            trades_data = await bot.get_open_trades()
            logger.info(f"Current trades: {trades_data}")
            
            # Run trading loop for a short time
            logger.info("Running trading loop for 2 minutes...")
            loop_task = asyncio.create_task(bot.run_trading_loop())
            
            # Wait for 2 minutes
            await asyncio.sleep(120)
            
            # Stop the loop
            await bot.stop()
            loop_task.cancel()
            
        else:
            logger.error("Failed to open test trade")
    
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
