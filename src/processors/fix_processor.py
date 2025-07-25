"""
FIX Message Processor
Handles FIX message creation, parsing, and processing
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
from loguru import logger

from core.config import AppConfig
from core.exceptions import MessageParsingError, FixConnectionError
from models.order import ProcessedOrder, ExecutionReport, OrderStatus
from models.fix_messages import (
    NewOrderSingle, FixFields, FixValues, 
    ExecutionReport as FixExecutionReport,
    OrderCancelReject as FixOrderCancelReject
)


class FixMessageProcessor:
    """FIX message processing engine"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        
        # Setup logger
        self.logger = logger.bind(category="FIX")
        
        # Message statistics
        self.stats = {
            "messages_created": 0,
            "messages_parsed": 0,
            "parse_errors": 0,
            "execution_reports": 0,
            "cancel_rejects": 0
        }
    
    def create_new_order_single(self, order: ProcessedOrder) -> NewOrderSingle:
        """Create FIX NewOrderSingle message from processed order"""
        try:
            self.logger.debug(f"Creating NewOrderSingle for order {order.order_id}")
            
            # Create the message
            nos = NewOrderSingle(
                cl_ord_id=order.client_order_id,
                symbol=order.symbol,
                side=self._map_side_to_fix(order.side.value),
                transact_time=datetime.utcnow(),
                ord_type=self._map_order_type_to_fix(order.order_type.value)
            )
            
            # Set quantity
            nos.order_qty = order.quantity
            
            # Set price for limit orders
            if order.price and order.order_type.value in ["LIMIT", "STOP_LIMIT"]:
                nos.price = order.price
            
            # Set stop price for stop orders
            if order.stop_price and order.order_type.value in ["STOP", "STOP_LIMIT"]:
                nos.stop_px = order.stop_price
            
            # Set time in force
            if order.time_in_force:
                nos.time_in_force = self._map_tif_to_fix(order.time_in_force.value)
            
            # Set account
            if order.account:
                nos.account = order.account
            
            # Set clearing account
            if order.clearing_account:
                nos.clearing_account = order.clearing_account
            
            # Options-specific fields
            if order.security_type == "OPT":
                nos.security_type = "OPT"
                
                if order.strike_price:
                    nos.strike_price = order.strike_price
                
                if order.option_type:
                    nos.put_or_call = 1 if order.option_type.value == "CALL" else 0
                
                if order.expiry_date:
                    nos.maturity_date = order.expiry_date.strftime("%Y%m%d")
            
            # Exchange and currency
            if order.security_exchange:
                nos.security_exchange = order.security_exchange
            
            if order.currency:
                nos.currency = order.currency
            
            # Security identification
            if order.security_id:
                nos.security_id = order.security_id
            
            if order.security_id_source:
                nos.security_id_source = order.security_id_source
            
            # Additional fields
            if order.text:
                nos.text = order.text
            
            if order.min_quantity:
                nos.min_qty = order.min_quantity
            
            if order.max_show:
                nos.max_show = order.max_show
            
            if order.expire_time:
                nos.expire_time = order.expire_time
            
            # Order management fields
            if order.order_capacity:
                nos.order_capacity = order.order_capacity
            
            if order.order_restrictions:
                nos.order_restrictions = order.order_restrictions
            
            self.stats["messages_created"] += 1
            self.logger.debug(f"NewOrderSingle created successfully for order {order.order_id}")
            
            return nos
            
        except Exception as e:
            self.logger.error(f"Failed to create NewOrderSingle for order {order.order_id}: {e}")
            raise MessageParsingError(f"Failed to create NewOrderSingle: {e}")
    
    def parse_execution_report(self, fix_fields: Dict[int, Any]) -> ExecutionReport:
        """Parse FIX execution report into internal format"""
        try:
            self.stats["messages_parsed"] += 1
            self.stats["execution_reports"] += 1
            
            # Extract required fields
            order_id = fix_fields.get(FixFields.ORDER_ID, "")
            exec_id = fix_fields.get(FixFields.EXEC_ID, "")
            exec_type = fix_fields.get(FixFields.EXEC_TYPE, "")
            order_status = fix_fields.get(FixFields.ORD_STATUS, "")
            side = fix_fields.get(FixFields.SIDE, "")
            symbol = fix_fields.get(FixFields.SYMBOL, "")
            
            # Extract quantities
            order_qty = int(fix_fields.get(FixFields.ORDER_QTY, 0))
            cum_qty = int(fix_fields.get(FixFields.CUM_QTY, 0))
            leaves_qty = int(fix_fields.get(FixFields.LEAVES_QTY, 0))
            last_qty = int(fix_fields.get(FixFields.LAST_SHARES, 0)) if FixFields.LAST_SHARES in fix_fields else None
            
            # Extract prices
            avg_px = Decimal(str(fix_fields[FixFields.AVG_PX])) if FixFields.AVG_PX in fix_fields else None
            last_px = Decimal(str(fix_fields[FixFields.LAST_PX])) if FixFields.LAST_PX in fix_fields else None
            
            # Extract timing
            transact_time = None
            if FixFields.TRANSACT_TIME in fix_fields:
                time_str = fix_fields[FixFields.TRANSACT_TIME]
                try:
                    transact_time = datetime.strptime(time_str, "%Y%m%d-%H:%M:%S.%f")
                except ValueError:
                    try:
                        transact_time = datetime.strptime(time_str, "%Y%m%d-%H:%M:%S")
                    except ValueError:
                        self.logger.warning(f"Could not parse transact time: {time_str}")
            
            # Create execution report
            exec_report = ExecutionReport(
                order_id=order_id,
                exec_id=exec_id,
                exec_type=exec_type,
                order_status=order_status,
                side=side,
                symbol=symbol,
                order_qty=order_qty,
                cum_qty=cum_qty,
                leaves_qty=leaves_qty,
                last_qty=last_qty,
                avg_px=avg_px,
                last_px=last_px,
                transact_time=transact_time,
                orig_client_order_id=fix_fields.get(FixFields.ORIG_CL_ORD_ID),
                exec_ref_id=fix_fields.get(FixFields.EXEC_REF_ID),
                text=fix_fields.get(FixFields.TEXT),
                account=fix_fields.get(FixFields.ACCOUNT)
            )
            
            self.logger.info(
                f"Parsed execution report: {exec_id} - {exec_type} - {order_status} "
                f"for order {order_id}"
            )
            
            return exec_report
            
        except Exception as e:
            self.stats["parse_errors"] += 1
            self.logger.error(f"Failed to parse execution report: {e}")
            raise MessageParsingError(f"Failed to parse execution report: {e}")
    
    def parse_cancel_reject(self, fix_fields: Dict[int, Any]) -> Dict[str, Any]:
        """Parse order cancel reject message"""
        try:
            self.stats["messages_parsed"] += 1
            self.stats["cancel_rejects"] += 1
            
            cancel_reject = {
                "order_id": fix_fields.get(FixFields.ORDER_ID, ""),
                "cl_ord_id": fix_fields.get(FixFields.CL_ORD_ID, ""),
                "orig_cl_ord_id": fix_fields.get(FixFields.ORIG_CL_ORD_ID, ""),
                "ord_status": fix_fields.get(FixFields.ORD_STATUS, ""),
                "cxl_rej_reason": fix_fields.get(FixFields.CXL_REJ_REASON, ""),
                "cxl_rej_response_to": fix_fields.get(FixFields.CXL_REJ_RESPONSE_TO, ""),
                "text": fix_fields.get(FixFields.TEXT, ""),
                "account": fix_fields.get(FixFields.ACCOUNT, "")
            }
            
            self.logger.warning(
                f"Order cancel rejected: {cancel_reject['cl_ord_id']} - "
                f"Reason: {cancel_reject['cxl_rej_reason']}"
            )
            
            return cancel_reject
            
        except Exception as e:
            self.stats["parse_errors"] += 1
            self.logger.error(f"Failed to parse cancel reject: {e}")
            raise MessageParsingError(f"Failed to parse cancel reject: {e}")
    
    def _map_side_to_fix(self, side: str) -> str:
        """Map order side to FIX value"""
        mapping = {
            "BUY": FixValues.BUY,
            "SELL": FixValues.SELL
        }
        return mapping.get(side, FixValues.BUY)
    
    def _map_order_type_to_fix(self, order_type: str) -> str:
        """Map order type to FIX value"""
        mapping = {
            "MARKET": FixValues.MARKET,
            "LIMIT": FixValues.LIMIT,
            "STOP": FixValues.STOP,
            "STOP_LIMIT": FixValues.STOP_LIMIT
        }
        return mapping.get(order_type, FixValues.LIMIT)
    
    def _map_tif_to_fix(self, tif: str) -> str:
        """Map time in force to FIX value"""
        mapping = {
            "DAY": FixValues.DAY,
            "GTC": FixValues.GTC,
            "IOC": FixValues.IOC,
            "FOK": FixValues.FOK,
            "GTD": FixValues.GTD
        }
        return mapping.get(tif, FixValues.DAY)
    
    def _map_fix_to_order_status(self, fix_status: str) -> OrderStatus:
        """Map FIX order status to internal order status"""
        mapping = {
            FixValues.NEW: OrderStatus.NEW,
            FixValues.PARTIALLY_FILLED: OrderStatus.PARTIALLY_FILLED,
            FixValues.FILLED: OrderStatus.FILLED,
            FixValues.CANCELED: OrderStatus.CANCELED,
            FixValues.REJECTED: OrderStatus.REJECTED,
            FixValues.EXPIRED: OrderStatus.EXPIRED,
            FixValues.PENDING_NEW: OrderStatus.PENDING_NEW,
            FixValues.PENDING_CANCEL: OrderStatus.PENDING_CANCEL
        }
        return mapping.get(fix_status, OrderStatus.NEW)
    
    def get_stats(self) -> dict:
        """Get message processing statistics"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset message processing statistics"""
        self.stats = {
            "messages_created": 0,
            "messages_parsed": 0,
            "parse_errors": 0,
            "execution_reports": 0,
            "cancel_rejects": 0
        }
