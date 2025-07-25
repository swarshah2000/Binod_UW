"""
Order validation utilities
"""

import re
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from core.exceptions import OrderValidationError
from models.order import OrderRequest


class OrderValidator:
    """Order validation utility class"""
    
    def __init__(self):
        # Validation patterns
        self.order_id_pattern = re.compile(r'^[A-Za-z0-9_-]{1,50}$')
        self.symbol_pattern = re.compile(r'^[A-Z]{1,12}$')
        self.account_pattern = re.compile(r'^[A-Za-z0-9_-]{1,20}$')
        
        # Valid values
        self.valid_sides = {"BUY", "SELL"}
        self.valid_order_types = {"MARKET", "LIMIT", "STOP", "STOP_LIMIT"}
        self.valid_time_in_force = {"DAY", "GTC", "IOC", "FOK", "GTD"}
        self.valid_option_types = {"CALL", "PUT"}
        
        # Limits
        self.max_quantity = 1_000_000
        self.max_price = Decimal("999999.99")
        self.min_price = Decimal("0.01")
    
    def validate_order_request(self, order: OrderRequest):
        """Validate an order request"""
        # Required field validation
        self._validate_required_fields(order)
        
        # Format validation
        self._validate_formats(order)
        
        # Business logic validation
        self._validate_business_logic(order)
        
        # Range validation
        self._validate_ranges(order)
    
    def _validate_required_fields(self, order: OrderRequest):
        """Validate required fields are present"""
        if not order.order_id:
            raise OrderValidationError("order_id is required")
        
        if not order.symbol:
            raise OrderValidationError("symbol is required")
        
        if not order.side:
            raise OrderValidationError("side is required")
        
        if not order.quantity or order.quantity <= 0:
            raise OrderValidationError("quantity is required and must be positive")
        
        if not order.order_type:
            raise OrderValidationError("order_type is required")
        
        if not order.time_in_force:
            raise OrderValidationError("time_in_force is required")
    
    def _validate_formats(self, order: OrderRequest):
        """Validate field formats"""
        # Order ID format
        if not self.order_id_pattern.match(order.order_id):
            raise OrderValidationError(
                "order_id must be alphanumeric with underscores/hyphens, max 50 chars"
            )
        
        # Symbol format
        if not self.symbol_pattern.match(order.symbol):
            raise OrderValidationError(
                "symbol must be uppercase letters only, max 12 chars"
            )
        
        # Account format (if provided)
        if order.account and not self.account_pattern.match(order.account):
            raise OrderValidationError(
                "account must be alphanumeric with underscores/hyphens, max 20 chars"
            )
        
        # Client order ID format (if provided)
        if order.client_order_id and not self.order_id_pattern.match(order.client_order_id):
            raise OrderValidationError(
                "client_order_id must be alphanumeric with underscores/hyphens, max 50 chars"
            )
    
    def _validate_business_logic(self, order: OrderRequest):
        """Validate business logic"""
        # Side validation
        if order.side.upper() not in self.valid_sides:
            raise OrderValidationError(
                f"side must be one of {self.valid_sides}"
            )
        
        # Order type validation
        if order.order_type.upper() not in self.valid_order_types:
            raise OrderValidationError(
                f"order_type must be one of {self.valid_order_types}"
            )
        
        # Time in force validation
        if order.time_in_force.upper() not in self.valid_time_in_force:
            raise OrderValidationError(
                f"time_in_force must be one of {self.valid_time_in_force}"
            )
        
        # Option type validation (if provided)
        if order.option_type and order.option_type.upper() not in self.valid_option_types:
            raise OrderValidationError(
                f"option_type must be one of {self.valid_option_types}"
            )
        
        # Price requirements for order types
        if order.order_type.upper() in ["LIMIT", "STOP_LIMIT"]:
            if order.price is None or order.price <= 0:
                raise OrderValidationError(
                    f"price is required and must be positive for {order.order_type} orders"
                )
        
        if order.order_type.upper() in ["STOP", "STOP_LIMIT"]:
            if order.stop_price is None or order.stop_price <= 0:
                raise OrderValidationError(
                    f"stop_price is required and must be positive for {order.order_type} orders"
                )
        
        # Expiry date validation
        if order.expiry_date:
            try:
                expiry = datetime.strptime(order.expiry_date, "%Y-%m-%d").date()
                if expiry <= date.today():
                    raise OrderValidationError("expiry_date must be in the future")
            except ValueError:
                raise OrderValidationError("expiry_date must be in YYYY-MM-DD format")
        
        # Expire time validation
        if order.expire_time:
            try:
                expire_time = datetime.fromisoformat(order.expire_time)
                if expire_time <= datetime.utcnow():
                    raise OrderValidationError("expire_time must be in the future")
            except ValueError:
                raise OrderValidationError("expire_time must be in ISO format")
    
    def _validate_ranges(self, order: OrderRequest):
        """Validate field ranges"""
        # Quantity range
        if order.quantity > self.max_quantity:
            raise OrderValidationError(
                f"quantity {order.quantity} exceeds maximum {self.max_quantity}"
            )
        
        # Price range
        if order.price is not None:
            price_decimal = Decimal(str(order.price))
            if price_decimal < self.min_price or price_decimal > self.max_price:
                raise OrderValidationError(
                    f"price {order.price} must be between {self.min_price} and {self.max_price}"
                )
        
        # Stop price range
        if order.stop_price is not None:
            stop_decimal = Decimal(str(order.stop_price))
            if stop_decimal < self.min_price or stop_decimal > self.max_price:
                raise OrderValidationError(
                    f"stop_price {order.stop_price} must be between {self.min_price} and {self.max_price}"
                )
        
        # Strike price range (for options)
        if order.strike_price is not None:
            strike_decimal = Decimal(str(order.strike_price))
            if strike_decimal <= 0 or strike_decimal > self.max_price:
                raise OrderValidationError(
                    f"strike_price {order.strike_price} must be positive and <= {self.max_price}"
                )
        
        # Min quantity validation
        if order.min_quantity is not None:
            if order.min_quantity <= 0 or order.min_quantity > order.quantity:
                raise OrderValidationError(
                    "min_quantity must be positive and <= order quantity"
                )
        
        # Max show validation
        if order.max_show is not None:
            if order.max_show <= 0 or order.max_show > order.quantity:
                raise OrderValidationError(
                    "max_show must be positive and <= order quantity"
                )


def validate_symbol(symbol: str) -> bool:
    """Validate symbol format"""
    if not symbol:
        return False
    
    pattern = re.compile(r'^[A-Z]{1,12}$')
    return bool(pattern.match(symbol))


def validate_price(price: Optional[float]) -> bool:
    """Validate price value"""
    if price is None:
        return True
    
    if price <= 0:
        return False
    
    # Check decimal places (max 4)
    price_str = str(price)
    if '.' in price_str:
        decimal_places = len(price_str.split('.')[1])
        if decimal_places > 4:
            return False
    
    return True


def validate_quantity(quantity: int) -> bool:
    """Validate quantity value"""
    return quantity > 0 and quantity <= 1_000_000


def validate_account(account: Optional[str]) -> bool:
    """Validate account format"""
    if not account:
        return True
    
    pattern = re.compile(r'^[A-Za-z0-9_-]{1,20}$')
    return bool(pattern.match(account))


def validate_expiry_date(expiry_date: Optional[str]) -> bool:
    """Validate expiry date format and value"""
    if not expiry_date:
        return True
    
    try:
        expiry = datetime.strptime(expiry_date, "%Y-%m-%d").date()
        return expiry > date.today()
    except ValueError:
        return False


def sanitize_text_field(text: Optional[str], max_length: int = 100) -> Optional[str]:
    """Sanitize text field"""
    if not text:
        return None
    
    # Remove control characters and limit length
    sanitized = ''.join(char for char in text if ord(char) >= 32)
    return sanitized[:max_length] if len(sanitized) > max_length else sanitized


def normalize_symbol(symbol: str) -> str:
    """Normalize symbol to uppercase"""
    return symbol.upper().strip() if symbol else ""


def normalize_side(side: str) -> str:
    """Normalize side to uppercase"""
    return side.upper().strip() if side else ""


def normalize_order_type(order_type: str) -> str:
    """Normalize order type to uppercase"""
    return order_type.upper().strip() if order_type else ""


def format_price(price: Optional[float], decimal_places: int = 2) -> Optional[str]:
    """Format price for display"""
    if price is None:
        return None
    
    return f"{price:.{decimal_places}f}"


def parse_decimal_price(price_str: str) -> Decimal:
    """Parse price string to Decimal"""
    try:
        return Decimal(price_str)
    except (ValueError, TypeError):
        raise OrderValidationError(f"Invalid price format: {price_str}")


class ValidationResult:
    """Validation result container"""
    
    def __init__(self):
        self.is_valid = True
        self.errors = []
        self.warnings = []
    
    def add_error(self, error: str):
        """Add validation error"""
        self.is_valid = False
        self.errors.append(error)
    
    def add_warning(self, warning: str):
        """Add validation warning"""
        self.warnings.append(warning)
    
    def has_errors(self) -> bool:
        """Check if there are validation errors"""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if there are validation warnings"""
        return len(self.warnings) > 0
    
    def get_summary(self) -> str:
        """Get validation summary"""
        if self.is_valid:
            summary = "Valid"
            if self.has_warnings():
                summary += f" (with {len(self.warnings)} warnings)"
        else:
            summary = f"Invalid ({len(self.errors)} errors"
            if self.has_warnings():
                summary += f", {len(self.warnings)} warnings"
            summary += ")"
        
        return summary
