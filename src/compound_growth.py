"""
Compound Growth System for 10% Daily Returns
Advanced profit tracking, reinvestment, and compound growth management
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    from .logger import logger
    from .models import Trade, TradeDirection
    from .config import config
except ImportError:
    from logger import logger
    from models import Trade, TradeDirection
    from config import config


@dataclass
class DailyTarget:
    """Daily profit target tracking"""
    date: str
    target_profit: float  # 10% of capital
    actual_profit: float
    capital_start: float
    capital_end: float
    trades_count: int
    win_rate: float
    compound_multiplier: float  # How much capital grew
    achieved: bool


@dataclass
class CompoundStats:
    """Compound growth statistics"""
    total_days: int
    successful_days: int
    total_return: float
    compound_return: float
    current_capital: float
    initial_capital: float
    best_day: float
    worst_day: float
    average_daily_return: float
    streak_current: int
    streak_longest: int


class CompoundGrowthManager:
    """Manages compound growth and daily profit targets"""
    
    def __init__(self, data_file: str = "compound_data.json"):
        self.data_file = Path(data_file)
        self.daily_targets: List[DailyTarget] = []
        self.current_capital: float = 0.0
        self.initial_capital: float = 0.0
        self.daily_target_percentage: float = 10.0  # 10% daily target
        
    async def initialize(self, initial_capital: float):
        """Initialize with starting capital"""
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        await self.load_data()
        
        logger.info(f"💰 Compound Growth Manager initialized")
        logger.info(f"   Initial Capital: ${self.initial_capital:,.2f}")
        logger.info(f"   Daily Target: {self.daily_target_percentage}%")
        logger.info(f"   Target Amount: ${self.get_daily_target():,.2f}")
        
    def get_daily_target(self) -> float:
        """Get today's profit target (10% of current capital)"""
        return self.current_capital * (self.daily_target_percentage / 100)
    
    def calculate_compound_growth(self, days: int) -> float:
        """Calculate potential compound growth over N days"""
        if days <= 0:
            return 1.0
        
        daily_multiplier = 1 + (self.daily_target_percentage / 100)
        return daily_multiplier ** days
    
    def get_projected_capital(self, days: int) -> float:
        """Get projected capital after N days of 10% daily growth"""
        return self.initial_capital * self.calculate_compound_growth(days)
    
    def get_position_size_for_target(self, win_probability: float = 0.7) -> float:
        """Calculate position size needed to achieve daily target"""
        daily_target = self.get_daily_target()
        
        # Assume average leverage of 20x and 70% win rate
        # Position size = target / (leverage * win_rate * average_return_per_trade)
        average_return_per_trade = 0.05  # 5% average return per winning trade
        leverage = 20.0
        
        required_position_size = daily_target / (leverage * win_probability * average_return_per_trade)
        
        # Cap at 50% of current capital for risk management
        max_position_size = self.current_capital * 0.5
        
        return min(required_position_size, max_position_size)
    
    async def record_daily_result(self, actual_profit: float, trades_count: int, 
                                win_rate: float, trades: List[Trade]) -> DailyTarget:
        """Record daily trading results"""
        today = datetime.now().strftime("%Y-%m-%d")
        capital_start = self.current_capital
        
        # Update capital
        self.current_capital += actual_profit
        capital_end = self.current_capital
        
        # Calculate compound multiplier
        compound_multiplier = self.current_capital / self.initial_capital
        
        # Check if target achieved
        target_profit = self.get_daily_target()
        achieved = actual_profit >= target_profit
        
        daily_target = DailyTarget(
            date=today,
            target_profit=target_profit,
            actual_profit=actual_profit,
            capital_start=capital_start,
            capital_end=capital_end,
            trades_count=trades_count,
            win_rate=win_rate,
            compound_multiplier=compound_multiplier,
            achieved=achieved
        )
        
        self.daily_targets.append(daily_target)
        await self.save_data()
        
        # Log results
        status = "✅ ACHIEVED" if achieved else "❌ MISSED"
        logger.info(f"📊 Daily Target Results - {today}")
        logger.info(f"   Status: {status}")
        logger.info(f"   Target: ${target_profit:,.2f}")
        logger.info(f"   Actual: ${actual_profit:,.2f}")
        logger.info(f"   Capital: ${capital_start:,.2f} → ${capital_end:,.2f}")
        logger.info(f"   Compound: {compound_multiplier:.2f}x")
        logger.info(f"   Trades: {trades_count}, Win Rate: {win_rate:.1%}")
        
        return daily_target
    
    def get_compound_stats(self) -> CompoundStats:
        """Get comprehensive compound growth statistics"""
        if not self.daily_targets:
            return CompoundStats(
                total_days=0, successful_days=0, total_return=0.0,
                compound_return=0.0, current_capital=self.current_capital,
                initial_capital=self.initial_capital, best_day=0.0,
                worst_day=0.0, average_daily_return=0.0, streak_current=0,
                streak_longest=0
            )
        
        total_days = len(self.daily_targets)
        successful_days = sum(1 for target in self.daily_targets if target.achieved)
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital * 100
        compound_return = (self.current_capital / self.initial_capital - 1) * 100
        
        daily_returns = [target.actual_profit / target.capital_start * 100 for target in self.daily_targets]
        best_day = max(daily_returns) if daily_returns else 0.0
        worst_day = min(daily_returns) if daily_returns else 0.0
        average_daily_return = sum(daily_returns) / len(daily_returns) if daily_returns else 0.0
        
        # Calculate streaks
        streak_current = 0
        streak_longest = 0
        current_streak = 0
        
        for target in reversed(self.daily_targets):
            if target.achieved:
                current_streak += 1
                streak_current = max(streak_current, current_streak)
            else:
                current_streak = 0
        
        # Calculate longest streak
        current_streak = 0
        for target in self.daily_targets:
            if target.achieved:
                current_streak += 1
                streak_longest = max(streak_longest, current_streak)
            else:
                current_streak = 0
        
        return CompoundStats(
            total_days=total_days,
            successful_days=successful_days,
            total_return=total_return,
            compound_return=compound_return,
            current_capital=self.current_capital,
            initial_capital=self.initial_capital,
            best_day=best_day,
            worst_day=worst_day,
            average_daily_return=average_daily_return,
            streak_current=streak_current,
            streak_longest=streak_longest
        )
    
    def get_projection_analysis(self) -> Dict[str, float]:
        """Get compound growth projections"""
        projections = {}
        
        for days in [7, 14, 30, 60, 90, 365]:
            projected_capital = self.get_projected_capital(days)
            growth_multiplier = projected_capital / self.initial_capital
            projections[f"{days}_days"] = {
                "capital": projected_capital,
                "multiplier": growth_multiplier,
                "total_return": (growth_multiplier - 1) * 100
            }
        
        return projections
    
    async def save_data(self):
        """Save compound growth data to file"""
        data = {
            "initial_capital": self.initial_capital,
            "current_capital": self.current_capital,
            "daily_target_percentage": self.daily_target_percentage,
            "daily_targets": [asdict(target) for target in self.daily_targets]
        }
        
        with open(self.data_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    async def load_data(self):
        """Load compound growth data from file"""
        if not self.data_file.exists():
            return
        
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            
            self.initial_capital = data.get("initial_capital", self.initial_capital)
            self.current_capital = data.get("current_capital", self.current_capital)
            self.daily_target_percentage = data.get("daily_target_percentage", self.daily_target_percentage)
            
            # Load daily targets
            targets_data = data.get("daily_targets", [])
            self.daily_targets = [
                DailyTarget(**target_data) for target_data in targets_data
            ]
            
            logger.info(f"📈 Loaded compound growth data: {len(self.daily_targets)} days tracked")
            
        except Exception as e:
            logger.error_occurred(e, "loading compound growth data")
    
    def print_daily_summary(self):
        """Print comprehensive daily summary"""
        stats = self.get_compound_stats()
        projections = self.get_projection_analysis()
        
        print("\n" + "="*60)
        print("🎯 COMPOUND GROWTH SUMMARY")
        print("="*60)
        
        print(f"💰 Capital: ${self.current_capital:,.2f} (Started: ${self.initial_capital:,.2f})")
        print(f"📊 Total Return: {stats.total_return:.1f}%")
        print(f"🔥 Compound Multiplier: {stats.compound_return/100 + 1:.2f}x")
        print(f"📅 Days Tracked: {stats.total_days}")
        print(f"✅ Successful Days: {stats.successful_days} ({stats.successful_days/stats.total_days*100:.1f}% if stats.total_days > 0 else 0}")
        print(f"📈 Average Daily Return: {stats.average_daily_return:.1f}%")
        print(f"🏆 Best Day: {stats.best_day:.1f}%")
        print(f"💥 Worst Day: {stats.worst_day:.1f}%")
        print(f"🔥 Current Streak: {stats.streak_current} days")
        print(f"🏅 Longest Streak: {stats.streak_longest} days")
        
        print(f"\n🎯 Today's Target: ${self.get_daily_target():,.2f}")
        
        print(f"\n🚀 PROJECTIONS:")
        for period, data in projections.items():
            days = period.replace("_days", "")
            print(f"   {days:>3} days: ${data['capital']:>12,.0f} ({data['total_return']:>6.0f}% return)")
        
        print("="*60)


class AggressiveTradingMode:
    """Aggressive trading mode for 10% daily targets"""
    
    def __init__(self, compound_manager: CompoundGrowthManager):
        self.compound_manager = compound_manager
        self.max_leverage = 50  # Higher leverage for aggressive trading
        self.min_position_size = 100  # Minimum position size
        self.max_positions_per_day = 20  # More frequent trading
        
    def calculate_aggressive_position_size(self, confidence: float, volatility: float) -> float:
        """Calculate position size for aggressive trading"""
        base_position = self.compound_manager.get_position_size_for_target(confidence)
        
        # Adjust for volatility (higher volatility = smaller position)
        volatility_adjustment = max(0.5, 1.0 - volatility)
        
        # Adjust for confidence (higher confidence = larger position)
        confidence_adjustment = confidence ** 2  # Square for exponential effect
        
        aggressive_size = base_position * volatility_adjustment * confidence_adjustment
        
        # Cap at 30% of capital for safety
        max_size = self.compound_manager.current_capital * 0.3
        
        return min(max(aggressive_size, self.min_position_size), max_size)
    
    def get_aggressive_leverage(self, pair: str, volatility: float) -> int:
        """Get aggressive leverage based on pair and volatility"""
        base_leverage = 25
        
        # Increase leverage for lower volatility pairs
        if volatility < 0.02:  # Low volatility
            leverage_multiplier = 1.5
        elif volatility < 0.05:  # Medium volatility
            leverage_multiplier = 1.2
        else:  # High volatility
            leverage_multiplier = 1.0
        
        aggressive_leverage = int(base_leverage * leverage_multiplier)
        return min(aggressive_leverage, self.max_leverage)
    
    def should_take_profit_early(self, current_profit_pct: float, time_in_trade_minutes: int) -> bool:
        """Determine if we should take profit early for daily targets"""
        # If we're close to daily target and trade has been open for a while
        daily_progress = current_profit_pct / self.compound_manager.daily_target_percentage
        
        if daily_progress >= 0.8 and time_in_trade_minutes > 30:
            return True
        
        # If we've hit 5% profit quickly, take it
        if current_profit_pct >= 5.0 and time_in_trade_minutes < 15:
            return True
        
        return False
    
    def should_cut_losses_quickly(self, current_loss_pct: float, time_in_trade_minutes: int) -> bool:
        """Determine if we should cut losses quickly"""
        # Cut losses at 2% if trade has been open for more than 10 minutes
        if current_loss_pct >= 2.0 and time_in_trade_minutes > 10:
            return True
        
        # Cut losses at 1% if trade has been open for more than 30 minutes
        if current_loss_pct >= 1.0 and time_in_trade_minutes > 30:
            return True
        
        return False


# Example usage and testing
async def test_compound_growth():
    """Test the compound growth system"""
    compound_manager = CompoundGrowthManager()
    await compound_manager.initialize(10000)  # Start with $10k
    
    # Simulate some daily results
    await compound_manager.record_daily_result(1200, 8, 0.75, [])  # 12% day
    await compound_manager.record_daily_result(800, 6, 0.67, [])   # 8% day
    await compound_manager.record_daily_result(1500, 10, 0.80, []) # 15% day
    
    compound_manager.print_daily_summary()
    
    # Test aggressive trading mode
    aggressive_mode = AggressiveTradingMode(compound_manager)
    
    position_size = aggressive_mode.calculate_aggressive_position_size(0.8, 0.03)
    leverage = aggressive_mode.get_aggressive_leverage("ETH/USD", 0.03)
    
    print(f"\n🎯 Aggressive Trading Settings:")
    print(f"   Position Size: ${position_size:,.2f}")
    print(f"   Leverage: {leverage}x")


if __name__ == "__main__":
    asyncio.run(test_compound_growth())
