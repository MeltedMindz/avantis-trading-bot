"""
Backtesting Example for Avantis Trading Bot

This example demonstrates how to use the backtesting functionality
to test trading strategies before deploying them live.
"""

import asyncio
from datetime import datetime, timedelta

from src.backtesting import Backtester, quick_backtest, compare_strategies_quick
from src.strategies import DCAStrategy, MomentumStrategy, MeanReversionStrategy, GridStrategy
from src.logger import logger


async def single_strategy_backtest():
    """Example of backtesting a single strategy"""
    logger.info("🧪 Single Strategy Backtest Example")
    
    # Create a DCA strategy
    dca_config = {
        'enabled': True,
        'pairs': ['ETH/USD'],
        'leverage': 5,
        'position_size': 100.0,
        'interval_minutes': 120,  # 2 hours
        'direction': 'long'
    }
    
    strategy = DCAStrategy(dca_config)
    
    # Run quick backtest for 30 days
    result = await quick_backtest(
        strategy=strategy,
        pair="ETH/USD",
        days=30,
        initial_capital=10000.0
    )
    
    # Display results
    logger.info("📊 Backtest Results:")
    logger.info(f"Total Trades: {result.total_trades}")
    logger.info(f"Win Rate: {result.win_rate:.1%}")
    logger.info(f"Total PnL: ${result.total_pnl:.2f}")
    logger.info(f"Max Drawdown: {result.max_drawdown:.2f}%")
    logger.info(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
    logger.info(f"Profit Factor: {result.profit_factor:.2f}")


async def strategy_comparison():
    """Example of comparing multiple strategies"""
    logger.info("🆚 Strategy Comparison Example")
    
    # Create multiple strategies
    strategies = [
        DCAStrategy({
            'enabled': True,
            'pairs': ['ETH/USD'],
            'leverage': 5,
            'position_size': 100.0,
            'interval_minutes': 60,
            'direction': 'long'
        }),
        MomentumStrategy({
            'enabled': True,
            'pairs': ['ETH/USD'],
            'leverage': 10,
            'position_size': 100.0,
            'rsi_period': 14,
            'min_signal_strength': 0.7
        }),
        MeanReversionStrategy({
            'enabled': True,
            'pairs': ['ETH/USD'],
            'leverage': 8,
            'position_size': 100.0,
            'z_score_entry': 2.0,
            'min_signal_strength': 0.6
        })
    ]
    
    # Compare strategies
    results = await compare_strategies_quick(
        strategies=strategies,
        pair="ETH/USD",
        days=30
    )
    
    # Display comparison
    logger.info("📈 Strategy Comparison Results:")
    for strategy_name, result in results.items():
        logger.info(f"\n{strategy_name}:")
        logger.info(f"  Trades: {result.total_trades}")
        logger.info(f"  Win Rate: {result.win_rate:.1%}")
        logger.info(f"  PnL: ${result.total_pnl:.2f}")
        logger.info(f"  Max Drawdown: {result.max_drawdown:.2f}%")
        logger.info(f"  Sharpe: {result.sharpe_ratio:.2f}")


async def advanced_backtest():
    """Example of advanced backtesting with custom parameters"""
    logger.info("⚙️ Advanced Backtest Example")
    
    # Create backtester with custom settings
    backtester = Backtester(initial_capital=50000.0)
    
    # Create a grid strategy
    grid_strategy = GridStrategy({
        'enabled': True,
        'pairs': ['ETH/USD'],
        'leverage': 5,
        'position_size': 200.0,
        'grid_levels': 10,
        'grid_spacing': 0.02  # 2% spacing
    })
    
    # Define custom date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)  # 60 days
    
    # Run backtest
    result = await backtester.run_backtest(
        strategy=grid_strategy,
        pair="ETH/USD",
        start_date=start_date,
        end_date=end_date,
        initial_position_size=200.0
    )
    
    # Generate detailed report
    report = backtester.generate_report(result, "Grid Strategy")
    logger.info("📋 Detailed Backtest Report:")
    logger.info(report)
    
    # Analyze individual trades
    if result.trades:
        logger.info(f"\n📊 Trade Analysis:")
        logger.info(f"First 5 trades:")
        for i, trade in enumerate(result.trades[:5]):
            logger.info(f"  Trade {i+1}: {trade.direction.value} {trade.pair} PnL: ${trade.pnl:.2f}")


async def parameter_optimization():
    """Example of parameter optimization through backtesting"""
    logger.info("🔧 Parameter Optimization Example")
    
    # Test different RSI periods for momentum strategy
    rsi_periods = [7, 14, 21, 28]
    results = {}
    
    for period in rsi_periods:
        strategy = MomentumStrategy({
            'enabled': True,
            'pairs': ['ETH/USD'],
            'leverage': 10,
            'position_size': 100.0,
            'rsi_period': period,
            'min_signal_strength': 0.7
        })
        
        result = await quick_backtest(strategy, "ETH/USD", 30)
        results[f"RSI_{period}"] = result
        
        logger.info(f"RSI Period {period}: Win Rate {result.win_rate:.1%}, PnL ${result.total_pnl:.2f}")
    
    # Find best performing parameters
    best_strategy = max(results.items(), key=lambda x: x[1].total_pnl)
    logger.info(f"🏆 Best performing: {best_strategy[0]} with PnL ${best_strategy[1].total_pnl:.2f}")


if __name__ == "__main__":
    # Run examples
    asyncio.run(single_strategy_backtest())
    print("\n" + "="*50 + "\n")
    asyncio.run(strategy_comparison())
    print("\n" + "="*50 + "\n")
    asyncio.run(advanced_backtest())
    print("\n" + "="*50 + "\n")
    asyncio.run(parameter_optimization())
