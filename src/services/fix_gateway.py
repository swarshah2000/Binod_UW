"""
FIX Gateway Service
Handles FIX session management and message processing for TT integration
"""

import asyncio
import quickfix as fix
from datetime import datetime
from typing import Dict, Optional, Callable
from loguru import logger

from core.config import AppConfig
from core.exceptions import FixConnectionError, OrderProcessingError
from models.order import ProcessedOrder
from models.fix_messages import NewOrderSingle, FixValues
from processors.fix_processor import FixMessageProcessor


class FixGatewayService(fix.Application):
    """FIX gateway service for TT integration"""
    
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.session_id = None
        self.initiator = None
        self.message_processor = FixMessageProcessor(config)
        self.running = False
        self.connected = False
        
        # Order tracking
        self.pending_orders: Dict[str, ProcessedOrder] = {}
        self.order_callbacks: Dict[str, Callable] = {}
        
        # Statistics
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "orders_sent": 0,
            "execution_reports": 0,
            "connection_time": None,
            "last_heartbeat": None
        }
        
        # Setup logger
        self.logger = logger.bind(category="FIX")
    
    async def initialize(self):
        """Initialize FIX gateway"""
        try:
            self.logger.info("Initializing FIX Gateway Service")
            
            # Load FIX configuration
            settings = fix.SessionSettings(str(self.config.get_fix_config_path()))
            store_factory = fix.FileStoreFactory(settings)
            log_factory = fix.ScreenLogFactory(settings)
            
            # Create initiator
            self.initiator = fix.SocketInitiator(self, store_factory, settings, log_factory)
            
            self.logger.info("FIX Gateway initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize FIX gateway: {e}")
            raise FixConnectionError(f"Failed to initialize FIX gateway: {e}")
    
    async def start(self):
        """Start FIX gateway"""
        try:
            self.logger.info("Starting FIX Gateway Service")
            
            if not self.initiator:
                raise FixConnectionError("FIX gateway not initialized")
            
            # Start the initiator
            self.initiator.start()
            self.running = True
            
            # Wait for connection
            await self._wait_for_connection()
            
            self.logger.info("FIX Gateway Service started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start FIX gateway: {e}")
            raise FixConnectionError(f"Failed to start FIX gateway: {e}")
    
    async def stop(self):
        """Stop FIX gateway"""
        self.logger.info("Stopping FIX Gateway Service")
        self.running = False
        
        if self.initiator:
            self.initiator.stop()
        
        self.connected = False
        self.logger.info("FIX Gateway Service stopped")
    
    async def _wait_for_connection(self, timeout: int = 30):
        """Wait for FIX connection to be established"""
        start_time = asyncio.get_event_loop().time()
        
        while not self.connected and (asyncio.get_event_loop().time() - start_time) < timeout:
            await asyncio.sleep(0.1)
        
        if not self.connected:
            raise FixConnectionError("FIX connection timeout")
    
    async def send_order(self, order: ProcessedOrder):
        """Send order to TT FIX gateway"""
        try:
            if not self.connected:
                raise FixConnectionError("FIX session not connected")
            
            self.logger.info(f"Sending order to FIX: {order.order_id}")
            
            # Create FIX message
            fix_message = self._create_new_order_single(order)
            
            # Store pending order
            self.pending_orders[order.client_order_id] = order
            
            # Send message
            if self.session_id:
                fix.Session.sendToTarget(fix_message, self.session_id)
                self.stats["messages_sent"] += 1
                self.stats["orders_sent"] += 1
                
                self.logger.info(f"Order {order.order_id} sent successfully")
            else:
                raise FixConnectionError("No active FIX session")
                
        except Exception as e:
            self.logger.error(f"Failed to send order {order.order_id}: {e}")
            raise OrderProcessingError(f"Failed to send order: {e}")
    
    def _create_new_order_single(self, order: ProcessedOrder) -> fix.Message:
        """Create FIX NewOrderSingle message"""
        # Create base message
        message = fix.Message()
        header = message.getHeader()
        header.setField(fix.MsgType(FixValues.NEW_ORDER_SINGLE))
        
        # Required fields
        message.setField(fix.ClOrdID(order.client_order_id))
        message.setField(fix.Symbol(order.symbol))
        message.setField(fix.Side(self._map_side_to_fix(order.side.value)))
        message.setField(fix.TransactTime(datetime.utcnow()))
        message.setField(fix.OrdType(self._map_order_type_to_fix(order.order_type.value)))
        
        # Quantity
        if order.quantity:
            message.setField(fix.OrderQty(order.quantity))
        
        # Price (for limit orders)
        if order.price and order.order_type.value in ["LIMIT", "STOP_LIMIT"]:
            message.setField(fix.Price(float(order.price)))
        
        # Stop price (for stop orders)
        if order.stop_price and order.order_type.value in ["STOP", "STOP_LIMIT"]:
            message.setField(fix.StopPx(float(order.stop_price)))
        
        # Time in force
        if order.time_in_force:
            message.setField(fix.TimeInForce(self._map_tif_to_fix(order.time_in_force.value)))
        
        # Account
        if order.account:
            message.setField(fix.Account(order.account))
        
        # Options-specific fields
        if order.security_type == "OPT":
            message.setField(fix.SecurityType(FixValues.OPTION))
            
            if order.strike_price:
                message.setField(fix.StrikePrice(float(order.strike_price)))
            
            if order.option_type:
                put_or_call = 1 if order.option_type.value == "CALL" else 0
                message.setField(fix.PutOrCall(put_or_call))
            
            if order.expiry_date:
                message.setField(fix.MaturityDate(order.expiry_date.strftime("%Y%m%d")))
        
        # Exchange and currency
        if order.security_exchange:
            message.setField(fix.SecurityExchange(order.security_exchange))
        
        if order.currency:
            message.setField(fix.Currency(order.currency))
        
        # Additional fields
        if order.text:
            message.setField(fix.Text(order.text))
        
        if order.min_quantity:
            message.setField(fix.MinQty(order.min_quantity))
        
        if order.max_show:
            message.setField(fix.MaxShow(order.max_show))
        
        return message
    
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
    
    # FIX Application callbacks
    def onCreate(self, sessionID):
        """Called when session is created"""
        self.session_id = sessionID
        self.logger.info(f"FIX session created: {sessionID}")
    
    def onLogon(self, sessionID):
        """Called when logon is successful"""
        self.connected = True
        self.stats["connection_time"] = datetime.utcnow()
        self.logger.info(f"FIX session logged on: {sessionID}")
    
    def onLogout(self, sessionID):
        """Called when logout occurs"""
        self.connected = False
        self.logger.info(f"FIX session logged out: {sessionID}")
    
    def toAdmin(self, message, sessionID):
        """Called for outgoing admin messages"""
        self.logger.debug(f"Sending admin message: {message}")
    
    def fromAdmin(self, message, sessionID):
        """Called for incoming admin messages"""
        msg_type = message.getHeader().getField(fix.MsgType())
        
        if msg_type == FixValues.HEARTBEAT:
            self.stats["last_heartbeat"] = datetime.utcnow()
        
        self.logger.debug(f"Received admin message: {msg_type}")
    
    def toApp(self, message, sessionID):
        """Called for outgoing application messages"""
        self.logger.debug(f"Sending app message: {message}")
    
    def fromApp(self, message, sessionID):
        """Called for incoming application messages"""
        try:
            self.stats["messages_received"] += 1
            
            # Process the message
            asyncio.create_task(self._process_app_message(message))
            
        except Exception as e:
            self.logger.error(f"Error processing app message: {e}")
    
    async def _process_app_message(self, message: fix.Message):
        """Process incoming application message"""
        try:
            msg_type = message.getHeader().getField(fix.MsgType())
            
            if msg_type == FixValues.EXECUTION_REPORT:
                await self._process_execution_report(message)
            elif msg_type == FixValues.ORDER_CANCEL_REJECT:
                await self._process_cancel_reject(message)
            else:
                self.logger.debug(f"Received unhandled message type: {msg_type}")
                
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
    
    async def _process_execution_report(self, message: fix.Message):
        """Process execution report"""
        try:
            self.stats["execution_reports"] += 1
            
            # Extract fields
            cl_ord_id = message.getField(fix.ClOrdID())
            exec_type = message.getField(fix.ExecType())
            ord_status = message.getField(fix.OrdStatus())
            
            self.logger.info(f"Execution report: {cl_ord_id} - {exec_type} - {ord_status}")
            
            # Update pending order if exists
            if cl_ord_id in self.pending_orders:
                order = self.pending_orders[cl_ord_id]
                # Update order status based on execution report
                # Implementation would depend on specific requirements
                
        except Exception as e:
            self.logger.error(f"Error processing execution report: {e}")
    
    async def _process_cancel_reject(self, message: fix.Message):
        """Process order cancel reject"""
        try:
            cl_ord_id = message.getField(fix.ClOrdID())
            reason = message.getField(fix.CxlRejReason())
            
            self.logger.warning(f"Cancel reject for {cl_ord_id}: {reason}")
            
        except Exception as e:
            self.logger.error(f"Error processing cancel reject: {e}")
    
    def get_stats(self) -> dict:
        """Get service statistics"""
        return {
            **self.stats,
            "connected": self.connected,
            "pending_orders": len(self.pending_orders)
        }
    
    def is_connected(self) -> bool:
        """Check if FIX session is connected"""
        return self.connected
