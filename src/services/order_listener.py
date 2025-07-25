"""
ZeroMQ Order Listener Service
Listens for incoming orders via ZMQ and forwards them to the FIX gateway
"""

import asyncio
import json
import zmq
import zmq.asyncio
from typing import Optional, Callable
from loguru import logger

from core.config import AppConfig
from core.exceptions import ZMQError, OrderProcessingError
from models.order import OrderRequest
from processors.order_processor import OrderProcessor


class OrderListenerService:
    """ZeroMQ order listener service"""
    
    def __init__(self, config: AppConfig, fix_gateway):
        self.config = config
        self.fix_gateway = fix_gateway
        self.context = None
        self.socket = None
        self.order_processor = OrderProcessor(config)
        self.running = False
        self.stats = {
            "orders_received": 0,
            "orders_processed": 0,
            "orders_failed": 0,
            "last_order_time": None
        }
        
        # Setup logger
        self.logger = logger.bind(category="ZMQ")
    
    async def start(self):
        """Start the ZMQ listener service"""
        try:
            self.logger.info("Starting ZMQ Order Listener Service")
            
            # Create ZMQ context and socket
            self.context = zmq.asyncio.Context()
            self.socket = self.context.socket(zmq.PULL)
            
            # Configure socket options
            self.socket.setsockopt(zmq.RCVHWM, self.config.zmq.high_water_mark)
            self.socket.setsockopt(zmq.RCVTIMEO, self.config.zmq.receive_timeout)
            
            # Bind to address
            self.socket.bind(self.config.zmq.bind_address)
            self.logger.info(f"ZMQ listener bound to {self.config.zmq.bind_address}")
            
            self.running = True
            
            # Start message processing loop
            await self._message_loop()
            
        except Exception as e:
            self.logger.error(f"Failed to start ZMQ listener: {e}")
            raise ZMQError(f"Failed to start ZMQ listener: {e}")
    
    async def stop(self):
        """Stop the ZMQ listener service"""
        self.logger.info("Stopping ZMQ Order Listener Service")
        self.running = False
        
        if self.socket:
            self.socket.close()
        
        if self.context:
            self.context.term()
        
        self.logger.info("ZMQ Order Listener Service stopped")
    
    async def _message_loop(self):
        """Main message processing loop"""
        self.logger.info("Starting message processing loop")
        
        while self.running:
            try:
                # Receive message with timeout
                try:
                    message = await asyncio.wait_for(
                        self.socket.recv_string(zmq.NOBLOCK),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                except zmq.Again:
                    continue
                
                # Process the received order
                await self._process_message(message)
                
            except Exception as e:
                self.logger.error(f"Error in message loop: {e}")
                await asyncio.sleep(0.1)  # Brief pause on error
    
    async def _process_message(self, message: str):
        """Process a received ZMQ message"""
        try:
            self.stats["orders_received"] += 1
            self.logger.debug(f"Received order message: {message}")
            
            # Parse JSON message
            try:
                order_data = json.loads(message)
            except json.JSONDecodeError as e:
                self.logger.error(f"Invalid JSON in order message: {e}")
                self.stats["orders_failed"] += 1
                return
            
            # Create order request object
            try:
                order_request = OrderRequest(**order_data)
            except Exception as e:
                self.logger.error(f"Invalid order request format: {e}")
                self.stats["orders_failed"] += 1
                return
            
            # Log order details
            self.logger.info(
                f"Processing order: {order_request.order_id} "
                f"{order_request.side} {order_request.quantity} "
                f"{order_request.symbol} @ {order_request.price}"
            )
            
            # Process the order
            processed_order = await self.order_processor.process_order(order_request)
            
            # Send to FIX gateway
            await self.fix_gateway.send_order(processed_order)
            
            self.stats["orders_processed"] += 1
            self.stats["last_order_time"] = asyncio.get_event_loop().time()
            
            self.logger.info(f"Order {order_request.order_id} sent to FIX gateway")
            
        except OrderProcessingError as e:
            self.logger.error(f"Order processing error: {e}")
            self.stats["orders_failed"] += 1
        except Exception as e:
            self.logger.error(f"Unexpected error processing order: {e}")
            self.stats["orders_failed"] += 1
    
    def get_stats(self) -> dict:
        """Get service statistics"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset service statistics"""
        self.stats = {
            "orders_received": 0,
            "orders_processed": 0,
            "orders_failed": 0,
            "last_order_time": None
        }
