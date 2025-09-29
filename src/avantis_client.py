"""
Avantis SDK client wrapper for the trading bot
"""

import asyncio
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from avantis_trader_sdk.client import TraderClient
from avantis_trader_sdk.feed.feed_client import FeedClient
from avantis_trader_sdk.types import TradeInput, TradeInputOrderType, MarginUpdateType
try:
    from .models import Trade, TradeDirection, OrderType, TradeStatus, MarketData
    from .logger import logger
    from .config import config
except ImportError:
    from models import Trade, TradeDirection, OrderType, TradeStatus, MarketData
    from logger import logger
    from config import config


class AvantisClient:
    """Wrapper around Avantis SDK for easier integration"""
    
    def __init__(self):
        self.client: Optional[TraderClient] = None
        self.feed_client: Optional[FeedClient] = None
        self.trader_address: Optional[str] = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the Avantis client"""
        try:
            logger.info("Initializing Avantis client...")
            
            # Initialize TraderClient
            self.client = TraderClient(config.wallet.provider_url)
            
            # Set local signer
            self.client.set_local_signer(config.wallet.private_key)
            
            # Get trader address
            self.trader_address = self.client.get_signer().get_ethereum_address()
            logger.info(f"Trader address: {self.trader_address}")
            
            self._initialized = True
            logger.info("Avantis client initialized successfully")
            return True
            
        except Exception as e:
            logger.error_occurred(e, "Avantis client initialization")
            return False
    
    async def check_usdc_allowance(self, required_amount: float) -> float:
        """Check USDC allowance for trading"""
        try:
            allowance = await self.client.get_usdc_allowance_for_trading(self.trader_address)
            logger.debug(f"USDC allowance: {allowance}")
            return allowance
        except Exception as e:
            logger.error_occurred(e, "checking USDC allowance")
            return 0.0
    
    async def approve_usdc(self, amount: float) -> bool:
        """Approve USDC for trading"""
        try:
            logger.info(f"Approving {amount} USDC for trading...")
            await self.client.approve_usdc_for_trading(amount)
            
            # Verify approval
            new_allowance = await self.check_usdc_allowance(amount)
            if new_allowance >= amount:
                logger.info(f"USDC approval successful. New allowance: {new_allowance}")
                return True
            else:
                logger.error(f"USDC approval failed. Allowance: {new_allowance}")
                return False
                
        except Exception as e:
            logger.error_occurred(e, "USDC approval")
            return False
    
    async def get_pair_index(self, pair: str) -> Optional[int]:
        """Get pair index for a trading pair"""
        try:
            # Convert pair format (e.g., "ETH/USD" -> "ETH/USD")
            pair_index = await self.client.pairs_cache.get_pair_index(pair)
            logger.debug(f"Pair {pair} has index: {pair_index}")
            return pair_index
        except Exception as e:
            logger.error_occurred(e, f"getting pair index for {pair}")
            return None
    
    async def get_current_price(self, pair: str) -> Optional[float]:
        """Get current price for a pair"""
        try:
            # This would need to be implemented based on available SDK methods
            # For now, we'll return None and handle pricing externally
            logger.debug(f"Getting current price for {pair}")
            return None
        except Exception as e:
            logger.error_occurred(e, f"getting current price for {pair}")
            return None
    
    async def get_opening_fee(self, trade_input: TradeInput) -> Optional[float]:
        """Get opening fee for a trade"""
        try:
            # Use the correct method name from the examples
            opening_fee = await self.client.fee_parameters.get_new_trade_opening_fee(trade_input)
            logger.debug(f"Opening fee: {opening_fee} USDC")
            return opening_fee
        except Exception as e:
            logger.error_occurred(e, "getting opening fee")
            return None
    
    async def get_loss_protection(self, trade_input: TradeInput, opening_fee: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Get loss protection information for a trade"""
        try:
            loss_protection_info = await self.client.trading_parameters.get_loss_protection_for_trade_input(
                trade_input, opening_fee_usdc=opening_fee
            )
            protection_data = {
                'percentage': loss_protection_info.percentage,
                'amount': loss_protection_info.amount
            }
            logger.debug(f"Loss protection: {protection_data}")
            return protection_data
        except Exception as e:
            logger.error_occurred(e, "getting loss protection")
            return None
    
    async def open_trade(self, trade: Trade) -> bool:
        """Open a trade on Avantis"""
        try:
            if not self._initialized:
                logger.error("Client not initialized")
                return False
            
            # Get pair index
            pair_index = await self.get_pair_index(trade.pair)
            if pair_index is None:
                logger.error(f"Could not get pair index for {trade.pair}")
                return False
            
            # Check and approve USDC if needed
            allowance = await self.check_usdc_allowance(trade.size)
            if allowance < trade.size:
                if not await self.approve_usdc(trade.size):
                    return False
            
            # Create trade input
            trade_input = TradeInput(
                trader=self.trader_address,
                open_price=trade.entry_price,
                pair_index=pair_index,
                collateral_in_trade=trade.size,
                is_long=(trade.direction == TradeDirection.LONG),
                leverage=trade.leverage,
                index=trade.trade_index or 0,
                tp=trade.take_profit,
                sl=trade.stop_loss or 0,
                timestamp=0
            )
            
            # Get opening fee and loss protection
            opening_fee = await self.client.fee_parameters.get_new_trade_opening_fee(trade_input)
            loss_protection = await self.client.trading_parameters.get_loss_protection_for_trade_input(
                trade_input, opening_fee_usdc=opening_fee
            )
            
            # Update trade with fee and protection info
            trade.opening_fee = opening_fee
            trade.loss_protection = loss_protection
            trade.pair_index = pair_index
            
            # Determine order type
            order_type_map = {
                OrderType.MARKET: TradeInputOrderType.MARKET,
                OrderType.LIMIT: TradeInputOrderType.LIMIT,
                OrderType.STOP_LIMIT: TradeInputOrderType.STOP_LIMIT,
                OrderType.MARKET_ZERO_FEE: TradeInputOrderType.MARKET_ZERO_FEE
            }
            
            trade_input_order_type = order_type_map.get(
                OrderType(trade.order_type or "market"),
                TradeInputOrderType.MARKET
            )
            
            # Build and send transaction
            slippage_percentage = config.trading.slippage_tolerance
            open_transaction = await self.client.trade.build_trade_open_tx(
                trade_input, trade_input_order_type, slippage_percentage
            )
            
            receipt = await self.client.sign_and_get_receipt(open_transaction)
            
            # Update trade status
            trade.status = TradeStatus.OPEN
            trade.fees_paid = opening_fee
            
            logger.trade_opened({
                'pair': trade.pair,
                'direction': trade.direction.value,
                'size': trade.size,
                'leverage': trade.leverage,
                'tx_hash': receipt.get('transactionHash', 'unknown')
            })
            
            return True
            
        except Exception as e:
            logger.error_occurred(e, f"opening trade {trade.pair}")
            return False
    
    async def close_trade(self, trade: Trade, collateral_to_close: Optional[float] = None) -> bool:
        """Close a trade on Avantis (fully or partially)"""
        try:
            if not self._initialized or not trade.pair_index or trade.trade_index is None:
                logger.error("Cannot close trade - missing required data")
                return False
            
            # Use full collateral if not specified (full close)
            if collateral_to_close is None:
                collateral_to_close = trade.collateral_in_trade or trade.size
            
            # Build close transaction
            close_transaction = await self.client.trade.build_trade_close_tx(
                pair_index=trade.pair_index,
                trade_index=trade.trade_index,
                collateral_to_close=collateral_to_close,
                trader=self.trader_address
            )
            
            receipt = await self.client.sign_and_get_receipt(close_transaction)
            
            # Update trade status
            if collateral_to_close >= (trade.collateral_in_trade or trade.size):
                trade.status = TradeStatus.CLOSED
                trade.closed_at = datetime.now()
            else:
                # Partial close - update collateral
                trade.collateral_in_trade = (trade.collateral_in_trade or trade.size) - collateral_to_close
                trade.size = trade.collateral_in_trade
            
            logger.trade_closed({
                'pair': trade.pair,
                'pnl': trade.pnl or 0,
                'collateral_closed': collateral_to_close,
                'tx_hash': receipt.get('transactionHash', 'unknown')
            })
            
            return True
            
        except Exception as e:
            logger.error_occurred(e, f"closing trade {trade.pair}")
            return False
    
    async def get_open_trades(self) -> List[Trade]:
        """Get all open trades for the trader"""
        try:
            if not self._initialized:
                return []
            
            trades_data, pending_orders = await self.client.trade.get_trades(self.trader_address)
            
            trades = []
            for trade_data in trades_data:
                trade = Trade(
                    pair=f"PAIR_{trade_data.trade.pair_index}",  # Convert pair index to pair name
                    direction=TradeDirection.LONG if trade_data.trade.is_long else TradeDirection.SHORT,
                    entry_price=trade_data.trade.open_price,
                    size=trade_data.trade.collateral,
                    leverage=trade_data.trade.leverage,
                    stop_loss=trade_data.trade.sl if trade_data.trade.sl > 0 else None,
                    take_profit=trade_data.trade.tp if trade_data.trade.tp > 0 else None,
                    status=TradeStatus.OPEN,
                    pair_index=trade_data.trade.pair_index,
                    trade_index=trade_data.trade.index,
                    collateral_in_trade=trade_data.trade.collateral
                )
                trades.append(trade)
            
            logger.debug(f"Retrieved {len(trades)} open trades")
            return trades
            
        except Exception as e:
            logger.error_occurred(e, "getting open trades")
            return []
    
    async def update_trade_tp_sl(self, trade: Trade, take_profit: Optional[float] = None, stop_loss: Optional[float] = None) -> bool:
        """Update take profit and stop loss for a trade"""
        try:
            if not self._initialized or not trade.pair_index or trade.trade_index is None:
                logger.error("Cannot update TP/SL - missing required data")
                return False
            
            # Build update transaction
            update_transaction = await self.client.trade.build_trade_tp_sl_update_tx(
                pair_index=trade.pair_index,
                trade_index=trade.trade_index,
                take_profit_price=take_profit or trade.take_profit,
                stop_loss_price=stop_loss or trade.stop_loss or 0,
                trader=self.trader_address
            )
            
            receipt = await self.client.sign_and_get_receipt(update_transaction)
            
            # Update trade object
            if take_profit is not None:
                trade.take_profit = take_profit
            if stop_loss is not None:
                trade.stop_loss = stop_loss
            
            logger.info(f"Updated TP/SL for trade {trade.pair}: TP={trade.take_profit}, SL={trade.stop_loss}")
            return True
            
        except Exception as e:
            logger.error_occurred(e, f"updating TP/SL for trade {trade.pair}")
            return False
    
    async def update_trade_margin(self, trade: Trade, margin_change: float, margin_update_type: str = "DEPOSIT") -> bool:
        """Update trade margin (add/remove collateral)"""
        try:
            if not self._initialized or not trade.pair_index or trade.trade_index is None:
                logger.error("Cannot update margin - missing required data")
                return False
            
            # Import MarginUpdateType
            from avantis_trader_sdk.types import MarginUpdateType
            update_type = MarginUpdateType.DEPOSIT if margin_update_type.upper() == "DEPOSIT" else MarginUpdateType.WITHDRAW
            
            # Check USDC allowance if depositing
            if update_type == MarginUpdateType.DEPOSIT:
                allowance = await self.check_usdc_allowance(margin_change)
                if allowance < margin_change:
                    if not await self.approve_usdc(margin_change):
                        return False
            
            # Build margin update transaction
            margin_transaction = await self.client.trade.build_trade_margin_update_tx(
                trader=self.trader_address,
                pair_index=trade.pair_index,
                trade_index=trade.trade_index,
                margin_update_type=update_type,
                collateral_change=margin_change
            )
            
            receipt = await self.client.sign_and_get_receipt(margin_transaction)
            
            # Update trade collateral
            if update_type == MarginUpdateType.DEPOSIT:
                trade.collateral_in_trade = (trade.collateral_in_trade or 0) + margin_change
            else:
                trade.collateral_in_trade = max(0, (trade.collateral_in_trade or 0) - margin_change)
            
            trade.size = trade.collateral_in_trade
            
            logger.info(f"Updated margin for trade {trade.pair}: {margin_change} USDC ({margin_update_type})")
            return True
            
        except Exception as e:
            logger.error_occurred(e, f"updating margin for trade {trade.pair}")
            return False
    
    async def place_limit_order(self, trade: Trade, limit_price: float) -> bool:
        """Place a limit order"""
        try:
            if not self._initialized:
                logger.error("Client not initialized")
                return False
            
            # Get pair index
            pair_index = await self.get_pair_index(trade.pair)
            if pair_index is None:
                logger.error(f"Could not get pair index for {trade.pair}")
                return False
            
            # Check and approve USDC if needed
            allowance = await self.check_usdc_allowance(trade.size)
            if allowance < trade.size:
                if not await self.approve_usdc(trade.size):
                    return False
            
            # Create trade input for limit order
            trade_input = TradeInput(
                trader=self.trader_address,
                open_price=limit_price,
                pair_index=pair_index,
                collateral_in_trade=trade.size,
                is_long=(trade.direction == TradeDirection.LONG),
                leverage=trade.leverage,
                index=trade.trade_index or 0,
                tp=trade.take_profit,
                sl=trade.stop_loss or 0,
                timestamp=0
            )
            
            # Build limit order transaction
            order_type = TradeInputOrderType.LIMIT
            slippage_percentage = config.trading.slippage_tolerance
            
            limit_transaction = await self.client.trade.build_trade_open_tx(
                trade_input, order_type, slippage_percentage
            )
            
            receipt = await self.client.sign_and_get_receipt(limit_transaction)
            
            # Update trade status
            trade.status = TradeStatus.PENDING
            trade.entry_price = limit_price
            trade.pair_index = pair_index
            
            logger.info(f"Limit order placed for {trade.pair} at {limit_price}")
            return True
            
        except Exception as e:
            logger.error_occurred(e, f"placing limit order for {trade.pair}")
            return False
    
    async def cancel_limit_order(self, trade: Trade) -> bool:
        """Cancel a pending limit order"""
        try:
            if not self._initialized or not trade.pair_index or trade.trade_index is None:
                logger.error("Cannot cancel order - missing required data")
                return False
            
            # Build cancel transaction
            cancel_transaction = await self.client.trade.build_order_cancel_tx(
                pair_index=trade.pair_index,
                trade_index=trade.trade_index,
                trader=self.trader_address
            )
            
            receipt = await self.client.sign_and_get_receipt(cancel_transaction)
            
            # Update trade status
            trade.status = TradeStatus.CANCELLED
            
            logger.info(f"Limit order cancelled for {trade.pair}")
            return True
            
        except Exception as e:
            logger.error_occurred(e, f"cancelling limit order for {trade.pair}")
            return False
    
    async def get_market_data(self, pair: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive market data for a pair"""
        try:
            if not self._initialized:
                return None
            
            # Get pair index
            pair_index = await self.get_pair_index(pair)
            if pair_index is None:
                return None
            
            # Get various market parameters
            snapshot = await self.client.snapshot.get_snapshot()
            
            # Get asset parameters
            oi_limits = await self.client.asset_parameters.get_oi_limits()
            oi = await self.client.asset_parameters.get_oi()
            utilization = await self.client.asset_parameters.get_utilization()
            skew = await self.client.asset_parameters.get_asset_skew()
            
            # Get fee parameters
            margin_fee = await self.client.fee_parameters.get_margin_fee()
            pair_spread = await self.client.fee_parameters.get_pair_spread()
            
            market_data = {
                'pair': pair,
                'pair_index': pair_index,
                'snapshot': snapshot,
                'open_interest_limits': oi_limits.limits.get(pair, 0),
                'open_interest_long': oi.long.get(pair, 0),
                'open_interest_short': oi.short.get(pair, 0),
                'utilization': utilization.utilization.get(pair, 0),
                'skew': skew.skew.get(pair, 50),
                'margin_fee_long': margin_fee.margin_long.get(pair, 0),
                'margin_fee_short': margin_fee.margin_short.get(pair, 0),
                'spread': pair_spread.spread.get(pair, 0)
            }
            
            return market_data
            
        except Exception as e:
            logger.error_occurred(e, f"getting market data for {pair}")
            return None
    
    async def calculate_price_impact(self, pair: str, position_size: float, is_long: bool) -> Optional[Dict[str, float]]:
        """Calculate price impact for a trade"""
        try:
            if not self._initialized:
                return None
            
            # Get price impact spreads
            price_impact = await self.client.asset_parameters.get_price_impact_spread(
                position_size=position_size,
                is_long=is_long,
                pair=pair
            )
            
            skew_impact = await self.client.asset_parameters.get_skew_impact_spread(
                position_size=position_size,
                is_long=is_long,
                pair=pair
            )
            
            # Get opening price impact
            opening_impact = await self.client.asset_parameters.get_opening_price_impact_spread(
                pair=pair,
                position_size=position_size,
                open_price=0,  # Current price
                is_long=is_long
            )
            
            impact_data = {
                'price_impact': price_impact.long.get(pair, 0) if is_long else price_impact.short.get(pair, 0),
                'skew_impact': skew_impact.long.get(pair, 0) if is_long else skew_impact.short.get(pair, 0),
                'opening_impact': opening_impact.long.get(pair, 0) if is_long else opening_impact.short.get(pair, 0),
                'total_impact': 0  # Will be calculated
            }
            
            # Calculate total impact
            impact_data['total_impact'] = (
                impact_data['price_impact'] + 
                impact_data['skew_impact'] + 
                impact_data['opening_impact']
            )
            
            return impact_data
            
        except Exception as e:
            logger.error_occurred(e, f"calculating price impact for {pair}")
            return None
    
    async def get_trading_parameters(self, pair: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive trading parameters for a pair"""
        try:
            if not self._initialized:
                return None
            
            pair_index = await self.get_pair_index(pair)
            if pair_index is None:
                return None
            
            # Create a sample trade input for calculations
            from avantis_trader_sdk.types import TradeInput
            
            sample_trade = TradeInput(
                trader=self.trader_address,
                pair_index=pair_index,
                collateral_in_trade=100,  # Sample size
                is_long=True,
                leverage=10
            )
            
            # Get loss protection info
            loss_protection_info = await self.get_loss_protection(sample_trade)
            
            # Get opening fee
            opening_fee = await self.get_opening_fee(sample_trade)
            
            # Get referral rebate
            referral_rebate = await self.client.trading_parameters.get_trade_referral_rebate_percentage(self.trader_address)
            
            trading_params = {
                'pair': pair,
                'pair_index': pair_index,
                'loss_protection': loss_protection_info,
                'opening_fee': opening_fee,
                'referral_rebate_percentage': referral_rebate,
                'loss_protection_tier': await self.client.trading_parameters.get_loss_protection_tier(sample_trade)
            }
            
            return trading_params
            
        except Exception as e:
            logger.error_occurred(e, f"getting trading parameters for {pair}")
            return None
