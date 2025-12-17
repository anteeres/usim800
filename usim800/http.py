"""
HTTP Client for SIM800

Robust HTTP implementation with:
- Proper +HTTPACTION URC waiting
- DOWNLOAD prompt detection for POST
- Binary-safe body parsing
- HTTP error code handling (601/603/604)
- Retry logic on transient errors
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Dict, Optional, Union
from functools import wraps

from .at import ATChannel
from .exceptions import HTTPError


@dataclass
class HTTPResponse:
    """HTTP response from SIM800."""
    status_code: int
    data: bytes

    @property
    def text(self) -> str:
        """Get response body as text."""
        return self.data.decode(errors="ignore")


def retry_on_http_error(max_retries=3, retry_codes=(604,), delay=5.0):
    """
    Decorator to retry HTTP operations on specific error codes.
    
    Args:
        max_retries: Maximum number of retries
        retry_codes: HTTP error codes to retry on (default: 604=stack busy)
        delay: Delay between retries in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(self, *args, **kwargs)
                except HTTPError as e:
                    last_error = e
                    if e.status_code not in retry_codes:
                        raise
                    if attempt < max_retries - 1:
                        if self.at.logger:
                            self.at.logger.warning(
                                f"HTTP error {e.status_code}, "
                                f"retry {attempt + 1}/{max_retries} after {delay}s"
                            )
                        time.sleep(delay)
                    else:
                        raise
            raise last_error
        return wrapper
    return decorator


class HTTP:
    """
    SIM800 HTTP client using AT+HTTP* commands.
    
    Usage:
        http = HTTP(at_channel, cid=1)
        http.init()
        response = http.get("http://example.com")
        http.term()
    """

    def __init__(self, at: ATChannel, cid: int = 1):
        self.at = at
        self.cid = cid

    def term(self) -> None:
        """
        Terminate HTTP service.
        
        Best-effort operation (does not raise on failure).
        """
        try:
            self.at.command("AT+HTTPTERM", timeout_s=5, expect_ok=False)
        except:
            pass

    def init(self) -> None:
        """
        Initialize HTTP service.
        
        Terminates any existing session first, then initializes new one.
        """
        self.term()  # Best-effort cleanup
        self.at.command("AT+HTTPINIT", timeout_s=5)
        self.at.command(f'AT+HTTPPARA="CID",{self.cid}', timeout_s=5)

    def set_headers(self, headers: Dict[str, str]) -> None:
        """
        Set custom HTTP headers via USERDATA parameter.
        
        Note: Not all SIM800 firmware versions support this.
        """
        if not headers:
            return
        
        header_blob = "\\r\\n".join([f"{k}: {v}" for k, v in headers.items()])
        self.at.command(f'AT+HTTPPARA="USERDATA","{header_blob}"', timeout_s=5)

    def _handle_http_error(self, status: int):
        """Handle HTTP error codes 600+."""
        if status == 601:
            raise HTTPError(
                "Network error (601) - bearer connection lost or network unreachable",
                status_code=status
            )
        elif status == 602:
            raise HTTPError(
                "No memory (602) - insufficient memory for operation",
                status_code=status
            )
        elif status == 603:
            raise HTTPError(
                "DNS error (603) - cannot resolve hostname",
                status_code=status
            )
        elif status == 604:
            raise HTTPError(
                "Stack busy (604) - HTTP stack is occupied",
                status_code=status
            )
        elif status == 606:
            raise HTTPError(
                "Timeout (606) - HTTP request timeout",
                status_code=status
            )
        else:
            raise HTTPError(
                f"HTTP stack error ({status})",
                status_code=status
            )

    def _read_http_body(self, expected_length: int) -> bytes:
        """
        Read HTTP response body from HTTPREAD.
        
        Binary-safe implementation that reads exact bytes.
        
        Args:
            expected_length: Expected body length in bytes
            
        Returns:
            Body bytes
        """
        if expected_length == 0:
            return b""

        # IMPORTANT: HTTPREAD is a multi-part response (header + raw bytes + OK).
        # Keep it atomic under the modem lock so that other commands/URCs can't
        # interleave and corrupt the byte stream.
        marker = b"+HTTPREAD:"
        crlf = b"\r\n"

        with self.at.lock.acquire():
            # Wake if needed (CSCLK=2)
            self.at.write_raw(self.at.sleep_wake_char)
            time.sleep(self.at.sleep_wake_delay_s)

            # Send HTTPREAD directly (avoid at.command(), we want full control)
            self.at.write_raw(b"AT+HTTPREAD\r\n")

            # Response format: +HTTPREAD: <len>\r\n<DATA>\r\nOK
            raw = bytearray()
            deadline = time.time() + 30.0

            # Read until we see the marker
            while time.time() < deadline and marker not in raw:
                chunk = self.at.ser.read(self.at.ser.in_waiting or 1)
                if chunk:
                    raw.extend(chunk)
                else:
                    time.sleep(0.01)

            if marker not in raw:
                raise HTTPError("Did not receive +HTTPREAD response")

            # Find end of header line
            marker_pos = raw.find(marker)
            first_crlf = raw.find(crlf, marker_pos)
            if first_crlf == -1:
                raise HTTPError("Malformed +HTTPREAD response")

            body_start = first_crlf + len(crlf)

            # Read until we have the full body
            while len(raw) < body_start + expected_length and time.time() < deadline:
                remaining = body_start + expected_length - len(raw)
                chunk = self.at.ser.read(min(remaining, 1024))
                if chunk:
                    raw.extend(chunk)
                else:
                    time.sleep(0.01)

            if len(raw) < body_start + expected_length:
                raise HTTPError(
                    f"HTTPREAD truncated: got {max(0, len(raw) - body_start)} of {expected_length} bytes"
                )

            body = bytes(raw[body_start:body_start + expected_length])

            # Drain trailing CRLF + OK/ERROR best-effort (do not block)
            _ = self.at.ser.read(self.at.ser.in_waiting or 0)

            return body

    def _action_and_read(
        self, 
        method: int, 
        read_timeout_s: float = 60.0
    ) -> HTTPResponse:
        """
        Execute HTTPACTION and read response.
        
        Args:
            method: 0=GET, 1=POST, 2=HEAD
            read_timeout_s: Timeout for waiting +HTTPACTION URC
            
        Returns:
            HTTPResponse with status and body
        """
        # Send HTTPACTION command
        self.at.command(f"AT+HTTPACTION={method}", timeout_s=5, expect_ok=True)
        
        # Wait for +HTTPACTION URC
        try:
            action_line = self.at.wait_for_urc(
                prefix="+HTTPACTION:",
                timeout_s=read_timeout_s
            )
        except Exception:
            raise HTTPError("Timeout waiting for +HTTPACTION")
        
        # Parse: +HTTPACTION: <method>,<status>,<length>
        match = re.search(r"\+HTTPACTION:\s*\d+,(\d+),(\d+)", action_line)
        if not match:
            raise HTTPError(f"Could not parse +HTTPACTION: {action_line}")
        
        status = int(match.group(1))
        length = int(match.group(2))
        
        # Handle HTTP error codes (600+)
        if status >= 600:
            self._handle_http_error(status)
        
        # HEAD request has no body
        if method == 2:
            return HTTPResponse(status_code=status, data=b"")
        
        # Read body if present
        if length == 0:
            return HTTPResponse(status_code=status, data=b"")
        
        body = self._read_http_body(length)
        return HTTPResponse(status_code=status, data=body)

    @retry_on_http_error(max_retries=3, retry_codes=(604,), delay=5.0)
    def get(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        timeout_s: float = 120.0
    ) -> HTTPResponse:
        """
        Execute HTTP GET request.
        
        Args:
            url: Full URL (http://...)
            headers: Optional custom headers
            timeout_s: Request timeout
            
        Returns:
            HTTPResponse
        """
        self.at.command(f'AT+HTTPPARA="URL","{url}"', timeout_s=5)
        
        if headers:
            self.set_headers(headers)
        
        return self._action_and_read(method=0, read_timeout_s=timeout_s)

    def head(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        timeout_s: float = 120.0
    ) -> HTTPResponse:
        """
        Execute HTTP HEAD request.
        
        Args:
            url: Full URL
            headers: Optional custom headers
            timeout_s: Request timeout
            
        Returns:
            HTTPResponse (empty body)
        """
        self.at.command(f'AT+HTTPPARA="URL","{url}"', timeout_s=5)
        
        if headers:
            self.set_headers(headers)
        
        return self._action_and_read(method=2, read_timeout_s=timeout_s)

    @retry_on_http_error(max_retries=3, retry_codes=(604,), delay=5.0)
    def post(
        self,
        url: str,
        data: Union[str, bytes],
        content_type: str = "application/json",
        headers: Optional[Dict[str, str]] = None,
        httpdata_timeout_ms: int = 10000,
        timeout_s: float = 120.0
    ) -> HTTPResponse:
        """
        Execute HTTP POST request.
        
        Args:
            url: Full URL
            data: Request body (str or bytes)
            content_type: Content-Type header
            headers: Optional custom headers
            httpdata_timeout_ms: HTTPDATA timeout (milliseconds)
            timeout_s: Request timeout
            
        Returns:
            HTTPResponse
        """
        if isinstance(data, str):
            body = data.encode("utf-8")
        else:
            body = data

        self.at.command(f'AT+HTTPPARA="URL","{url}"', timeout_s=5)
        self.at.command(f'AT+HTTPPARA="CONTENT","{content_type}"', timeout_s=5)
        
        if headers:
            self.set_headers(headers)

        # HTTPDATA with DOWNLOAD prompt detection (atomic operation)
        with self.at.lock.acquire():
            if self.at.logger:
                self.at.logger.debug(f"Sending HTTPDATA command, size={len(body)}")
            
            # Send HTTPDATA command
            cmd = f"AT+HTTPDATA={len(body)},{httpdata_timeout_ms}\r\n"
            self.at.write_raw(cmd.encode("ascii"))
            
            # Wait for DOWNLOAD prompt
            deadline = time.time() + (httpdata_timeout_ms / 1000.0 + 5.0)
            got_download = False
            
            while time.time() < deadline:
                chunk = self.at.ser.read(self.at.ser.in_waiting or 1)
                if chunk:
                    if b"DOWNLOAD" in chunk:
                        got_download = True
                        if self.at.logger:
                            self.at.logger.debug("Received DOWNLOAD prompt")
                        break
                else:
                    time.sleep(0.05)
            
            if not got_download:
                raise HTTPError("Did not receive DOWNLOAD prompt from modem")
            
            # Send body
            self.at.write_raw(body)
            
            if self.at.logger:
                self.at.logger.debug(f"Sent {len(body)} bytes of POST data")
            
            # Give modem time to process
            time.sleep(0.3)
            
            # Wait for OK from HTTPDATA
            resp = self.at._read_until_terminal(timeout_s=10)
            self.at._raise_if_error("AT+HTTPDATA", resp)
        
        # Now execute POST action
        return self._action_and_read(method=1, read_timeout_s=timeout_s)
