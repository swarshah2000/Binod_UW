"""
FIX utility functions
"""

import re
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional


def parse_fix_message(message: str) -> Dict[int, str]:
    """Parse FIX message string into field dictionary"""
    fields = {}
    
    # Split by SOH (Start of Header) character
    parts = message.split('\x01')
    
    for part in parts:
        if '=' in part:
            try:
                tag_str, value = part.split('=', 1)
                tag = int(tag_str)
                fields[tag] = value
            except ValueError:
                continue
    
    return fields


def build_fix_message(fields: Dict[int, Any], msg_type: str) -> str:
    """Build FIX message string from fields"""
    # Start with basic header fields
    message_parts = []
    
    # Begin String (8)
    message_parts.append("8=FIX.4.4")
    
    # Message Type (35)
    message_parts.append(f"35={msg_type}")
    
    # Add other fields (excluding BeginString, BodyLength, CheckSum)
    for tag in sorted(fields.keys()):
        if tag not in [8, 9, 10]:  # Skip BeginString, BodyLength, CheckSum
            value = fields[tag]
            message_parts.append(f"{tag}={value}")
    
    # Join with SOH
    body = '\x01'.join(message_parts[1:])  # Exclude BeginString for body length calc
    
    # Calculate body length
    body_length = len(body) + 1  # +1 for final SOH
    
    # Complete message
    full_message = f"8=FIX.4.4\x019={body_length}\x01{body}\x01"
    
    # Calculate checksum
    checksum = calculate_checksum(full_message)
    full_message += f"10={checksum:03d}\x01"
    
    return full_message


def calculate_checksum(message: str) -> int:
    """Calculate FIX message checksum"""
    total = sum(ord(char) for char in message)
    return total % 256


def format_fix_timestamp(dt: datetime) -> str:
    """Format datetime for FIX timestamp fields"""
    return dt.strftime("%Y%m%d-%H:%M:%S.%f")[:-3]


def parse_fix_timestamp(timestamp: str) -> datetime:
    """Parse FIX timestamp string to datetime"""
    formats = [
        "%Y%m%d-%H:%M:%S.%f",
        "%Y%m%d-%H:%M:%S",
        "%H:%M:%S.%f",
        "%H:%M:%S"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(timestamp, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Could not parse timestamp: {timestamp}")


def format_fix_date(dt: datetime) -> str:
    """Format date for FIX date fields"""
    return dt.strftime("%Y%m%d")


def format_fix_time(dt: datetime) -> str:
    """Format time for FIX time fields"""
    return dt.strftime("%H:%M:%S.%f")[:-3]


def clean_fix_string(value: str) -> str:
    """Clean string for FIX message (remove SOH and control chars)"""
    if not value:
        return ""
    
    # Remove SOH and other control characters
    cleaned = ''.join(char for char in value if ord(char) >= 32 and char != '\x01')
    
    return cleaned


def validate_fix_tag(tag: int) -> bool:
    """Validate FIX tag number"""
    return 1 <= tag <= 99999


def is_header_field(tag: int) -> bool:
    """Check if tag is a header field"""
    header_fields = {
        8, 9, 35, 49, 56, 115, 128, 90, 91, 34, 50, 142, 57, 143,
        116, 144, 129, 145, 43, 97, 52, 122, 212, 213, 347, 369
    }
    return tag in header_fields


def is_trailer_field(tag: int) -> bool:
    """Check if tag is a trailer field"""
    trailer_fields = {10, 89, 93}
    return tag in trailer_fields


def get_message_type_name(msg_type: str) -> str:
    """Get human-readable message type name"""
    message_types = {
        "0": "Heartbeat",
        "1": "TestRequest",
        "2": "ResendRequest",
        "3": "Reject",
        "4": "SequenceReset",
        "5": "Logout",
        "8": "ExecutionReport",
        "9": "OrderCancelReject",
        "A": "Logon",
        "B": "News",
        "D": "NewOrderSingle",
        "F": "OrderCancelRequest",
        "G": "OrderCancelReplaceRequest",
        "H": "OrderStatusRequest",
        "V": "MarketDataRequest",
        "W": "MarketDataSnapshot",
        "X": "MarketDataIncrementalRefresh",
        "Y": "MarketDataRequestReject",
        "c": "SecurityDefinitionRequest",
        "d": "SecurityDefinition",
        "e": "SecurityStatusRequest",
        "f": "SecurityStatus",
        "j": "BusinessMessageReject"
    }
    
    return message_types.get(msg_type, f"Unknown({msg_type})")


def format_fix_decimal(value: Decimal, precision: int = 2) -> str:
    """Format decimal for FIX message"""
    if value is None:
        return ""
    
    # Remove trailing zeros and ensure minimum precision
    formatted = f"{value:.{precision}f}"
    
    # Remove trailing zeros after decimal point
    if '.' in formatted:
        formatted = formatted.rstrip('0').rstrip('.')
    
    return formatted


def parse_fix_decimal(value: str) -> Optional[Decimal]:
    """Parse FIX decimal field"""
    if not value:
        return None
    
    try:
        return Decimal(value)
    except (ValueError, TypeError):
        return None


def validate_fix_message_structure(message: str) -> bool:
    """Validate basic FIX message structure"""
    if not message:
        return False
    
    # Must start with BeginString
    if not message.startswith("8=FIX"):
        return False
    
    # Must end with checksum
    if not re.search(r'10=\d{3}\x01$', message):
        return False
    
    # Must have required fields
    required_pattern = r'8=FIX\.\d\.\d\x019=\d+\x0135='
    if not re.match(required_pattern, message):
        return False
    
    return True


def extract_session_id(sender_comp_id: str, target_comp_id: str, session_qualifier: str = "") -> str:
    """Extract session identifier"""
    if session_qualifier:
        return f"{sender_comp_id}->{target_comp_id}:{session_qualifier}"
    else:
        return f"{sender_comp_id}->{target_comp_id}"


def generate_fix_order_id(prefix: str = "ORD") -> str:
    """Generate unique FIX order ID"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")[:-3]
    return f"{prefix}_{timestamp}"


def generate_fix_exec_id(prefix: str = "EXEC") -> str:
    """Generate unique FIX execution ID"""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")[:-3]
    return f"{prefix}_{timestamp}"


class FixFieldMap:
    """FIX field tag to name mapping"""
    
    FIELD_NAMES = {
        1: "Account",
        6: "AvgPx",
        8: "BeginString",
        9: "BodyLength",
        10: "CheckSum",
        11: "ClOrdID",
        14: "CumQty",
        15: "Currency",
        17: "ExecID",
        18: "ExecInst",
        19: "ExecRefID",
        20: "ExecTransType",
        30: "LastMkt",
        31: "LastPx",
        32: "LastShares",
        34: "MsgSeqNum",
        35: "MsgType",
        37: "OrderID",
        38: "OrderQty",
        39: "OrdStatus",
        40: "OrdType",
        41: "OrigClOrdID",
        44: "Price",
        48: "SecurityID",
        49: "SenderCompID",
        52: "SendingTime",
        54: "Side",
        55: "Symbol",
        56: "TargetCompID",
        58: "Text",
        59: "TimeInForce",
        60: "TransactTime",
        99: "StopPx",
        100: "ExDestination",
        102: "CxlRejReason",
        103: "OrdRejReason",
        110: "MinQty",
        150: "ExecType",
        151: "LeavesQty",
        167: "SecurityType",
        200: "MaturityMonthYear",
        201: "PutOrCall",
        202: "StrikePrice",
        207: "SecurityExchange",
        262: "MDReqID",
        268: "NoMDEntries",
        269: "MDEntryType",
        270: "MDEntryPx",
        271: "MDEntrySize",
        541: "MaturityDate"
    }
    
    @classmethod
    def get_field_name(cls, tag: int) -> str:
        """Get field name for tag"""
        return cls.FIELD_NAMES.get(tag, f"Field{tag}")
    
    @classmethod
    def format_message_for_logging(cls, fields: Dict[int, Any]) -> str:
        """Format FIX message for logging with field names"""
        formatted_fields = []
        
        for tag in sorted(fields.keys()):
            field_name = cls.get_field_name(tag)
            value = fields[tag]
            formatted_fields.append(f"{field_name}({tag})={value}")
        
        return " | ".join(formatted_fields)
