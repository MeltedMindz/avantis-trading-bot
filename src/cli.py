"""
Command Line Interface for the Avantis Trading Bot
"""

import asyncio
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from datetime import datetime
import json

from .trading_bot import AvantisTradingBot
from .logger import logger
from .config import config


console = Console()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Avantis Trading Bot - A comprehensive trading bot for Avantis Protocol"""
    pass


@cli.command()
@click.option('--config-check', is_flag=True, help='Check configuration without starting bot')
def start(config_check: bool):
    """Start the Avantis Trading Bot"""
    
    if config_check:
        console.print("🔧 Checking configuration...")
        
        # Validate configuration
        if config.validate():
            console.print("✅ Configuration is valid", style="green")
            
            # Display configuration summary
            table = Table(title="Configuration Summary")
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Provider URL", config.wallet.provider_url)
            table.add_row("Trader Address", config.wallet.trader_address[:10] + "..." if hasattr(config.wallet, 'trader_address') else "Not set")
            table.add_row("Default Leverage", str(config.trading.default_leverage))
            table.add_row("Max Position Size", f"${config.trading.max_position_size}")
            table.add_row("Max Daily Loss", f"${config.trading.max_daily_loss}")
            table.add_row("Slippage Tolerance", f"{config.trading.slippage_tolerance}%")
            
            console.print(table)
        else:
            console.print("❌ Configuration validation failed", style="red")
            return
    else:
        # Start the bot
        asyncio.run(_start_bot())


async def _start_bot():
    """Start the trading bot with live dashboard"""
    console.print("🚀 Starting Avantis Trading Bot...")
    
    # Create bot instance
    bot = AvantisTradingBot()
    
    # Initialize bot
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Initializing bot...", total=None)
        
        if not await bot.initialize():
            console.print("❌ Failed to initialize bot", style="red")
            return
        
        progress.update(task, description="Bot initialized successfully!")
    
    # Start live dashboard
    await _run_live_dashboard(bot)


async def _run_live_dashboard(bot: AvantisTradingBot):
    """Run the live dashboard"""
    layout = Layout()
    
    layout.split_column(
        Layout(name="header"),
        Layout(name="main"),
        Layout(name="footer")
    )
    
    layout["main"].split_row(
        Layout(name="left"),
        Layout(name="right")
    )
    
    layout["left"].split_column(
        Layout(name="status"),
        Layout(name="trades")
    )
    
    layout["right"].split_column(
        Layout(name="strategies"),
        Layout(name="risk")
    )
    
    try:
        with Live(layout, refresh_per_second=1, screen=True) as live:
            # Start bot
            bot_task = asyncio.create_task(bot.start())
            
            # Update dashboard
            while True:
                await asyncio.sleep(1)
                _update_dashboard(layout, bot)
                
    except KeyboardInterrupt:
        console.print("\n🛑 Stopping bot...")
        await bot.stop()
        bot_task.cancel()


def _update_dashboard(layout: Layout, bot: AvantisTradingBot):
    """Update the live dashboard"""
    status = bot.get_status()
    
    # Header
    layout["header"].update(
        Panel(
            f"Avantis Trading Bot - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            style="bold blue"
        )
    )
    
    # Status panel
    status_table = Table(title="Bot Status")
    status_table.add_column("Metric", style="cyan")
    status_table.add_column("Value", style="green")
    
    status_table.add_row("Status", "🟢 Running" if status['is_trading'] else "🔴 Stopped")
    status_table.add_row("Total PnL", f"${status['total_pnl']:.2f}")
    status_table.add_row("Daily PnL", f"${status['daily_pnl']:.2f}")
    status_table.add_row("Active Trades", str(status['active_trades']))
    status_table.add_row("Total Trades", str(status['status']['total_trades']))
    status_table.add_row("Win Rate", f"{status['status']['win_rate']:.1%}" if status['status']['win_rate'] else "N/A")
    
    layout["status"].update(Panel(status_table, title="Status"))
    
    # Active trades panel
    trades_table = Table(title="Active Trades")
    trades_table.add_column("Pair", style="cyan")
    trades_table.add_column("Direction", style="green")
    trades_table.add_column("Size", style="yellow")
    trades_table.add_column("Leverage", style="blue")
    trades_table.add_column("Strategy", style="magenta")
    
    for trade in bot.active_trades[:10]:  # Show max 10 trades
        direction_emoji = "📈" if trade.direction.value == "long" else "📉"
        trades_table.add_row(
            trade.pair,
            f"{direction_emoji} {trade.direction.value}",
            f"${trade.size:.2f}",
            f"{trade.leverage}x",
            trade.strategy.value if trade.strategy else "N/A"
        )
    
    layout["trades"].update(Panel(trades_table, title="Active Trades"))
    
    # Strategies panel
    strategies_table = Table(title="Strategies")
    strategies_table.add_column("Strategy", style="cyan")
    strategies_table.add_column("Status", style="green")
    strategies_table.add_column("Signals", style="yellow")
    strategies_table.add_column("Trades", style="blue")
    strategies_table.add_column("PnL", style="magenta")
    
    for name, strategy_data in status['strategies'].items():
        status_emoji = "🟢" if strategy_data['enabled'] else "🔴"
        strategies_table.add_row(
            name,
            status_emoji,
            str(strategy_data['signals_generated']),
            str(strategy_data['trades_executed']),
            f"${strategy_data['total_pnl']:.2f}"
        )
    
    layout["strategies"].update(Panel(strategies_table, title="Strategies"))
    
    # Risk panel
    risk_table = Table(title="Risk Metrics")
    risk_table.add_column("Metric", style="cyan")
    risk_table.add_column("Value", style="green")
    
    risk_metrics = status['risk_metrics']
    risk_table.add_row("Daily PnL", f"${risk_metrics['daily_pnl']:.2f}")
    risk_table.add_row("Max Drawdown", f"{risk_metrics['max_drawdown']:.2f}%")
    risk_table.add_row("Win Rate", f"{risk_metrics['win_rate']:.1%}" if risk_metrics['win_rate'] else "N/A")
    risk_table.add_row("Open Positions", str(risk_metrics['open_positions']))
    risk_table.add_row("Total Trades", str(risk_metrics['total_trades']))
    
    layout["risk"].update(Panel(risk_table, title="Risk"))
    
    # Footer
    layout["footer"].update(
        Panel(
            "Press Ctrl+C to stop the bot",
            style="dim"
        )
    )


@cli.command()
def status():
    """Show current bot status"""
    console.print("📊 Bot Status", style="bold blue")
    
    # This would load from saved state in a real implementation
    console.print("Bot is not currently running. Use 'avantis-bot start' to start the bot.")


@cli.command()
@click.option('--strategy', type=click.Choice(['dca', 'momentum', 'mean_reversion', 'grid', 'breakout']), 
              help='Enable specific strategy')
@click.option('--disable', is_flag=True, help='Disable the strategy instead of enabling')
def strategy(strategy: str, disable: bool):
    """Enable or disable trading strategies"""
    if not strategy:
        console.print("Please specify a strategy with --strategy option")
        return
    
    action = "disabled" if disable else "enabled"
    console.print(f"Strategy '{strategy}' {action}")


@cli.command()
@click.option('--pair', default='ETH/USD', help='Trading pair to analyze')
@click.option('--period', default=24, help='Analysis period in hours')
def analyze(pair: str, period: int):
    """Analyze market conditions for a trading pair"""
    console.print(f"📈 Analyzing {pair} for the last {period} hours...")
    
    # This would implement market analysis in a real bot
    table = Table(title=f"Market Analysis - {pair}")
    table.add_column("Indicator", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Signal", style="yellow")
    
    table.add_row("RSI (14)", "45.2", "🟡 Neutral")
    table.add_row("MACD", "0.0023", "🟢 Bullish")
    table.add_row("MA (20)", "1985.50", "🟡 Neutral")
    table.add_row("Volume", "1.2M", "🟢 High")
    
    console.print(table)


@cli.command()
def config_show():
    """Show current configuration"""
    console.print("⚙️ Current Configuration", style="bold blue")
    
    # Display configuration
    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Provider URL", config.wallet.provider_url)
    table.add_row("Default Leverage", str(config.trading.default_leverage))
    table.add_row("Max Position Size", f"${config.trading.max_position_size}")
    table.add_row("Max Daily Loss", f"${config.trading.max_daily_loss}")
    table.add_row("Slippage Tolerance", f"{config.trading.slippage_tolerance}%")
    table.add_row("Max Open Positions", str(config.trading.max_open_positions))
    
    console.print(table)


@cli.command()
@click.option('--file', default='bot_state.json', help='File to export data to')
def export(file: str):
    """Export bot data and performance metrics"""
    console.print(f"📤 Exporting bot data to {file}...")
    
    # This would export real data in a real implementation
    export_data = {
        "timestamp": datetime.now().isoformat(),
        "status": "exported",
        "message": "Data export functionality would be implemented here"
    }
    
    with open(file, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    console.print(f"✅ Data exported to {file}", style="green")


@cli.command()
def help_advanced():
    """Show advanced usage and examples"""
    console.print("📚 Advanced Usage Guide", style="bold blue")
    
    help_text = """
    Advanced Configuration:
    
    1. Environment Variables:
       export PRIVATE_KEY="0x..."
       export PROVIDER_URL="https://mainnet.base.org"
       export DEFAULT_LEVERAGE=10
    
    2. Strategy Configuration:
       avantis-bot strategy --strategy momentum
       avantis-bot strategy --strategy dca --disable
    
    3. Market Analysis:
       avantis-bot analyze --pair BTC/USD --period 48
    
    4. Configuration Management:
       avantis-bot config-show
       avantis-bot start --config-check
    
    For more information, visit: https://sdk.avantisfi.com/
    """
    
    console.print(Panel(help_text, title="Advanced Usage", border_style="blue"))


if __name__ == "__main__":
    cli()
