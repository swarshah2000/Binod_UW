"""
Logging configuration and setup for TT FIX Order Adapter
"""

import os
import sys
from pathlib import Path
from typing import Optional
from loguru import logger


def setup_logging(logging_config: Optional[object] = None):
    """
    Setup logging configuration using Loguru
    
    Args:
        logging_config: LoggingConfig object with logging settings
    """
    # Remove default handler
    logger.remove()
    
    # Default configuration if none provided
    if logging_config is None:
        level = "INFO"
        log_format = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"
        log_dir = "data/logs"
        console_logging = True
        file_logging = True
        rotation = "1 day"
        retention = "30 days"
        compression = "gz"
    else:
        level = logging_config.level
        log_format = logging_config.format
        log_dir = logging_config.log_dir
        console_logging = logging_config.console_logging
        file_logging = logging_config.file_logging
        rotation = logging_config.rotation
        retention = logging_config.retention
        compression = logging_config.compression
    
    # Ensure log directory exists
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Console logging
    if console_logging:
        logger.add(
            sys.stderr,
            format=log_format,
            level=level,
            colorize=True,
            backtrace=True,
            diagnose=True
        )
    
    # File logging
    if file_logging:
        # Main application log
        logger.add(
            os.path.join(log_dir, "app_{time:YYYY-MM-DD}.log"),
            format=log_format,
            level=level,
            rotation=rotation,
            retention=retention,
            compression=compression,
            backtrace=True,
            diagnose=True
        )
        
        # Error log (ERROR and CRITICAL only)
        logger.add(
            os.path.join(log_dir, "error_{time:YYYY-MM-DD}.log"),
            format=log_format,
            level="ERROR",
            rotation=rotation,
            retention=retention,
            compression=compression,
            backtrace=True,
            diagnose=True
        )
        
        # Order flow log
        logger.add(
            os.path.join(log_dir, "orders_{time:YYYY-MM-DD}.log"),
            format=log_format,
            level="INFO",
            rotation=rotation,
            retention=retention,
            compression=compression,
            filter=lambda record: "ORDER" in record["extra"].get("category", ""),
            backtrace=True,
            diagnose=True
        )
        
        # FIX message log
        logger.add(
            os.path.join(log_dir, "fix_{time:YYYY-MM-DD}.log"),
            format=log_format,
            level="DEBUG",
            rotation=rotation,
            retention=retention,
            compression=compression,
            filter=lambda record: "FIX" in record["extra"].get("category", ""),
            backtrace=True,
            diagnose=True
        )
    
    logger.info("Logging system initialized")


def get_order_logger():
    """Get logger for order flow events"""
    return logger.bind(category="ORDER")


def get_fix_logger():
    """Get logger for FIX message events"""
    return logger.bind(category="FIX")


def get_risk_logger():
    """Get logger for risk management events"""
    return logger.bind(category="RISK")


def get_zmq_logger():
    """Get logger for ZMQ events"""
    return logger.bind(category="ZMQ")


def get_monitoring_logger():
    """Get logger for monitoring events"""
    return logger.bind(category="MONITORING")
