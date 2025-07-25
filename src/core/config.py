"""
Configuration management for TT FIX Order Adapter
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class ZMQConfig:
    """ZeroMQ configuration"""
    order_port: int = 5555
    bind_address: str = "tcp://*:5555"
    socket_type: str = "PULL"
    high_water_mark: int = 1000
    receive_timeout: int = 100  # milliseconds


@dataclass_json
@dataclass 
class FixConfig:
    """FIX configuration"""
    config_file: str = "config/fix_config.cfg"
    data_dictionary: str = "FIX_SCHEMA/UAT_TT-FIX44.xml"
    sender_comp_id: str = "YOUR_SENDER_COMP_ID"
    target_comp_id: str = "TTUAT_SERVER"
    session_qualifier: str = "ORD"
    heartbeat_interval: int = 30
    reconnect_interval: int = 60
    ssl_enabled: bool = True
    ssl_certificate: str = "./TTFIX.crt"


@dataclass_json
@dataclass
class RiskLimits:
    """Risk management limits"""
    max_order_size: int = 1000
    max_daily_volume: int = 10000
    max_orders_per_second: int = 10
    max_position_size: int = 5000
    enabled: bool = True


@dataclass_json
@dataclass
class TradingConfig:
    """Trading configuration"""
    default_currency: str = "USD"
    default_exchange: str = "CBOE"
    default_security_type: str = "OPT"
    risk_limits: RiskLimits = field(default_factory=RiskLimits)
    order_timeout_seconds: int = 30


@dataclass_json
@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}"
    rotation: str = "1 day"
    retention: str = "30 days"
    compression: str = "gz"
    log_dir: str = "data/logs"
    console_logging: bool = True
    file_logging: bool = True


@dataclass_json
@dataclass
class MonitoringConfig:
    """Monitoring configuration"""
    enabled: bool = True
    metrics_port: int = 8080
    health_check_interval: int = 30
    alert_thresholds: Dict[str, Any] = field(default_factory=lambda: {
        "error_rate": 0.05,
        "latency_p99": 1000,
        "queue_depth": 100
    })


@dataclass_json
@dataclass
class AppConfig:
    """Main application configuration"""
    zmq: ZMQConfig = field(default_factory=ZMQConfig)
    fix: FixConfig = field(default_factory=FixConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration from file or defaults"""
        if config_file is None:
            config_file = os.getenv("CONFIG_FILE", "config/app_config.yaml")
        
        config_path = Path(config_file)
        
        if config_path.exists():
            self._load_from_file(config_path)
        else:
            # Use defaults and create config file
            self._set_defaults()
            self._create_config_file(config_path)
    
    def _set_defaults(self):
        """Set default configuration values"""
        self.zmq = ZMQConfig()
        self.fix = FixConfig()
        self.trading = TradingConfig()
        self.logging = LoggingConfig()
        self.monitoring = MonitoringConfig()
    
    def _load_from_file(self, config_path: Path):
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Load each section
            self.zmq = ZMQConfig(**config_data.get('zmq', {}))
            self.fix = FixConfig(**config_data.get('fix', {}))
            self.trading = TradingConfig(**config_data.get('trading', {}))
            self.logging = LoggingConfig(**config_data.get('logging', {}))
            self.monitoring = MonitoringConfig(**config_data.get('monitoring', {}))
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from {config_path}: {e}")
    
    def _create_config_file(self, config_path: Path):
        """Create a default configuration file"""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        config_data = {
            'zmq': self.zmq.to_dict(),
            'fix': self.fix.to_dict(),
            'trading': self.trading.to_dict(),
            'logging': self.logging.to_dict(),
            'monitoring': self.monitoring.to_dict()
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, indent=2)
    
    def validate(self) -> bool:
        """Validate configuration settings"""
        errors = []
        
        # Validate ZMQ config
        if self.zmq.order_port <= 0 or self.zmq.order_port > 65535:
            errors.append("ZMQ order_port must be between 1 and 65535")
        
        # Validate FIX config
        if not self.fix.sender_comp_id or self.fix.sender_comp_id == "YOUR_SENDER_COMP_ID":
            errors.append("FIX sender_comp_id must be configured")
        
        if not Path(self.fix.data_dictionary).exists():
            errors.append(f"FIX data dictionary not found: {self.fix.data_dictionary}")
        
        # Validate trading config
        if self.trading.risk_limits.max_order_size <= 0:
            errors.append("Risk limit max_order_size must be positive")
        
        if errors:
            raise ConfigurationError(f"Configuration validation failed: {', '.join(errors)}")
        
        return True
    
    def get_fix_config_path(self) -> Path:
        """Get the absolute path to the FIX configuration file"""
        return Path(self.fix.config_file).resolve()
    
    def get_data_dictionary_path(self) -> Path:
        """Get the absolute path to the FIX data dictionary"""
        return Path(self.fix.data_dictionary).resolve()


class ConfigurationError(Exception):
    """Configuration-related errors"""
    pass
