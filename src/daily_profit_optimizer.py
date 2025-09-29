"""
Daily Profit Optimizer for 10% Daily Returns
Manages trading activity to achieve and maintain daily profit targets
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from .compound_growth import CompoundGrowthManager, AggressiveTradingMode
    from .avantis_client import AvantisClient
    from .models import Trade, TradeDirection, TradeStatus
    from .logger import logger
except ImportError:
    from compound_growth import CompoundGrowthManager, AggressiveTradingMode
    from avantis_client import AvantisClient
    from models import Trade, TradeDirection, TradeStatus
    from logger import logger


class TradingPhase(Enum):
    """Trading phases throughout the day"""
    MORNING_AGGRESSIVE = "morning_aggressive"  # 6-10 AM: High risk, high reward
    MIDDAY_BALANCED = "midday_balanced"        # 10 AM-2 PM: Balanced approach
    AFTERNOON_MOMENTUM = "afternoon_momentum"  # 2-6 PM: Momentum following
    EVENING_CONSOLIDATION = "evening_consolidation"  # 6-10 PM: Consolidation
    NIGHT_DEFENSIVE = "night_defensive"        # 10 PM-6 AM: Defensive mode


@dataclass
class DailyTargetStatus:
    """Current status of daily profit target"""
    target_amount: float
    current_profit: float
    progress_percentage: float
    remaining_amount: float
    hours_remaining: float
    required_hourly_rate: float
    phase: TradingPhase
    risk_level: str  # "LOW", "MEDIUM", "HIGH", "EXTREME"
    recommended_action: str


class DailyProfitOptimizer:
    """Optimizes trading activity to achieve 10% daily returns"""
    
    def __init__(self, compound_manager: CompoundGrowthManager, 
                 avantis_client: AvantisClient):
        self.compound_manager = compound_manager
        self.avantis_client = avantis_client
        self.aggressive_mode = AggressiveTradingMode(compound_manager)
        
        # Daily tracking
        self.daily_start_time: Optional[datetime] = None
        self.daily_start_capital: float = 0.0
        self.current_daily_profit: float = 0.0
        self.trades_today: List[Trade] = []
        
        # Performance tracking
        self.hourly_profits: Dict[int, float] = {}  # Hour -> Profit
        self.phase_performance: Dict[TradingPhase, float] = {}
        
        # Risk management
        self.max_daily_loss: float = 0.05  # 5% max daily loss
        self.current_daily_loss: float = 0.0
        self.consecutive_losses: int = 0
        self.trading_paused: bool = False
        
        # Optimization parameters
        self.min_trades_per_day = 5
        self.max_trades_per_day = 50
        self.target_win_rate = 0.70
        
    async def initialize(self):
        """Initialize the daily profit optimizer"""
        await self._start_new_day()
        logger.info("🎯 Daily Profit Optimizer initialized")
        logger.info(f"   Daily Target: ${self.compound_manager.get_daily_target():,.2f}")
        logger.info(f"   Current Phase: {self._get_current_phase().value}")
        
    async def _start_new_day(self):
        """Start tracking a new trading day"""
        self.daily_start_time = datetime.now()
        self.daily_start_capital = self.compound_manager.current_capital
        self.current_daily_profit = 0.0
        self.trades_today = []
        self.hourly_profits = {}
        self.current_daily_loss = 0.0
        self.consecutive_losses = 0
        self.trading_paused = False
        
        logger.info(f"🌅 New trading day started")
        logger.info(f"   Capital: ${self.daily_start_capital:,.2f}")
        logger.info(f"   Target: ${self.compound_manager.get_daily_target():,.2f}")
    
    def _get_current_phase(self) -> TradingPhase:
        """Get current trading phase based on time"""
        current_hour = datetime.now().hour
        
        if 6 <= current_hour < 10:
            return TradingPhase.MORNING_AGGRESSIVE
        elif 10 <= current_hour < 14:
            return TradingPhase.MIDDAY_BALANCED
        elif 14 <= current_hour < 18:
            return TradingPhase.AFTERNOON_MOMENTUM
        elif 18 <= current_hour < 22:
            return TradingPhase.EVENING_CONSOLIDATION
        else:
            return TradingPhase.NIGHT_DEFENSIVE
    
    async def get_daily_status(self) -> DailyTargetStatus:
        """Get current daily profit target status"""
        target_amount = self.compound_manager.get_daily_target()
        progress_percentage = (self.current_daily_profit / target_amount) * 100
        remaining_amount = max(0, target_amount - self.current_daily_profit)
        
        # Calculate time remaining
        if self.daily_start_time:
            hours_elapsed = (datetime.now() - self.daily_start_time).total_seconds() / 3600
            hours_remaining = max(0, 24 - hours_elapsed)
        else:
            hours_remaining = 24
        
        # Calculate required hourly rate
        required_hourly_rate = remaining_amount / max(hours_remaining, 1)
        
        # Determine risk level
        risk_level = self._determine_risk_level(progress_percentage, hours_remaining)
        
        # Get recommended action
        recommended_action = self._get_recommended_action(
            progress_percentage, hours_remaining, risk_level
        )
        
        return DailyTargetStatus(
            target_amount=target_amount,
            current_profit=self.current_daily_profit,
            progress_percentage=progress_percentage,
            remaining_amount=remaining_amount,
            hours_remaining=hours_remaining,
            required_hourly_rate=required_hourly_rate,
            phase=self._get_current_phase(),
            risk_level=risk_level,
            recommended_action=recommended_action
        )
    
    def _determine_risk_level(self, progress_percentage: float, hours_remaining: float) -> str:
        """Determine current risk level based on progress and time"""
        if progress_percentage >= 100:
            return "LOW"  # Target achieved
        elif progress_percentage >= 80:
            return "MEDIUM"  # Close to target
        elif progress_percentage >= 50:
            if hours_remaining > 8:
                return "MEDIUM"
            else:
                return "HIGH"
        elif progress_percentage >= 25:
            if hours_remaining > 12:
                return "HIGH"
            else:
                return "EXTREME"
        else:
            if hours_remaining > 16:
                return "HIGH"
            else:
                return "EXTREME"
    
    def _get_recommended_action(self, progress_percentage: float, 
                               hours_remaining: float, risk_level: str) -> str:
        """Get recommended trading action"""
        if self.trading_paused:
            return "TRADING_PAUSED - Too many consecutive losses"
        
        if progress_percentage >= 100:
            return "TARGET_ACHIEVED - Consider taking profits and reducing risk"
        elif progress_percentage >= 90:
            return "CONSOLIDATE - Close risky positions, maintain gains"
        elif progress_percentage >= 70:
            return "BALANCED - Continue with moderate risk"
        elif progress_percentage >= 50:
            return "INCREASE_FREQUENCY - More trades needed"
        elif progress_percentage >= 25:
            return "AGGRESSIVE - Increase position sizes and leverage"
        else:
            return "EXTREME_RISK - Maximum leverage, high frequency trading"
    
    async def should_take_trade(self, signal_confidence: float, expected_return: float) -> bool:
        """Determine if we should take a trade based on daily progress"""
        status = await self.get_daily_status()
        
        # Don't trade if paused
        if self.trading_paused:
            return False
        
        # Don't trade if we've hit max daily loss
        if self.current_daily_loss >= self.max_daily_loss * self.daily_start_capital:
            logger.warning("🛑 Daily loss limit reached, pausing trading")
            self.trading_paused = True
            return False
        
        # Adjust confidence threshold based on daily progress
        if status.progress_percentage >= 90:
            min_confidence = 0.8  # Be very selective when close to target
        elif status.progress_percentage >= 70:
            min_confidence = 0.7
        elif status.progress_percentage >= 50:
            min_confidence = 0.65
        elif status.progress_percentage >= 25:
            min_confidence = 0.6
        else:
            min_confidence = 0.55  # Lower threshold when far from target
        
        return signal_confidence >= min_confidence
    
    async def calculate_optimal_position_size(self, base_size: float, confidence: float, 
                                            expected_return: float) -> float:
        """Calculate optimal position size based on daily progress"""
        status = await self.get_daily_status()
        
        # Base position size multiplier based on daily progress
        if status.progress_percentage >= 90:
            size_multiplier = 0.5  # Reduce size when close to target
        elif status.progress_percentage >= 70:
            size_multiplier = 0.7
        elif status.progress_percentage >= 50:
            size_multiplier = 1.0
        elif status.progress_percentage >= 25:
            size_multiplier = 1.3  # Increase size when behind
        else:
            size_multiplier = 1.5  # Maximum size when far behind
        
        # Adjust for risk level
        if status.risk_level == "EXTREME":
            size_multiplier *= 1.5
        elif status.risk_level == "HIGH":
            size_multiplier *= 1.2
        elif status.risk_level == "LOW":
            size_multiplier *= 0.8
        
        # Confidence scaling
        confidence_multiplier = confidence ** 1.5
        
        # Expected return scaling
        return_multiplier = 1.0 + expected_return * 3
        
        optimal_size = base_size * size_multiplier * confidence_multiplier * return_multiplier
        
        # Cap at 30% of current capital
        max_size = self.compound_manager.current_capital * 0.3
        
        return min(optimal_size, max_size)
    
    async def calculate_optimal_leverage(self, base_leverage: int, volatility: float) -> int:
        """Calculate optimal leverage based on daily progress and risk"""
        status = await self.get_daily_status()
        
        # Base leverage adjustment based on daily progress
        if status.progress_percentage >= 90:
            leverage_multiplier = 0.8  # Reduce leverage when close to target
        elif status.progress_percentage >= 70:
            leverage_multiplier = 0.9
        elif status.progress_percentage >= 50:
            leverage_multiplier = 1.0
        elif status.progress_percentage >= 25:
            leverage_multiplier = 1.2  # Increase leverage when behind
        else:
            leverage_multiplier = 1.5  # Maximum leverage when far behind
        
        # Risk level adjustment
        if status.risk_level == "EXTREME":
            leverage_multiplier *= 1.3
        elif status.risk_level == "HIGH":
            leverage_multiplier *= 1.1
        elif status.risk_level == "LOW":
            leverage_multiplier *= 0.9
        
        # Volatility adjustment (lower volatility = higher leverage)
        volatility_multiplier = max(0.5, 1.0 - volatility * 10)
        
        optimal_leverage = int(base_leverage * leverage_multiplier * volatility_multiplier)
        
        # Cap at 50x leverage
        return min(optimal_leverage, 50)
    
    async def record_trade_result(self, trade: Trade, profit_loss: float):
        """Record the result of a completed trade"""
        self.trades_today.append(trade)
        self.current_daily_profit += profit_loss
        
        # Track hourly profits
        current_hour = datetime.now().hour
        if current_hour not in self.hourly_profits:
            self.hourly_profits[current_hour] = 0.0
        self.hourly_profits[current_hour] += profit_loss
        
        # Track phase performance
        current_phase = self._get_current_phase()
        if current_phase not in self.phase_performance:
            self.phase_performance[current_phase] = 0.0
        self.phase_performance[current_phase] += profit_loss
        
        # Track consecutive losses
        if profit_loss < 0:
            self.consecutive_losses += 1
            self.current_daily_loss += abs(profit_loss)
            
            # Pause trading after 3 consecutive losses
            if self.consecutive_losses >= 3:
                logger.warning(f"🛑 {self.consecutive_losses} consecutive losses, pausing trading")
                self.trading_paused = True
        else:
            self.consecutive_losses = 0
            # Resume trading after a win
            if self.trading_paused and profit_loss > 0:
                logger.info("✅ Trading resumed after profitable trade")
                self.trading_paused = False
        
        # Log trade result
        status = "✅ WIN" if profit_loss > 0 else "❌ LOSS"
        logger.info(f"📊 Trade Result - {status}: ${profit_loss:,.2f}")
        logger.info(f"   Daily Progress: ${self.current_daily_profit:,.2f} / ${self.compound_manager.get_daily_target():,.2f}")
        
    async def get_hourly_performance(self) -> Dict[int, float]:
        """Get hourly performance breakdown"""
        return self.hourly_profits.copy()
    
    async def get_phase_performance(self) -> Dict[str, float]:
        """Get performance by trading phase"""
        return {phase.value: profit for phase, profit in self.phase_performance.items()}
    
    async def should_end_trading_day(self) -> bool:
        """Determine if we should end the trading day"""
        status = await self.get_daily_status()
        
        # End if target achieved with good margin
        if status.progress_percentage >= 110:
            logger.info("🎯 Daily target exceeded by 10%, ending trading day")
            return True
        
        # End if we've hit max daily loss
        if self.current_daily_loss >= self.max_daily_loss * self.daily_start_capital:
            logger.warning("🛑 Daily loss limit reached, ending trading day")
            return True
        
        # End if it's very late and we're close to target
        if status.hours_remaining < 2 and status.progress_percentage >= 80:
            logger.info("🌙 End of day, target nearly achieved, ending trading")
            return True
        
        # End if we've made too many trades
        if len(self.trades_today) >= self.max_trades_per_day:
            logger.info(f"📊 Maximum trades ({self.max_trades_per_day}) reached, ending day")
            return True
        
        return False
    
    async def end_trading_day(self):
        """End the current trading day and record results"""
        status = await self.get_daily_status()
        
        # Calculate final statistics
        win_rate = len([t for t in self.trades_today if getattr(t, 'pnl', 0) > 0]) / max(len(self.trades_today), 1)
        
        # Record in compound manager
        await self.compound_manager.record_daily_result(
            actual_profit=self.current_daily_profit,
            trades_count=len(self.trades_today),
            win_rate=win_rate,
            trades=self.trades_today
        )
        
        # Log daily summary
        logger.info("📊 DAILY TRADING SUMMARY")
        logger.info("=" * 50)
        logger.info(f"💰 Daily Profit: ${self.current_daily_profit:,.2f}")
        logger.info(f"🎯 Target: ${status.target_amount:,.2f}")
        logger.info(f"📈 Achievement: {status.progress_percentage:.1f}%")
        logger.info(f"📊 Total Trades: {len(self.trades_today)}")
        logger.info(f"✅ Win Rate: {win_rate:.1%}")
        logger.info(f"⏰ Hours Traded: {24 - status.hours_remaining:.1f}")
        
        # Log hourly breakdown
        hourly_perf = await self.get_hourly_performance()
        if hourly_perf:
            logger.info(f"🕐 Hourly Performance:")
            for hour, profit in sorted(hourly_perf.items()):
                logger.info(f"   {hour:02d}:00 - ${profit:,.2f}")
        
        # Log phase performance
        phase_perf = await self.get_phase_performance()
        if phase_perf:
            logger.info(f"🌅 Phase Performance:")
            for phase, profit in phase_perf.items():
                logger.info(f"   {phase} - ${profit:,.2f}")
        
        logger.info("=" * 50)
        
        # Start new day if target not achieved
        if status.progress_percentage < 100:
            logger.warning(f"⚠️ Daily target not achieved ({status.progress_percentage:.1f}%)")
        
        # Reset for next day
        await self._start_new_day()


# Example usage and testing
async def test_daily_optimizer():
    """Test the daily profit optimizer"""
    from compound_growth import CompoundGrowthManager
    
    # Initialize components
    compound_manager = CompoundGrowthManager()
    await compound_manager.initialize(10000)  # Start with $10k
    
    # Mock AvantisClient
    class MockAvantisClient:
        pass
    
    avantis_client = MockAvantisClient()
    
    # Initialize optimizer
    optimizer = DailyProfitOptimizer(compound_manager, avantis_client)
    await optimizer.initialize()
    
    # Get initial status
    status = await optimizer.get_daily_status()
    print(f"🎯 Daily Status:")
    print(f"   Target: ${status.target_amount:,.2f}")
    print(f"   Progress: {status.progress_percentage:.1f}%")
    print(f"   Phase: {status.phase.value}")
    print(f"   Risk Level: {status.risk_level}")
    print(f"   Action: {status.recommended_action}")
    
    # Test position sizing
    optimal_size = await optimizer.calculate_optimal_position_size(1000, 0.8, 0.05)
    optimal_leverage = await optimizer.calculate_optimal_leverage(25, 0.03)
    
    print(f"\n📊 Optimal Settings:")
    print(f"   Position Size: ${optimal_size:,.2f}")
    print(f"   Leverage: {optimal_leverage}x")


if __name__ == "__main__":
    asyncio.run(test_daily_optimizer())
