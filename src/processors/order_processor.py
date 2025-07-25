"""
Order Processing Engine
Validates, processes, and enriches incoming orders
"""

import asyncio
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from loguru import logger

from core.config import AppConfig
from core.exceptions import OrderValidationError, OrderProcessingError, InstrumentError
from models.order import OrderRequest, ProcessedOrder, OrderSide, OrderType, TimeInForce, OrderStatus, OptionType
from models.spxw_instruments import SPXWInstrument, SPXWInstrumentFactory
from processors.risk_processor import RiskProcessor
from utils.validation import OrderValidator


class OrderProcessor:
    """Main order processing engine"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.risk_processor = RiskProcessor(config)
        self.validator = OrderValidator()
        
        # Setup logger
        self.logger = logger.bind(category="ORDER")
        
        # Processing statistics
        self.stats = {
            "total_processed": 0,
            "total_failed": 0,
            "validation_failures": 0,
            "risk_failures": 0,
            "instrument_failures": 0
        }
    
    async def process_order(self, order_request: OrderRequest) -> ProcessedOrder:
        """
        Main order processing pipeline
        1. Validate order format and business rules
        2. Enrich with instrument data
        3. Apply risk checks
        4. Create processed order
        """
        try:
            start_time = datetime.utcnow()
            self.logger.info(f"Processing order: {order_request.order_id}")
            
            # Step 1: Validate order
            await self._validate_order(order_request)
            
            # Step 2: Enrich with instrument data
            instrument = await self._resolve_instrument(order_request)
            
            # Step 3: Create processed order
            processed_order = await self._create_processed_order(order_request, instrument)
            
            # Step 4: Apply risk checks
            await self.risk_processor.check_order(processed_order)
            
            # Step 5: Final enrichment
            await self._enrich_order(processed_order)
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            self.stats["total_processed"] += 1
            
            self.logger.info(
                f"Order {order_request.order_id} processed successfully in {processing_time:.3f}s"
            )
            
            return processed_order
            
        except Exception as e:
            self.stats["total_failed"] += 1
            self.logger.error(f"Failed to process order {order_request.order_id}: {e}")
            raise OrderProcessingError(f"Order processing failed: {e}")
    
    async def _validate_order(self, order_request: OrderRequest):
        """Validate order request"""
        try:
            # Basic validation
            self.validator.validate_order_request(order_request)
            
            # Business rule validation
            await self._validate_business_rules(order_request)
            
        except Exception as e:
            self.stats["validation_failures"] += 1
            raise OrderValidationError(f"Order validation failed: {e}")
    
    async def _validate_business_rules(self, order_request: OrderRequest):
        """Validate business rules"""
        # Check required fields for options
        if order_request.symbol == "SPXW":
            if not order_request.strike_price:
                raise OrderValidationError("Strike price required for SPXW options")
            
            if not order_request.expiry_date:
                raise OrderValidationError("Expiry date required for SPXW options")
            
            if not order_request.option_type:
                raise OrderValidationError("Option type (CALL/PUT) required for SPXW options")
            
            # Validate expiry date format and value
            try:
                expiry = datetime.strptime(order_request.expiry_date, "%Y-%m-%d").date()
                if expiry <= date.today():
                    raise OrderValidationError("Expiry date must be in the future")
            except ValueError:
                raise OrderValidationError("Invalid expiry date format. Use YYYY-MM-DD")
        
        # Validate price and quantity
        if order_request.price is not None and order_request.price <= 0:
            raise OrderValidationError("Price must be positive")
        
        if order_request.quantity <= 0:
            raise OrderValidationError("Quantity must be positive")
        
        # Validate order type and price relationship
        if order_request.order_type in ["LIMIT", "STOP_LIMIT"] and order_request.price is None:
            raise OrderValidationError(f"Price required for {order_request.order_type} orders")
        
        if order_request.order_type in ["STOP", "STOP_LIMIT"] and order_request.stop_price is None:
            raise OrderValidationError(f"Stop price required for {order_request.order_type} orders")
    
    async def _resolve_instrument(self, order_request: OrderRequest) -> Optional[SPXWInstrument]:
        """Resolve and validate instrument"""
        try:
            if order_request.symbol == "SPXW":
                # Create SPXW instrument
                expiry_date = datetime.strptime(order_request.expiry_date, "%Y-%m-%d").date()
                strike_price = Decimal(str(order_request.strike_price))
                
                instrument = SPXWInstrumentFactory.create_option(
                    strike_price=strike_price,
                    expiry_date=expiry_date,
                    option_type=order_request.option_type
                )
                
                # Validate instrument is tradable
                if instrument.is_expired():
                    raise InstrumentError("Option has expired")
                
                if not instrument.is_tradable:
                    raise InstrumentError("Instrument is not tradable")
                
                return instrument
            else:
                # For non-SPXW symbols, return None (would be extended for other instruments)
                return None
                
        except Exception as e:
            self.stats["instrument_failures"] += 1
            raise InstrumentError(f"Failed to resolve instrument: {e}")
    
    async def _create_processed_order(
        self, 
        order_request: OrderRequest, 
        instrument: Optional[SPXWInstrument]
    ) -> ProcessedOrder:
        """Create processed order from request and instrument data"""
        
        # Map enums
        side = OrderSide(order_request.side.upper())
        order_type = OrderType(order_request.order_type.upper())
        time_in_force = TimeInForce(order_request.time_in_force.upper())
        
        # Create base processed order
        processed_order = ProcessedOrder(
            order_id=order_request.order_id,
            client_order_id=order_request.client_order_id or order_request.order_id,
            symbol=order_request.symbol,
            side=side,
            quantity=order_request.quantity,
            order_type=order_type,
            time_in_force=time_in_force,
            account=order_request.account or self.config.trading.default_currency,
            price=Decimal(str(order_request.price)) if order_request.price else None,
            stop_price=Decimal(str(order_request.stop_price)) if order_request.stop_price else None,
            text=order_request.text,
            source=order_request.source,
            original_request=order_request
        )
        
        # Add instrument-specific data
        if instrument:
            processed_order.strike_price = instrument.strike_price
            processed_order.expiry_date = instrument.expiry_date
            processed_order.option_type = OptionType(instrument.option_type)
            processed_order.security_id = instrument.security_id
            processed_order.security_id_source = instrument.security_id_source
            processed_order.security_type = instrument.security_type
            processed_order.security_exchange = instrument.exchange
            processed_order.currency = instrument.currency
        else:
            # Default values for non-instrument orders
            processed_order.security_exchange = self.config.trading.default_exchange
            processed_order.currency = self.config.trading.default_currency
        
        # Handle optional fields
        if order_request.min_quantity:
            processed_order.min_quantity = order_request.min_quantity
        
        if order_request.max_show:
            processed_order.max_show = order_request.max_show
        
        if order_request.expire_time:
            try:
                processed_order.expire_time = datetime.fromisoformat(order_request.expire_time)
            except ValueError:
                self.logger.warning(f"Invalid expire_time format: {order_request.expire_time}")
        
        return processed_order
    
    async def _enrich_order(self, order: ProcessedOrder):
        """Final order enrichment"""
        # Set clearing account if not specified
        if not order.clearing_account:
            order.clearing_account = order.account
        
        # Set order capacity for regulatory reporting
        if not order.order_capacity:
            order.order_capacity = "A"  # Agency
        
        # Add any additional enrichment logic here
        pass
    
    def get_stats(self) -> dict:
        """Get processing statistics"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset processing statistics"""
        self.stats = {
            "total_processed": 0,
            "total_failed": 0,
            "validation_failures": 0,
            "risk_failures": 0,
            "instrument_failures": 0
        }
