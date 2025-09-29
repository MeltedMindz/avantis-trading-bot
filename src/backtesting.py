"""
Backtesting module for the Avantis Trading Bot
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass

from .models import Trade, Signal, MarketData, TradeDirection, TradeStatus
from .strategies import BaseStrategy
from .risk_manager import RiskManager
from .logger import logger


@dataclass
class BacktestResult:
    """Backtest result data"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    profit_factor: float
    trades: List[Trade]
    equity_curve: List[float]
    daily_returns: List[float]


class Backtester:
    """Backtesting engine for trading strategies"""
    
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.risk_manager = RiskManager()
        
        # Performance tracking
        self.equity_curve = [initial_capital]
        self.daily_returns = []
        self.peak_capital = initial_capital
        self.max_drawdown = 0.0
        
        # Trade tracking
        self.completed_trades = []
        self.active_trades = []
        
        logger.info(f"Backtester initialized with ${initial_capital} capital")
    
    def _generate_market_data(self, 
                             pair: str, 
                             start_date: datetime, 
                             end_date: datetime, 
                             interval_minutes: int = 60) -> List[MarketData]:
        """Generate synthetic market data for backtesting"""
        try:
            market_data = []
            current_date = start_date
            
            # Generate price data using random walk
            base_price = 2000 if 'ETH' in pair else 40000 if 'BTC' in pair else 1000
            current_price = base_price
            
            while current_date <= end_date:
                # Generate price movement (random walk with trend)
                price_change = np.random.normal(0, 0.02)  # 2% volatility
                current_price *= (1 + price_change)
                
                # Generate volume
                volume = np.random.uniform(1000, 5000)
                
                market_data.append(MarketData(
                    pair=pair,
                    price=current_price,
                    volume=volume,
                    timestamp=current_date
                ))
                
                current_date += timedelta(minutes=interval_minutes)
            
            logger.info(f"Generated {len(market_data)} data points for {pair}")
            return market_data
            
        except Exception as e:
            logger.error_occurred(e, "generating market data")
            return []
    
    def _calculate_trade_pnl(self, trade: Trade, exit_price: float) -> float:
        """Calculate PnL for a completed trade"""
        try:
            if trade.direction == TradeDirection.LONG:
                pnl = (exit_price - trade.entry_price) / trade.entry_price * trade.size * trade.leverage
            else:
                pnl = (trade.entry_price - exit_price) / trade.entry_price * trade.size * trade.leverage
            
            # Subtract fees (simplified)
            pnl -= trade.fees_paid or (trade.size * 0.001)  # 0.1% fee
            
            return pnl
            
        except Exception as e:
            logger.error_occurred(e, "calculating trade PnL")
            return 0.0
    
    def _update_equity_curve(self, pnl: float):
        """Update equity curve and calculate drawdown"""
        try:
            self.current_capital += pnl
            self.equity_curve.append(self.current_capital)
            
            # Update peak and drawdown
            if self.current_capital > self.peak_capital:
                self.peak_capital = self.current_capital
                self.max_drawdown = 0.0
            else:
                drawdown = (self.peak_capital - self.current_capital) / self.peak_capital * 100
                self.max_drawdown = max(self.max_drawdown, drawdown)
            
            # Calculate daily return
            if len(self.equity_curve) > 1:
                daily_return = (self.current_capital - self.equity_curve[-2]) / self.equity_curve[-2]
                self.daily_returns.append(daily_return)
                
        except Exception as e:
            logger.error_occurred(e, "updating equity curve")
    
    def _close_trade(self, trade: Trade, exit_price: float, exit_reason: str):
        """Close a trade and update performance metrics"""
        try:
            # Calculate PnL
            pnl = self._calculate_trade_pnl(trade, exit_price)
            
            # Update trade
            trade.pnl = pnl
            trade.status = TradeStatus.CLOSED
            trade.closed_at = datetime.now()
            
            # Update capital and equity curve
            self._update_equity_curve(pnl)
            
            # Move to completed trades
            self.active_trades.remove(trade)
            self.completed_trades.append(trade)
            
            # Update risk manager
            self.risk_manager.update_trade_result(pnl)
            
            logger.debug(f"Trade closed: {trade.pair} {trade.direction.value} PnL: ${pnl:.2f} Reason: {exit_reason}")
            
        except Exception as e:
            logger.error_occurred(e, "closing trade")
    
    async def run_backtest(self, 
                          strategy: BaseStrategy, 
                          pair: str, 
                          start_date: datetime, 
                          end_date: datetime,
                          initial_position_size: float = 100.0) -> BacktestResult:
        """Run backtest for a strategy"""
        try:
            logger.info(f"Starting backtest for {strategy.name} on {pair}")
            logger.info(f"Period: {start_date} to {end_date}")
            
            # Generate market data
            market_data = self._generate_market_data(pair, start_date, end_date)
            if not market_data:
                raise ValueError("Failed to generate market data")
            
            # Reset state
            self.current_capital = self.initial_capital
            self.equity_curve = [self.initial_capital]
            self.daily_returns = []
            self.completed_trades = []
            self.active_trades = []
            self.peak_capital = self.initial_capital
            self.max_drawdown = 0.0
            
            # Process each market data point
            for i, data in enumerate(market_data):
                try:
                    # Generate signals
                    signal = await strategy.analyze(data)
                    
                    if signal and strategy.validate_signal(signal):
                        # Check if we can open a new trade
                        if len(self.active_trades) < 5:  # Max 5 concurrent trades
                            # Create trade from signal
                            trade = strategy.create_trade_from_signal(signal)
                            trade.size = min(initial_position_size, self.current_capital * 0.1)  # 10% of capital
                            
                            # Validate with risk manager
                            is_valid, reason = self.risk_manager.validate_trade(trade, [])
                            
                            if is_valid:
                                self.active_trades.append(trade)
                                logger.debug(f"Trade opened: {trade.pair} {trade.direction.value} at {trade.entry_price}")
                    
                    # Check exit conditions for active trades
                    trades_to_close = []
                    for trade in self.active_trades:
                        should_exit = await strategy.should_exit(trade, data)
                        
                        if should_exit:
                            trades_to_close.append((trade, "strategy_exit"))
                        elif trade.stop_loss and data.price <= trade.stop_loss:
                            trades_to_close.append((trade, "stop_loss"))
                        elif trade.take_profit and data.price >= trade.take_profit:
                            trades_to_close.append((trade, "take_profit"))
                        elif trade.created_at and (data.timestamp - trade.created_at).total_seconds() > 86400 * 7:  # 7 days
                            trades_to_close.append((trade, "timeout"))
                    
                    # Close trades
                    for trade, reason in trades_to_close:
                        self._close_trade(trade, data.price, reason)
                    
                    # Update strategy performance
                    for trade in self.completed_trades[-len(trades_to_close):]:
                        strategy.update_performance(trade, trade.pnl or 0)
                    
                except Exception as e:
                    logger.error_occurred(e, f"processing market data point {i}")
                    continue
            
            # Close any remaining active trades
            for trade in self.active_trades:
                self._close_trade(trade, market_data[-1].price, "backtest_end")
            
            # Calculate performance metrics
            result = self._calculate_performance_metrics()
            
            logger.info(f"Backtest completed: {result.total_trades} trades, {result.win_rate:.1%} win rate, ${result.total_pnl:.2f} PnL")
            
            return result
            
        except Exception as e:
            logger.error_occurred(e, "running backtest")
            raise
    
    def _calculate_performance_metrics(self) -> BacktestResult:
        """Calculate comprehensive performance metrics"""
        try:
            total_trades = len(self.completed_trades)
            winning_trades = sum(1 for t in self.completed_trades if (t.pnl or 0) > 0)
            losing_trades = total_trades - winning_trades
            
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            total_pnl = sum(t.pnl or 0 for t in self.completed_trades)
            
            # Calculate Sharpe ratio
            sharpe_ratio = 0.0
            if self.daily_returns and len(self.daily_returns) > 1:
                mean_return = np.mean(self.daily_returns)
                std_return = np.std(self.daily_returns)
                if std_return > 0:
                    sharpe_ratio = mean_return / std_return * np.sqrt(252)  # Annualized
            
            # Calculate profit factor
            gross_profit = sum(t.pnl or 0 for t in self.completed_trades if (t.pnl or 0) > 0)
            gross_loss = abs(sum(t.pnl or 0 for t in self.completed_trades if (t.pnl or 0) < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            return BacktestResult(
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                total_pnl=total_pnl,
                max_drawdown=self.max_drawdown,
                sharpe_ratio=sharpe_ratio,
                profit_factor=profit_factor,
                trades=self.completed_trades,
                equity_curve=self.equity_curve,
                daily_returns=self.daily_returns
            )
            
        except Exception as e:
            logger.error_occurred(e, "calculating performance metrics")
            return BacktestResult(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                profit_factor=0.0,
                trades=[],
                equity_curve=[],
                daily_returns=[]
            )
    
    def generate_report(self, result: BacktestResult, strategy_name: str) -> str:
        """Generate a comprehensive backtest report"""
        try:
            report = f"""
# Backtest Report: {strategy_name}

## Performance Summary
- **Total Trades**: {result.total_trades}
- **Winning Trades**: {result.winning_trades}
- **Losing Trades**: {result.losing_trades}
- **Win Rate**: {result.win_rate:.1%}
- **Total PnL**: ${result.total_pnl:.2f}
- **Max Drawdown**: {result.max_drawdown:.2f}%
- **Sharpe Ratio**: {result.sharpe_ratio:.2f}
- **Profit Factor**: {result.profit_factor:.2f}

## Capital Performance
- **Initial Capital**: ${self.initial_capital:,.2f}
- **Final Capital**: ${self.current_capital:,.2f}
- **Total Return**: {((self.current_capital - self.initial_capital) / self.initial_capital * 100):.2f}%

## Trade Analysis
"""
            
            if result.trades:
                # Calculate average trade metrics
                avg_pnl = np.mean([t.pnl or 0 for t in result.trades])
                avg_win = np.mean([t.pnl or 0 for t in result.trades if (t.pnl or 0) > 0])
                avg_loss = np.mean([t.pnl or 0 for t in result.trades if (t.pnl or 0) < 0])
                
                report += f"""
- **Average PnL**: ${avg_pnl:.2f}
- **Average Win**: ${avg_win:.2f}
- **Average Loss**: ${avg_loss:.2f}
"""
            
            return report
            
        except Exception as e:
            logger.error_occurred(e, "generating backtest report")
            return f"Error generating report: {str(e)}"
    
    async def compare_strategies(self, 
                               strategies: List[BaseStrategy], 
                               pair: str, 
                               start_date: datetime, 
                               end_date: datetime) -> Dict[str, BacktestResult]:
        """Compare multiple strategies"""
        try:
            results = {}
            
            for strategy in strategies:
                logger.info(f"Backtesting strategy: {strategy.name}")
                
                # Run backtest
                result = await self.run_backtest(strategy, pair, start_date, end_date)
                results[strategy.name] = result
                
                # Generate report
                report = self.generate_report(result, strategy.name)
                logger.info(f"Backtest completed for {strategy.name}")
                logger.info(report)
            
            return results
            
        except Exception as e:
            logger.error_occurred(e, "comparing strategies")
            return {}


# Convenience functions for easy backtesting
async def quick_backtest(strategy: BaseStrategy, 
                        pair: str = "ETH/USD", 
                        days: int = 30,
                        initial_capital: float = 10000.0) -> BacktestResult:
    """Quick backtest for a strategy"""
    backtester = Backtester(initial_capital)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    return await backtester.run_backtest(strategy, pair, start_date, end_date)


async def compare_strategies_quick(strategies: List[BaseStrategy], 
                                 pair: str = "ETH/USD", 
                                 days: int = 30) -> Dict[str, BacktestResult]:
    """Quick comparison of multiple strategies"""
    backtester = Backtester()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    return await backtester.compare_strategies(strategies, pair, start_date, end_date)
