"""
Dollar Cost Averaging (DCA) Strategy
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
from .base_strategy import BaseStrategy
from ..models import Signal, MarketData, StrategyType, TradeDirection
from ..logger import logger


class DCAStrategy(BaseStrategy):
    """
    Dollar Cost Averaging Strategy
    
    This strategy buys/sells at regular intervals regardless of price,
    helping to average out the cost basis over time.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("DCA Strategy", StrategyType.DCA, config)
        
        # DCA specific parameters
        self.interval_minutes = config.get('interval_minutes', 60)  # 1 hour default
        self.last_trade_time = {}
        self.direction = config.get('direction', 'long')  # 'long', 'short', or 'both'
        self.max_positions = config.get('max_positions', 10)
        
        logger.info(f"DCA Strategy initialized with {self.interval_minutes} minute intervals")
    
    async def analyze(self, market_data: MarketData) -> Optional[Signal]:
        """Generate DCA signals based on time intervals"""
        try:
            current_time = datetime.now()
            pair = market_data.pair
            
            # Check if enough time has passed since last trade
            last_trade = self.last_trade_time.get(pair)
            if last_trade:
                time_since_last = current_time - last_trade
                if time_since_last.total_seconds() < self.interval_minutes * 60:
                    return None
            
            # Determine trade direction
            if self.direction == 'long':
                direction = TradeDirection.LONG
            elif self.direction == 'short':
                direction = TradeDirection.SHORT
            else:  # 'both' - alternate between long and short
                trade_count = len(self.last_trade_time)
                direction = TradeDirection.LONG if trade_count % 2 == 0 else TradeDirection.SHORT
            
            # Calculate signal strength based on time since last trade
            if last_trade:
                hours_since_last = time_since_last.total_seconds() / 3600
                strength = min(1.0, hours_since_last / (self.interval_minutes / 60))
            else:
                strength = 1.0
            
            # Create signal
            signal = Signal(
                pair=pair,
                direction=direction,
                strength=strength,
                price=market_data.price,
                strategy=StrategyType.DCA,
                metadata={
                    'interval_minutes': self.interval_minutes,
                    'dca_type': self.direction,
                    'time_since_last': time_since_last.total_seconds() if last_trade else 0
                }
            )
            
            # Update last trade time
            self.last_trade_time[pair] = current_time
            self.signals_generated += 1
            
            logger.debug(f"DCA signal generated for {pair}: {direction.value} at {market_data.price}")
            return signal
            
        except Exception as e:
            logger.error_occurred(e, "DCA strategy analysis")
            return None
    
    async def should_exit(self, trade: Trade, market_data: MarketData) -> bool:
        """DCA strategy typically doesn't have specific exit conditions"""
        try:
            # Check if trade has been open for too long
            max_hold_time = self.config.get('max_hold_time_hours', 24 * 7)  # 7 days default
            if trade.created_at:
                hold_time = datetime.now() - trade.created_at
                if hold_time.total_seconds() > max_hold_time * 3600:
                    logger.info(f"DCA trade {trade.pair} held for {hold_time}, considering exit")
                    return True
            
            # Check if we've reached profit target
            if trade.take_profit and market_data.price:
                if trade.direction == TradeDirection.LONG and market_data.price >= trade.take_profit:
                    return True
                elif trade.direction == TradeDirection.SHORT and market_data.price <= trade.take_profit:
                    return True
            
            # Check stop loss
            if trade.stop_loss and market_data.price:
                if trade.direction == TradeDirection.LONG and market_data.price <= trade.stop_loss:
                    return True
                elif trade.direction == TradeDirection.SHORT and market_data.price >= trade.stop_loss:
                    return True
            
            return False
            
        except Exception as e:
            logger.error_occurred(e, "DCA strategy exit check")
            return False
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get DCA strategy specific information"""
        info = self.get_performance_metrics()
        info.update({
            'interval_minutes': self.interval_minutes,
            'direction': self.direction,
            'max_positions': self.max_positions,
            'active_pairs': list(self.last_trade_time.keys()),
            'next_trade_times': {
                pair: last_time + timedelta(minutes=self.interval_minutes)
                for pair, last_time in self.last_trade_time.items()
            }
        })
        return info
