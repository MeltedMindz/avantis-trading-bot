#!/usr/bin/env python3
"""
Aggressive Trading Bot Runner for 10% Daily Returns
Main entry point for the aggressive compound growth trading bot
"""

import asyncio
import os
import sys
import argparse
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.aggressive_trading_bot import AggressiveTradingBot
from src.compound_growth import CompoundGrowthManager
from src.daily_profit_optimizer import DailyProfitOptimizer
from src.logger import logger


def setup_environment():
    """Set up environment variables for aggressive trading"""
    # Load aggressive configuration
    aggressive_config = Path(__file__).parent / "config_aggressive.env.example"
    
    if aggressive_config.exists():
        # Load environment variables from config file
        with open(aggressive_config, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key not in os.environ:  # Don't override existing env vars
                        os.environ[key] = value
    
    # Set defaults if not provided
    defaults = {
        'DAILY_TARGET_PERCENTAGE': '10.0',
        'MAX_LEVERAGE': '50',
        'MAX_CONCURRENT_TRADES': '10',
        'QUICK_PROFIT_THRESHOLD': '3.0',
        'QUICK_STOP_LOSS': '1.5',
        'MIN_CONFIDENCE_THRESHOLD': '0.55',
        'TRADING_INTERVAL': '30'
    }
    
    for key, value in defaults.items():
        if key not in os.environ:
            os.environ[key] = value


async def run_aggressive_bot(initial_capital: float = None, 
                           daily_target: float = None,
                           max_leverage: int = None,
                           dry_run: bool = False):
    """Run the aggressive trading bot"""
    
    setup_environment()
    
    # Override with command line arguments if provided
    if daily_target:
        os.environ['DAILY_TARGET_PERCENTAGE'] = str(daily_target)
    if max_leverage:
        os.environ['MAX_LEVERAGE'] = str(max_leverage)
    
    logger.info("🚀 Starting Avantis Aggressive Trading Bot")
    logger.info("=" * 60)
    logger.info("🎯 MISSION: 10% Daily Returns with Compound Growth")
    logger.info("=" * 60)
    
    if dry_run:
        logger.info("🧪 DRY RUN MODE - No actual trades will be executed")
        os.environ['MOCK_TRADING'] = 'true'
    
    try:
        # Initialize and run bot
        bot = AggressiveTradingBot()
        
        # Set dry run mode
        if dry_run:
            bot.emergency_stop = False  # Allow dry run to proceed
        
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error_occurred(e, "running aggressive bot")
        return False
    
    return True


async def show_compound_projections():
    """Show compound growth projections"""
    setup_environment()
    
    compound_manager = CompoundGrowthManager()
    
    # Get initial capital from environment or use default
    initial_capital = float(os.getenv('INITIAL_CAPITAL', 10000))
    
    await compound_manager.initialize(initial_capital)
    
    print("\n" + "="*60)
    print("📈 COMPOUND GROWTH PROJECTIONS (10% Daily)")
    print("="*60)
    
    projections = compound_manager.get_projection_analysis()
    
    print(f"💰 Starting Capital: ${initial_capital:,.2f}")
    print(f"🎯 Daily Target: {compound_manager.daily_target_percentage}%")
    print()
    
    for period, data in projections.items():
        days = period.replace("_days", "")
        print(f"📅 After {days:>3} days:")
        print(f"   Capital: ${data['capital']:>12,.0f}")
        print(f"   Return:  {data['total_return']:>12.0f}%")
        print(f"   Multiple: {data['multiplier']:>11.1f}x")
        print()
    
    # Show some specific milestones
    milestones = [
        (30, "1 Month"),
        (90, "3 Months"),
        (180, "6 Months"),
        (365, "1 Year")
    ]
    
    print("🏆 KEY MILESTONES:")
    for days, label in milestones:
        if f"{days}_days" in projections:
            data = projections[f"{days}_days"]
            print(f"   {label:>8}: ${data['capital']:>10,.0f} ({data['total_return']:>6.0f}% return)")
    
    print("="*60)
    print("⚠️  DISCLAIMER: These are theoretical projections.")
    print("    Actual results may vary significantly.")
    print("    Trading involves substantial risk of loss.")
    print("="*60)


async def show_daily_status():
    """Show current daily trading status"""
    setup_environment()
    
    try:
        from src.avantis_client import AvantisClient
        
        # Initialize components
        avantis_client = AvantisClient()
        if not await avantis_client.initialize():
            print("❌ Failed to initialize Avantis client")
            return
        
        # Get current balance
        balance = await avantis_client.client.get_usdc_balance(
            avantis_client.trader_address
        )
        
        # Initialize compound manager
        compound_manager = CompoundGrowthManager()
        await compound_manager.initialize(float(balance))
        
        # Initialize daily optimizer
        daily_optimizer = DailyProfitOptimizer(compound_manager, avantis_client)
        await daily_optimizer.initialize()
        
        # Get status
        status = await daily_optimizer.get_daily_status()
        
        print("\n" + "="*60)
        print("📊 DAILY TRADING STATUS")
        print("="*60)
        
        print(f"💰 Current Capital: ${compound_manager.current_capital:,.2f}")
        print(f"🎯 Daily Target: ${status.target_amount:,.2f}")
        print(f"📈 Current Progress: {status.progress_percentage:.1f}%")
        print(f"📊 Profit Today: ${status.current_profit:,.2f}")
        print(f"⏰ Hours Remaining: {status.hours_remaining:.1f}")
        print(f"🕐 Required Hourly Rate: ${status.required_hourly_rate:,.2f}")
        print(f"🌅 Current Phase: {status.phase.value}")
        print(f"⚠️  Risk Level: {status.risk_level}")
        print(f"💡 Recommended Action: {status.recommended_action}")
        
        # Show compound stats
        stats = compound_manager.get_compound_stats()
        print(f"\n📊 COMPOUND GROWTH STATS:")
        print(f"   Total Days: {stats.total_days}")
        print(f"   Successful Days: {stats.successful_days}")
        print(f"   Win Rate: {stats.successful_days/max(stats.total_days, 1)*100:.1f}%")
        print(f"   Current Streak: {stats.streak_current} days")
        print(f"   Compound Multiple: {stats.compound_return/100 + 1:.2f}x")
        
        print("="*60)
        
    except Exception as e:
        logger.error_occurred(e, "showing daily status")


async def test_strategies():
    """Test the aggressive trading strategies"""
    setup_environment()
    
    logger.info("🧪 Testing Aggressive Trading Strategies")
    
    try:
        from src.strategies.aggressive_momentum_strategy import AggressiveMomentumStrategy
        
        # Initialize strategy
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
        
        # Generate signals
        signals = await strategy.analyze(market_data)
        
        if signals:
            logger.info(f"✅ Generated {len(signals)} trading signals")
            
            for pair, signal in signals.items():
                logger.info(f"🚀 {pair} Signal:")
                logger.info(f"   Direction: {signal.direction.value}")
                logger.info(f"   Confidence: {signal.confidence:.2f}")
                logger.info(f"   Urgency: {signal.urgency}")
                logger.info(f"   Expected Return: {signal.expected_return:.1%}")
                logger.info(f"   Leverage: {signal.leverage}x")
                logger.info(f"   Position Size: ${signal.position_size:,.0f}")
        else:
            logger.info("⚠️ No signals generated with current market data")
            
    except Exception as e:
        logger.error_occurred(e, "testing strategies")


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Avantis Aggressive Trading Bot - 10% Daily Returns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_aggressive_bot.py                    # Start bot with default settings
  python run_aggressive_bot.py --capital 5000    # Start with $5000
  python run_aggressive_bot.py --target 15       # 15% daily target
  python run_aggressive_bot.py --dry-run         # Test mode
  python run_aggressive_bot.py --projections     # Show compound projections
  python run_aggressive_bot.py --status          # Show daily status
  python run_aggressive_bot.py --test            # Test strategies
        """
    )
    
    parser.add_argument('--capital', type=float, help='Starting capital amount')
    parser.add_argument('--target', type=float, help='Daily profit target percentage')
    parser.add_argument('--leverage', type=int, help='Maximum leverage')
    parser.add_argument('--dry-run', action='store_true', help='Run in dry-run mode')
    parser.add_argument('--projections', action='store_true', help='Show compound growth projections')
    parser.add_argument('--status', action='store_true', help='Show daily trading status')
    parser.add_argument('--test', action='store_true', help='Test trading strategies')
    
    args = parser.parse_args()
    
    # Handle special commands
    if args.projections:
        asyncio.run(show_compound_projections())
        return
    
    if args.status:
        asyncio.run(show_daily_status())
        return
    
    if args.test:
        asyncio.run(test_strategies())
        return
    
    # Run the bot
    asyncio.run(run_aggressive_bot(
        initial_capital=args.capital,
        daily_target=args.target,
        max_leverage=args.leverage,
        dry_run=args.dry_run
    ))


if __name__ == "__main__":
    main()
