# TT FIX 4.4 Order Adapter Server

A Python-based order adapter server for Trading Technologies (TT) FIX 4.4 protocol integration. This system handles SPXW options orders via ZeroMQ messaging and processes them through the TT FIX gateway.

## Project Structure

```
├── src/
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── tt_fix_adapter.py      # TT FIX gateway adapter
│   │   └── zmq_adapter.py         # ZeroMQ order listener
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Configuration management
│   │   ├── logger.py              # Logging setup
│   │   └── exceptions.py          # Custom exceptions
│   ├── models/
│   │   ├── __init__.py
│   │   ├── order.py               # Order data models
│   │   ├── fix_messages.py        # FIX message models
│   │   └── spxw_instruments.py    # SPXW options models
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── order_processor.py     # Order validation and processing
│   │   ├── fix_processor.py       # FIX message processing
│   │   └── risk_processor.py      # Risk management
│   ├── services/
│   │   ├── __init__.py
│   │   ├── order_listener.py      # ZMQ order listening service
│   │   ├── fix_gateway.py         # FIX gateway service
│   │   └── monitoring.py          # System monitoring
│   └── utils/
│       ├── __init__.py
│       ├── fix_utils.py           # FIX utility functions
│       ├── datetime_utils.py      # Date/time utilities
│       └── validation.py          # Validation utilities
├── tests/
│   ├── __init__.py
│   ├── test_order_processor.py
│   ├── test_fix_adapter.py
│   └── test_zmq_adapter.py
├── config/
│   ├── app_config.yaml            # Application configuration
│   ├── fix_config.cfg             # FIX session configuration
│   └── logging_config.yaml        # Logging configuration
├── scripts/
│   ├── start_server.py            # Main server startup script
│   ├── test_order_sender.py       # Test order sender
│   └── health_check.py            # Health check script
├── data/
│   ├── fix_store/                 # FIX message store
│   └── logs/                      # Log files
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
└── main.py                        # Application entry point
```

## Features

- **ZeroMQ Order Listening**: High-performance order ingestion via ZMQ
- **TT FIX 4.4 Integration**: Full FIX 4.4 protocol support for TT
- **SPXW Options Support**: Specialized handling for SPXW options contracts
- **Order Processing Pipeline**: Validation, risk checks, and order routing
- **Real-time Monitoring**: Comprehensive logging and monitoring
- **SSL/TLS Security**: Secure connections to TT FIX gateways
- **Error Handling**: Robust error handling and recovery mechanisms
- **Configuration Management**: Flexible YAML-based configuration

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Settings**:
   - Update `config/app_config.yaml` with your settings
   - Update `config/fix_config.cfg` with your TT credentials
   - Place your TT certificate in the root directory

3. **Start the Server**:
   ```bash
   python main.py
   ```

4. **Send Test Orders**:
   ```bash
   python scripts/test_order_sender.py
   ```

## Configuration

### Application Config (`config/app_config.yaml`)
```yaml
zmq:
  order_port: 5555
  bind_address: "tcp://*:5555"
  
fix:
  config_file: "config/fix_config.cfg"
  data_dictionary: "FIX_SCHEMA/UAT_TT-FIX44.xml"
  
trading:
  default_currency: "USD"
  default_exchange: "CBOE"
  risk_limits:
    max_order_size: 1000
    max_daily_volume: 10000
```

### FIX Config (`config/fix_config.cfg`)
Based on your existing TT UAT configuration with proper session settings.

## Order Message Format

Orders should be sent via ZMQ in JSON format:

```json
{
  "order_id": "ORD_12345",
  "symbol": "SPXW",
  "side": "BUY",
  "quantity": 10,
  "price": 4150.50,
  "order_type": "LIMIT",
  "time_in_force": "DAY",
  "strike_price": 4150.0,
  "expiry_date": "2025-01-31",
  "option_type": "CALL",
  "account": "TEST_ACCOUNT"
}
```

## Monitoring

The system provides comprehensive monitoring through:
- Structured logging with Loguru
- Order flow metrics
- FIX session status
- Error tracking and alerting

## Security

- SSL/TLS encryption for FIX connections
- Certificate-based authentication with TT
- Input validation and sanitization
- Risk management controls

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Adding New Order Types
1. Extend the order models in `src/models/order.py`
2. Update the processors in `src/processors/`
3. Add validation rules in `src/utils/validation.py`

### Debugging FIX Messages
Enable debug logging in `config/logging_config.yaml` to see full FIX message details.

## Production Deployment

- Use Docker containers for deployment
- Configure proper SSL certificates
- Set up monitoring and alerting
- Implement backup and recovery procedures
- Configure rate limiting and risk controls

## Support

For issues and questions:
1. Check the logs in `data/logs/`
2. Verify FIX session status
3. Test ZMQ connectivity
4. Review TT documentation for FIX specifications

## License

Proprietary - For internal use only