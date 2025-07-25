"""
FIX message models for TT FIX 4.4 integration
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class FixMessage:
    """Base FIX message"""
    msg_type: str
    sender_comp_id: str
    target_comp_id: str
    msg_seq_num: int
    sending_time: datetime
    
    # Optional header fields
    sender_sub_id: Optional[str] = None
    target_sub_id: Optional[str] = None
    orig_sending_time: Optional[datetime] = None
    
    # Message body fields
    fields: Dict[int, Any] = field(default_factory=dict)
    
    def add_field(self, tag: int, value: Any):
        """Add a field to the message"""
        self.fields[tag] = value
    
    def get_field(self, tag: int) -> Optional[Any]:
        """Get a field value"""
        return self.fields.get(tag)


@dataclass_json
@dataclass
class NewOrderSingle:
    """New Order Single (35=D) message"""
    cl_ord_id: str  # 11
    symbol: str     # 55
    side: str       # 54 (1=Buy, 2=Sell)
    transact_time: datetime  # 60
    ord_type: str   # 40 (1=Market, 2=Limit)
    
    # Conditional fields
    order_qty: Optional[int] = None      # 38
    price: Optional[Decimal] = None      # 44
    stop_px: Optional[Decimal] = None    # 99
    time_in_force: Optional[str] = None  # 59 (0=Day, 1=GTC, 3=IOC, 4=FOK)
    
    # Options-specific fields
    security_type: Optional[str] = None     # 167
    maturity_date: Optional[str] = None     # 541
    strike_price: Optional[Decimal] = None  # 202
    put_or_call: Optional[int] = None       # 201 (0=Put, 1=Call)
    
    # Account and routing
    account: Optional[str] = None           # 1
    clearing_account: Optional[str] = None  # 440
    ex_destination: Optional[str] = None    # 100
    
    # Additional fields
    currency: Optional[str] = None          # 15
    security_exchange: Optional[str] = None # 207
    security_id: Optional[str] = None       # 48
    security_id_source: Optional[str] = None # 22
    text: Optional[str] = None              # 58
    
    # Order management
    expire_time: Optional[datetime] = None  # 126
    min_qty: Optional[int] = None          # 110
    max_show: Optional[int] = None         # 210
    
    # TT-specific fields
    order_capacity: Optional[str] = None    # 528
    order_restrictions: Optional[str] = None # 529
    
    def to_fix_fields(self) -> Dict[int, Any]:
        """Convert to FIX field dictionary"""
        fields = {
            11: self.cl_ord_id,
            55: self.symbol,
            54: self.side,
            60: self.transact_time.strftime("%Y%m%d-%H:%M:%S.%f")[:-3],
            40: self.ord_type
        }
        
        # Add conditional fields
        if self.order_qty is not None:
            fields[38] = self.order_qty
        if self.price is not None:
            fields[44] = str(self.price)
        if self.stop_px is not None:
            fields[99] = str(self.stop_px)
        if self.time_in_force is not None:
            fields[59] = self.time_in_force
        if self.security_type is not None:
            fields[167] = self.security_type
        if self.maturity_date is not None:
            fields[541] = self.maturity_date
        if self.strike_price is not None:
            fields[202] = str(self.strike_price)
        if self.put_or_call is not None:
            fields[201] = self.put_or_call
        if self.account is not None:
            fields[1] = self.account
        if self.clearing_account is not None:
            fields[440] = self.clearing_account
        if self.ex_destination is not None:
            fields[100] = self.ex_destination
        if self.currency is not None:
            fields[15] = self.currency
        if self.security_exchange is not None:
            fields[207] = self.security_exchange
        if self.security_id is not None:
            fields[48] = self.security_id
        if self.security_id_source is not None:
            fields[22] = self.security_id_source
        if self.text is not None:
            fields[58] = self.text
        if self.expire_time is not None:
            fields[126] = self.expire_time.strftime("%Y%m%d-%H:%M:%S.%f")[:-3]
        if self.min_qty is not None:
            fields[110] = self.min_qty
        if self.max_show is not None:
            fields[210] = self.max_show
        if self.order_capacity is not None:
            fields[528] = self.order_capacity
        if self.order_restrictions is not None:
            fields[529] = self.order_restrictions
        
        return fields


@dataclass_json
@dataclass
class OrderCancelRequest:
    """Order Cancel Request (35=F) message"""
    orig_cl_ord_id: str    # 41
    cl_ord_id: str         # 11
    symbol: str            # 55
    side: str              # 54
    transact_time: datetime # 60
    
    # Optional fields
    order_id: Optional[str] = None    # 37
    order_qty: Optional[int] = None   # 38
    account: Optional[str] = None     # 1
    text: Optional[str] = None        # 58
    
    def to_fix_fields(self) -> Dict[int, Any]:
        """Convert to FIX field dictionary"""
        fields = {
            41: self.orig_cl_ord_id,
            11: self.cl_ord_id,
            55: self.symbol,
            54: self.side,
            60: self.transact_time.strftime("%Y%m%d-%H:%M:%S.%f")[:-3]
        }
        
        if self.order_id is not None:
            fields[37] = self.order_id
        if self.order_qty is not None:
            fields[38] = self.order_qty
        if self.account is not None:
            fields[1] = self.account
        if self.text is not None:
            fields[58] = self.text
        
        return fields


@dataclass_json
@dataclass
class OrderCancelReplaceRequest:
    """Order Cancel/Replace Request (35=G) message"""
    orig_cl_ord_id: str    # 41
    cl_ord_id: str         # 11
    symbol: str            # 55
    side: str              # 54
    transact_time: datetime # 60
    ord_type: str          # 40
    
    # New order parameters
    order_qty: Optional[int] = None      # 38
    price: Optional[Decimal] = None      # 44
    stop_px: Optional[Decimal] = None    # 99
    time_in_force: Optional[str] = None  # 59
    
    # Optional fields
    order_id: Optional[str] = None       # 37
    account: Optional[str] = None        # 1
    text: Optional[str] = None           # 58
    
    def to_fix_fields(self) -> Dict[int, Any]:
        """Convert to FIX field dictionary"""
        fields = {
            41: self.orig_cl_ord_id,
            11: self.cl_ord_id,
            55: self.symbol,
            54: self.side,
            60: self.transact_time.strftime("%Y%m%d-%H:%M:%S.%f")[:-3],
            40: self.ord_type
        }
        
        if self.order_qty is not None:
            fields[38] = self.order_qty
        if self.price is not None:
            fields[44] = str(self.price)
        if self.stop_px is not None:
            fields[99] = str(self.stop_px)
        if self.time_in_force is not None:
            fields[59] = self.time_in_force
        if self.order_id is not None:
            fields[37] = self.order_id
        if self.account is not None:
            fields[1] = self.account
        if self.text is not None:
            fields[58] = self.text
        
        return fields


@dataclass_json
@dataclass
class ExecutionReport:
    """Execution Report (35=8) message"""
    order_id: str          # 37
    cl_ord_id: str         # 11
    exec_id: str           # 17
    exec_type: str         # 150
    ord_status: str        # 39
    symbol: str            # 55
    side: str              # 54
    
    # Quantities
    order_qty: int         # 38
    cum_qty: int           # 14
    leaves_qty: int        # 151
    
    # Prices
    avg_px: Optional[Decimal] = None    # 6
    last_px: Optional[Decimal] = None   # 31
    last_shares: Optional[int] = None   # 32
    
    # Timing
    transact_time: Optional[datetime] = None  # 60
    
    # Optional fields
    orig_cl_ord_id: Optional[str] = None      # 41
    exec_ref_id: Optional[str] = None         # 19
    text: Optional[str] = None                # 58
    account: Optional[str] = None             # 1
    
    @classmethod
    def from_fix_fields(cls, fields: Dict[int, Any]) -> 'ExecutionReport':
        """Create ExecutionReport from FIX fields"""
        return cls(
            order_id=fields.get(37, ""),
            cl_ord_id=fields.get(11, ""),
            exec_id=fields.get(17, ""),
            exec_type=fields.get(150, ""),
            ord_status=fields.get(39, ""),
            symbol=fields.get(55, ""),
            side=fields.get(54, ""),
            order_qty=int(fields.get(38, 0)),
            cum_qty=int(fields.get(14, 0)),
            leaves_qty=int(fields.get(151, 0)),
            avg_px=Decimal(fields[6]) if 6 in fields else None,
            last_px=Decimal(fields[31]) if 31 in fields else None,
            last_shares=int(fields[32]) if 32 in fields else None,
            transact_time=datetime.strptime(fields[60], "%Y%m%d-%H:%M:%S.%f") if 60 in fields else None,
            orig_cl_ord_id=fields.get(41),
            exec_ref_id=fields.get(19),
            text=fields.get(58),
            account=fields.get(1)
        )


@dataclass_json
@dataclass
class OrderCancelReject:
    """Order Cancel Reject (35=9) message"""
    order_id: str          # 37
    cl_ord_id: str         # 11
    orig_cl_ord_id: str    # 41
    ord_status: str        # 39
    cxl_rej_reason: str    # 102
    
    # Optional fields
    cxl_rej_response_to: Optional[str] = None  # 434
    text: Optional[str] = None                 # 58
    account: Optional[str] = None              # 1
    
    @classmethod
    def from_fix_fields(cls, fields: Dict[int, Any]) -> 'OrderCancelReject':
        """Create OrderCancelReject from FIX fields"""
        return cls(
            order_id=fields.get(37, ""),
            cl_ord_id=fields.get(11, ""),
            orig_cl_ord_id=fields.get(41, ""),
            ord_status=fields.get(39, ""),
            cxl_rej_reason=fields.get(102, ""),
            cxl_rej_response_to=fields.get(434),
            text=fields.get(58),
            account=fields.get(1)
        )


# FIX field constants
class FixFields:
    """FIX field tag constants"""
    ACCOUNT = 1
    AVG_PX = 6
    CUM_QTY = 14
    CURRENCY = 15
    EXEC_ID = 17
    EXEC_INST = 18
    EXEC_REF_ID = 19
    EXEC_TRANS_TYPE = 20
    HANDL_INST = 21
    SECURITY_ID_SOURCE = 22
    LAST_MKT = 30
    LAST_PX = 31
    LAST_SHARES = 32
    MSG_SEQ_NUM = 34
    MSG_TYPE = 35
    ORDER_ID = 37
    ORDER_QTY = 38
    ORD_STATUS = 39
    ORD_TYPE = 40
    ORIG_CL_ORD_ID = 41
    PRICE = 44
    SECURITY_ID = 48
    SENDER_COMP_ID = 49
    SENDING_TIME = 52
    SIDE = 54
    SYMBOL = 55
    TARGET_COMP_ID = 56
    TEXT = 58
    TIME_IN_FORCE = 59
    TRANSACT_TIME = 60
    STOP_PX = 99
    EX_DESTINATION = 100
    CXL_REJ_REASON = 102
    ORD_REJ_REASON = 103
    MIN_QTY = 110
    EXEC_TYPE = 150
    LEAVES_QTY = 151
    SECURITY_TYPE = 167
    MATURITY_MONTH_YEAR = 200
    PUT_OR_CALL = 201
    STRIKE_PRICE = 202
    SECURITY_EXCHANGE = 207
    MAX_SHOW = 210
    CXL_REJ_RESPONSE_TO = 434
    CLEARING_ACCOUNT = 440
    ORDER_CAPACITY = 528
    ORDER_RESTRICTIONS = 529
    MATURITY_DATE = 541


# FIX value constants
class FixValues:
    """FIX field value constants"""
    
    # Message types
    HEARTBEAT = "0"
    TEST_REQUEST = "1"
    RESEND_REQUEST = "2"
    REJECT = "3"
    SEQUENCE_RESET = "4"
    LOGOUT = "5"
    EXECUTION_REPORT = "8"
    ORDER_CANCEL_REJECT = "9"
    LOGON = "A"
    NEW_ORDER_SINGLE = "D"
    ORDER_CANCEL_REQUEST = "F"
    ORDER_CANCEL_REPLACE_REQUEST = "G"
    
    # Order sides
    BUY = "1"
    SELL = "2"
    
    # Order types
    MARKET = "1"
    LIMIT = "2"
    STOP = "3"
    STOP_LIMIT = "4"
    
    # Time in force
    DAY = "0"
    GTC = "1"
    OPQ = "2"  # At the Opening
    IOC = "3"
    FOK = "4"
    GTX = "5"  # Good Till Crossing
    GTD = "6"
    
    # Order status
    NEW = "0"
    PARTIALLY_FILLED = "1"
    FILLED = "2"
    DONE_FOR_DAY = "3"
    CANCELED = "4"
    REPLACED = "5"
    PENDING_CANCEL = "6"
    STOPPED = "7"
    REJECTED = "8"
    SUSPENDED = "9"
    PENDING_NEW = "A"
    CALCULATED = "B"
    EXPIRED = "C"
    ACCEPTED_FOR_BIDDING = "D"
    PENDING_REPLACE = "E"
    
    # Execution types
    NEW_EXEC = "0"
    PARTIAL_FILL = "1"
    FILL = "2"
    DONE_FOR_DAY_EXEC = "3"
    CANCELED_EXEC = "4"
    REPLACED_EXEC = "5"
    PENDING_CANCEL_EXEC = "6"
    STOPPED_EXEC = "7"
    REJECTED_EXEC = "8"
    SUSPENDED_EXEC = "9"
    PENDING_NEW_EXEC = "A"
    CALCULATED_EXEC = "B"
    EXPIRED_EXEC = "C"
    RESTATED = "D"
    PENDING_REPLACE_EXEC = "E"
    TRADE = "F"
    TRADE_CORRECT = "G"
    TRADE_CANCEL = "H"
    ORDER_STATUS = "I"
    
    # Put or Call
    PUT = 0
    CALL = 1
    
    # Security types
    FUTURE = "FUT"
    OPTION = "OPT"
    STOCK = "CS"
    BOND = "BOND"
