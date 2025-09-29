"""
Base strategy class for all trading strategies
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from ..models import Signal, Trade, MarketData, StrategyType, TradeDirection
from ..logger import logger


class BaseStrategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, name: str, strategy_type: StrategyType, config: Dict[str, Any]):
        self.name = name
        self.strategy_type = strategy_type
        self.config = config
        self.enabled = config.get('enabled', True)
        self.pairs = config.get('pairs', [])
        self.leverage = config.get('leverage', 10)
        self.position_size = config.get('position_size', 10.0)
        
        # Performance tracking
        self.signals_generated = 0
        self.trades_executed = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        
        logger.info(f"Initialized strategy: {self.name}")
    
    @abstractmethod
    async def analyze(self, market_data: MarketData) -> Optional[Signal]:
        """
        Analyze market data and generate trading signals
        
        Args:
            market_data: Current market data
            
        Returns:
            Signal object if a trade should be executed, None otherwise
        """
        pass
    
    @abstractmethod
    async def should_exit(self, trade: Trade, market_data: MarketData) -> bool:
        """
        Determine if a trade should be exited
        
        Args:
            trade: Current trade to evaluate
            market_data: Current market data
            
        Returns:
            True if trade should be exited, False otherwise
        """
        pass
    
    def validate_signal(self, signal: Signal) -> bool:
        """Validate a trading signal"""
        try:
            # Check if strategy is enabled
            if not self.enabled:
                return False
            
            # Check if pair is supported
            if signal.pair not in self.pairs:
                return False
            
            # Check signal strength
            if signal.strength < self.config.get('min_signal_strength', 0.6):
                return False
            
            # Check if we have required parameters
            if not signal.price or signal.price <= 0:
                return False
            
            return True
            
        except Exception as e:
            logger.error_occurred(e, f"validating signal in {self.name}")
            return False
    
    def create_trade_from_signal(self, signal: Signal) -> Trade:
        """Create a trade object from a signal"""
        try:
            trade = Trade(
                pair=signal.pair,
                direction=signal.direction,
                entry_price=signal.price,
                size=self.position_size,
                leverage=self.leverage,
                strategy=self.strategy_type,
                stop_loss=self._calculate_stop_loss(signal),
                take_profit=self._calculate_take_profit(signal)
            )
            
            return trade
            
        except Exception as e:
            logger.error_occurred(e, f"creating trade from signal in {self.name}")
            raise
    
    def _calculate_stop_loss(self, signal: Signal) -> float:
        """Calculate stop loss price"""
        stop_loss_pct = self.config.get('stop_loss_percentage', 5.0)
        
        if signal.direction == TradeDirection.LONG:
            return signal.price * (1 - stop_loss_pct / 100)
        else:
            return signal.price * (1 + stop_loss_pct / 100)
    
    def _calculate_take_profit(self, signal: Signal) -> float:
        """Calculate take profit price"""
        take_profit_pct = self.config.get('take_profit_percentage', 10.0)
        
        if signal.direction == TradeDirection.LONG:
            return signal.price * (1 + take_profit_pct / 100)
        else:
            return signal.price * (1 - take_profit_pct / 100)
    
    def update_performance(self, trade: Trade, pnl: float):
        """Update strategy performance metrics"""
        try:
            self.trades_executed += 1
            self.total_pnl += pnl
            
            if pnl > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1
            
            logger.debug(f"Strategy {self.name} performance updated: PnL={pnl}, Total={self.total_pnl}")
            
        except Exception as e:
            logger.error_occurred(e, f"updating performance in {self.name}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get strategy performance metrics"""
        win_rate = self.winning_trades / self.trades_executed if self.trades_executed > 0 else 0
        
        return {
            'name': self.name,
            'type': self.strategy_type.value,
            'enabled': self.enabled,
            'signals_generated': self.signals_generated,
            'trades_executed': self.trades_executed,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'total_pnl': self.total_pnl,
            'average_pnl': self.total_pnl / self.trades_executed if self.trades_executed > 0 else 0
        }
    
    def reset_performance(self):
        """Reset performance metrics"""
        self.signals_generated = 0
        self.trades_executed = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        
        logger.info(f"Performance metrics reset for strategy: {self.name}")
    
    def enable(self):
        """Enable the strategy"""
        self.enabled = True
        logger.info(f"Strategy enabled: {self.name}")
    
    def disable(self):
        """Disable the strategy"""
        self.enabled = False
        logger.info(f"Strategy disabled: {self.name}")
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update strategy configuration"""
        try:
            self.config.update(new_config)
            
            # Update instance variables
            self.enabled = self.config.get('enabled', self.enabled)
            self.pairs = self.config.get('pairs', self.pairs)
            self.leverage = self.config.get('leverage', self.leverage)
            self.position_size = self.config.get('position_size', self.position_size)
            
            logger.info(f"Configuration updated for strategy: {self.name}")
            
        except Exception as e:
            logger.error_occurred(e, f"updating config for {self.name}")
    
    def __str__(self):
        return f"{self.name} ({self.strategy_type.value})"
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(name='{self.name}', type='{self.strategy_type.value}', enabled={self.enabled})>"
