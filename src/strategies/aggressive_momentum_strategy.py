"""
Aggressive Momentum Strategy for 10% Daily Returns
High-frequency, high-leverage trading with quick profit taking
"""

import asyncio
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

try:
    from .base_strategy import BaseStrategy
    from ..models import Trade, TradeDirection, OrderType
    from ..logger import logger
except ImportError:
    from base_strategy import BaseStrategy
    from models import Trade, TradeDirection, OrderType
    from logger import logger


@dataclass
class AggressiveSignal:
    """Enhanced signal for aggressive trading"""
    pair: str
    direction: TradeDirection
    confidence: float
    urgency: str  # "HIGH", "MEDIUM", "LOW"
    expected_return: float
    time_horizon: int  # Expected holding time in minutes
    leverage: int
    position_size: float


class AggressiveMomentumStrategy(BaseStrategy):
    """Aggressive momentum strategy optimized for daily profit targets"""
    
    def __init__(self):
        super().__init__()
        self.name = "Aggressive Momentum"
        self.description = "High-frequency momentum trading for 10% daily returns"
        
        # Aggressive parameters
        self.min_confidence = 0.65  # Lower threshold for more signals
        self.max_leverage = 50
        self.quick_profit_threshold = 3.0  # Take profit at 3%
        self.quick_stop_loss = 1.5  # Stop loss at 1.5%
        self.max_hold_time = 60  # Maximum hold time in minutes
        
        # Multi-timeframe analysis
        self.timeframes = [1, 5, 15, 30]  # minutes
        self.volume_threshold = 1.5  # 50% above average volume
        
        # Momentum indicators
        self.rsi_oversold = 25  # More aggressive oversold
        self.rsi_overbought = 75  # More aggressive overbought
        self.macd_signal_threshold = 0.3  # Lower threshold for signals
        self.ma_crossover_sensitivity = 0.5  # More sensitive to crossovers
        
        # Volatility filters
        self.min_volatility = 0.01  # Minimum volatility for signals
        self.max_volatility = 0.15  # Maximum volatility for safety
        
    async def initialize(self):
        """Initialize the aggressive momentum strategy"""
        await super().initialize()
        logger.info(f"🚀 {self.name} Strategy initialized (Aggressive Mode)")
        logger.info(f"   Max Leverage: {self.max_leverage}x")
        logger.info(f"   Quick Profit: {self.quick_profit_threshold}%")
        logger.info(f"   Quick Stop Loss: {self.quick_stop_loss}%")
        logger.info(f"   Max Hold Time: {self.max_hold_time} minutes")
    
    async def analyze(self, market_data: Dict) -> Dict[str, AggressiveSignal]:
        """Analyze market data and generate aggressive trading signals"""
        signals = {}
        
        for pair, data in market_data.items():
            try:
                signal = await self._analyze_pair_aggressive(pair, data)
                if signal:
                    signals[pair] = signal
                    
            except Exception as e:
                logger.error_occurred(e, f"analyzing {pair} aggressively")
                continue
        
        # Sort signals by urgency and confidence
        sorted_signals = dict(sorted(
            signals.items(), 
            key=lambda x: (x[1].urgency == "HIGH", x[1].confidence), 
            reverse=True
        ))
        
        return sorted_signals
    
    async def _analyze_pair_aggressive(self, pair: str, data: Dict) -> Optional[AggressiveSignal]:
        """Analyze a single pair for aggressive momentum signals"""
        
        # Extract indicators
        price = data.get('price', 0)
        volume = data.get('volume', 0)
        rsi = data.get('rsi', 50)
        macd = data.get('macd', 0)
        macd_signal = data.get('macd_signal', 0)
        ma_20 = data.get('ma_20', price)
        ma_50 = data.get('ma_50', price)
        ma_5 = data.get('ma_5', price)
        volatility = data.get('volatility', 0.02)
        
        if price <= 0:
            return None
        
        # Calculate momentum score
        momentum_score = await self._calculate_momentum_score(
            price, rsi, macd, macd_signal, ma_5, ma_20, ma_50, volatility
        )
        
        # Volume confirmation
        volume_ratio = data.get('volume_ratio', 1.0)
        volume_confirmed = volume_ratio >= self.volume_threshold
        
        # Volatility filter
        if volatility < self.min_volatility or volatility > self.max_volatility:
            return None
        
        # Determine signal strength
        confidence = momentum_score * 0.7 + (1.0 if volume_confirmed else 0.3) * 0.3
        
        if confidence < self.min_confidence:
            return None
        
        # Determine direction
        direction = TradeDirection.LONG if momentum_score > 0 else TradeDirection.SHORT
        
        # Determine urgency based on multiple factors
        urgency = await self._determine_urgency(
            momentum_score, volume_ratio, volatility, rsi, macd
        )
        
        # Calculate expected return and time horizon
        expected_return = await self._calculate_expected_return(
            momentum_score, volatility, direction
        )
        
        time_horizon = await self._calculate_time_horizon(
            volatility, momentum_score, urgency
        )
        
        # Calculate optimal leverage
        leverage = await self._calculate_aggressive_leverage(
            volatility, confidence, urgency
        )
        
        # Calculate position size
        position_size = await self._calculate_aggressive_position_size(
            confidence, volatility, leverage, expected_return
        )
        
        return AggressiveSignal(
            pair=pair,
            direction=direction,
            confidence=confidence,
            urgency=urgency,
            expected_return=expected_return,
            time_horizon=time_horizon,
            leverage=leverage,
            position_size=position_size
        )
    
    async def _calculate_momentum_score(self, price: float, rsi: float, macd: float, 
                                      macd_signal: float, ma_5: float, ma_20: float, 
                                      ma_50: float, volatility: float) -> float:
        """Calculate aggressive momentum score"""
        score = 0.0
        
        # RSI momentum (more aggressive thresholds)
        if rsi < self.rsi_oversold:
            score += 0.3  # Strong oversold bounce potential
        elif rsi > self.rsi_overbought:
            score -= 0.3  # Strong overbought sell potential
        elif rsi < 35:
            score += 0.2  # Moderate oversold
        elif rsi > 65:
            score -= 0.2  # Moderate overbought
        
        # MACD momentum
        macd_diff = macd - macd_signal
        if abs(macd_diff) > self.macd_signal_threshold:
            score += 0.3 if macd_diff > 0 else -0.3
        
        # Moving average momentum
        ma_score = 0.0
        if ma_5 > ma_20 > ma_50:
            ma_score = 0.2  # Strong uptrend
        elif ma_5 < ma_20 < ma_50:
            ma_score = -0.2  # Strong downtrend
        elif ma_5 > ma_20:
            ma_score = 0.1  # Weak uptrend
        elif ma_5 < ma_20:
            ma_score = -0.1  # Weak downtrend
        
        score += ma_score
        
        # Price momentum (rate of change)
        price_momentum = (price - ma_20) / ma_20
        if abs(price_momentum) > 0.02:  # 2% deviation from MA
            score += price_momentum * 5  # Amplify momentum
        
        # Volatility adjustment (higher volatility = higher potential returns)
        volatility_multiplier = min(2.0, 1.0 + volatility * 10)
        score *= volatility_multiplier
        
        # Normalize to [-1, 1]
        return np.tanh(score)
    
    async def _determine_urgency(self, momentum_score: float, volume_ratio: float, 
                               volatility: float, rsi: float, macd: float) -> str:
        """Determine signal urgency"""
        urgency_score = 0.0
        
        # High momentum = high urgency
        urgency_score += abs(momentum_score) * 0.4
        
        # High volume = high urgency
        urgency_score += min(volume_ratio - 1.0, 1.0) * 0.3
        
        # High volatility = high urgency
        urgency_score += min(volatility * 10, 1.0) * 0.2
        
        # Extreme RSI = high urgency
        if rsi < 20 or rsi > 80:
            urgency_score += 0.3
        elif rsi < 30 or rsi > 70:
            urgency_score += 0.2
        
        # Strong MACD = high urgency
        if abs(macd) > 0.5:
            urgency_score += 0.2
        
        if urgency_score >= 0.7:
            return "HIGH"
        elif urgency_score >= 0.4:
            return "MEDIUM"
        else:
            return "LOW"
    
    async def _calculate_expected_return(self, momentum_score: float, 
                                      volatility: float, direction: TradeDirection) -> float:
        """Calculate expected return for the trade"""
        base_return = abs(momentum_score) * 0.08  # Up to 8% base return
        
        # Volatility amplification
        volatility_multiplier = 1.0 + volatility * 5
        
        # Direction doesn't matter for expected return (absolute value)
        expected_return = base_return * volatility_multiplier
        
        # Cap at reasonable maximum
        return min(expected_return, 0.15)  # Max 15% expected return
    
    async def _calculate_time_horizon(self, volatility: float, momentum_score: float, 
                                    urgency: str) -> int:
        """Calculate expected time horizon in minutes"""
        base_time = 30  # Base 30 minutes
        
        # High volatility = shorter time horizon
        if volatility > 0.05:
            time_multiplier = 0.5
        elif volatility > 0.03:
            time_multiplier = 0.7
        else:
            time_multiplier = 1.0
        
        # High urgency = shorter time horizon
        if urgency == "HIGH":
            time_multiplier *= 0.6
        elif urgency == "MEDIUM":
            time_multiplier *= 0.8
        
        # Strong momentum = shorter time horizon (quick moves)
        if abs(momentum_score) > 0.7:
            time_multiplier *= 0.7
        
        time_horizon = int(base_time * time_multiplier)
        return max(10, min(time_horizon, self.max_hold_time))  # 10-60 minutes
    
    async def _calculate_aggressive_leverage(self, volatility: float, confidence: float, 
                                           urgency: str) -> int:
        """Calculate aggressive leverage"""
        base_leverage = 25
        
        # Higher confidence = higher leverage
        confidence_multiplier = confidence * 1.5
        
        # Lower volatility = higher leverage
        volatility_multiplier = max(0.5, 1.0 - volatility * 10)
        
        # Higher urgency = higher leverage
        urgency_multiplier = 1.2 if urgency == "HIGH" else 1.0
        
        leverage = int(base_leverage * confidence_multiplier * volatility_multiplier * urgency_multiplier)
        
        # Cap at maximum leverage
        return min(leverage, self.max_leverage)
    
    async def _calculate_aggressive_position_size(self, confidence: float, volatility: float, 
                                                leverage: int, expected_return: float) -> float:
        """Calculate aggressive position size"""
        # Base position size (this would be adjusted based on available capital)
        base_size = 1000  # $1000 base
        
        # Confidence scaling
        confidence_multiplier = confidence ** 1.5  # Exponential scaling
        
        # Volatility adjustment (higher volatility = smaller position)
        volatility_multiplier = max(0.3, 1.0 - volatility * 5)
        
        # Leverage adjustment (higher leverage = smaller base position for same risk)
        leverage_multiplier = max(0.5, 1.0 - (leverage - 20) * 0.02)
        
        # Expected return scaling (higher expected return = larger position)
        return_multiplier = 1.0 + expected_return * 2
        
        position_size = (base_size * confidence_multiplier * volatility_multiplier * 
                        leverage_multiplier * return_multiplier)
        
        return max(100, position_size)  # Minimum $100 position
    
    async def should_exit_trade(self, trade: Trade, current_data: Dict) -> Tuple[bool, str]:
        """Determine if we should exit an aggressive trade"""
        if not trade.entry_price:
            return False, ""
        
        current_price = current_data.get('price', trade.entry_price)
        price_change_pct = (current_price - trade.entry_price) / trade.entry_price * 100
        
        # Adjust for short positions
        if trade.direction == TradeDirection.SHORT:
            price_change_pct = -price_change_pct
        
        # Apply leverage
        leveraged_return = price_change_pct * trade.leverage
        
        # Quick profit taking
        if leveraged_return >= self.quick_profit_threshold:
            return True, f"Quick profit: {leveraged_return:.1f}%"
        
        # Quick stop loss
        if leveraged_return <= -self.quick_stop_loss:
            return True, f"Quick stop loss: {leveraged_return:.1f}%"
        
        # Time-based exit
        if trade.created_at:
            time_elapsed = datetime.now() - trade.created_at
            if time_elapsed.total_seconds() / 60 > self.max_hold_time:
                return True, f"Time exit: {time_elapsed.total_seconds()/60:.1f} min"
        
        # Momentum reversal
        momentum_score = await self._calculate_momentum_score(
            current_price,
            current_data.get('rsi', 50),
            current_data.get('macd', 0),
            current_data.get('macd_signal', 0),
            current_data.get('ma_5', current_price),
            current_data.get('ma_20', current_price),
            current_data.get('ma_50', current_price),
            current_data.get('volatility', 0.02)
        )
        
        # Exit if momentum reversed
        if (trade.direction == TradeDirection.LONG and momentum_score < -0.3) or \
           (trade.direction == TradeDirection.SHORT and momentum_score > 0.3):
            return True, f"Momentum reversal: {momentum_score:.2f}"
        
        return False, ""
    
    async def get_risk_parameters(self, signal: AggressiveSignal) -> Dict:
        """Get risk parameters for aggressive trading"""
        return {
            "stop_loss": self.quick_stop_loss,
            "take_profit": self.quick_profit_threshold,
            "max_hold_time": signal.time_horizon,
            "leverage": signal.leverage,
            "position_size": signal.position_size,
            "urgency": signal.urgency,
            "expected_return": signal.expected_return
        }


# Example usage
async def test_aggressive_momentum():
    """Test the aggressive momentum strategy"""
    strategy = AggressiveMomentumStrategy()
    await strategy.initialize()
    
    # Mock market data
    market_data = {
        'ETH/USD': {
            'price': 2000.0,
            'volume': 1500000,
            'volume_ratio': 2.0,
            'rsi': 25,  # Oversold
            'macd': 0.8,
            'macd_signal': 0.5,
            'ma_5': 1950.0,
            'ma_20': 1900.0,
            'ma_50': 1850.0,
            'volatility': 0.03
        }
    }
    
    signals = await strategy.analyze(market_data)
    
    for pair, signal in signals.items():
        logger.info(f"🚀 {pair} Signal:")
        logger.info(f"   Direction: {signal.direction.value}")
        logger.info(f"   Confidence: {signal.confidence:.2f}")
        logger.info(f"   Urgency: {signal.urgency}")
        logger.info(f"   Expected Return: {signal.expected_return:.1%}")
        logger.info(f"   Time Horizon: {signal.time_horizon} min")
        logger.info(f"   Leverage: {signal.leverage}x")
        logger.info(f"   Position Size: ${signal.position_size:,.0f}")


if __name__ == "__main__":
    asyncio.run(test_aggressive_momentum())
