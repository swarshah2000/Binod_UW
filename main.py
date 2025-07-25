#!/usr/bin/env python3
"""
TT FIX 4.4 Order Adapter Server
Main application entry point
"""

import asyncio
import signal
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config import AppConfig
from core.logger import setup_logging
from services.order_listener import OrderListenerService
from services.fix_gateway import FixGatewayService
from services.monitoring import MonitoringService
from loguru import logger


class OrderAdapterServer:
    """Main order adapter server application"""
    
    def __init__(self):
        self.config = None
        self.order_listener = None
        self.fix_gateway = None
        self.monitoring = None
        self.shutdown_event = asyncio.Event()
        
    async def initialize(self):
        """Initialize all services"""
        try:
            # Load configuration
            self.config = AppConfig()
            
            # Setup logging
            setup_logging(self.config.logging)
            logger.info("Starting TT FIX Order Adapter Server")
            
            # Initialize services
            self.monitoring = MonitoringService(self.config)
            self.fix_gateway = FixGatewayService(self.config)
            self.order_listener = OrderListenerService(self.config, self.fix_gateway)
            
            # Initialize FIX gateway
            await self.fix_gateway.initialize()
            
            # Initialize monitoring
            await self.monitoring.initialize()
            
            logger.info("All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize server: {e}")
            raise
    
    async def start(self):
        """Start all services"""
        try:
            logger.info("Starting all services...")
            
            # Start services
            await asyncio.gather(
                self.fix_gateway.start(),
                self.order_listener.start(),
                self.monitoring.start()
            )
            
            logger.info("All services started successfully")
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"Error starting services: {e}")
            raise
    
    async def shutdown(self):
        """Gracefully shutdown all services"""
        logger.info("Shutting down Order Adapter Server...")
        
        try:
            # Stop services in reverse order
            if self.order_listener:
                await self.order_listener.stop()
            
            if self.fix_gateway:
                await self.fix_gateway.stop()
            
            if self.monitoring:
                await self.monitoring.stop()
            
            logger.info("Server shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown_event.set()


async def main():
    """Main application function"""
    server = OrderAdapterServer()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, server.signal_handler)
    signal.signal(signal.SIGTERM, server.signal_handler)
    
    try:
        await server.initialize()
        await server.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    finally:
        await server.shutdown()
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
