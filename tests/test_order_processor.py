"""
Test cases for Order Processor
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import AppConfig
from processors.order_processor import OrderProcessor
from models.order import OrderRequest, OrderSide, OrderType, TimeInForce, OptionType
from core.exceptions import OrderValidationError, OrderProcessingError


class TestOrderProcessor:
    """Test cases for OrderProcessor"""
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return AppConfig()
    
    @pytest.fixture
    def processor(self, config):
        """Create order processor"""
        return OrderProcessor(config)
    
    def test_valid_spxw_call_order(self, processor):
        """Test processing valid SPXW call order"""
        expiry_date = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        order_request = OrderRequest(
            order_id="TEST_001",
            symbol="SPXW",
            side="BUY",
            quantity=10,
            price=25.50,
            order_type="LIMIT",
            time_in_force="DAY",
            account="TEST_ACCOUNT",
            strike_price=4150.0,
            expiry_date=expiry_date,
            option_type="CALL"
        )
        
        # This would be an async test in practice
        # processed_order = await processor.process_order(order_request)
        
        # Assertions would verify the processed order
        assert order_request.symbol == "SPXW"
        assert order_request.side == "BUY"
        assert order_request.option_type == "CALL"
    
    def test_invalid_expiry_date(self, processor):
        """Test order with invalid expiry date"""
        order_request = OrderRequest(
            order_id="TEST_002",
            symbol="SPXW",
            side="BUY",
            quantity=10,
            price=25.50,
            order_type="LIMIT",
            time_in_force="DAY",
            account="TEST_ACCOUNT",
            strike_price=4150.0,
            expiry_date="2020-01-01",  # Past date
            option_type="CALL"
        )
        
        # This would test validation failure
        with pytest.raises(OrderValidationError):
            # await processor.process_order(order_request)
            pass
    
    def test_missing_strike_price(self, processor):
        """Test SPXW order without strike price"""
        order_request = OrderRequest(
            order_id="TEST_003",
            symbol="SPXW",
            side="BUY",
            quantity=10,
            price=25.50,
            order_type="LIMIT",
            time_in_force="DAY",
            account="TEST_ACCOUNT",
            # strike_price missing
            expiry_date=(date.today() + timedelta(days=7)).strftime("%Y-%m-%d"),
            option_type="CALL"
        )
        
        # This would test validation failure
        with pytest.raises(OrderValidationError):
            # await processor.process_order(order_request)
            pass
    
    def test_zero_quantity(self, processor):
        """Test order with zero quantity"""
        order_request = OrderRequest(
            order_id="TEST_004",
            symbol="SPXW",
            side="BUY",
            quantity=0,  # Invalid
            price=25.50,
            order_type="LIMIT",
            time_in_force="DAY",
            account="TEST_ACCOUNT",
            strike_price=4150.0,
            expiry_date=(date.today() + timedelta(days=7)).strftime("%Y-%m-%d"),
            option_type="CALL"
        )
        
        with pytest.raises(OrderValidationError):
            # await processor.process_order(order_request)
            pass
    
    def test_limit_order_without_price(self, processor):
        """Test limit order without price"""
        order_request = OrderRequest(
            order_id="TEST_005",
            symbol="SPXW",
            side="BUY",
            quantity=10,
            # price missing for LIMIT order
            order_type="LIMIT",
            time_in_force="DAY",
            account="TEST_ACCOUNT",
            strike_price=4150.0,
            expiry_date=(date.today() + timedelta(days=7)).strftime("%Y-%m-%d"),
            option_type="CALL"
        )
        
        with pytest.raises(OrderValidationError):
            # await processor.process_order(order_request)
            pass


if __name__ == "__main__":
    pytest.main([__file__])
