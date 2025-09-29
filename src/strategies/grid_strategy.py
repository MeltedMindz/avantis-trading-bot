"""
Grid Trading Strategy
"""

import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
from .base_strategy import BaseStrategy
from ..models import Signal, MarketData, StrategyType, TradeDirection
from ..logger import logger


class GridStrategy(BaseStrategy):
    """
    Grid Trading Strategy
    
    Places buy and sell orders at predetermined price levels,
    profiting from price oscillations within a range.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("Grid Strategy", StrategyType.GRID, config)
        
        # Grid specific parameters
        self.grid_levels = config.get('grid_levels', 10)
        self.grid_spacing = config.get('grid_spacing', 0.01)  # 1% spacing
        self.grid_range = config.get('grid_range', 0.1)  # 10% range
        self.base_price = config.get('base_price', None)
        self.grid_positions = {}  # Track grid positions per pair
        
        logger.info(f"Grid Strategy initialized with {self.grid_levels} levels and {self.grid_spacing*100}% spacing")
    
    def _calculate_grid_levels(self, current_price: float, pair: str) -> List[Tuple[float, TradeDirection]]:
        """Calculate grid buy and sell levels"""
        try:
            if not self.base_price:
                self.base_price = current_price
            
            levels = []
            half_levels = self.grid_levels // 2
            
            # Calculate buy levels (below current price)
            for i in range(1, half_levels + 1):
                buy_price = self.base_price * (1 - i * self.grid_spacing)
                levels.append((buy_price, TradeDirection.LONG))
            
            # Calculate sell levels (above current price)
            for i in range(1, half_levels + 1):
                sell_price = self.base_price * (1 + i * self.grid_spacing)
                levels.append((sell_price, TradeDirection.SHORT))
            
            return levels
            
        except Exception as e:
            logger.error_occurred(e, "calculating grid levels")
            return []
    
    def _find_nearest_grid_level(self, current_price: float, pair: str) -> Optional[Tuple[float, TradeDirection]]:
        """Find the nearest grid level for the current price"""
        try:
            levels = self._calculate_grid_levels(current_price, pair)
            if not levels:
                return None
            
            # Find closest level
            closest_level = None
            min_distance = float('inf')
            
            for price, direction in levels:
                distance = abs(current_price - price)
                if distance < min_distance:
                    min_distance = distance
                    closest_level = (price, direction)
            
            return closest_level
            
        except Exception as e:
            logger.error_occurred(e, "finding nearest grid level")
            return None
    
    async def analyze(self, market_data: MarketData) -> Optional[Signal]:
        """Generate grid trading signals"""
        try:
            pair = market_data.pair
            current_price = market_data.price
            
            # Initialize grid positions for this pair if not exists
            if pair not in self.grid_positions:
                self.grid_positions[pair] = {
                    'levels': self._calculate_grid_levels(current_price, pair),
                    'filled_levels': set(),
                    'last_update': datetime.now()
                }
            
            grid_data = self.grid_positions[pair]
            
            # Check if we're near a grid level
            nearest_level = self._find_nearest_grid_level(current_price, pair)
            if not nearest_level:
                return None
            
            level_price, direction = nearest_level
            
            # Check if this level has already been filled
            level_key = f"{direction.value}_{level_price:.6f}"
            if level_key in grid_data['filled_levels']:
                return None
            
            # Calculate signal strength based on distance to grid level
            distance_to_level = abs(current_price - level_price)
            price_threshold = current_price * 0.001  # 0.1% threshold
            
            if distance_to_level <= price_threshold:
                # Mark this level as filled
                grid_data['filled_levels'].add(level_key)
                
                # Create signal
                signal = Signal(
                    pair=pair,
                    direction=direction,
                    strength=0.8,  # High confidence for grid trades
                    price=level_price,
                    strategy=StrategyType.GRID,
                    metadata={
                        'grid_level': level_price,
                        'distance_to_level': distance_to_level,
                        'total_levels': self.grid_levels,
                        'filled_levels': len(grid_data['filled_levels'])
                    }
                )
                
                self.signals_generated += 1
                logger.debug(f"Grid signal generated for {pair}: {direction.value} at {level_price}")
                return signal
            
            return None
            
        except Exception as e:
            logger.error_occurred(e, "Grid strategy analysis")
            return None
    
    async def should_exit(self, trade: Trade, market_data: MarketData) -> bool:
        """Grid strategy exit conditions"""
        try:
            # Check if we should take profit (opposite direction from entry)
            if trade.direction == TradeDirection.LONG:
                # Look for sell levels above entry
                exit_price = trade.entry_price * (1 + self.grid_spacing)
                if market_data.price >= exit_price:
                    return True
            else:
                # Look for buy levels below entry
                exit_price = trade.entry_price * (1 - self.grid_spacing)
                if market_data.price <= exit_price:
                    return True
            
            # Check stop loss
            if trade.stop_loss and market_data.price:
                if trade.direction == TradeDirection.LONG and market_data.price <= trade.stop_loss:
                    return True
                elif trade.direction == TradeDirection.SHORT and market_data.price >= trade.stop_loss:
                    return True
            
            return False
            
        except Exception as e:
            logger.error_occurred(e, "Grid strategy exit check")
            return False
    
    def reset_grid(self, pair: str = None):
        """Reset grid positions for a pair or all pairs"""
        try:
            if pair:
                if pair in self.grid_positions:
                    del self.grid_positions[pair]
                    logger.info(f"Grid reset for pair: {pair}")
            else:
                self.grid_positions.clear()
                logger.info("All grids reset")
                
        except Exception as e:
            logger.error_occurred(e, "resetting grid")
    
    def update_base_price(self, new_base_price: float, pair: str):
        """Update base price for grid calculation"""
        try:
            self.base_price = new_base_price
            
            # Reset grid for this pair
            if pair in self.grid_positions:
                del self.grid_positions[pair]
            
            logger.info(f"Base price updated to {new_base_price} for pair {pair}")
            
        except Exception as e:
            logger.error_occurred(e, "updating base price")
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get grid strategy specific information"""
        info = self.get_performance_metrics()
        info.update({
            'grid_levels': self.grid_levels,
            'grid_spacing': self.grid_spacing,
            'grid_range': self.grid_range,
            'base_price': self.base_price,
            'active_grids': {
                pair: {
                    'total_levels': len(data['levels']),
                    'filled_levels': len(data['filled_levels']),
                    'last_update': data['last_update'].isoformat()
                }
                for pair, data in self.grid_positions.items()
            }
        })
        return info
