"""
usim800 Exception Classes

Complete exception hierarchy for SIM800 module errors.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


class SIM800Error(Exception):
    """Base exception for all usim800 library errors."""
    pass


class ATTimeoutError(SIM800Error):
    """Raised when an AT command or response times out."""
    pass


@dataclass
class ATCommandErrorDetails:
    """Details about AT command error."""
    command: str
    response: str
    cme_code: Optional[int] = None  # Mobile Equipment Error
    cms_code: Optional[int] = None  # Message Service Error


class ATError(SIM800Error):
    """Raised when modem returns ERROR or +CME/+CMS error."""
    
    def __init__(self, details: ATCommandErrorDetails):
        super().__init__(f"AT command failed: {details.command!r} -> {details.response!r}")
        self.details = details


class NetworkError(SIM800Error):
    """Network registration or radio errors."""
    pass


class GPRSError(SIM800Error):
    """GPRS bearer or PDP context errors."""
    pass


class HTTPError(SIM800Error):
    """HTTP stack errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class SMSError(SIM800Error):
    """SMS errors."""
    pass


class USSDError(SIM800Error):
    """USSD errors."""
    pass


class LocationError(SIM800Error):
    """Cell-based location/time errors."""
    pass


class PowerError(SIM800Error):
    """Power management or sleep errors."""
    pass
