# usim800

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/)

**Robust Python driver for SIM800/SIM800L GSM/GPRS modules**

This is a **fork** of the original [usim800](https://github.com/Bhagyarsh/usim800) library, enhanced with:
- **Thread & process locking** - Safe for concurrent access
- **Proper error handling** - Comprehensive exception hierarchy
- **Sleep/wake support** - CSCLK=2 automatic sleep with wake-before-command
- **Network error recovery** - Automatic retry on transient errors
- **HTTP improvements** - URC waiting, DOWNLOAD prompt detection, binary-safe parsing
- **Backward compatible API** - Existing code works without changes

---

## Quick Start

```python
from usim800 import sim800

# Initialize (9600 baud for RPi + STM32 hat)
gsm = sim800(baudrate=9600, path="/dev/ttyUSB0")

# Configure APN
gsm.requests.APN = "www"  # Change to your operator's APN

# Send HTTP GET request
gsm.requests.get(url="http://httpbin.org/get")

# Access response
print(f"Status: {gsm.requests.status_code}")
print(f"IP: {gsm.requests.IP}")
print(f"Content: {gsm.requests.text}")

# Send SMS
gsm.sms.send("+1234567890", "Hello from SIM800!")

# Close connection
gsm.close()
```

---

## Features

### HTTP Requests
- GET and POST methods
- JSON support
- Custom headers
- Automatic bearer management
- Binary-safe response parsing
- HTTP error handling (601/603/604)
- Retry logic on transient errors

### SMS
- Send SMS (text mode)
- Read all messages (`readAll()`)
- Delete messages
- UTF-16 encoded message support

### Device Information
- IMEI, ICCID, firmware version
- Signal strength (RSSI, bars)
- SIM status
- Network operator
- Battery status
- Cell-based location (CIPGSMLOC)

### Power Management
- Automatic sleep mode (CSCLK=2)
- Wake-before-command
- Minimum functionality mode
- Power down

### Concurrency
- Thread-safe operations
- Process lock (prevents multiple Python processes from corrupting state)
- Reentrant lock support

---

## Examples

### Example 1: Multiple HTTP Requests

Perfect for sending multiple requests without repeatedly opening/closing bearer.

```python
from usim800 import sim800

gsm = sim800(baudrate=9600, path="/dev/ttyUSB0")

# Session-based approach
with gsm.session(apn="www") as sess:
    # Bearer opened once for all requests
    resp1 = sess.http.get("http://example.com/api/1")
    resp2 = sess.http.get("http://example.com/api/2")
    resp3 = sess.http.get("http://example.com/api/3")
    resp4 = sess.http.get("http://example.com/api/4")
    # Bearer closed automatically

gsm.close()
```

### Example 2: HTTP POST with JSON

```python
from usim800 import sim800
import json

gsm = sim800(baudrate=9600, path="/dev/ttyUSB0")
gsm.requests.APN = "www"

data = {"temperature": 23.5, "humidity": 65}
gsm.requests.post(
    url="http://your-server.com/api/data",
    data=json.dumps(data)
)

print(f"Status: {gsm.requests.status_code}")
gsm.close()
```

### Example 3: SMS Read and Send

```python
from usim800 import sim800

gsm = sim800(baudrate=9600, path="/dev/ttyUSB0")

# Send SMS
gsm.sms.send("+1234567890", "Hello!")

# Read all messages
messages = gsm.sms.readAll()
for msg_id, msg in messages.items():
    print(f"From: {msg[2]}, Text: {msg[5]}")

# Delete all read messages
if messages:
    first_id = list(messages.keys())[0]
    gsm.sms.deleteAllReadMsg(index=first_id)

gsm.close()
```

### Example 4: Device Information

```python
from usim800 import sim800

gsm = sim800(baudrate=9600, path="/dev/ttyUSB0")

info = gsm.info.all()
print(f"IMEI: {info['imei']}")
print(f"Signal: {info['signal_bars']}/5 bars")
print(f"Operator: {info['operator']}")
print(f"Battery: {info['battery'][0]}%")

gsm.close()
```

### Example 5: Power Management

```python
from usim800 import sim800

gsm = sim800(baudrate=9600, path="/dev/ttyUSB0")

# Enable automatic sleep (saves power)
gsm.power.enable_auto_sleep()

# Module will wake automatically before each command
imei = gsm.info.getIMEI()  # Works even after sleep!

# Disable sleep for intensive operations
gsm.power.disable_sleep()

gsm.close()
```

---

## Hardware Setup

### Raspberry Pi + STM32 Hat

This library is optimized for Raspberry Pi with STM32 hat configurations where:
- Raspberry Pi GPIO pins connect to STM32 hat
- SIM800 module connects via header to the hat
- Serial communication at 9600 baud

**Typical setup:**
```
Raspberry Pi → STM32 Hat → SIM800 Module Header
    (GPIO)      (routing)      (AT commands)
```

**Serial port:** Usually `/dev/ttyUSB0`, `/dev/ttyS0`, or `/dev/ttyAMA0`

---

## API Reference

### Main Class: `sim800`

```python
sim800(baudrate, path, timeout=1.0, lockfile="/tmp/usim800.lock", logger=None)
```

**Parameters:**
- `baudrate`: Serial baudrate (9600, 115200, etc.)
- `path`: Serial port path (`/dev/ttyUSB0`, etc.)
- `timeout`: Serial read timeout (default: 1.0s)
- `lockfile`: Path to lock file for process locking
- `logger`: Optional logging.Logger instance

### HTTP API (`gsm.requests`)

**Properties:**
- `APN`: Get/set APN (required for HTTP)
- `status_code`: Last response status code (string)
- `content`: Last response body (bytes)
- `text`: Last response body (text)
- `IP`: Assigned IP address
- `url`: Last request URL

**Methods:**
- `get(url, header=None)` → status code
- `post(url, data, waittime=4000, headers=None)` → status code
- `json()` → Parsed JSON response

### SMS API (`gsm.sms`)

**Methods:**
- `send(number, text, timeout_s=60)` → bool
- `readAll(index=None)` → dict of messages
- `list_messages(status="ALL")` → List[SMSMessage]
- `read(index)` → SMSMessage
- `delete(index, delflag=0)`
- `deleteAllReadMsg(index=None)`

### Info API (`gsm.info`)

**Methods:**
- `getIMEI()` → IMEI string
- `getICCID()` → ICCID string
- `getModuleVersion()` → Firmware version
- `checkSim()` → SIM status
- `getRSSI()` → Signal strength (0-31)
- `getSignalBars()` → Signal bars (0-5)
- `getOperator()` → Operator name
- `getCBC()` → (battery_percent, voltage_V)
- `getLocation(apn)` → (latitude, longitude)
- `all()` → dict with all info

### Power API (`gsm.power`)

**Methods:**
- `enable_auto_sleep()` - Enable CSCLK=2
- `disable_sleep()` - Disable sleep
- `set_sleep(mode)` - Set sleep mode (0/1/2)
- `set_functionality(fun)` - Set CFUN (0=min, 1=full)
- `minimum_functionality()` - RF off
- `full_functionality()` - Normal operation
- `power_down(urgent=False)` - Power off module

### Advanced: Session API

```python
with gsm.session(apn="www", keep_bearer_open=False) as sess:
    resp1 = sess.http.get("http://example.com/1")
    resp2 = sess.http.get("http://example.com/2")
```

**Benefits:**
- Bearer opened once for all requests
- Automatic cleanup on exit
- Network error recovery
- More efficient for multiple operations

---

## Troubleshooting

### "Permission denied" on serial port

```bash
sudo usermod -a -G dialout $USER
# Log out and log back in
```

### Module not responding

1. Check power supply (SIM800 needs 3.4-4.4V, 2A peak)
2. Check antenna connection
3. Verify serial port: `ls -l /dev/ttyUSB*`
4. Test with minicom: `minicom -D /dev/ttyUSB0 -b 9600`

### HTTP requests timing out

1. Check signal strength: `gsm.info.getRSSI()` (should be > 10)
2. Verify APN is correct for your operator
3. Check SIM card has data plan
4. Try increasing timeout: `resp = sess.http.get(url, timeout_s=180)`

### SMS not sending

1. Check SIM status: `gsm.info.checkSim()` (should be "READY")
2. Verify phone number format (+1234567890)
3. Check signal strength
4. Some SIMs require PIN - use AT+CPIN command

---

## Thread Safety

This library is **thread-safe** and **process-safe**:

```python
# Multiple threads can safely use the same instance
import threading

def worker():
    gsm.requests.get("http://example.com")

threads = [threading.Thread(target=worker) for _ in range(10)]
for t in threads:
    t.start()
```

Process lock prevents corruption if multiple Python processes access the same SIM800.

---

## Performance

**Typical timings @ 9600 baud:**
- HTTP GET request: 5-10 seconds
- HTTP POST request: 6-12 seconds
- SMS send: 5-15 seconds
- Network registration: 10-30 seconds

**Session-based requests are ~40% faster** (bearer reuse).

---

## Acknowledgments

This library is a fork of the excellent [usim800](https://github.com/Bhagyarsh/usim800) by [Bhagyarsh Dhumal](https://github.com/Bhagyarsh).

**Original features** retained:
- Simple API design
- HTTP GET/POST support
- SMS functionality
- `readAll()` SMS parser (community contribution)

**Enhancements added:**
- Production-ready error handling
- Thread + process locking
- Sleep/wake support (CSCLK=2)
- Network error recovery
- HTTP retry logic
- Binary-safe response parsing
- Comprehensive documentation

---

## License

MIT License - see [LICENSE](LICENSE) file

---

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

---

## Support

- **Original library:** https://github.com/Bhagyarsh/usim800
- **This fork:** https://github.com/anteeres/usim800
- **Issues:** https://github.com/anteeres/usim800/issues
