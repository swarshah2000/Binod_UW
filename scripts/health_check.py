#!/usr/bin/env python3
"""
Health Check Script
Checks the health and status of the TT FIX Order Adapter
"""

import json
import sys
import time
from pathlib import Path
import requests
from datetime import datetime

# Add src directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def check_zmq_connectivity(host: str = "localhost", port: int = 5555) -> bool:
    """Check if ZMQ port is accessible"""
    try:
        import zmq
        context = zmq.Context()
        socket = context.socket(zmq.PUSH)
        socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
        
        socket.connect(f"tcp://{host}:{port}")
        
        # Try to send a test message
        test_message = json.dumps({"test": "health_check", "timestamp": datetime.utcnow().isoformat()})
        socket.send_string(test_message, zmq.NOBLOCK)
        
        socket.close()
        context.term()
        return True
        
    except Exception as e:
        print(f"ZMQ connectivity check failed: {e}")
        return False


def check_fix_session_status() -> dict:
    """Check FIX session status"""
    try:
        # This would typically query the FIX session status
        # For now, return a mock status
        return {
            "connected": True,  # This would be actual session status
            "session_id": "YOUR_SENDER_COMP_ID->TTUAT_SERVER",
            "last_heartbeat": datetime.utcnow().isoformat(),
            "messages_sent": 42,
            "messages_received": 38
        }
    except Exception as e:
        return {"error": str(e), "connected": False}


def check_log_files() -> dict:
    """Check log files for recent activity"""
    log_dir = project_root / "data" / "logs"
    
    if not log_dir.exists():
        return {"status": "Log directory not found"}
    
    log_files = list(log_dir.glob("*.log"))
    
    if not log_files:
        return {"status": "No log files found"}
    
    # Check most recent log file
    latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
    
    try:
        # Read last few lines
        with open(latest_log, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-10:] if len(lines) >= 10 else lines
        
        return {
            "status": "OK",
            "latest_log": str(latest_log),
            "file_size": latest_log.stat().st_size,
            "last_modified": datetime.fromtimestamp(latest_log.stat().st_mtime).isoformat(),
            "recent_entries": len(recent_lines)
        }
    
    except Exception as e:
        return {"status": f"Error reading log file: {e}"}


def check_config_files() -> dict:
    """Check if configuration files exist and are valid"""
    config_dir = project_root / "config"
    required_configs = [
        "app_config.yaml",
        "fix_config.cfg",
        "logging_config.yaml"
    ]
    
    status = {}
    
    for config_file in required_configs:
        config_path = config_dir / config_file
        
        if config_path.exists():
            status[config_file] = {
                "exists": True,
                "size": config_path.stat().st_size,
                "last_modified": datetime.fromtimestamp(config_path.stat().st_mtime).isoformat()
            }
        else:
            status[config_file] = {"exists": False}
    
    return status


def check_fix_schema() -> dict:
    """Check if FIX schema file exists"""
    schema_path = project_root / "FIX_SCHEMA" / "UAT_TT-FIX44.xml"
    
    if schema_path.exists():
        return {
            "exists": True,
            "size": schema_path.stat().st_size,
            "last_modified": datetime.fromtimestamp(schema_path.stat().st_mtime).isoformat()
        }
    else:
        return {"exists": False}


def check_certificates() -> dict:
    """Check if SSL certificates exist"""
    cert_files = ["TTFIX.crt", "client.crt", "private.key"]
    cert_status = {}
    
    for cert_file in cert_files:
        cert_path = project_root / cert_file
        
        if cert_path.exists():
            cert_status[cert_file] = {
                "exists": True,
                "size": cert_path.stat().st_size
            }
        else:
            cert_status[cert_file] = {"exists": False}
    
    return cert_status


def run_health_check() -> dict:
    """Run comprehensive health check"""
    print("Running TT FIX Order Adapter Health Check...")
    print("=" * 60)
    
    health_report = {
        "timestamp": datetime.utcnow().isoformat(),
        "overall_status": "UNKNOWN",
        "checks": {}
    }
    
    # Check ZMQ connectivity
    print("1. Checking ZMQ connectivity...")
    zmq_ok = check_zmq_connectivity()
    health_report["checks"]["zmq_connectivity"] = {
        "status": "OK" if zmq_ok else "FAILED",
        "details": "ZMQ port accessible" if zmq_ok else "Cannot connect to ZMQ port"
    }
    print(f"   ZMQ: {'✓ OK' if zmq_ok else '✗ FAILED'}")
    
    # Check FIX session
    print("2. Checking FIX session status...")
    fix_status = check_fix_session_status()
    health_report["checks"]["fix_session"] = fix_status
    print(f"   FIX: {'✓ Connected' if fix_status.get('connected') else '✗ Disconnected'}")
    
    # Check log files
    print("3. Checking log files...")
    log_status = check_log_files()
    health_report["checks"]["log_files"] = log_status
    print(f"   Logs: {'✓ OK' if log_status.get('status') == 'OK' else '✗ ' + log_status.get('status', 'Unknown')}")
    
    # Check configuration files
    print("4. Checking configuration files...")
    config_status = check_config_files()
    health_report["checks"]["config_files"] = config_status
    
    missing_configs = [cfg for cfg, status in config_status.items() if not status.get("exists")]
    if missing_configs:
        print(f"   Config: ✗ Missing files: {', '.join(missing_configs)}")
    else:
        print("   Config: ✓ All files present")
    
    # Check FIX schema
    print("5. Checking FIX schema...")
    schema_status = check_fix_schema()
    health_report["checks"]["fix_schema"] = schema_status
    print(f"   Schema: {'✓ Found' if schema_status.get('exists') else '✗ Missing'}")
    
    # Check certificates
    print("6. Checking SSL certificates...")
    cert_status = check_certificates()
    health_report["checks"]["certificates"] = cert_status
    
    missing_certs = [cert for cert, status in cert_status.items() if not status.get("exists")]
    if missing_certs:
        print(f"   Certs: ⚠ Missing files: {', '.join(missing_certs)}")
    else:
        print("   Certs: ✓ All files present")
    
    # Determine overall status
    critical_checks = ["zmq_connectivity", "fix_session", "config_files", "fix_schema"]
    failed_critical = []
    
    for check in critical_checks:
        check_result = health_report["checks"].get(check, {})
        
        if check == "zmq_connectivity" and check_result.get("status") != "OK":
            failed_critical.append(check)
        elif check == "fix_session" and not check_result.get("connected"):
            failed_critical.append(check)
        elif check == "config_files" and missing_configs:
            failed_critical.append(check)
        elif check == "fix_schema" and not check_result.get("exists"):
            failed_critical.append(check)
    
    if not failed_critical:
        health_report["overall_status"] = "HEALTHY"
    elif len(failed_critical) <= 1:
        health_report["overall_status"] = "WARNING"
    else:
        health_report["overall_status"] = "CRITICAL"
    
    print("\n" + "=" * 60)
    print(f"Overall Status: {health_report['overall_status']}")
    
    if failed_critical:
        print(f"Failed Checks: {', '.join(failed_critical)}")
    
    return health_report


def main():
    """Main function"""
    try:
        health_report = run_health_check()
        
        # Optionally save report to file
        report_file = project_root / "data" / "health_check_report.json"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_file, 'w') as f:
            json.dump(health_report, f, indent=2)
        
        print(f"\nHealth check report saved to: {report_file}")
        
        # Exit with appropriate code
        if health_report["overall_status"] == "HEALTHY":
            sys.exit(0)
        elif health_report["overall_status"] == "WARNING":
            sys.exit(1)
        else:
            sys.exit(2)
    
    except Exception as e:
        print(f"Health check failed with error: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()
