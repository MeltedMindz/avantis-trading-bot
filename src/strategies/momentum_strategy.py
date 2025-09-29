"""
Momentum Trading Strategy
"""

import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
from ..models import Signal, MarketData, StrategyType, TradeDirection
from ..logger import logger


class MomentumStrategy(BaseStrategy):
    """
    Momentum Trading Strategy
    
    Identifies and trades in the direction of strong price momentum
    using technical indicators like RSI, MACD, and moving averages.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("Momentum Strategy", StrategyType.MOMENTUM, config)
        
        # Momentum specific parameters
        self.rsi_period = config.get('rsi_period', 14)
        self.rsi_oversold = config.get('rsi_oversold', 30)
        self.rsi_overbought = config.get('rsi_overbought', 70)
        self.macd_fast = config.get('macd_fast', 12)
        self.macd_slow = config.get('macd_slow', 26)
        self.macd_signal = config.get('macd_signal', 9)
        self.ma_short = config.get('ma_short', 10)
        self.ma_long = config.get('ma_long', 50)
        self.volume_threshold = config.get('volume_threshold', 1.5)  # 1.5x average volume
        
        # Price history for calculations
        self.price_history = {}
        self.volume_history = {}
        
        logger.info(f"Momentum Strategy initialized with RSI({self.rsi_period}), MACD({self.macd_fast},{self.macd_slow},{self.macd_signal})")
    
    def _update_price_history(self, market_data: MarketData):
        """Update price and volume history"""
        try:
            pair = market_data.pair
            
            if pair not in self.price_history:
                self.price_history[pair] = []
                self.volume_history[pair] = []
            
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
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI indicator"""
        try:
            if len(prices) < period + 1:
                return 50  # Neutral RSI if not enough data
            
            prices = prices[-period-1:]
            deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            
            gains = [delta if delta > 0 else 0 for delta in deltas]
            losses = [-delta if delta < 0 else 0 for delta in deltas]
            
            avg_gain = sum(gains) / period
            avg_loss = sum(losses) / period
            
            if avg_loss == 0:
                return 100
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            logger.error_occurred(e, "calculating RSI")
            return 50
    
    def _calculate_macd(self, prices: List[float]) -> Dict[str, float]:
        """Calculate MACD indicator"""
        try:
            if len(prices) < self.macd_slow:
                return {'macd': 0, 'signal': 0, 'histogram': 0}
            
            prices = prices[-self.macd_slow:]
            
            # Calculate EMAs
            ema_fast = self._calculate_ema(prices, self.macd_fast)
            ema_slow = self._calculate_ema(prices, self.macd_slow)
            
            macd_line = ema_fast - ema_slow
            
            # Calculate signal line (EMA of MACD)
            # For simplicity, we'll use a simple average for signal line
            signal_line = macd_line * 0.9  # Simplified signal line
            
            histogram = macd_line - signal_line
            
            return {
                'macd': macd_line,
                'signal': signal_line,
                'histogram': histogram
            }
            
        except Exception as e:
            logger.error_occurred(e, "calculating MACD")
            return {'macd': 0, 'signal': 0, 'histogram': 0}
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average"""
        try:
            if len(prices) < period:
                return prices[-1] if prices else 0
            
            prices = prices[-period:]
            multiplier = 2 / (period + 1)
            
            ema = prices[0]
            for price in prices[1:]:
                ema = (price * multiplier) + (ema * (1 - multiplier))
            
            return ema
            
        except Exception as e:
            logger.error_occurred(e, "calculating EMA")
            return prices[-1] if prices else 0
    
    def _calculate_ma(self, prices: List[float], period: int) -> float:
        """Calculate Simple Moving Average"""
        try:
            if len(prices) < period:
                return prices[-1] if prices else 0
            
            return sum(prices[-period:]) / period
            
        except Exception as e:
            logger.error_occurred(e, "calculating MA")
            return prices[-1] if prices else 0
    
    def _check_volume_confirmation(self, pair: str) -> bool:
        """Check if current volume confirms momentum"""
        try:
            if pair not in self.volume_history or len(self.volume_history[pair]) < 20:
                return True  # Assume confirmed if no volume data
            
            recent_volumes = self.volume_history[pair][-20:]
            current_volume = recent_volumes[-1]
            avg_volume = sum(recent_volumes[:-1]) / len(recent_volumes[:-1])
            
            return current_volume >= avg_volume * self.volume_threshold
            
        except Exception as e:
            logger.error_occurred(e, "checking volume confirmation")
            return True
    
    async def analyze(self, market_data: MarketData) -> Optional[Signal]:
        """Generate momentum trading signals"""
        try:
            pair = market_data.pair
            current_price = market_data.price
            
            # Update price history
            self._update_price_history(market_data)
            
            # Need sufficient data for analysis
            if pair not in self.price_history or len(self.price_history[pair]) < self.ma_long:
                return None
            
            prices = [point['price'] for point in self.price_history[pair]]
            
            # Calculate indicators
            rsi = self._calculate_rsi(prices, self.rsi_period)
            macd_data = self._calculate_macd(prices)
            ma_short = self._calculate_ma(prices, self.ma_short)
            ma_long = self._calculate_ma(prices, self.ma_long)
            
            # Check volume confirmation
            volume_confirmed = self._check_volume_confirmation(pair)
            
            # Generate signals based on momentum conditions
            signal_strength = 0.0
            direction = None
            
            # Bullish momentum conditions
            if (rsi > 50 and rsi < self.rsi_overbought and  # RSI in bullish range
                macd_data['macd'] > macd_data['signal'] and  # MACD bullish
                macd_data['histogram'] > 0 and  # MACD histogram positive
                ma_short > ma_long and  # Short MA above long MA
                current_price > ma_short and  # Price above short MA
                volume_confirmed):
                
                direction = TradeDirection.LONG
                signal_strength = min(0.9, (rsi - 50) / 50 + 0.5)
            
            # Bearish momentum conditions
            elif (rsi < 50 and rsi > self.rsi_oversold and  # RSI in bearish range
                  macd_data['macd'] < macd_data['signal'] and  # MACD bearish
                  macd_data['histogram'] < 0 and  # MACD histogram negative
                  ma_short < ma_long and  # Short MA below long MA
                  current_price < ma_short and  # Price below short MA
                  volume_confirmed):
                
                direction = TradeDirection.SHORT
                signal_strength = min(0.9, (50 - rsi) / 50 + 0.5)
            
            # Create signal if conditions are met
            if direction and signal_strength >= self.config.get('min_signal_strength', 0.6):
                signal = Signal(
                    pair=pair,
                    direction=direction,
                    strength=signal_strength,
                    price=current_price,
                    strategy=StrategyType.MOMENTUM,
                    metadata={
                        'rsi': rsi,
                        'macd': macd_data['macd'],
                        'macd_signal': macd_data['signal'],
                        'macd_histogram': macd_data['histogram'],
                        'ma_short': ma_short,
                        'ma_long': ma_long,
                        'volume_confirmed': volume_confirmed
                    }
                )
                
                self.signals_generated += 1
                logger.debug(f"Momentum signal generated for {pair}: {direction.value} (RSI: {rsi:.2f}, MACD: {macd_data['macd']:.4f})")
                return signal
            
            return None
            
        except Exception as e:
            logger.error_occurred(e, "Momentum strategy analysis")
            return None
    
    async def should_exit(self, trade: Trade, market_data: MarketData) -> bool:
        """Momentum strategy exit conditions"""
        try:
            pair = market_data.pair
            current_price = market_data.price
            
            # Need price history for analysis
            if pair not in self.price_history or len(self.price_history[pair]) < self.rsi_period:
                return False
            
            prices = [point['price'] for point in self.price_history[pair]]
            rsi = self._calculate_rsi(prices, self.rsi_period)
            
            # Exit if momentum reverses
            if trade.direction == TradeDirection.LONG:
                # Exit long if RSI becomes overbought or momentum weakens
                if rsi > self.rsi_overbought or rsi < 45:
                    return True
            else:
                # Exit short if RSI becomes oversold or momentum weakens
                if rsi < self.rsi_oversold or rsi > 55:
                    return True
            
            # Check stop loss and take profit
            if trade.stop_loss and current_price <= trade.stop_loss:
                return True
            if trade.take_profit and current_price >= trade.take_profit:
                return True
            
            return False
            
        except Exception as e:
            logger.error_occurred(e, "Momentum strategy exit check")
            return False
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get momentum strategy specific information"""
        info = self.get_performance_metrics()
        info.update({
            'rsi_period': self.rsi_period,
            'rsi_oversold': self.rsi_oversold,
            'rsi_overbought': self.rsi_overbought,
            'macd_fast': self.macd_fast,
            'macd_slow': self.macd_slow,
            'macd_signal': self.macd_signal,
            'ma_short': self.ma_short,
            'ma_long': self.ma_long,
            'volume_threshold': self.volume_threshold,
            'active_pairs': list(self.price_history.keys()),
            'data_points_per_pair': {
                pair: len(data) for pair, data in self.price_history.items()
            }
        })
        return info
