"""
Custom exceptions for TT FIX Order Adapter
"""


class OrderAdapterError(Exception):
    """Base exception for Order Adapter"""
    pass


class ConfigurationError(OrderAdapterError):
    """Configuration-related errors"""
    pass


class OrderProcessingError(OrderAdapterError):
    """Order processing errors"""
    pass


class FixConnectionError(OrderAdapterError):
    """FIX connection and communication errors"""
    pass


class OrderValidationError(OrderAdapterError):
    """Order validation errors"""
    pass


class RiskManagementError(OrderAdapterError):
    """Risk management related errors"""
    pass


class ZMQError(OrderAdapterError):
    """ZeroMQ related errors"""
    pass


class InstrumentError(OrderAdapterError):
    """Instrument/security related errors"""
    pass


class TimeoutError(OrderAdapterError):
    """Timeout related errors"""
    pass


class MessageParsingError(OrderAdapterError):
    """Message parsing errors"""
    pass


class AuthenticationError(OrderAdapterError):
    """Authentication and authorization errors"""
    pass
