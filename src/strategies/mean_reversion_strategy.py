"""
Mean Reversion Trading Strategy
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
from ..models import Signal, MarketData, StrategyType, TradeDirection
from ..logger import logger


class MeanReversionStrategy(BaseStrategy):
    """
    Mean Reversion Trading Strategy
    
    Identifies when prices deviate significantly from their mean
    and trades expecting a reversion to the mean.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("Mean Reversion Strategy", StrategyType.MEAN_REVERSION, config)
        
        # Mean reversion specific parameters
        self.lookback_period = config.get('lookback_period', 20)
        self.std_threshold = config.get('std_threshold', 2.0)  # 2 standard deviations
        self.z_score_entry = config.get('z_score_entry', 2.0)
        self.z_score_exit = config.get('z_score_exit', 0.5)
        self.bollinger_period = config.get('bollinger_period', 20)
        self.bollinger_std = config.get('bollinger_std', 2.0)
        
        # Price history for calculations
        self.price_history = {}
        
        logger.info(f"Mean Reversion Strategy initialized with {self.lookback_period} period and {self.std_threshold} std threshold")
    
    def _update_price_history(self, market_data: MarketData):
        """Update price history"""
        try:
            pair = market_data.pair
            
            if pair not in self.price_history:
                self.price_history[pair] = []
            
            # Add new data point
            self.price_history[pair].append({
                'price': market_data.price,
                'timestamp': market_data.timestamp
            })
            
            # Keep only last 200 data points
            if len(self.price_history[pair]) > 200:
                self.price_history[pair] = self.price_history[pair][-200:]
                
        except Exception as e:
            logger.error_occurred(e, "updating price history")
    
    def _calculate_z_score(self, prices: List[float], current_price: float) -> float:
        """Calculate Z-score for current price"""
        try:
            if len(prices) < 2:
                return 0
            
            mean_price = np.mean(prices)
            std_price = np.std(prices)
            
            if std_price == 0:
                return 0
            
            z_score = (current_price - mean_price) / std_price
            return z_score
            
        except Exception as e:
            logger.error_occurred(e, "calculating Z-score")
            return 0
    
    def _calculate_bollinger_bands(self, prices: List[float]) -> Dict[str, float]:
        """Calculate Bollinger Bands"""
        try:
            if len(prices) < self.bollinger_period:
                return {'upper': 0, 'middle': 0, 'lower': 0, 'width': 0}
            
            recent_prices = prices[-self.bollinger_period:]
            
            middle = np.mean(recent_prices)
            std = np.std(recent_prices)
            
            upper = middle + (self.bollinger_std * std)
            lower = middle - (self.bollinger_std * std)
            width = (upper - lower) / middle  # Band width as percentage
            
            return {
                'upper': upper,
                'middle': middle,
                'lower': lower,
                'width': width
            }
            
        except Exception as e:
            logger.error_occurred(e, "calculating Bollinger Bands")
            return {'upper': 0, 'middle': 0, 'lower': 0, 'width': 0}
    
    def _calculate_mean_reversion_signal(self, prices: List[float], current_price: float) -> Optional[Dict[str, Any]]:
        """Calculate mean reversion signal"""
        try:
            if len(prices) < self.lookback_period:
                return None
            
            # Calculate Z-score
            z_score = self._calculate_z_score(prices, current_price)
            
            # Calculate Bollinger Bands
            bollinger = self._calculate_bollinger_bands(prices)
            
            # Determine signal
            signal_data = {
                'z_score': z_score,
                'bollinger': bollinger,
                'direction': None,
                'strength': 0.0
            }
            
            # Oversold conditions (buy signal)
            if (z_score <= -self.z_score_entry and 
                current_price <= bollinger['lower'] and
                bollinger['width'] > 0.02):  # Ensure bands are wide enough
                
                signal_data['direction'] = TradeDirection.LONG
                signal_data['strength'] = min(0.9, abs(z_score) / self.z_score_entry)
            
            # Overbought conditions (sell signal)
            elif (z_score >= self.z_score_entry and 
                  current_price >= bollinger['upper'] and
                  bollinger['width'] > 0.02):  # Ensure bands are wide enough
                
                signal_data['direction'] = TradeDirection.SHORT
                signal_data['strength'] = min(0.9, abs(z_score) / self.z_score_entry)
            
            return signal_data if signal_data['direction'] else None
            
        except Exception as e:
            logger.error_occurred(e, "calculating mean reversion signal")
            return None
    
    async def analyze(self, market_data: MarketData) -> Optional[Signal]:
        """Generate mean reversion trading signals"""
        try:
            pair = market_data.pair
            current_price = market_data.price
            
            # Update price history
            self._update_price_history(market_data)
            
            # Need sufficient data for analysis
            if pair not in self.price_history or len(self.price_history[pair]) < self.lookback_period:
                return None
            
            prices = [point['price'] for point in self.price_history[pair]]
            
            # Calculate mean reversion signal
            signal_data = self._calculate_mean_reversion_signal(prices, current_price)
            
            if signal_data and signal_data['direction']:
                # Check if signal strength meets minimum threshold
                if signal_data['strength'] >= self.config.get('min_signal_strength', 0.6):
                    signal = Signal(
                        pair=pair,
                        direction=signal_data['direction'],
                        strength=signal_data['strength'],
                        price=current_price,
                        strategy=StrategyType.MEAN_REVERSION,
                        metadata={
                            'z_score': signal_data['z_score'],
                            'bollinger_upper': signal_data['bollinger']['upper'],
                            'bollinger_middle': signal_data['bollinger']['middle'],
                            'bollinger_lower': signal_data['bollinger']['lower'],
                            'bollinger_width': signal_data['bollinger']['width'],
                            'lookback_period': self.lookback_period
                        }
                    )
                    
                    self.signals_generated += 1
                    logger.debug(f"Mean reversion signal generated for {pair}: {signal_data['direction'].value} "
                               f"(Z-score: {signal_data['z_score']:.2f})")
                    return signal
            
            return None
            
        except Exception as e:
            logger.error_occurred(e, "Mean reversion strategy analysis")
            return None
    
    async def should_exit(self, trade: Trade, market_data: MarketData) -> bool:
        """Mean reversion strategy exit conditions"""
        try:
            pair = market_data.pair
            current_price = market_data.price
            
            # Need price history for analysis
            if pair not in self.price_history or len(self.price_history[pair]) < self.lookback_period:
                return False
            
            prices = [point['price'] for point in self.price_history[pair]]
            z_score = self._calculate_z_score(prices, current_price)
            
            # Exit conditions based on Z-score
            if trade.direction == TradeDirection.LONG:
                # Exit long when price approaches or exceeds mean (Z-score close to 0 or positive)
                if z_score >= -self.z_score_exit:
                    return True
            else:
                # Exit short when price approaches or falls below mean (Z-score close to 0 or negative)
                if z_score <= self.z_score_exit:
                    return True
            
            # Check Bollinger Bands for exit
            bollinger = self._calculate_bollinger_bands(prices)
            if bollinger['middle'] > 0:
                if trade.direction == TradeDirection.LONG and current_price >= bollinger['middle']:
                    return True
                elif trade.direction == TradeDirection.SHORT and current_price <= bollinger['middle']:
                    return True
            
            # Check stop loss and take profit
            if trade.stop_loss and current_price <= trade.stop_loss:
                return True
            if trade.take_profit and current_price >= trade.take_profit:
                return True
            
            return False
            
        except Exception as e:
            logger.error_occurred(e, "Mean reversion strategy exit check")
            return False
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get mean reversion strategy specific information"""
        info = self.get_performance_metrics()
        info.update({
            'lookback_period': self.lookback_period,
            'std_threshold': self.std_threshold,
            'z_score_entry': self.z_score_entry,
            'z_score_exit': self.z_score_exit,
            'bollinger_period': self.bollinger_period,
            'bollinger_std': self.bollinger_std,
            'active_pairs': list(self.price_history.keys()),
            'data_points_per_pair': {
                pair: len(data) for pair, data in self.price_history.items()
            }
        })
        return info
