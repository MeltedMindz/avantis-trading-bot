"""
Data models for the Avantis Trading Bot
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class TradeDirection(str, Enum):
    """Trade direction enum"""
    LONG = "long"
    SHORT = "short"


class OrderType(str, Enum):
    """Order type enum"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LIMIT = "stop_limit"
    MARKET_ZERO_FEE = "market_zero_fee"


class TradeStatus(str, Enum):
    """Trade status enum"""
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class StrategyType(str, Enum):
    """Strategy type enum"""
    DCA = "dca"  # Dollar Cost Averaging
    GRID = "grid"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    SCALPING = "scalping"


class Trade(BaseModel):
    """Trade model"""
    id: Optional[str] = None
    pair: str
    direction: TradeDirection
    entry_price: float
    current_price: Optional[float] = None
    size: float
    leverage: int
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: TradeStatus = TradeStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    pnl: Optional[float] = None
    fees_paid: Optional[float] = None
    strategy: Optional[StrategyType] = None
    
    # Avantis specific fields
    pair_index: Optional[int] = None
    trade_index: Optional[int] = None
    collateral_in_trade: Optional[float] = None
    opening_fee: Optional[float] = None
    loss_protection: Optional[Dict[str, Any]] = None


class Position(BaseModel):
    """Position model"""
    pair: str
    total_size: float
    average_entry: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    trades: List[Trade] = []
    leverage: int
    
    @property
    def is_long(self) -> bool:
        return self.total_size > 0
    
    @property
    def is_short(self) -> bool:
        return self.total_size < 0


class StrategyConfig(BaseModel):
    """Strategy configuration"""
    name: str
    strategy_type: StrategyType
    enabled: bool = True
    parameters: Dict[str, Any] = {}
    
    # Risk parameters
    max_position_size: float = 100.0
    stop_loss_percentage: float = 5.0
    take_profit_percentage: float = 10.0
    max_trades_per_day: int = 10


class MarketData(BaseModel):
    """Market data model"""
    pair: str
    price: float
    volume: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None


class Signal(BaseModel):
    """Trading signal model"""
    pair: str
    direction: TradeDirection
    strength: float = Field(ge=0.0, le=1.0)  # Signal strength 0-1
    price: float
    timestamp: datetime = Field(default_factory=datetime.now)
    strategy: StrategyType
    metadata: Dict[str, Any] = {}


class RiskMetrics(BaseModel):
    """Risk metrics model"""
    total_exposure: float
    daily_pnl: float
    max_drawdown: float
    sharpe_ratio: Optional[float] = None
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    open_positions: int
    total_trades: int
    timestamp: datetime = Field(default_factory=datetime.now)


class BotStatus(BaseModel):
    """Bot status model"""
    is_running: bool = False
    is_trading: bool = False
    start_time: Optional[datetime] = None
    last_update: datetime = Field(default_factory=datetime.now)
    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    total_pnl: float = 0.0
    daily_pnl: float = 0.0
    active_strategies: List[str] = []
    error_count: int = 0
    last_error: Optional[str] = None
