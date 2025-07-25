"""
Risk Management Processor
Handles pre-trade risk checks and position limits
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from loguru import logger

from core.config import AppConfig
from core.exceptions import RiskManagementError
from models.order import ProcessedOrder


class RiskProcessor:
    """Risk management processor"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.risk_limits = config.trading.risk_limits
        
        # Risk tracking
        self.daily_volumes: Dict[str, int] = {}  # symbol -> volume
        self.daily_orders: Dict[str, int] = {}   # symbol -> count
        self.positions: Dict[str, int] = {}      # symbol -> position
        self.order_history: List[Dict] = []      # recent orders for rate limiting
        
        # Risk statistics
        self.stats = {
            "total_checks": 0,
            "risk_violations": 0,
            "orders_blocked": 0,
            "last_reset": datetime.utcnow()
        }
        
        # Setup logger
        self.logger = logger.bind(category="RISK")
        
        # Reset daily counters at midnight
        self._last_reset_date = datetime.utcnow().date()
    
    async def check_order(self, order: ProcessedOrder):
        """Perform comprehensive risk checks on order"""
        try:
            self.stats["total_checks"] += 1
            self.logger.debug(f"Performing risk checks for order {order.order_id}")
            
            # Check if risk management is enabled
            if not self.risk_limits.enabled:
                self.logger.debug("Risk management disabled, skipping checks")
                return
            
            # Reset daily counters if needed
            await self._check_daily_reset()
            
            # Perform individual risk checks
            await self._check_order_size(order)
            await self._check_daily_volume(order)
            await self._check_position_limits(order)
            await self._check_order_rate(order)
            await self._check_instrument_specific_risks(order)
            
            # Record the order for tracking
            await self._record_order(order)
            
            self.logger.debug(f"Risk checks passed for order {order.order_id}")
            
        except RiskManagementError:
            self.stats["risk_violations"] += 1
            self.stats["orders_blocked"] += 1
            raise
        except Exception as e:
            self.logger.error(f"Error in risk checks for order {order.order_id}: {e}")
            raise RiskManagementError(f"Risk check error: {e}")
    
    async def _check_order_size(self, order: ProcessedOrder):
        """Check order size against limits"""
        if order.quantity > self.risk_limits.max_order_size:
            raise RiskManagementError(
                f"Order size {order.quantity} exceeds maximum allowed {self.risk_limits.max_order_size}"
            )
    
    async def _check_daily_volume(self, order: ProcessedOrder):
        """Check daily volume limits"""
        symbol = order.symbol
        current_volume = self.daily_volumes.get(symbol, 0)
        new_total = current_volume + order.quantity
        
        if new_total > self.risk_limits.max_daily_volume:
            raise RiskManagementError(
                f"Daily volume limit exceeded for {symbol}: {new_total} > {self.risk_limits.max_daily_volume}"
            )
    
    async def _check_position_limits(self, order: ProcessedOrder):
        """Check position limits"""
        symbol = order.symbol
        current_position = self.positions.get(symbol, 0)
        
        # Calculate new position after order
        quantity_delta = order.quantity if order.side.value == "BUY" else -order.quantity
        new_position = current_position + quantity_delta
        
        if abs(new_position) > self.risk_limits.max_position_size:
            raise RiskManagementError(
                f"Position limit exceeded for {symbol}: {abs(new_position)} > {self.risk_limits.max_position_size}"
            )
    
    async def _check_order_rate(self, order: ProcessedOrder):
        """Check order rate limits"""
        now = datetime.utcnow()
        one_second_ago = now - timedelta(seconds=1)
        
        # Count orders in the last second
        recent_orders = [
            o for o in self.order_history 
            if o["timestamp"] > one_second_ago
        ]
        
        if len(recent_orders) >= self.risk_limits.max_orders_per_second:
            raise RiskManagementError(
                f"Order rate limit exceeded: {len(recent_orders)} orders in last second "
                f"(max: {self.risk_limits.max_orders_per_second})"
            )
    
    async def _check_instrument_specific_risks(self, order: ProcessedOrder):
        """Check instrument-specific risk rules"""
        if order.symbol == "SPXW":
            await self._check_spxw_risks(order)
    
    async def _check_spxw_risks(self, order: ProcessedOrder):
        """Check SPXW-specific risk rules"""
        # Check option expiry
        if order.expiry_date and order.expiry_date <= datetime.utcnow().date():
            raise RiskManagementError("Cannot trade expired options")
        
        # Check days to expiry (e.g., no trading within 1 day of expiry)
        if order.expiry_date:
            days_to_expiry = (order.expiry_date - datetime.utcnow().date()).days
            if days_to_expiry < 1:
                raise RiskManagementError("Cannot trade options expiring within 1 day")
        
        # Check strike price reasonableness (basic sanity check)
        if order.strike_price and order.strike_price <= 0:
            raise RiskManagementError("Invalid strike price")
        
        # Check minimum price for options
        if order.price and order.price < Decimal("0.05"):
            self.logger.warning(f"Very low option price: {order.price}")
    
    async def _record_order(self, order: ProcessedOrder):
        """Record order for tracking"""
        # Update daily volumes
        symbol = order.symbol
        self.daily_volumes[symbol] = self.daily_volumes.get(symbol, 0) + order.quantity
        self.daily_orders[symbol] = self.daily_orders.get(symbol, 0) + 1
        
        # Add to order history for rate limiting
        order_record = {
            "order_id": order.order_id,
            "symbol": order.symbol,
            "quantity": order.quantity,
            "timestamp": datetime.utcnow()
        }
        self.order_history.append(order_record)
        
        # Keep only recent orders (last 5 minutes for rate limiting)
        five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
        self.order_history = [
            o for o in self.order_history 
            if o["timestamp"] > five_minutes_ago
        ]
    
    async def _check_daily_reset(self):
        """Reset daily counters if needed"""
        current_date = datetime.utcnow().date()
        
        if current_date > self._last_reset_date:
            self.logger.info("Resetting daily risk counters")
            self.daily_volumes.clear()
            self.daily_orders.clear()
            self._last_reset_date = current_date
            self.stats["last_reset"] = datetime.utcnow()
    
    def update_position(self, symbol: str, quantity: int, side: str):
        """Update position tracking"""
        quantity_delta = quantity if side == "BUY" else -quantity
        self.positions[symbol] = self.positions.get(symbol, 0) + quantity_delta
        
        self.logger.debug(f"Position updated for {symbol}: {self.positions[symbol]}")
    
    def get_risk_status(self) -> Dict:
        """Get current risk status"""
        return {
            "enabled": self.risk_limits.enabled,
            "limits": {
                "max_order_size": self.risk_limits.max_order_size,
                "max_daily_volume": self.risk_limits.max_daily_volume,
                "max_orders_per_second": self.risk_limits.max_orders_per_second,
                "max_position_size": self.risk_limits.max_position_size
            },
            "current_state": {
                "daily_volumes": self.daily_volumes.copy(),
                "daily_orders": self.daily_orders.copy(),
                "positions": self.positions.copy(),
                "recent_order_count": len(self.order_history)
            },
            "statistics": self.stats.copy()
        }
    
    def get_position(self, symbol: str) -> int:
        """Get current position for symbol"""
        return self.positions.get(symbol, 0)
    
    def get_daily_volume(self, symbol: str) -> int:
        """Get daily volume for symbol"""
        return self.daily_volumes.get(symbol, 0)
    
    def reset_positions(self):
        """Reset all positions (for testing/end of day)"""
        self.logger.warning("Resetting all positions")
        self.positions.clear()
    
    def set_position(self, symbol: str, position: int):
        """Set position for symbol (for initialization)"""
        self.positions[symbol] = position
        self.logger.info(f"Position set for {symbol}: {position}")
    
    def get_stats(self) -> Dict:
        """Get risk management statistics"""
        return self.stats.copy()
