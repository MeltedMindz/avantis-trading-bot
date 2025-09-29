"""
Logging configuration for the Avantis Trading Bot
"""

import logging
import os
from datetime import datetime
from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom colored formatter for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


class TradingLogger:
    """Enhanced logger for trading bot"""
    
    def __init__(self, name: str = "trading_bot", log_level: str = "INFO", log_file: Optional[str] = None):
        self.name = name
        self.log_level = log_level
        self.log_file = log_file
        self.console = Console()
        
        # Install rich traceback
        install()
        
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup logger with handlers"""
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(getattr(logging, self.log_level.upper()))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler with rich formatting
        console_handler = RichHandler(
            console=self.console,
            show_time=True,
            show_path=False,
            markup=True,
            rich_tracebacks=True
        )
        console_handler.setLevel(getattr(logging, self.log_level.upper()))
        
        # File handler if log file specified
        if self.log_file:
            # Create logs directory if it doesn't exist
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
            
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        
        # Set console handler
        self.logger.addHandler(console_handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(message, **kwargs)
    
    def trade_opened(self, trade_data: dict):
        """Log trade opened event"""
        self.info(f"🔵 Trade Opened: {trade_data['pair']} {trade_data['direction']} "
                 f"Size: {trade_data['size']} Leverage: {trade_data['leverage']}x")
    
    def trade_closed(self, trade_data: dict):
        """Log trade closed event"""
        pnl = trade_data.get('pnl', 0)
        pnl_emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
        self.info(f"{pnl_emoji} Trade Closed: {trade_data['pair']} "
                 f"PnL: ${pnl:.2f}")
    
    def signal_generated(self, signal_data: dict):
        """Log signal generated event"""
        direction_emoji = "📈" if signal_data['direction'] == 'long' else "📉"
        self.info(f"{direction_emoji} Signal Generated: {signal_data['pair']} "
                 f"{signal_data['direction']} Strength: {signal_data['strength']:.2f}")
    
    def error_occurred(self, error: Exception, context: str = ""):
        """Log error with context"""
        self.error(f"❌ Error in {context}: {str(error)}")
    
    def risk_alert(self, message: str):
        """Log risk alert"""
        self.warning(f"⚠️ Risk Alert: {message}")
    
    def performance_update(self, metrics: dict):
        """Log performance metrics"""
        self.info(f"📊 Performance: PnL: ${metrics.get('total_pnl', 0):.2f} "
                 f"Trades: {metrics.get('total_trades', 0)} "
                 f"Win Rate: {metrics.get('win_rate', 0):.1%}")


# Global logger instance
logger = TradingLogger()
