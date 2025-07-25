#!/usr/bin/env python3
"""
Test Order Sender
Sends test orders to the ZMQ order listener for testing
"""

import json
import time
import zmq
from datetime import datetime, date, timedelta
from decimal import Decimal


def create_test_order(order_id: str, symbol: str = "SPXW", side: str = "BUY", quantity: int = 10) -> dict:
    """Create a test order"""
    # Calculate expiry date (next Friday)
    today = date.today()
    days_ahead = 4 - today.weekday()  # Friday is 4
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    expiry_date = today + timedelta(days=days_ahead)
    
    order = {
        "order_id": order_id,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "price": 4150.50 if side == "BUY" else 4151.00,
        "order_type": "LIMIT",
        "time_in_force": "DAY",
        "account": "TEST_ACCOUNT",
        "strike_price": 4150.0,
        "expiry_date": expiry_date.strftime("%Y-%m-%d"),
        "option_type": "CALL",
        "client_order_id": f"CLI_{order_id}",
        "text": "Test order from order sender",
        "timestamp": datetime.utcnow().isoformat(),
        "source": "test_sender"
    }
    
    return order


def send_orders(host: str = "localhost", port: int = 5555, num_orders: int = 5):
    """Send test orders to the order adapter"""
    # Create ZMQ context and socket
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    
    try:
        # Connect to order adapter
        socket.connect(f"tcp://{host}:{port}")
        print(f"Connected to order adapter at tcp://{host}:{port}")
        
        # Send test orders
        for i in range(num_orders):
            order_id = f"TEST_{datetime.now().strftime('%H%M%S')}_{i:03d}"
            side = "BUY" if i % 2 == 0 else "SELL"
            quantity = 10 + (i * 5)
            
            order = create_test_order(order_id, side=side, quantity=quantity)
            
            # Send order as JSON
            message = json.dumps(order)
            socket.send_string(message)
            
            print(f"Sent order {i+1}/{num_orders}: {order_id} - {side} {quantity} SPXW")
            
            # Small delay between orders
            time.sleep(0.5)
        
        print(f"Successfully sent {num_orders} test orders")
        
    except Exception as e:
        print(f"Error sending orders: {e}")
    
    finally:
        socket.close()
        context.term()


def send_spxw_put_order():
    """Send a specific SPXW PUT order"""
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    
    try:
        socket.connect("tcp://localhost:5555")
        
        order = {
            "order_id": f"PUT_{datetime.now().strftime('%H%M%S')}",
            "symbol": "SPXW",
            "side": "SELL",
            "quantity": 25,
            "price": 15.25,
            "order_type": "LIMIT",
            "time_in_force": "DAY",
            "account": "TEST_ACCOUNT",
            "strike_price": 4100.0,
            "expiry_date": (date.today() + timedelta(days=7)).strftime("%Y-%m-%d"),
            "option_type": "PUT",
            "text": "SPXW PUT test order",
            "timestamp": datetime.utcnow().isoformat(),
            "source": "manual_test"
        }
        
        message = json.dumps(order)
        socket.send_string(message)
        
        print(f"Sent SPXW PUT order: {order['order_id']}")
        print(f"Strike: ${order['strike_price']}, Price: ${order['price']}")
        
    except Exception as e:
        print(f"Error sending PUT order: {e}")
    
    finally:
        socket.close()
        context.term()


def send_market_order():
    """Send a market order for testing"""
    context = zmq.Context()
    socket = context.socket(zmq.PUSH)
    
    try:
        socket.connect("tcp://localhost:5555")
        
        order = {
            "order_id": f"MKT_{datetime.now().strftime('%H%M%S')}",
            "symbol": "SPXW",
            "side": "BUY",
            "quantity": 5,
            "order_type": "MARKET",
            "time_in_force": "IOC",
            "account": "TEST_ACCOUNT",
            "strike_price": 4200.0,
            "expiry_date": (date.today() + timedelta(days=14)).strftime("%Y-%m-%d"),
            "option_type": "CALL",
            "text": "Market order test",
            "timestamp": datetime.utcnow().isoformat(),
            "source": "market_test"
        }
        
        message = json.dumps(order)
        socket.send_string(message)
        
        print(f"Sent MARKET order: {order['order_id']}")
        print(f"Strike: ${order['strike_price']}, Quantity: {order['quantity']}")
        
    except Exception as e:
        print(f"Error sending market order: {e}")
    
    finally:
        socket.close()
        context.term()


def main():
    """Main function with menu"""
    print("TT FIX Order Adapter - Test Order Sender")
    print("=" * 50)
    print("1. Send 5 test orders")
    print("2. Send 10 test orders")
    print("3. Send SPXW PUT order")
    print("4. Send market order")
    print("5. Send custom batch")
    print("0. Exit")
    
    while True:
        try:
            choice = input("\nEnter your choice (0-5): ").strip()
            
            if choice == "0":
                print("Exiting...")
                break
            elif choice == "1":
                send_orders(num_orders=5)
            elif choice == "2":
                send_orders(num_orders=10)
            elif choice == "3":
                send_spxw_put_order()
            elif choice == "4":
                send_market_order()
            elif choice == "5":
                try:
                    num = int(input("Enter number of orders to send: "))
                    if num > 0:
                        send_orders(num_orders=num)
                    else:
                        print("Number must be positive")
                except ValueError:
                    print("Invalid number")
            else:
                print("Invalid choice. Please enter 0-5.")
        
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
