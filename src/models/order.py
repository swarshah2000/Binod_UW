"""
Order data models for TT FIX Order Adapter
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json


class OrderSide(Enum):
    """Order side enumeration"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class TimeInForce(Enum):
    """Time in force enumeration"""
    DAY = "DAY"
    GTC = "GTC"  # Good Till Cancel
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill
    GTD = "GTD"  # Good Till Date


class OrderStatus(Enum):
    """Order status enumeration"""
    NEW = "NEW"
    PENDING_NEW = "PENDING_NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    PENDING_CANCEL = "PENDING_CANCEL"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OptionType(Enum):
    """Option type enumeration"""
    CALL = "CALL"
    PUT = "PUT"


@dataclass_json
@dataclass
class OrderRequest:
    """Incoming order request from ZMQ"""
    order_id: str
    symbol: str
    side: str
    quantity: int
    price: Optional[float] = None
    order_type: str = "LIMIT"
    time_in_force: str = "DAY"
    account: Optional[str] = None
    
    # Options-specific fields
    strike_price: Optional[float] = None
    expiry_date: Optional[str] = None  # YYYY-MM-DD format
    option_type: Optional[str] = None  # CALL or PUT
    
    # Additional fields
    client_order_id: Optional[str] = None
    stop_price: Optional[float] = None
    expire_time: Optional[str] = None
    min_quantity: Optional[int] = None
    max_show: Optional[int] = None
    text: Optional[str] = None
    
    # Metadata
    timestamp: Optional[str] = None
    source: Optional[str] = None
    extra_fields: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and normalize fields after initialization"""
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()
        
        if self.client_order_id is None:
            self.client_order_id = self.order_id


@dataclass_json
@dataclass
class ProcessedOrder:
    """Internal order representation after processing"""
    order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType
    time_in_force: TimeInForce
    account: str
    
    # Pricing
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    
    # Options fields
    strike_price: Optional[Decimal] = None
    expiry_date: Optional[date] = None
    option_type: Optional[OptionType] = None
    
    # Security identification
    security_id: Optional[str] = None
    security_id_source: Optional[str] = None
    security_type: str = "OPT"
    security_exchange: str = "CBOE"
    currency: str = "USD"
    
    # Order management
    status: OrderStatus = OrderStatus.NEW
    created_time: datetime = field(default_factory=datetime.utcnow)
    updated_time: datetime = field(default_factory=datetime.utcnow)
    
    # Additional fields
    expire_time: Optional[datetime] = None
    min_quantity: Optional[int] = None
    max_show: Optional[int] = None
    text: Optional[str] = None
    
    # Execution tracking
    filled_quantity: int = 0
    remaining_quantity: int = field(init=False)
    avg_price: Optional[Decimal] = None
    last_price: Optional[Decimal] = None
    last_quantity: Optional[int] = None
    
    # Risk and routing
    order_capacity: Optional[str] = None
    order_restrictions: Optional[str] = None
    clearing_account: Optional[str] = None
    
    # Metadata
    source: Optional[str] = None
    original_request: Optional[OrderRequest] = None
    fix_messages: list = field(default_factory=list)
    
    def __post_init__(self):
        """Calculate derived fields"""
        self.remaining_quantity = self.quantity - self.filled_quantity
    
    def update_status(self, status: OrderStatus):
        """Update order status and timestamp"""
        self.status = status
        self.updated_time = datetime.utcnow()
    
    def add_fill(self, fill_quantity: int, fill_price: Decimal):
        """Add a fill to the order"""
        self.filled_quantity += fill_quantity
        self.remaining_quantity = self.quantity - self.filled_quantity
        self.last_quantity = fill_quantity
        self.last_price = fill_price
        
        # Update average price
        if self.avg_price is None:
            self.avg_price = fill_price
        else:
            total_value = (self.avg_price * (self.filled_quantity - fill_quantity)) + (fill_price * fill_quantity)
            self.avg_price = total_value / self.filled_quantity
        
        # Update status
        if self.remaining_quantity == 0:
            self.update_status(OrderStatus.FILLED)
        else:
            self.update_status(OrderStatus.PARTIALLY_FILLED)
    
    def is_complete(self) -> bool:
        """Check if order is in a terminal state"""
        return self.status in [
            OrderStatus.FILLED,
            OrderStatus.CANCELED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED
        ]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for logging/monitoring"""
        return {
            "order_id": self.order_id,
            "client_order_id": self.client_order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "order_type": self.order_type.value,
            "status": self.status.value,
            "filled_quantity": self.filled_quantity,
            "remaining_quantity": self.remaining_quantity,
            "price": float(self.price) if self.price else None,
            "avg_price": float(self.avg_price) if self.avg_price else None,
            "account": self.account,
            "created_time": self.created_time.isoformat(),
            "updated_time": self.updated_time.isoformat()
        }


@dataclass_json
@dataclass
class ExecutionReport:
    """Execution report from TT FIX"""
    order_id: str
    exec_id: str
    exec_type: str
    order_status: str
    side: str
    symbol: str
    
    # Quantities
    order_qty: int
    cum_qty: int
    leaves_qty: int
    last_qty: Optional[int] = None
    
    # Prices
    price: Optional[Decimal] = None
    last_px: Optional[Decimal] = None
    avg_px: Optional[Decimal] = None
    
    # Timing
    transact_time: Optional[datetime] = None
    
    # Additional fields
    text: Optional[str] = None
    exec_ref_id: Optional[str] = None
    
    def __post_init__(self):
        """Set default timestamp"""
        if self.transact_time is None:
            self.transact_time = datetime.utcnow()


@dataclass_json
@dataclass
class OrderCancelRequest:
    """Order cancel request"""
    order_id: str
    client_order_id: str
    orig_client_order_id: str
    symbol: str
    side: str
    quantity: int
    
    # Optional fields
    account: Optional[str] = None
    text: Optional[str] = None
    
    # Metadata
    cancel_request_id: str = field(default_factory=lambda: f"CXL_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass_json
@dataclass
class OrderReplaceRequest:
    """Order replace request"""
    order_id: str
    client_order_id: str
    orig_client_order_id: str
    symbol: str
    side: str
    
    # New order parameters
    quantity: int
    price: Optional[Decimal] = None
    order_type: str = "LIMIT"
    time_in_force: str = "DAY"
    
    # Optional fields
    account: Optional[str] = None
    text: Optional[str] = None
    
    # Metadata
    replace_request_id: str = field(default_factory=lambda: f"REP_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
    timestamp: datetime = field(default_factory=datetime.utcnow)
