"""
Breakout Trading Strategy
"""

import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
from ..models import Signal, MarketData, StrategyType, TradeDirection
from ..logger import logger


class BreakoutStrategy(BaseStrategy):
    """
    Breakout Trading Strategy
    
    Identifies when prices break through key support/resistance levels
    and trades in the direction of the breakout.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("Breakout Strategy", StrategyType.BREAKOUT, config)
        
        # Breakout specific parameters
        self.lookback_period = config.get('lookback_period', 20)
        self.breakout_threshold = config.get('breakout_threshold', 0.02)  # 2% breakout
        self.confirmation_candles = config.get('confirmation_candles', 2)
        self.volume_multiplier = config.get('volume_multiplier', 1.5)  # 1.5x average volume
        self.min_range_size = config.get('min_range_size', 0.01)  # 1% minimum range
        
        # Support/Resistance tracking
        self.support_resistance = {}
        self.price_history = {}
        self.volume_history = {}
        
        logger.info(f"Breakout Strategy initialized with {self.lookback_period} period and {self.breakout_threshold*100}% threshold")
    
    def _update_price_history(self, market_data: MarketData):
        """Update price and volume history"""
        try:
            pair = market_data.pair
            
            if pair not in self.price_history:
                self.price_history[pair] = []
                self.volume_history[pair] = []
                self.support_resistance[pair] = {
                    'support': [],
                    'resistance': [],
                    'last_update': None
                }
            
            # Add new data point
            self.price_history[pair].append({
                'price': market_data.price,
                'timestamp': market_data.timestamp,
                'volume': market_data.volume or 0
            })
            self.volume_history[pair].append(market_data.volume or 0)
            
            # Keep only last 200 data points
            if len(self.price_history[pair]) > 200:
                self.price_history[pair] = self.price_history[pair][-200:]
                self.volume_history[pair] = self.volume_history[pair][-200:]
                
        except Exception as e:
            logger.error_occurred(e, "updating price history")
    
    def _find_support_resistance(self, prices: List[float]) -> Dict[str, List[float]]:
        """Find support and resistance levels"""
        try:
            if len(prices) < 10:
                return {'support': [], 'resistance': []}
            
            # Find local minima (support) and maxima (resistance)
            support_levels = []
            resistance_levels = []
            
            # Use a simple peak detection algorithm
            for i in range(2, len(prices) - 2):
                # Local minimum (support)
                if (prices[i] < prices[i-1] and prices[i] < prices[i-2] and
                    prices[i] < prices[i+1] and prices[i] < prices[i+2]):
                    support_levels.append(prices[i])
                
                # Local maximum (resistance)
                if (prices[i] > prices[i-1] and prices[i] > prices[i-2] and
                    prices[i] > prices[i+1] and prices[i] > prices[i+2]):
                    resistance_levels.append(prices[i])
            
            # Remove duplicates and sort
            support_levels = sorted(list(set(support_levels)))
            resistance_levels = sorted(list(set(resistance_levels)))
            
            # Keep only recent and significant levels
            recent_support = [s for s in support_levels if s > min(prices[-10:])]
            recent_resistance = [r for r in resistance_levels if r < max(prices[-10:])]
            
            return {
                'support': recent_support[-3:],  # Keep last 3 support levels
                'resistance': recent_resistance[-3:]  # Keep last 3 resistance levels
            }
            
        except Exception as e:
            logger.error_occurred(e, "finding support/resistance")
            return {'support': [], 'resistance': []}
    
    def _detect_breakout(self, pair: str, current_price: float) -> Optional[Dict[str, Any]]:
        """Detect breakout patterns"""
        try:
            if pair not in self.price_history or len(self.price_history[pair]) < self.lookback_period:
                return None
            
            prices = [point['price'] for point in self.price_history[pair]]
            volumes = self.volume_history[pair]
            
            # Find support and resistance levels
            levels = self._find_support_resistance(prices)
            
            # Calculate average volume
            avg_volume = np.mean(volumes[-20:]) if len(volumes) >= 20 else volumes[-1] if volumes else 1
            current_volume = volumes[-1] if volumes else 1
            
            # Check for resistance breakout (bullish)
            for resistance in levels['resistance']:
                if (current_price > resistance * (1 + self.breakout_threshold) and
                    current_volume >= avg_volume * self.volume_multiplier):
                    
                    return {
                        'direction': TradeDirection.LONG,
                        'breakout_level': resistance,
                        'current_price': current_price,
                        'strength': min(0.9, (current_price - resistance) / resistance),
                        'volume_confirmed': current_volume / avg_volume,
                        'breakout_type': 'resistance'
                    }
            
            # Check for support breakdown (bearish)
            for support in levels['support']:
                if (current_price < support * (1 - self.breakout_threshold) and
                    current_volume >= avg_volume * self.volume_multiplier):
                    
                    return {
                        'direction': TradeDirection.SHORT,
                        'breakout_level': support,
                        'current_price': current_price,
                        'strength': min(0.9, (support - current_price) / support),
                        'volume_confirmed': current_volume / avg_volume,
                        'breakout_type': 'support'
                    }
            
            return None
            
        except Exception as e:
            logger.error_occurred(e, "detecting breakout")
            return None
    
    def _check_range_consolidation(self, prices: List[float]) -> bool:
        """Check if price is in a consolidation range"""
        try:
            if len(prices) < self.lookback_period:
                return False
            
            recent_prices = prices[-self.lookback_period:]
            price_range = max(recent_prices) - min(recent_prices)
            avg_price = np.mean(recent_prices)
            
            # Check if price is consolidating (small range relative to average price)
            range_percentage = price_range / avg_price
            
            return range_percentage < self.min_range_size
            
        except Exception as e:
            logger.error_occurred(e, "checking range consolidation")
            return False
    
    async def analyze(self, market_data: MarketData) -> Optional[Signal]:
        """Generate breakout trading signals"""
        try:
            pair = market_data.pair
            current_price = market_data.price
            
            # Update price history
            self._update_price_history(market_data)
            
            # Need sufficient data for analysis
            if pair not in self.price_history or len(self.price_history[pair]) < self.lookback_period:
                return None
            
            prices = [point['price'] for point in self.price_history[pair]]
            
            # Check if price was in consolidation before breakout
            if not self._check_range_consolidation(prices):
                return None
            
            # Detect breakout
            breakout_data = self._detect_breakout(pair, current_price)
            
            if breakout_data and breakout_data['strength'] >= self.config.get('min_signal_strength', 0.6):
                signal = Signal(
                    pair=pair,
                    direction=breakout_data['direction'],
                    strength=breakout_data['strength'],
                    price=current_price,
                    strategy=StrategyType.BREAKOUT,
                    metadata={
                        'breakout_level': breakout_data['breakout_level'],
                        'breakout_type': breakout_data['breakout_type'],
                        'volume_confirmed': breakout_data['volume_confirmed'],
                        'strength': breakout_data['strength'],
                        'lookback_period': self.lookback_period
                    }
                )
                
                self.signals_generated += 1
                logger.debug(f"Breakout signal generated for {pair}: {breakout_data['direction'].value} "
                           f"from {breakout_data['breakout_type']} at {breakout_data['breakout_level']}")
                return signal
            
            return None
            
        except Exception as e:
            logger.error_occurred(e, "Breakout strategy analysis")
            return None
    
    async def should_exit(self, trade: Trade, market_data: MarketData) -> bool:
        """Breakout strategy exit conditions"""
        try:
            pair = market_data.pair
            current_price = market_data.price
            
            # Need price history for analysis
            if pair not in self.price_history or len(self.price_history[pair]) < self.lookback_period:
                return False
            
            prices = [point['price'] for point in self.price_history[pair]]
            
            # Exit if price breaks back through the breakout level (false breakout)
            breakout_level = trade.metadata.get('breakout_level') if hasattr(trade, 'metadata') else None
            
            if breakout_level:
                if trade.direction == TradeDirection.LONG:
                    # Exit long if price falls back below resistance
                    if current_price < breakout_level * 0.98:  # 2% buffer
                        logger.info(f"False breakout detected for {pair} long position")
                        return True
                else:
                    # Exit short if price rises back above support
                    if current_price > breakout_level * 1.02:  # 2% buffer
                        logger.info(f"False breakout detected for {pair} short position")
                        return True
            
            # Exit if breakout momentum weakens (price moves back into consolidation)
            if self._check_range_consolidation(prices):
                logger.info(f"Breakout momentum weakening for {pair}")
                return True
            
            # Check stop loss and take profit
            if trade.stop_loss and current_price <= trade.stop_loss:
                return True
            if trade.take_profit and current_price >= trade.take_profit:
                return True
            
            return False
            
        except Exception as e:
            logger.error_occurred(e, "Breakout strategy exit check")
            return False
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get breakout strategy specific information"""
        info = self.get_performance_metrics()
        info.update({
            'lookback_period': self.lookback_period,
            'breakout_threshold': self.breakout_threshold,
            'confirmation_candles': self.confirmation_candles,
            'volume_multiplier': self.volume_multiplier,
            'min_range_size': self.min_range_size,
            'active_pairs': list(self.price_history.keys()),
            'data_points_per_pair': {
                pair: len(data) for pair, data in self.price_history.items()
            },
            'support_resistance_levels': {
                pair: {
                    'support': data['support'],
                    'resistance': data['resistance']
                }
                for pair, data in self.support_resistance.items()
            }
        })
        return info
