"""
Main SIM800 Device Facade

Provides backward-compatible API with original usim800 library
while using robust internal implementation.

Usage:
    gsm = sim800(baudrate=9600, path="/dev/ttyUSB0")
    gsm.requests.APN = "www"
    gsm.requests.get(url="http://example.com")
    print(gsm.requests.status_code)
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Optional

from .at import ATChannel
from .network import Network
from .gprs import GPRS
from .http import HTTP, HTTPResponse
from .sms import SMS
from .info import Info
from .power import Power
from .exceptions import SIM800Error


class RequestsWrapper:
    """
    Wrapper to provide backward-compatible requests API.
    
    Original API:
        gsm.requests.APN = "www"
        gsm.requests.get(url="http://...")
        r = gsm.requests
        print(r.status_code, r.content, r.IP)
    """
    
    def __init__(self, parent: 'sim800'):
        self._parent = parent
        self._apn: Optional[str] = None
        
        # Response attributes (backward compatible)
        self._status_code: Optional[str] = None
        self._content: Optional[bytes] = None
        self._text: Optional[str] = None
        self._json: Optional[list] = None
        self._url: Optional[str] = None
        self._ip: Optional[str] = None

    @property
    def APN(self) -> Optional[str]:
        """Get configured APN."""
        return self._apn

    @APN.setter
    def APN(self, apn: str):
        """Set APN for requests."""
        self._apn = apn

    @property
    def status_code(self) -> Optional[str]:
        """Get last response status code (as string for compatibility)."""
        return self._status_code

    @property
    def content(self) -> Optional[bytes]:
        """Get last response content (bytes)."""
        return self._content

    @property
    def text(self) -> Optional[str]:
        """Get last response as text."""
        return self._text

    @property
    def IP(self) -> Optional[str]:
        """Get assigned IP address from last request."""
        return self._ip

    @property
    def url(self) -> Optional[str]:
        """Get last request URL."""
        return self._url

    def json(self) -> Optional[list]:
        """
        Get last response as JSON.
        
        Returns list for compatibility with original implementation.
        """
        if self._json is not None:
            return self._json
        
        if self._content:
            import json
            try:
                parsed = json.loads(self._content)
                # Wrap in list for compatibility
                return [parsed] if not isinstance(parsed, list) else parsed
            except:
                return None
        
        return None

    def _init_response(self):
        """Reset response attributes."""
        self._status_code = None
        self._content = None
        self._text = None
        self._json = None
        self._url = None
        self._ip = None

    def _store_response(self, resp: HTTPResponse, url: str, ip: Optional[str]):
        """Store response for property access."""
        self._status_code = str(resp.status_code)
        self._content = resp.data
        self._text = resp.text
        self._url = url
        self._ip = ip

    def get(self, url: str, header=None) -> str:
        """
        Execute HTTP GET request.
        
        Args:
            url: Full URL
            header: Custom headers (not fully implemented in SIM800)
            
        Returns:
            Status code as string
        """
        self._init_response()
        
        if not self._apn:
            raise SIM800Error("APN not configured. Set gsm.requests.APN first.")
        
        # Open bearer and execute request
        gprs = GPRS(self._parent._at, apn=self._apn, cid=1)
        http = HTTP(self._parent._at, cid=1)
        
        try:
            # Ensure network ready
            self._parent._ensure_network_ready()
            
            # Open bearer
            gprs.attach(timeout_s=30)
            status = gprs.open()
            self._ip = status.ip
            
            # Execute HTTP request
            http.init()
            resp = http.get(url, timeout_s=120)
            
            # Store response
            self._store_response(resp, url, self._ip)
            
            # Cleanup
            http.term()
            gprs.close()
            
            return self._status_code
            
        except Exception as e:
            # Cleanup on error
            try:
                http.term()
            except:
                pass
            try:
                gprs.close()
            except:
                pass
            
            raise

    def post(self, url: str, data, waittime=4000, bytes_data=None, headers=None) -> str:
        """
        Execute HTTP POST request.
        
        Args:
            url: Full URL
            data: Request body (JSON string or bytes)
            waittime: HTTPDATA timeout in milliseconds
            bytes_data: Ignored (calculated automatically)
            headers: Custom headers
            
        Returns:
            Status code as string
        """
        self._init_response()
        
        if not self._apn:
            raise SIM800Error("APN not configured. Set gsm.requests.APN first.")
        
        # Open bearer and execute request
        gprs = GPRS(self._parent._at, apn=self._apn, cid=1)
        http = HTTP(self._parent._at, cid=1)
        
        try:
            # Ensure network ready
            self._parent._ensure_network_ready()
            
            # Open bearer
            gprs.attach(timeout_s=30)
            status = gprs.open()
            self._ip = status.ip
            
            # Execute HTTP request
            http.init()
            resp = http.post(
                url=url,
                data=data,
                httpdata_timeout_ms=waittime,
                timeout_s=120
            )
            
            # Store response
            self._store_response(resp, url, self._ip)
            
            # Cleanup
            http.term()
            gprs.close()
            
            return self._status_code
            
        except Exception as e:
            # Cleanup on error
            try:
                http.term()
            except:
                pass
            try:
                gprs.close()
            except:
                pass
            
            raise


class sim800:
    """
    Main SIM800 device interface.
    
    Provides backward-compatible API with original usim800 library.
    
    Usage:
        gsm = sim800(baudrate=9600, path="/dev/ttyUSB0")
        gsm.requests.APN = "www"
        gsm.requests.get("http://example.com")
        print(gsm.requests.status_code)
    """
    
    def __init__(
        self, 
        baudrate: int, 
        path: str,
        timeout: float = 1.0,
        lockfile: str | None = "/tmp/usim800.lock",
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize SIM800 device.
        
        Args:
            baudrate: Serial baudrate (9600, 115200, etc.)
            path: Serial port path (/dev/ttyUSB0, etc.)
            timeout: Serial read timeout
            lockfile: Path to lock file for process locking
            logger: Optional logger instance
        """
        # Create AT channel (owns the serial port)
        self._at = ATChannel(
            port=path,
            baudrate=baudrate,
            timeout=timeout,
            lockfile=lockfile,
            logger=logger
        )
        
        # Create modules
        self._network = Network(self._at)
        
        # Public API (backward compatible)
        self.requests = RequestsWrapper(self)
        self.sms = SMS(self._at)
        self.info = Info(self._at, self._network)
        self.power = Power(self._at)
        
        # Internal state
        self._initialized = False

    def _ensure_network_ready(self):
        """
        Ensure modem is synchronized and network is registered.
        
        Called automatically before network operations.
        """
        if not self._initialized:
            # Sync with modem
            self._at.sync()
            
            # Wait for SIM ready
            if not self._network.sim_ready():
                raise SIM800Error("SIM card not ready")
            
            # Wait for network registration
            self._network.wait_registered(timeout_s=60, gprs=False)
            
            self._initialized = True

    @contextmanager
    def session(self, apn: str, keep_bearer_open: bool = False):
        """
        Context manager for efficient multiple requests.
        
        Usage:
            with gsm.session(apn="www") as sess:
                resp1 = sess.http.get("http://example.com/1")
                resp2 = sess.http.get("http://example.com/2")
        
        Args:
            apn: APN for GPRS connection
            keep_bearer_open: If True, leave bearer open on exit
                            (useful for consecutive sessions)
        """
        from .session import SIM800Session, SessionConfig
        
        cfg = SessionConfig(apn=apn, cid=1, keep_bearer_open=keep_bearer_open)
        session = SIM800Session(self._at, cfg)
        
        try:
            session.__enter__()
            yield session
        finally:
            session.__exit__(None, None, None)

    def close(self):
        """Close serial port."""
        try:
            self._at.close()
        except:
            pass
