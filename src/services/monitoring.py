"""
Monitoring Service
Provides health checks, metrics, and system monitoring
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from loguru import logger

from core.config import AppConfig


class MonitoringService:
    """System monitoring and health check service"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.running = False
        self.start_time = None
        
        # Component references (set by main application)
        self.fix_gateway = None
        self.order_listener = None
        
        # Metrics storage
        self.metrics = {
            "system": {
                "uptime_seconds": 0,
                "start_time": None,
                "last_health_check": None
            },
            "orders": {
                "total_received": 0,
                "total_processed": 0,
                "total_failed": 0,
                "processing_rate": 0.0,
                "avg_processing_time": 0.0
            },
            "fix": {
                "connected": False,
                "messages_sent": 0,
                "messages_received": 0,
                "last_heartbeat": None,
                "connection_uptime": 0
            },
            "errors": {
                "total_errors": 0,
                "error_rate": 0.0,
                "last_error": None,
                "critical_errors": 0
            }
        }
        
        # Health check results
        self.health_status = {
            "overall": "UNKNOWN",
            "components": {
                "zmq_listener": "UNKNOWN",
                "fix_gateway": "UNKNOWN",
                "order_processor": "UNKNOWN"
            },
            "last_check": None,
            "issues": []
        }
        
        # Setup logger
        self.logger = logger.bind(category="MONITORING")
    
    async def initialize(self):
        """Initialize monitoring service"""
        self.logger.info("Initializing Monitoring Service")
        self.start_time = datetime.utcnow()
        self.metrics["system"]["start_time"] = self.start_time.isoformat()
    
    async def start(self):
        """Start monitoring service"""
        try:
            self.logger.info("Starting Monitoring Service")
            self.running = True
            
            # Start monitoring tasks
            await asyncio.gather(
                self._health_check_loop(),
                self._metrics_collection_loop(),
                self._alert_monitoring_loop()
            )
            
        except Exception as e:
            self.logger.error(f"Error in monitoring service: {e}")
    
    async def stop(self):
        """Stop monitoring service"""
        self.logger.info("Stopping Monitoring Service")
        self.running = False
    
    def set_components(self, fix_gateway=None, order_listener=None):
        """Set component references for monitoring"""
        self.fix_gateway = fix_gateway
        self.order_listener = order_listener
    
    async def _health_check_loop(self):
        """Periodic health check loop"""
        while self.running:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.config.monitoring.health_check_interval)
            except Exception as e:
                self.logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(5)
    
    async def _metrics_collection_loop(self):
        """Periodic metrics collection loop"""
        while self.running:
            try:
                await self._collect_metrics()
                await asyncio.sleep(10)  # Collect metrics every 10 seconds
            except Exception as e:
                self.logger.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(5)
    
    async def _alert_monitoring_loop(self):
        """Monitor for alert conditions"""
        while self.running:
            try:
                await self._check_alert_conditions()
                await asyncio.sleep(30)  # Check alerts every 30 seconds
            except Exception as e:
                self.logger.error(f"Error in alert monitoring: {e}")
                await asyncio.sleep(5)
    
    async def _perform_health_check(self):
        """Perform comprehensive health check"""
        issues = []
        component_status = {}
        
        # Check ZMQ listener
        if self.order_listener:
            zmq_stats = self.order_listener.get_stats()
            if zmq_stats.get("last_order_time"):
                time_since_last = time.time() - zmq_stats["last_order_time"]
                if time_since_last > 300:  # 5 minutes
                    issues.append("No orders received in last 5 minutes")
                    component_status["zmq_listener"] = "WARNING"
                else:
                    component_status["zmq_listener"] = "HEALTHY"
            else:
                component_status["zmq_listener"] = "NO_DATA"
        else:
            component_status["zmq_listener"] = "NOT_AVAILABLE"
        
        # Check FIX gateway
        if self.fix_gateway:
            if self.fix_gateway.is_connected():
                component_status["fix_gateway"] = "HEALTHY"
            else:
                issues.append("FIX gateway not connected")
                component_status["fix_gateway"] = "CRITICAL"
        else:
            component_status["fix_gateway"] = "NOT_AVAILABLE"
        
        # Check order processor
        # This would typically check processing queue depth, error rates, etc.
        component_status["order_processor"] = "HEALTHY"
        
        # Determine overall status
        if any(status == "CRITICAL" for status in component_status.values()):
            overall_status = "CRITICAL"
        elif any(status == "WARNING" for status in component_status.values()):
            overall_status = "WARNING"
        elif all(status in ["HEALTHY", "NO_DATA"] for status in component_status.values()):
            overall_status = "HEALTHY"
        else:
            overall_status = "UNKNOWN"
        
        # Update health status
        self.health_status.update({
            "overall": overall_status,
            "components": component_status,
            "last_check": datetime.utcnow().isoformat(),
            "issues": issues
        })
        
        self.metrics["system"]["last_health_check"] = datetime.utcnow().isoformat()
        
        if issues:
            self.logger.warning(f"Health check issues: {issues}")
        else:
            self.logger.debug("Health check passed")
    
    async def _collect_metrics(self):
        """Collect system metrics"""
        # Update system metrics
        if self.start_time:
            uptime = datetime.utcnow() - self.start_time
            self.metrics["system"]["uptime_seconds"] = uptime.total_seconds()
        
        # Collect order metrics
        if self.order_listener:
            zmq_stats = self.order_listener.get_stats()
            self.metrics["orders"].update({
                "total_received": zmq_stats.get("orders_received", 0),
                "total_processed": zmq_stats.get("orders_processed", 0),
                "total_failed": zmq_stats.get("orders_failed", 0)
            })
            
            # Calculate processing rate
            total_orders = zmq_stats.get("orders_processed", 0)
            if self.start_time and total_orders > 0:
                uptime_hours = (datetime.utcnow() - self.start_time).total_seconds() / 3600
                self.metrics["orders"]["processing_rate"] = total_orders / uptime_hours
        
        # Collect FIX metrics
        if self.fix_gateway:
            fix_stats = self.fix_gateway.get_stats()
            self.metrics["fix"].update({
                "connected": fix_stats.get("connected", False),
                "messages_sent": fix_stats.get("messages_sent", 0),
                "messages_received": fix_stats.get("messages_received", 0),
                "last_heartbeat": fix_stats.get("last_heartbeat")
            })
            
            # Calculate connection uptime
            if fix_stats.get("connection_time"):
                connection_time = fix_stats["connection_time"]
                if isinstance(connection_time, str):
                    connection_time = datetime.fromisoformat(connection_time)
                uptime = (datetime.utcnow() - connection_time).total_seconds()
                self.metrics["fix"]["connection_uptime"] = uptime
    
    async def _check_alert_conditions(self):
        """Check for alert conditions"""
        thresholds = self.config.monitoring.alert_thresholds
        
        # Check error rate
        total_orders = self.metrics["orders"]["total_received"]
        total_failed = self.metrics["orders"]["total_failed"]
        
        if total_orders > 0:
            error_rate = total_failed / total_orders
            self.metrics["errors"]["error_rate"] = error_rate
            
            if error_rate > thresholds.get("error_rate", 0.05):
                self.logger.error(f"High error rate detected: {error_rate:.2%}")
        
        # Check FIX connection
        if not self.metrics["fix"]["connected"]:
            self.logger.error("FIX gateway disconnected")
        
        # Check processing latency (would need actual latency measurements)
        # This is a placeholder for latency monitoring
        
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        return self.health_status.copy()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return self.metrics.copy()
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        return {
            "application": "TT FIX Order Adapter",
            "version": "1.0.0",
            "uptime": self.metrics["system"]["uptime_seconds"],
            "start_time": self.metrics["system"]["start_time"],
            "health_status": self.health_status["overall"],
            "components": len(self.health_status["components"]),
            "total_orders": self.metrics["orders"]["total_processed"],
            "fix_connected": self.metrics["fix"]["connected"]
        }
    
    def record_error(self, error: Exception, severity: str = "ERROR"):
        """Record an error for monitoring"""
        self.metrics["errors"]["total_errors"] += 1
        self.metrics["errors"]["last_error"] = {
            "message": str(error),
            "type": type(error).__name__,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if severity == "CRITICAL":
            self.metrics["errors"]["critical_errors"] += 1
        
        self.logger.error(f"Recorded {severity} error: {error}")
    
    def record_order_processed(self, processing_time: float):
        """Record order processing time for metrics"""
        # Update average processing time
        current_avg = self.metrics["orders"]["avg_processing_time"]
        total_processed = self.metrics["orders"]["total_processed"]
        
        if total_processed > 0:
            new_avg = ((current_avg * (total_processed - 1)) + processing_time) / total_processed
            self.metrics["orders"]["avg_processing_time"] = new_avg
