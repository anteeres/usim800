"""
Robust AT Command Channel for SIM800

Key features:
- Thread + process locking
- Command echo filtering
- URC (Unsolicited Result Code) detection
- Timeout and retry support
- Sleep/wake handling (CSCLK=2)
- CME/CMS error parsing
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Iterable, Optional

import serial

from .exceptions import ATError, ATTimeoutError, ATCommandErrorDetails
from .locks import CombinedLock


_CME_RE = re.compile(r"\+CME ERROR:\s*(\d+)")
_CMS_RE = re.compile(r"\+CMS ERROR:\s*(\d+)")


@dataclass
class ATResponse:
    """
    Parsed AT command response.
    
    lines: Response lines (without echo, with terminal OK/ERROR)
    raw: Raw bytes received
    """
    lines: list[str]
    raw: bytes

    def text(self) -> str:
        """Get response as text (lines joined)."""
        return "\n".join(self.lines)


class ATChannel:
    """
    Robust AT command channel over serial port.
    
    Features:
    - Thread + process locking
    - Line-oriented reads
    - URC-safe operations
    - Echo filtering
    - Sleep wake support
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 1.0,
        lockfile: str | None = "/tmp/usim800.lock",
        logger=None,
    ):
        self.ser = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
        self.lock = CombinedLock(lockfile=lockfile)
        self.logger = logger

        # Sleep wake strategy for CSCLK=2
        self.sleep_wake_char = b"\r"
        self.sleep_wake_delay_s = 0.15  # >=100ms recommended

    def close(self) -> None:
        """Close serial port."""
        self.ser.close()

    # ---------------------------
    # Low-level IO helpers
    # ---------------------------

    def write_raw(self, data: bytes) -> None:
        """Write raw bytes to serial port."""
        self.ser.write(data)

    def _read_until_terminal(
        self,
        timeout_s: float,
        terminals: Iterable[str] = ("OK", "ERROR"),
        cmd_sent: Optional[str] = None,
    ) -> ATResponse:
        """
        Read lines until we see one of 'terminals' or timeout.
        
        Filters command echo if cmd_sent is provided.
        """
        deadline = time.time() + timeout_s
        raw = bytearray()
        lines: list[str] = []
        echo_filtered = False

        while time.time() < deadline:
            chunk = self.ser.readline()
            if not chunk:
                continue
            
            raw.extend(chunk)
            line = chunk.decode(errors="ignore").strip()
            
            if not line:
                continue
            
            # Filter command echo (first non-empty line)
            if cmd_sent and not echo_filtered:
                # Echo can be full command or without AT prefix
                if line == cmd_sent or line == cmd_sent.replace("AT", "").strip():
                    echo_filtered = True
                    continue
            
            lines.append(line)
            
            # Check for terminal
            if line in terminals:
                return ATResponse(lines=lines, raw=bytes(raw))
            
            # Some commands end with "+CME ERROR:" / "+CMS ERROR:" before ERROR
            if "ERROR" in line and line != "OK":
                return ATResponse(lines=lines, raw=bytes(raw))

        raise ATTimeoutError(f"Timeout waiting for terminals {terminals}")

    def _raise_if_error(self, cmd: str, resp: ATResponse) -> None:
        """Check if response contains error and raise exception."""
        text = resp.text()
        
        if "ERROR" in resp.lines or \
           any(l.startswith("+CME ERROR") for l in resp.lines) or \
           any(l.startswith("+CMS ERROR") for l in resp.lines):
            
            cme = _CME_RE.search(text)
            cms = _CMS_RE.search(text)
            
            details = ATCommandErrorDetails(
                command=cmd,
                response=text,
                cme_code=int(cme.group(1)) if cme else None,
                cms_code=int(cms.group(1)) if cms else None,
            )
            raise ATError(details)

    def wait_for_urc(
        self, 
        prefix: str, 
        timeout_s: float,
    ) -> str:
        """
        Wait for specific URC (Unsolicited Result Code).
        
        Args:
            prefix: URC prefix to wait for (e.g., "+HTTPACTION:")
            timeout_s: Timeout in seconds
            
        Returns:
            Full URC line
            
        Raises:
            ATTimeoutError: If URC not received within timeout
        """
        deadline = time.time() + timeout_s
        
        with self.lock.acquire():
            while time.time() < deadline:
                line = self.ser.readline()
                if not line:
                    time.sleep(0.01)
                    continue
                
                decoded = line.decode("utf-8", errors="ignore").strip()
                if not decoded:
                    continue
                
                if decoded.startswith(prefix):
                    if self.logger:
                        self.logger.debug(f"URC << {decoded}")
                    return decoded
        
        raise ATTimeoutError(f"Timeout waiting for URC {prefix!r}")

    # ---------------------------
    # Public: send AT commands
    # ---------------------------

    def command(
        self,
        cmd: str,
        timeout_s: float = 5.0,
        expect_ok: bool = True,
        wake_if_needed: bool = True,
        retries: int = 0,
    ) -> ATResponse:
        """
        Send an AT command and wait for OK/ERROR.

        Args:
            cmd: AT command (without \\r\\n)
            timeout_s: Response timeout
            expect_ok: If True, raise error on ERROR response
            wake_if_needed: Send wake char first (for CSCLK=2)
            retries: Number of retries on timeout

        Returns:
            ATResponse with parsed lines

        Raises:
            ATTimeoutError: On timeout
            ATError: On ERROR response (if expect_ok=True)
        """
        cmd = cmd.strip()

        for attempt in range(retries + 1):
            with self.lock.acquire():
                if wake_if_needed:
                    # For CSCLK=2 auto-sleep: send dummy char, wait >=100ms
                    self.write_raw(self.sleep_wake_char)
                    time.sleep(self.sleep_wake_delay_s)

                wire = (cmd + "\r\n").encode("ascii", errors="ignore")
                if self.logger:
                    self.logger.debug("AT >> %s", cmd)
                
                self.write_raw(wire)
                
                try:
                    resp = self._read_until_terminal(
                        timeout_s=timeout_s,
                        cmd_sent=cmd
                    )
                except ATTimeoutError:
                    if attempt < retries:
                        if self.logger:
                            self.logger.warning(f"Retry {attempt + 1}/{retries} for {cmd}")
                        continue
                    raise

            if self.logger:
                self.logger.debug("AT << %s", resp.text())

            if expect_ok:
                self._raise_if_error(cmd, resp)

            return resp

        raise ATTimeoutError(f"Timeout sending {cmd!r}")

    def flush_input(self) -> None:
        """Discard anything currently in the RX buffer."""
        with self.lock.acquire():
            self.ser.reset_input_buffer()

    def sync(self) -> None:
        """
        Synchronize with modem.
        
        - Test with AT
        - Disable echo (ATE0)
        - Enable verbose errors (AT+CMEE=2)
        """
        self.command("AT", timeout_s=2, retries=2)
        self.command("ATE0", timeout_s=2)
        self.command("AT+CMEE=2", timeout_s=2)
