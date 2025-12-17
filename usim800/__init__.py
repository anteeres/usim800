"""
usim800 - Robust Python driver for SIM800 GSM/GPRS module

Fork of: https://github.com/Bhagyarsh/usim800
Enhanced with production-ready features:
- Thread and process locking
- Proper error handling
- Sleep/wake support
- Network error recovery
- HTTP with retry logic
- SMS with readAll support

Usage:
    from usim800 import sim800
    
    gsm = sim800(baudrate=9600, path="/dev/ttyUSB0")
    gsm.requests.APN = "www"
    gsm.requests.get(url="http://example.com")
    print(gsm.requests.status_code)
"""

from .sim800 import sim800
from .exceptions import (
    SIM800Error,
    ATTimeoutError,
    ATError,
    NetworkError,
    GPRSError,
    HTTPError,
    SMSError,
    LocationError,
    PowerError,
)

__version__ = "1.0.0"
__author__ = "Fork maintainer (based on Bhagyarsh Dhumal's original)"
__all__ = [
    "sim800",
    "SIM800Error",
    "ATTimeoutError",
    "ATError",
    "NetworkError",
    "GPRSError",
    "HTTPError",
    "SMSError",
    "LocationError",
    "PowerError",
]
