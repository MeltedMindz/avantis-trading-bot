"""
Main Trading Bot Class for Avantis
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from dataclasses import asdict

from .models import (
    Trade, Position, Signal, MarketData, BotStatus, 
    StrategyType, TradeDirection, TradeStatus
)
from .avantis_client import AvantisClient
from .risk_manager import RiskManager
from .logger import logger
from .config import config
from .strategies import (
    DCAStrategy, GridStrategy, MomentumStrategy, 
    MeanReversionStrategy, BreakoutStrategy
)


class AvantisTradingBot:
    """Main trading bot class that orchestrates all components"""
    
    def __init__(self):
        self.avantis_client = AvantisClient()
        self.risk_manager = RiskManager()
        
        # Strategy management
        self.strategies: Dict[str, Any] = {}
        self.active_trades: List[Trade] = []
        self.closed_trades: List[Trade] = []
        
        # Bot state
        self.status = BotStatus()
        self.is_running = False
        self.is_trading = False
        
        # Market data
        self.market_data_cache: Dict[str, MarketData] = {}
        
        # Performance tracking
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.start_balance = 0.0
        
        logger.info("Avantis Trading Bot initialized")
    
    async def initialize(self) -> bool:
        """Initialize the trading bot"""
        try:
            logger.info("Initializing Avantis Trading Bot...")
            
            # Validate configuration
            if not config.validate():
                logger.error("Configuration validation failed")
                return False
            
            # Initialize Avantis client
            if not await self.avantis_client.initialize():
                logger.error("Failed to initialize Avantis client")
                return False
            
            # Load strategies
            await self._load_strategies()
            
            # Get initial balance and open trades
            await self._load_initial_state()
            
            self.status.is_running = True
            self.status.start_time = datetime.now()
            self.is_running = True
            
            logger.info("Avantis Trading Bot initialized successfully")
            return True
            
        except Exception as e:
            logger.error_occurred(e, "bot initialization")
            return False
    
    async def _load_strategies(self):
        """Load and initialize trading strategies"""
        try:
            # Default strategy configurations
            default_strategies = {
                'dca': {
                    'enabled': True,
                    'pairs': ['ETH/USD', 'BTC/USD'],
                    'leverage': 5,
                    'position_size': 10.0,
                    'interval_minutes': 60,
                    'direction': 'long'
                },
                'momentum': {
                    'enabled': True,
                    'pairs': ['ETH/USD', 'BTC/USD'],
                    'leverage': 10,
                    'position_size': 15.0,
                    'rsi_period': 14,
                    'min_signal_strength': 0.7
                },
                'mean_reversion': {
                    'enabled': False,
                    'pairs': ['ETH/USD'],
                    'leverage': 8,
                    'position_size': 12.0,
                    'z_score_entry': 2.0,
                    'min_signal_strength': 0.6
                },
                'grid': {
                    'enabled': False,
                    'pairs': ['ETH/USD'],
                    'leverage': 5,
                    'position_size': 8.0,
                    'grid_levels': 10,
                    'grid_spacing': 0.01
                },
                'breakout': {
                    'enabled': False,
                    'pairs': ['ETH/USD', 'BTC/USD'],
                    'leverage': 15,
                    'position_size': 20.0,
                    'breakout_threshold': 0.02,
                    'min_signal_strength': 0.7
                }
            }
            
            # Initialize strategies
            self.strategies['dca'] = DCAStrategy(default_strategies['dca'])
            self.strategies['momentum'] = MomentumStrategy(default_strategies['momentum'])
            self.strategies['mean_reversion'] = MeanReversionStrategy(default_strategies['mean_reversion'])
            self.strategies['grid'] = GridStrategy(default_strategies['grid'])
            self.strategies['breakout'] = BreakoutStrategy(default_strategies['breakout'])
            
            # Update bot status
            self.status.active_strategies = [
                name for name, strategy in self.strategies.items() 
                if strategy.enabled
            ]
            
            logger.info(f"Loaded {len(self.strategies)} strategies: {list(self.strategies.keys())}")
            
        except Exception as e:
            logger.error_occurred(e, "loading strategies")
    
    async def _load_initial_state(self):
        """Load initial bot state (balance, open trades)"""
        try:
            # Get open trades from Avantis
            open_trades = await self.avantis_client.get_open_trades()
            self.active_trades = open_trades
            
            # Calculate initial balance (simplified)
            self.start_balance = 1000.0  # This would be fetched from wallet balance
            self.status.total_trades = len(self.active_trades)
            
            logger.info(f"Loaded {len(open_trades)} active trades")
            
        except Exception as e:
            logger.error_occurred(e, "loading initial state")
    
    async def start(self):
        """Start the trading bot"""
        try:
            if not self.is_running:
                logger.error("Bot not initialized. Call initialize() first.")
                return
            
            logger.info("🚀 Starting Avantis Trading Bot...")
            self.is_trading = True
            self.status.is_trading = True
            
            # Start main trading loop
            await self._main_trading_loop()
            
        except Exception as e:
            logger.error_occurred(e, "starting bot")
            await self.stop()
    
    async def stop(self):
        """Stop the trading bot"""
        try:
            logger.info("🛑 Stopping Avantis Trading Bot...")
            self.is_trading = False
            self.is_running = False
            self.status.is_trading = False
            
            # Save bot state
            await self._save_bot_state()
            
            logger.info("Avantis Trading Bot stopped")
            
        except Exception as e:
            logger.error_occurred(e, "stopping bot")
    
    async def _main_trading_loop(self):
        """Main trading loop"""
        try:
            logger.info("Main trading loop started")
            
            while self.is_trading:
                try:
                    # Update market data
                    await self._update_market_data()
                    
                    # Process signals from all strategies
                    await self._process_strategy_signals()
                    
                    # Check exit conditions for active trades
                    await self._check_exit_conditions()
                    
                    # Update risk metrics
                    await self._update_risk_metrics()
                    
                    # Check for emergency stop conditions
                    if self.risk_manager.should_reduce_exposure([]):  # Pass current positions
                        logger.risk_alert("Risk limits approaching, reducing exposure")
                        await self._emergency_reduce_exposure()
                    
                    # Log performance update
                    self._log_performance_update()
                    
                    # Wait before next iteration
                    await asyncio.sleep(30)  # 30 second intervals
                    
                except Exception as e:
                    logger.error_occurred(e, "main trading loop")
                    self.status.error_count += 1
                    self.status.last_error = str(e)
                    await asyncio.sleep(60)  # Wait longer on error
                    
        except Exception as e:
            logger.error_occurred(e, "main trading loop")
    
    async def _update_market_data(self):
        """Update market data for all pairs"""
        try:
            # This would typically fetch from external price feeds
            # For now, we'll simulate market data updates
            pairs = ['ETH/USD', 'BTC/USD']
            
            for pair in pairs:
                # Simulate price data (in real implementation, fetch from price feed)
                import random
                base_price = 2000 if 'ETH' in pair else 40000
                price = base_price * (1 + random.uniform(-0.02, 0.02))  # ±2% variation
                
                market_data = MarketData(
                    pair=pair,
                    price=price,
                    volume=random.uniform(1000, 5000),
                    timestamp=datetime.now()
                )
                
                self.market_data_cache[pair] = market_data
                
        except Exception as e:
            logger.error_occurred(e, "updating market data")
    
    async def _process_strategy_signals(self):
        """Process signals from all active strategies"""
        try:
            for pair, market_data in self.market_data_cache.items():
                for strategy_name, strategy in self.strategies.items():
                    if not strategy.enabled:
                        continue
                    
                    try:
                        # Generate signal
                        signal = await strategy.analyze(market_data)
                        
                        if signal and strategy.validate_signal(signal):
                            # Check if we already have a position for this pair
                            existing_trade = next(
                                (t for t in self.active_trades if t.pair == pair), 
                                None
                            )
                            
                            if not existing_trade:
                                # Create and execute new trade
                                await self._execute_signal(signal, strategy)
                            else:
                                logger.debug(f"Pair {pair} already has active trade, skipping signal")
                                
                    except Exception as e:
                        logger.error_occurred(e, f"processing signal from {strategy_name}")
                        
        except Exception as e:
            logger.error_occurred(e, "processing strategy signals")
    
    async def _execute_signal(self, signal: Signal, strategy):
        """Execute a trading signal"""
        try:
            # Create trade from signal
            trade = strategy.create_trade_from_signal(signal)
            
            # Validate trade with risk manager
            is_valid, reason = self.risk_manager.validate_trade(trade, [])
            
            if not is_valid:
                logger.warning(f"Trade rejected by risk manager: {reason}")
                return
            
            # Execute trade on Avantis
            success = await self.avantis_client.open_trade(trade)
            
            if success:
                self.active_trades.append(trade)
                self.status.total_trades += 1
                self.status.successful_trades += 1
                
                logger.trade_opened({
                    'pair': trade.pair,
                    'direction': trade.direction.value,
                    'size': trade.size,
                    'leverage': trade.leverage,
                    'strategy': strategy.name
                })
            else:
                self.status.failed_trades += 1
                logger.error(f"Failed to execute trade for {trade.pair}")
                
        except Exception as e:
            logger.error_occurred(e, "executing signal")
            self.status.failed_trades += 1
    
    async def _check_exit_conditions(self):
        """Check exit conditions for all active trades"""
        try:
            trades_to_close = []
            
            for trade in self.active_trades:
                try:
                    # Get market data for this pair
                    market_data = self.market_data_cache.get(trade.pair)
                    if not market_data:
                        continue
                    
                    # Check strategy-specific exit conditions
                    strategy = self.strategies.get(trade.strategy.value)
                    should_exit = False
                    
                    if strategy:
                        should_exit = await strategy.should_exit(trade, market_data)
                    
                    # Check risk-based exit conditions
                    if not should_exit:
                        # Check if trade has been open too long
                        if trade.created_at:
                            time_open = datetime.now() - trade.created_at
                            if time_open.total_seconds() > 86400 * 7:  # 7 days
                                should_exit = True
                    
                    if should_exit:
                        trades_to_close.append(trade)
                        
                except Exception as e:
                    logger.error_occurred(e, f"checking exit conditions for {trade.pair}")
            
            # Close trades that met exit conditions
            for trade in trades_to_close:
                await self._close_trade(trade)
                
        except Exception as e:
            logger.error_occurred(e, "checking exit conditions")
    
    async def _close_trade(self, trade: Trade):
        """Close a trade"""
        try:
            # Close trade on Avantis
            success = await self.avantis_client.close_trade(trade)
            
            if success:
                # Calculate PnL (simplified)
                market_data = self.market_data_cache.get(trade.pair)
                if market_data:
                    if trade.direction == TradeDirection.LONG:
                        pnl = (market_data.price - trade.entry_price) / trade.entry_price * trade.size * trade.leverage
                    else:
                        pnl = (trade.entry_price - market_data.price) / trade.entry_price * trade.size * trade.leverage
                    
                    trade.pnl = pnl
                    trade.status = TradeStatus.CLOSED
                    trade.closed_at = datetime.now()
                    
                    # Update performance metrics
                    self.total_pnl += pnl
                    self.daily_pnl += pnl
                    self.risk_manager.update_trade_result(pnl)
                    
                    # Update strategy performance
                    strategy = self.strategies.get(trade.strategy.value)
                    if strategy:
                        strategy.update_performance(trade, pnl)
                
                # Move trade to closed trades
                self.active_trades.remove(trade)
                self.closed_trades.append(trade)
                
                logger.trade_closed({
                    'pair': trade.pair,
                    'pnl': trade.pnl or 0,
                    'strategy': trade.strategy.value
                })
                
        except Exception as e:
            logger.error_occurred(e, f"closing trade {trade.pair}")
    
    async def _update_risk_metrics(self):
        """Update risk management metrics"""
        try:
            # Calculate current positions
            positions = self._calculate_positions()
            
            # Update risk manager
            current_balance = self.start_balance + self.total_pnl
            self.risk_manager.update_balance(current_balance)
            
            # Get risk recommendations
            recommendations = self.risk_manager.get_position_recommendations(positions)
            
            for rec in recommendations:
                if rec['priority'] == 'high':
                    logger.risk_alert(f"High priority recommendation: {rec['action']} for {rec['pair']}")
                    
        except Exception as e:
            logger.error_occurred(e, "updating risk metrics")
    
    def _calculate_positions(self) -> List[Position]:
        """Calculate current positions from active trades"""
        positions = []
        position_map = {}
        
        for trade in self.active_trades:
            if trade.pair not in position_map:
                position_map[trade.pair] = {
                    'trades': [],
                    'total_size': 0,
                    'total_value': 0
                }
            
            position_map[trade.pair]['trades'].append(trade)
            
            # Calculate size (positive for long, negative for short)
            size = trade.size if trade.direction == TradeDirection.LONG else -trade.size
            position_map[trade.pair]['total_size'] += size
            position_map[trade.pair]['total_value'] += trade.size * trade.entry_price
        
        # Create position objects
        for pair, data in position_map.items():
            market_data = self.market_data_cache.get(pair)
            current_price = market_data.price if market_data else data['trades'][0].entry_price
            
            position = Position(
                pair=pair,
                total_size=data['total_size'],
                average_entry=data['total_value'] / abs(data['total_size']) if data['total_size'] != 0 else 0,
                current_price=current_price,
                unrealized_pnl=0,  # Would calculate based on current price
                realized_pnl=0,
                trades=data['trades'],
                leverage=data['trades'][0].leverage if data['trades'] else 1
            )
            positions.append(position)
        
        return positions
    
    async def _emergency_reduce_exposure(self):
        """Emergency reduction of exposure"""
        try:
            logger.critical("🚨 Emergency exposure reduction triggered")
            
            # Close 50% of positions
            trades_to_close = self.active_trades[:len(self.active_trades)//2]
            
            for trade in trades_to_close:
                await self._close_trade(trade)
                
            logger.critical(f"Emergency reduction: closed {len(trades_to_close)} trades")
            
        except Exception as e:
            logger.error_occurred(e, "emergency exposure reduction")
    
    def _log_performance_update(self):
        """Log performance update"""
        try:
            metrics = {
                'total_pnl': self.total_pnl,
                'daily_pnl': self.daily_pnl,
                'total_trades': self.status.total_trades,
                'active_trades': len(self.active_trades),
                'win_rate': self.risk_manager.winning_trades / max(self.risk_manager.total_trades, 1)
            }
            
            logger.performance_update(metrics)
            
        except Exception as e:
            logger.error_occurred(e, "logging performance update")
    
    async def _save_bot_state(self):
        """Save bot state to file"""
        try:
            state = {
                'status': asdict(self.status),
                'total_pnl': self.total_pnl,
                'daily_pnl': self.daily_pnl,
                'active_trades': [asdict(trade) for trade in self.active_trades],
                'closed_trades': [asdict(trade) for trade in self.closed_trades[-100:]],  # Keep last 100
                'strategies': {
                    name: strategy.get_performance_metrics() 
                    for name, strategy in self.strategies.items()
                },
                'timestamp': datetime.now().isoformat()
            }
            
            with open('bot_state.json', 'w') as f:
                json.dump(state, f, indent=2, default=str)
                
        except Exception as e:
            logger.error_occurred(e, "saving bot state")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bot status"""
        return {
            'is_running': self.is_running,
            'is_trading': self.is_trading,
            'status': asdict(self.status),
            'total_pnl': self.total_pnl,
            'daily_pnl': self.daily_pnl,
            'active_trades': len(self.active_trades),
            'closed_trades': len(self.closed_trades),
            'strategies': {
                name: strategy.get_performance_metrics() 
                for name, strategy in self.strategies.items()
            },
            'risk_metrics': asdict(self.risk_manager.get_risk_metrics())
        }
