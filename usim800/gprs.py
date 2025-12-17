"""
GPRS Bearer Management for SIM800

Handles GPRS attachment and bearer (SAPBR) configuration.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Optional

from .at import ATChannel
from .exceptions import GPRSError


@dataclass
class BearerStatus:
    """Bearer connection status."""
    cid: int              # Context ID
    status: int           # 0=connecting, 1=connected, 2=closing, 3=closed
    ip: Optional[str]     # Assigned IP address (if connected)


class GPRS:
    """
    GPRS bearer management using AT+SAPBR commands.
    
    Handles:
    - GPRS attachment (AT+CGATT)
    - Bearer configuration (APN, username, password)
    - Bearer open/close/query
    """

    def __init__(
        self, 
        at: ATChannel, 
        apn: str, 
        cid: int = 1,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        self.at = at
        self.apn = apn
        self.cid = cid
        self.username = username
        self.password = password

    def attach(self, timeout_s: float = 30.0) -> None:
        """
        Attach to GPRS packet service.
        
        Args:
            timeout_s: Maximum time to wait for attachment
            
        Raises:
            GPRSError: If cannot attach within timeout
        """
        deadline = time.time() + timeout_s
        
        while time.time() < deadline:
            try:
                self.at.command("AT+CGATT=1", timeout_s=5, retries=1)
                
                # Verify attachment
                resp = self.at.command("AT+CGATT?", timeout_s=3)
                if any("+CGATT: 1" in line for line in resp.lines):
                    return
            except:
                pass
            
            time.sleep(1.0)
        
        raise GPRSError("Could not attach to GPRS (AT+CGATT=1)")

    def open(self) -> BearerStatus:
        """
        Configure and open bearer connection.
        
        Returns:
            BearerStatus with connection details
            
        Raises:
            GPRSError: If bearer cannot be opened
        """
        # Configure bearer
        self.at.command(f'AT+SAPBR=3,{self.cid},"Contype","GPRS"', timeout_s=5)
        self.at.command(f'AT+SAPBR=3,{self.cid},"APN","{self.apn}"', timeout_s=5)
        
        # Add authentication if provided
        if self.username:
            self.at.command(
                f'AT+SAPBR=3,{self.cid},"USER","{self.username}"', 
                timeout_s=5
            )
        
        if self.password:
            self.at.command(
                f'AT+SAPBR=3,{self.cid},"PWD","{self.password}"', 
                timeout_s=5
            )
        
        # Open bearer (this can take 30-90 seconds on some networks)
        self.at.command(f"AT+SAPBR=1,{self.cid}", timeout_s=90, retries=1)
        
        return self.query()

    def query(self) -> BearerStatus:
        """
        Query bearer connection status.
        
        Returns:
            BearerStatus with current connection details
            
        Raises:
            GPRSError: If status cannot be queried
        """
        resp = self.at.command(f"AT+SAPBR=2,{self.cid}", timeout_s=10)
        
        # Response: +SAPBR: <cid>,<status>,"<ip>"
        # or: +SAPBR: <cid>,<status>
        for line in resp.lines:
            if line.startswith("+SAPBR:"):
                # Try with IP
                match = re.search(r'\+SAPBR:\s*(\d+),(\d+),\"([^\"]*)\"', line)
                if match:
                    cid = int(match.group(1))
                    status = int(match.group(2))
                    ip = match.group(3) or None
                    return BearerStatus(cid=cid, status=status, ip=ip)
                
                # Try without IP
                match = re.search(r"\+SAPBR:\s*(\d+),(\d+)", line)
                if match:
                    cid = int(match.group(1))
                    status = int(match.group(2))
                    return BearerStatus(cid=cid, status=status, ip=None)
        
        raise GPRSError("Could not parse SAPBR status")

    def close(self) -> None:
        """
        Close bearer connection.
        
        Best-effort operation (does not raise on failure).
        """
        try:
            self.at.command(f"AT+SAPBR=0,{self.cid}", timeout_s=20, retries=0)
        except:
            pass  # Best effort
