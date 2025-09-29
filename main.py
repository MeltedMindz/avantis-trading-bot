#!/usr/bin/env python3
"""
Avantis Trading Bot - Main Entry Point

A comprehensive trading bot for Avantis Protocol using their official SDK.
Supports multiple trading strategies, risk management, and real-time monitoring.

Usage:
    python main.py start                    # Start the trading bot
    python main.py start --config-check     # Check configuration
    python main.py status                   # Show bot status
    python main.py strategy --strategy dca  # Enable DCA strategy
    python main.py analyze --pair ETH/USD   # Analyze market conditions
    python main.py backtest --strategy momentum --days 30  # Run backtest
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.cli import cli


def main():
    """Main entry point for the Avantis Trading Bot"""
    try:
        # Run the CLI
        cli()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
