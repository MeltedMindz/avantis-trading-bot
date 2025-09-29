"""
Configuration management for the Avantis Trading Bot
"""

import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class TradingConfig(BaseModel):
    """Trading configuration parameters"""
    default_leverage: int = Field(default=10, ge=1, le=100)
    max_position_size: float = Field(default=100.0, gt=0)
    min_position_size: float = Field(default=1.0, gt=0)
    slippage_tolerance: float = Field(default=1.0, ge=0.1, le=10.0)
    
    # Risk management
    max_daily_loss: float = Field(default=50.0, gt=0)
    max_open_positions: int = Field(default=5, ge=1, le=20)
    stop_loss_percentage: float = Field(default=5.0, gt=0, le=50.0)
    take_profit_percentage: float = Field(default=10.0, gt=0, le=500.0)


class WalletConfig(BaseModel):
    """Wallet configuration parameters"""
    private_key: str
    provider_url: str = "https://mainnet.base.org"
    ws_url: str = "wss://hermes.pyth.network/ws"
    
    @classmethod
    def from_env(cls) -> "WalletConfig":
        private_key = os.getenv("PRIVATE_KEY")
        if not private_key:
            raise ValueError("PRIVATE_KEY environment variable is required")
        
        return cls(
            private_key=private_key,
            provider_url=os.getenv("PROVIDER_URL", "https://mainnet.base.org"),
            ws_url=os.getenv("WS_URL", "wss://hermes.pyth.network/ws")
        )


class APIConfig(BaseModel):
    """External API configuration"""
    binance_api_key: Optional[str] = None
    binance_secret_key: Optional[str] = None


class LoggingConfig(BaseModel):
    """Logging configuration"""
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="logs/trading_bot.log")


class DatabaseConfig(BaseModel):
    """Database configuration"""
    database_url: str = Field(default="sqlite:///trades.db")


class Config:
    """Main configuration class"""
    
    def __init__(self):
        self.wallet = WalletConfig.from_env()
        self.trading = TradingConfig(
            default_leverage=int(os.getenv("DEFAULT_LEVERAGE", 10)),
            max_position_size=float(os.getenv("MAX_POSITION_SIZE", 100)),
            min_position_size=float(os.getenv("MIN_POSITION_SIZE", 1)),
            slippage_tolerance=float(os.getenv("SLIPPAGE_TOLERANCE", 1)),
            max_daily_loss=float(os.getenv("MAX_DAILY_LOSS", 50)),
            max_open_positions=int(os.getenv("MAX_OPEN_POSITIONS", 5)),
            stop_loss_percentage=float(os.getenv("STOP_LOSS_PERCENTAGE", 5)),
            take_profit_percentage=float(os.getenv("TAKE_PROFIT_PERCENTAGE", 10))
        )
        self.api = APIConfig(
            binance_api_key=os.getenv("BINANCE_API_KEY"),
            binance_secret_key=os.getenv("BINANCE_SECRET_KEY")
        )
        self.logging = LoggingConfig(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_file=os.getenv("LOG_FILE", "logs/trading_bot.log")
        )
        self.database = DatabaseConfig(
            database_url=os.getenv("DATABASE_URL", "sqlite:///trades.db")
        )
    
    def validate(self) -> bool:
        """Validate configuration"""
        try:
            # Validate wallet config
            if not self.wallet.private_key.startswith("0x"):
                raise ValueError("Private key must start with 0x")
            
            # Validate trading config
            if self.trading.min_position_size >= self.trading.max_position_size:
                raise ValueError("Min position size must be less than max position size")
            
            return True
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return False


# Global config instance
config = Config()
