"""
Risk management module for the Avantis Trading Bot
"""

import asyncio
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from .models import Trade, Position, RiskMetrics, TradeDirection
from .logger import logger
from .config import config


@dataclass
class RiskLimits:
    """Risk limits configuration"""
    max_position_size: float
    max_total_exposure: float
    max_daily_loss: float
    max_open_positions: int
    max_leverage: int
    stop_loss_percentage: float
    take_profit_percentage: float
    max_drawdown: float


class RiskManager:
    """Risk management system for the trading bot"""
    
    def __init__(self):
        self.risk_limits = RiskLimits(
            max_position_size=config.trading.max_position_size,
            max_total_exposure=config.trading.max_position_size * config.trading.max_open_positions,
            max_daily_loss=config.trading.max_daily_loss,
            max_open_positions=config.trading.max_open_positions,
            max_leverage=50,  # Conservative max leverage
            stop_loss_percentage=config.trading.stop_loss_percentage,
            take_profit_percentage=config.trading.take_profit_percentage,
            max_drawdown=20.0  # 20% max drawdown
        )
        
        self.daily_pnl = 0.0
        self.daily_start_balance = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.current_drawdown = 0.0
        self.peak_balance = 0.0
        self.last_reset_date = datetime.now().date()
    
    def reset_daily_metrics(self):
        """Reset daily metrics"""
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.daily_pnl = 0.0
            self.last_reset_date = today
            logger.info("Daily metrics reset")
    
    def update_balance(self, current_balance: float):
        """Update balance and calculate drawdown"""
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
            self.current_drawdown = 0.0
        else:
            self.current_drawdown = (self.peak_balance - current_balance) / self.peak_balance * 100
        
        self.daily_start_balance = current_balance if self.daily_pnl == 0.0 else self.daily_start_balance
    
    def update_trade_result(self, pnl: float):
        """Update trade result metrics"""
        self.daily_pnl += pnl
        self.total_trades += 1
        
        if pnl > 0:
            self.winning_trades += 1
        elif pnl < 0:
            self.losing_trades += 1
    
    def calculate_position_size(self, 
                              pair: str, 
                              direction: TradeDirection, 
                              entry_price: float, 
                              risk_percentage: float = 2.0) -> float:
        """Calculate optimal position size based on risk parameters"""
        try:
            # Base position size from config
            base_size = config.trading.min_position_size
            
            # Adjust based on available balance and risk
            max_risk_amount = self.daily_start_balance * (risk_percentage / 100)
            
            # Calculate stop loss distance
            stop_loss_price = self._calculate_stop_loss(entry_price, direction)
            price_distance = abs(entry_price - stop_loss_price)
            risk_per_unit = price_distance / entry_price
            
            # Calculate position size based on risk
            risk_based_size = max_risk_amount / risk_per_unit if risk_per_unit > 0 else base_size
            
            # Apply limits
            position_size = min(
                risk_based_size,
                self.risk_limits.max_position_size,
                base_size * 5  # Max 5x base size
            )
            
            # Ensure minimum size
            position_size = max(position_size, self.risk_limits.max_position_size * 0.1)
            
            logger.debug(f"Calculated position size for {pair}: {position_size} USDC")
            return position_size
            
        except Exception as e:
            logger.error_occurred(e, "calculating position size")
            return config.trading.min_position_size
    
    def _calculate_stop_loss(self, entry_price: float, direction: TradeDirection) -> float:
        """Calculate stop loss price"""
        if direction == TradeDirection.LONG:
            return entry_price * (1 - self.risk_limits.stop_loss_percentage / 100)
        else:
            return entry_price * (1 + self.risk_limits.stop_loss_percentage / 100)
    
    def _calculate_take_profit(self, entry_price: float, direction: TradeDirection) -> float:
        """Calculate take profit price"""
        if direction == TradeDirection.LONG:
            return entry_price * (1 + self.risk_limits.take_profit_percentage / 100)
        else:
            return entry_price * (1 - self.risk_limits.take_profit_percentage / 100)
    
    def validate_trade(self, trade: Trade, current_positions: List[Position]) -> Tuple[bool, str]:
        """Validate if a trade meets risk requirements"""
        try:
            # Reset daily metrics if needed
            self.reset_daily_metrics()
            
            # Check daily loss limit
            if abs(self.daily_pnl) >= self.risk_limits.max_daily_loss:
                return False, f"Daily loss limit reached: {self.daily_pnl}"
            
            # Check drawdown limit
            if self.current_drawdown >= self.risk_limits.max_drawdown:
                return False, f"Maximum drawdown reached: {self.current_drawdown:.2f}%"
            
            # Check position size
            if trade.size > self.risk_limits.max_position_size:
                return False, f"Position size too large: {trade.size}"
            
            # Check leverage
            if trade.leverage > self.risk_limits.max_leverage:
                return False, f"Leverage too high: {trade.leverage}"
            
            # Check total exposure
            total_exposure = sum(pos.total_size * pos.leverage for pos in current_positions)
            new_exposure = trade.size * trade.leverage
            if total_exposure + new_exposure > self.risk_limits.max_total_exposure:
                return False, f"Total exposure limit would be exceeded"
            
            # Check open positions count
            if len(current_positions) >= self.risk_limits.max_open_positions:
                return False, f"Maximum open positions reached: {len(current_positions)}"
            
            # Check for same pair exposure
            pair_positions = [pos for pos in current_positions if pos.pair == trade.pair]
            if pair_positions:
                total_pair_exposure = sum(pos.total_size for pos in pair_positions)
                if total_pair_exposure + trade.size > self.risk_limits.max_position_size * 2:
                    return False, f"Pair exposure limit would be exceeded for {trade.pair}"
            
            # Set default stop loss and take profit if not provided
            if not trade.stop_loss:
                trade.stop_loss = self._calculate_stop_loss(trade.entry_price, trade.direction)
            
            if not trade.take_profit:
                trade.take_profit = self._calculate_take_profit(trade.entry_price, trade.direction)
            
            return True, "Trade validated"
            
        except Exception as e:
            logger.error_occurred(e, "validating trade")
            return False, f"Validation error: {str(e)}"
    
    def should_reduce_exposure(self, current_positions: List[Position]) -> bool:
        """Check if exposure should be reduced based on risk metrics"""
        try:
            # Check drawdown
            if self.current_drawdown > self.risk_limits.max_drawdown * 0.8:
                logger.risk_alert(f"High drawdown detected: {self.current_drawdown:.2f}%")
                return True
            
            # Check daily loss
            if abs(self.daily_pnl) > self.risk_limits.max_daily_loss * 0.8:
                logger.risk_alert(f"High daily loss: {self.daily_pnl}")
                return True
            
            # Check win rate (if we have enough trades)
            if self.total_trades > 10:
                win_rate = self.winning_trades / self.total_trades
                if win_rate < 0.3:  # Less than 30% win rate
                    logger.risk_alert(f"Low win rate detected: {win_rate:.2%}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error_occurred(e, "checking exposure reduction")
            return False
    
    def get_risk_metrics(self) -> RiskMetrics:
        """Get current risk metrics"""
        try:
            win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
            
            return RiskMetrics(
                total_exposure=0,  # Will be calculated by caller
                daily_pnl=self.daily_pnl,
                max_drawdown=self.current_drawdown,
                win_rate=win_rate,
                open_positions=0,  # Will be calculated by caller
                total_trades=self.total_trades
            )
            
        except Exception as e:
            logger.error_occurred(e, "getting risk metrics")
            return RiskMetrics(
                total_exposure=0,
                daily_pnl=0,
                max_drawdown=0,
                win_rate=0,
                open_positions=0,
                total_trades=0
            )
    
    def get_position_recommendations(self, positions: List[Position]) -> List[Dict[str, any]]:
        """Get recommendations for position management"""
        recommendations = []
        
        try:
            for position in positions:
                # Check if position is in drawdown
                if position.unrealized_pnl < -position.total_size * 0.1:  # 10% of position
                    recommendations.append({
                        'action': 'reduce',
                        'pair': position.pair,
                        'reason': 'Position in significant drawdown',
                        'priority': 'high'
                    })
                
                # Check if position is profitable and should take profits
                elif position.unrealized_pnl > position.total_size * 0.2:  # 20% of position
                    recommendations.append({
                        'action': 'partial_close',
                        'pair': position.pair,
                        'reason': 'Position highly profitable',
                        'priority': 'medium'
                    })
                
                # Check if position has been open too long
                if hasattr(position, 'open_duration') and position.open_duration > timedelta(days=7):
                    recommendations.append({
                        'action': 'review',
                        'pair': position.pair,
                        'reason': 'Position open for extended period',
                        'priority': 'low'
                    })
            
            return recommendations
            
        except Exception as e:
            logger.error_occurred(e, "getting position recommendations")
            return []
    
    def emergency_stop(self) -> bool:
        """Emergency stop - close all positions"""
        try:
            logger.critical("🚨 EMERGENCY STOP TRIGGERED")
            logger.critical(f"Daily PnL: {self.daily_pnl}")
            logger.critical(f"Drawdown: {self.current_drawdown:.2f}%")
            logger.critical(f"Total Trades: {self.total_trades}")
            
            # This would trigger the main bot to close all positions
            return True
            
        except Exception as e:
            logger.error_occurred(e, "emergency stop")
            return False
