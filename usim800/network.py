"""
Network Management for SIM800

Handles:
- Network registration (CREG/CGREG)
- Signal quality (CSQ)
- Operator selection
- IMEI/ICCID reading
- SIM status check
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Optional

from .at import ATChannel
from .exceptions import NetworkError


@dataclass
class SignalQuality:
    """Signal quality information."""
    rssi: int  # Received Signal Strength Indicator (0-31, 99=unknown)
    ber: int   # Bit Error Rate (0-7, 99=unknown)

    def rssi_dbm_estimate(self) -> Optional[int]:
        """
        Estimate signal strength in dBm.
        
        GSM RSSI mapping (approximate):
        - 0 = -113 dBm or less
        - 31 = -51 dBm or more
        - 99 = unknown
        """
        if self.rssi == 99:
            return None
        return -113 + 2 * self.rssi
    
    def bars(self) -> int:
        """
        Get signal strength in "bars" (0-5).
        
        - 0 bars: No signal or unknown
        - 1 bar: Very weak
        - 2 bars: Weak
        - 3 bars: Fair
        - 4 bars: Good
        - 5 bars: Excellent
        """
        if self.rssi == 99 or self.rssi < 2:
            return 0
        elif self.rssi < 10:
            return 1
        elif self.rssi < 15:
            return 2
        elif self.rssi < 20:
            return 3
        elif self.rssi < 25:
            return 4
        else:
            return 5


class Network:
    """Network management and information."""
    
    def __init__(self, at: ATChannel):
        self.at = at

    def get_imei(self) -> str:
        """
        Get module IMEI number.
        
        Returns:
            IMEI string (15 digits)
            
        Raises:
            NetworkError: If IMEI cannot be read
        """
        # Try AT+CGSN (most common) and AT+GSN (fallback)
        for cmd in ("AT+CGSN", "AT+GSN"):
            try:
                resp = self.at.command(cmd, timeout_s=3, expect_ok=True)
                for line in resp.lines:
                    if line.isdigit() and len(line) >= 14:
                        return line
            except:
                continue
        
        raise NetworkError("Could not read IMEI")

    def get_iccid(self) -> str:
        """
        Get SIM card ICCID number.
        
        Returns:
            ICCID string
            
        Raises:
            NetworkError: If ICCID cannot be read
        """
        resp = self.at.command("AT+CCID", timeout_s=3)
        # Response: +CCID: 89860...
        for line in resp.lines:
            if line.startswith("+CCID"):
                return line.split(":")[-1].strip()
        
        raise NetworkError("Could not read ICCID")

    def sim_ready(self) -> bool:
        """
        Check if SIM card is ready.
        
        Returns:
            True if SIM is ready, False otherwise
        """
        try:
            resp = self.at.command("AT+CPIN?", timeout_s=3)
            return any("READY" in line for line in resp.lines)
        except:
            return False

    def get_signal(self) -> SignalQuality:
        """
        Get current signal quality.
        
        Returns:
            SignalQuality with RSSI and BER
            
        Raises:
            NetworkError: If signal quality cannot be read
        """
        resp = self.at.command("AT+CSQ", timeout_s=3)
        # Response: +CSQ: <rssi>,<ber>
        for line in resp.lines:
            if line.startswith("+CSQ:"):
                _, rest = line.split(":", 1)
                rssi_s, ber_s = [x.strip() for x in rest.split(",", 1)]
                return SignalQuality(rssi=int(rssi_s), ber=int(ber_s))
        
        raise NetworkError("Could not parse CSQ response")

    def wait_registered(
        self, 
        timeout_s: float = 60.0, 
        gprs: bool = False
    ) -> None:
        """
        Wait until registered on network.
        
        Args:
            timeout_s: Maximum time to wait
            gprs: If True, check GPRS registration (CGREG),
                  otherwise check circuit-switched (CREG)
        
        Raises:
            NetworkError: If not registered within timeout
        
        Notes:
            Accepts registration status 1 (home) or 5 (roaming).
        """
        cmd = "AT+CGREG?" if gprs else "AT+CREG?"
        deadline = time.time() + timeout_s
        
        while time.time() < deadline:
            try:
                resp = self.at.command(cmd, timeout_s=3, retries=1)
                for line in resp.lines:
                    if line.startswith("+CREG:") or line.startswith("+CGREG:"):
                        # Format: +CREG: n,stat or +CREG: stat
                        parts = re.split(r"[:,]", line)
                        parts = [p.strip() for p in parts if p.strip()]
                        stat = int(parts[-1])
                        
                        if stat in (1, 5):  # 1=home, 5=roaming
                            return
            except:
                pass
            
            time.sleep(1.0)
        
        raise NetworkError(f"Not registered on network (cmd={cmd}) within {timeout_s}s")
    
    def get_operator(self) -> Optional[str]:
        """
        Get current network operator name.
        
        Returns:
            Operator name or None if not available
        """
        try:
            # Try AT+COPS? first
            resp = self.at.command("AT+COPS?", timeout_s=5)
            for line in resp.lines:
                if line.startswith("+COPS:"):
                    # +COPS: <mode>,<format>,"<oper>"
                    match = re.search(r'"([^"]+)"', line)
                    if match:
                        return match.group(1)
            
            # Fallback to AT+CSPN?
            resp = self.at.command("AT+CSPN?", timeout_s=5)
            for line in resp.lines:
                if line.startswith("+CSPN:"):
                    match = re.search(r'"([^"]+)"', line)
                    if match:
                        return match.group(1)
        except:
            pass
        
        return None
