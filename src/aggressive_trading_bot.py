"""
Aggressive Trading Bot for 10% Daily Returns
Main bot that integrates compound growth, daily optimization, and aggressive strategies
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import signal
import sys

try:
    from .avantis_client import AvantisClient
    from .compound_growth import CompoundGrowthManager, AggressiveTradingMode
    from .daily_profit_optimizer import DailyProfitOptimizer, TradingPhase
    from .strategies.aggressive_momentum_strategy import AggressiveMomentumStrategy
    from .strategies.grid_strategy import GridStrategy
    from .risk_manager import RiskManager
    from .logger import logger
    from .config import config
except ImportError:
    from avantis_client import AvantisClient
    from compound_growth import CompoundGrowthManager, AggressiveTradingMode
    from daily_profit_optimizer import DailyProfitOptimizer, TradingPhase
    from strategies.aggressive_momentum_strategy import AggressiveMomentumStrategy
    from strategies.grid_strategy import GridStrategy
    from risk_manager import RiskManager
    from logger import logger
    from config import config


class AggressiveTradingBot:
    """Main aggressive trading bot for 10% daily returns"""
    
    def __init__(self):
        self.name = "Avantis Aggressive Trading Bot"
        self.version = "2.0.0"
        
        # Core components
        self.avantis_client: Optional[AvantisClient] = None
        self.compound_manager: Optional[CompoundGrowthManager] = None
        self.daily_optimizer: Optional[DailyProfitOptimizer] = None
        self.aggressive_mode: Optional[AggressiveTradingMode] = None
        
        # Strategies
        self.momentum_strategy: Optional[AggressiveMomentumStrategy] = None
        self.grid_strategy: Optional[GridStrategy] = None
        
        # Risk management
        self.risk_manager: Optional[RiskManager] = None
        
        # Bot state
        self.running = False
        self.active_trades: List = []
        self.daily_stats = {}
        
        # Configuration
        self.trading_interval = 30  # seconds between trading cycles
        self.max_concurrent_trades = 10
        self.emergency_stop = False
        
        # Performance tracking
        self.session_start_time = datetime.now()
        self.total_trades = 0
        self.successful_trades = 0
        
    async def initialize(self, initial_capital: float = None):
        """Initialize all bot components"""
        try:
            logger.info(f"🚀 Initializing {self.name} v{self.version}")
            
            # Initialize Avantis client
            self.avantis_client = AvantisClient()
            if not await self.avantis_client.initialize():
                raise Exception("Failed to initialize Avantis client")
            
            # Get current balance if initial capital not provided
            if initial_capital is None:
                balance = await self.avantis_client.client.get_usdc_balance(
                    self.avantis_client.trader_address
                )
                initial_capital = float(balance)
            
            # Initialize compound growth manager
            self.compound_manager = CompoundGrowthManager()
            await self.compound_manager.initialize(initial_capital)
            
            # Initialize aggressive trading mode
            self.aggressive_mode = AggressiveTradingMode(self.compound_manager)
            
            # Initialize daily profit optimizer
            self.daily_optimizer = DailyProfitOptimizer(
                self.compound_manager, self.avantis_client
            )
            await self.daily_optimizer.initialize()
            
            # Initialize strategies
            self.momentum_strategy = AggressiveMomentumStrategy()
            await self.momentum_strategy.initialize()
            
            self.grid_strategy = GridStrategy()
            await self.grid_strategy.initialize()
            
            # Initialize risk manager
            self.risk_manager = RiskManager()
            await self.risk_manager.initialize()
            
            logger.info("✅ All components initialized successfully")
            logger.info(f"💰 Starting Capital: ${initial_capital:,.2f}")
            logger.info(f"🎯 Daily Target: ${self.compound_manager.get_daily_target():,.2f}")
            
            return True
            
        except Exception as e:
            logger.error_occurred(e, "bot initialization")
            return False
    
    async def start(self):
        """Start the aggressive trading bot"""
        if not await self.initialize():
            logger.error("❌ Failed to initialize bot")
            return False
        
        self.running = True
        logger.info("🚀 Starting aggressive trading bot...")
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            # Main trading loop
            while self.running and not self.emergency_stop:
                await self._trading_cycle()
                
                # Check if we should end the trading day
                if await self.daily_optimizer.should_end_trading_day():
                    await self.daily_optimizer.end_trading_day()
                    await self._overnight_mode()
                
                # Wait before next cycle
                await asyncio.sleep(self.trading_interval)
                
        except Exception as e:
            logger.error_occurred(e, "main trading loop")
        finally:
            await self.stop()
    
    async def _trading_cycle(self):
        """Execute one trading cycle"""
        try:
            # Get current market data
            market_data = await self._get_market_data()
            
            # Get daily status
            daily_status = await self.daily_optimizer.get_daily_status()
            
            # Log status
            if self.total_trades % 10 == 0:  # Log every 10 cycles
                logger.info(f"📊 Trading Cycle - {self.total_trades}")
                logger.info(f"   Daily Progress: {daily_status.progress_percentage:.1f}%")
                logger.info(f"   Active Trades: {len(self.active_trades)}")
                logger.info(f"   Phase: {daily_status.phase.value}")
                logger.info(f"   Risk Level: {daily_status.risk_level}")
            
            # Check existing trades for exits
            await self._check_existing_trades(market_data)
            
            # Generate new trading signals
            await self._generate_and_execute_signals(market_data, daily_status)
            
            # Update compound growth tracking
            await self._update_performance_tracking()
            
            self.total_trades += 1
            
        except Exception as e:
            logger.error_occurred(e, "trading cycle")
    
    async def _get_market_data(self) -> Dict:
        """Get current market data for all trading pairs"""
        market_data = {}
        
        # Popular pairs for aggressive trading
        pairs = ["ETH/USD", "BTC/USD", "SOL/USD", "AVAX/USD", "MATIC/USD"]
        
        for pair in pairs:
            try:
                # Get comprehensive market data
                pair_data = await self.avantis_client.get_market_data(pair)
                
                if pair_data:
                    # Get price impact for position sizing
                    price_impact = await self.avantis_client.calculate_price_impact(
                        pair, 1000, True  # Sample 1k position, long
                    )
                    
                    # Combine data
                    market_data[pair] = {
                        'price': 2000.0,  # Mock price - would get from feed
                        'volume': pair_data.get('open_interest_long', 0) + pair_data.get('open_interest_short', 0),
                        'volatility': abs(pair_data.get('skew', 50) - 50) / 100,  # Convert skew to volatility
                        'rsi': 45.0,  # Mock RSI - would calculate from price data
                        'macd': 0.5,  # Mock MACD
                        'macd_signal': 0.3,
                        'ma_5': 1950.0,  # Mock moving averages
                        'ma_20': 1900.0,
                        'ma_50': 1850.0,
                        'utilization': pair_data.get('utilization', 0),
                        'skew': pair_data.get('skew', 50),
                        'price_impact': price_impact,
                        'market_data': pair_data
                    }
                    
            except Exception as e:
                logger.error_occurred(e, f"getting market data for {pair}")
                continue
        
        return market_data
    
    async def _check_existing_trades(self, market_data: Dict):
        """Check existing trades for exit conditions"""
        trades_to_close = []
        
        for trade in self.active_trades:
            try:
                pair = trade.pair
                if pair not in market_data:
                    continue
                
                # Check exit conditions based on strategy
                should_exit, reason = await self.momentum_strategy.should_exit_trade(
                    trade, market_data[pair]
                )
                
                if should_exit:
                    trades_to_close.append((trade, reason))
                    
            except Exception as e:
                logger.error_occurred(e, f"checking trade {trade.pair}")
                continue
        
        # Close trades that met exit conditions
        for trade, reason in trades_to_close:
            await self._close_trade(trade, reason)
    
    async def _generate_and_execute_signals(self, market_data: Dict, daily_status):
        """Generate trading signals and execute trades"""
        # Skip if we have too many active trades
        if len(self.active_trades) >= self.max_concurrent_trades:
            return
        
        # Skip if trading is paused
        if daily_status.recommended_action == "TRADING_PAUSED":
            return
        
        try:
            # Generate momentum signals
            momentum_signals = await self.momentum_strategy.analyze(market_data)
            
            # Execute high-priority signals first
            for pair, signal in list(momentum_signals.items())[:3]:  # Top 3 signals
                if signal.urgency == "HIGH" and len(self.active_trades) < self.max_concurrent_trades:
                    await self._execute_aggressive_trade(signal, daily_status)
                    
        except Exception as e:
            logger.error_occurred(e, "generating and executing signals")
    
    async def _execute_aggressive_trade(self, signal, daily_status):
        """Execute an aggressive trade based on signal"""
        try:
            # Check if we should take this trade
            should_trade = await self.daily_optimizer.should_take_trade(
                signal.confidence, signal.expected_return
            )
            
            if not should_trade:
                return
            
            # Calculate optimal position size and leverage
            optimal_size = await self.daily_optimizer.calculate_optimal_position_size(
                signal.position_size, signal.confidence, signal.expected_return
            )
            
            optimal_leverage = await self.daily_optimizer.calculate_optimal_leverage(
                signal.leverage, signal.market_data.get('volatility', 0.03) if hasattr(signal, 'market_data') else 0.03
            )
            
            # Create trade
            from models import Trade, TradeDirection, OrderType
            
            trade = Trade(
                pair=signal.pair,
                direction=signal.direction,
                entry_price=signal.market_data.get('price', 2000) if hasattr(signal, 'market_data') else 2000,
                size=optimal_size,
                leverage=optimal_leverage,
                order_type=OrderType.MARKET,
                take_profit=optimal_size * (1 + signal.expected_return),
                stop_loss=optimal_size * (1 - 0.02)  # 2% stop loss
            )
            
            # Execute trade
            success = await self.avantis_client.open_trade(trade)
            
            if success:
                self.active_trades.append(trade)
                logger.info(f"🚀 Aggressive Trade Opened:")
                logger.info(f"   Pair: {trade.pair}")
                logger.info(f"   Direction: {trade.direction.value}")
                logger.info(f"   Size: ${trade.size:,.2f}")
                logger.info(f"   Leverage: {trade.leverage}x")
                logger.info(f"   Expected Return: {signal.expected_return:.1%}")
                logger.info(f"   Confidence: {signal.confidence:.2f}")
                logger.info(f"   Urgency: {signal.urgency}")
            else:
                logger.warning(f"⚠️ Failed to open trade for {signal.pair}")
                
        except Exception as e:
            logger.error_occurred(e, f"executing aggressive trade for {signal.pair}")
    
    async def _close_trade(self, trade, reason: str):
        """Close a trade and record results"""
        try:
            # Calculate PnL (mock calculation)
            current_price = 2050.0  # Mock current price
            price_change = (current_price - trade.entry_price) / trade.entry_price
            
            if trade.direction == TradeDirection.SHORT:
                price_change = -price_change
            
            pnl = trade.size * price_change * trade.leverage
            
            # Close trade
            success = await self.avantis_client.close_trade(trade)
            
            if success:
                self.active_trades.remove(trade)
                
                # Record result
                await self.daily_optimizer.record_trade_result(trade, pnl)
                
                # Update stats
                if pnl > 0:
                    self.successful_trades += 1
                
                logger.info(f"📊 Trade Closed - {trade.pair}")
                logger.info(f"   Reason: {reason}")
                logger.info(f"   PnL: ${pnl:,.2f}")
                logger.info(f"   Win Rate: {self.successful_trades}/{self.total_trades} ({self.successful_trades/max(self.total_trades, 1)*100:.1f}%)")
                
        except Exception as e:
            logger.error_occurred(e, f"closing trade {trade.pair}")
    
    async def _update_performance_tracking(self):
        """Update performance tracking and compound growth"""
        try:
            # Update compound manager with current capital
            current_balance = await self.avantis_client.client.get_usdc_balance(
                self.avantis_client.trader_address
            )
            
            self.compound_manager.current_capital = float(current_balance)
            
        except Exception as e:
            logger.error_occurred(e, "updating performance tracking")
    
    async def _overnight_mode(self):
        """Handle overnight mode (defensive trading)"""
        logger.info("🌙 Entering overnight mode")
        
        # Close all aggressive positions
        for trade in self.active_trades[:]:
            await self._close_trade(trade, "Overnight mode - closing aggressive positions")
        
        # Wait until morning
        await asyncio.sleep(3600)  # Wait 1 hour
    
    async def stop(self):
        """Stop the trading bot"""
        self.running = False
        logger.info("🛑 Stopping aggressive trading bot...")
        
        # Close all active trades
        for trade in self.active_trades[:]:
            await self._close_trade(trade, "Bot stopping")
        
        # End trading day
        if self.daily_optimizer:
            await self.daily_optimizer.end_trading_day()
        
        # Print final statistics
        self._print_session_summary()
        
        logger.info("✅ Bot stopped successfully")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"🛑 Received signal {signum}, shutting down...")
        self.emergency_stop = True
        self.running = False
    
    def _print_session_summary(self):
        """Print session summary"""
        session_duration = datetime.now() - self.session_start_time
        
        logger.info("📊 SESSION SUMMARY")
        logger.info("=" * 50)
        logger.info(f"⏰ Duration: {session_duration}")
        logger.info(f"📊 Total Trades: {self.total_trades}")
        logger.info(f"✅ Successful Trades: {self.successful_trades}")
        logger.info(f"📈 Win Rate: {self.successful_trades/max(self.total_trades, 1)*100:.1f}%")
        
        if self.compound_manager:
            stats = self.compound_manager.get_compound_stats()
            logger.info(f"💰 Current Capital: ${stats.current_capital:,.2f}")
            logger.info(f"📊 Total Return: {stats.total_return:.1f}%")
            logger.info(f"🔥 Compound Multiplier: {stats.compound_return/100 + 1:.2f}x")
        
        logger.info("=" * 50)


# Example usage
async def main():
    """Main function to run the aggressive trading bot"""
    bot = AggressiveTradingBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("🛑 Bot interrupted by user")
    except Exception as e:
        logger.error_occurred(e, "main bot execution")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
