"""
Device Information Module for SIM800

Provides access to device and network information:
- IMEI, ICCID, firmware version
- Signal strength (RSSI)
- SIM status
- Network operator
- Battery status
- GPS location (CIPGSMLOC)
"""
from __future__ import annotations

import re
from typing import Optional, Tuple

from .at import ATChannel
from .network import Network
from .exceptions import LocationError


class Info:
    """
    Device and network information.
    
    Provides methods to query various device parameters and status.
    """
    
    def __init__(self, at: ATChannel, network: Network):
        self.at = at
        self.network = network
        self._apn: Optional[str] = None

    @property
    def APN(self) -> Optional[str]:
        """Get configured APN."""
        return self._apn

    @APN.setter
    def APN(self, val: str):
        """Set APN for location services."""
        self._apn = val

    def getIMEI(self) -> Optional[str]:
        """
        Get module IMEI number.
        
        Returns:
            IMEI string or None on error
        """
        try:
            return self.network.get_imei()
        except Exception as e:
            if self.at.logger:
                self.at.logger.error(f"getIMEI failed: {e}")
            return None

    def getICCID(self) -> Optional[str]:
        """
        Get SIM ICCID number.
        
        Returns:
            ICCID string or None on error
        """
        try:
            return self.network.get_iccid()
        except Exception as e:
            if self.at.logger:
                self.at.logger.error(f"getICCID failed: {e}")
            return None

    def getModuleVersion(self) -> Optional[str]:
        """
        Get module firmware version.
        
        Returns:
            Firmware version string or None on error
        """
        try:
            cmd = "AT+CGMR"
            resp = self.at.command(cmd, timeout_s=3, expect_ok=True)
            
            for line in resp.lines:
                if "Revision" in line:
                    # Example: Revision:1418B05SIM800L24
                    parts = line.split(":")
                    if len(parts) >= 2:
                        return parts[1].strip()
            
            return None
            
        except Exception as e:
            if self.at.logger:
                self.at.logger.error(f"getModuleVersion failed: {e}")
            return None

    def checkSim(self) -> Optional[str]:
        """
        Check SIM card status.
        
        Returns:
            Status string ("READY", "SIM PIN", etc.) or None on error
        """
        try:
            cmd = "AT+CMEE=2"  # Enable extended error codes
            self.at.command(cmd, timeout_s=2, expect_ok=False)
            
            cmd = "AT+CPIN?"
            resp = self.at.command(cmd, timeout_s=3, expect_ok=True)
            
            for line in resp.lines:
                if line.startswith("+CPIN:"):
                    status = line.split(":")[1].strip()
                    return status
            
            return None
            
        except Exception as e:
            if self.at.logger:
                self.at.logger.error(f"checkSim failed: {e}")
            return None

    def getRSSI(self) -> Optional[int]:
        """
        Get signal strength (RSSI).
        
        Returns:
            RSSI value (0-31, 99=unknown) or None on error
        """
        try:
            sig = self.network.get_signal()
            return sig.rssi
        except Exception as e:
            if self.at.logger:
                self.at.logger.error(f"getRSSI failed: {e}")
            return None

    def getSignalBars(self) -> Optional[int]:
        """
        Get signal strength as "bars" (0-5).
        
        Returns:
            Signal bars (0-5) or None on error
        """
        try:
            sig = self.network.get_signal()
            return sig.bars()
        except Exception as e:
            if self.at.logger:
                self.at.logger.error(f"getSignalBars failed: {e}")
            return None

    def getOperator(self) -> Optional[str]:
        """
        Get network operator name.
        
        Returns:
            Operator name or None on error
        """
        try:
            return self.network.get_operator()
        except Exception as e:
            if self.at.logger:
                self.at.logger.error(f"getOperator failed: {e}")
            return None

    def getCBC(self) -> Optional[Tuple[int, float]]:
        """
        Get battery status.
        
        Returns:
            Tuple of (battery_percent, voltage_V) or None on error
        """
        try:
            cmd = "AT+CBC"
            resp = self.at.command(cmd, timeout_s=3, expect_ok=True)
            
            for line in resp.lines:
                if line.startswith("+CBC:"):
                    # +CBC: <bcs>,<bcl>,<voltage>
                    # bcs: battery charge status (0=not charging, 1=charging, 2=charging done)
                    # bcl: battery charge level (1-100%)
                    # voltage: battery voltage in mV
                    parts = line.split(":")[1].split(",")
                    if len(parts) >= 3:
                        battery_percent = int(parts[1].strip())
                        voltage_mv = int(parts[2].strip())
                        voltage_v = voltage_mv / 1000.0
                        return (battery_percent, voltage_v)
            
            return None
            
        except Exception as e:
            if self.at.logger:
                self.at.logger.error(f"getCBC failed: {e}")
            return None

    def getLocation(self, apn: Optional[str] = None) -> Optional[Tuple[float, float]]:
        """
        Get location via CIPGSMLOC (cell-based positioning).
        
        Requires:
        - Active GPRS bearer
        - APN configured (via constructor or parameter)
        
        Args:
            apn: APN to use (overrides self.APN)
            
        Returns:
            Tuple of (latitude, longitude) or None on error
            
        Note:
            This requires bearer to be open. If you're using session-based
            approach, call this within a session context.
        """
        try:
            # Use provided APN or stored APN
            apn_to_use = apn or self._apn
            if not apn_to_use:
                raise LocationError("APN not configured")
            
            # Query location
            cmd = "AT+CIPGSMLOC=1,1"
            resp = self.at.command(cmd, timeout_s=30, expect_ok=True)
            
            for line in resp.lines:
                if line.startswith("+CIPGSMLOC:"):
                    # +CIPGSMLOC: <loccode>,<longitude>,<latitude>,<date>,<time>
                    parts = [p.strip() for p in line.split(":")[1].split(",")]
                    
                    if len(parts) >= 3:
                        loccode = int(parts[0])
                        
                        if loccode != 0:
                            raise LocationError(f"CIPGSMLOC error code {loccode}")
                        
                        longitude = float(parts[1])
                        latitude = float(parts[2])
                        
                        return (latitude, longitude)
            
            return None
            
        except Exception as e:
            if self.at.logger:
                self.at.logger.error(f"getLocation failed: {e}")
            return None

    def all(self) -> dict:
        """
        Get all device information as dictionary.
        
        Returns:
            Dictionary with all available information
        """
        info = {}
        
        info['imei'] = self.getIMEI()
        info['iccid'] = self.getICCID()
        info['module_version'] = self.getModuleVersion()
        info['sim_status'] = self.checkSim()
        info['rssi'] = self.getRSSI()
        info['signal_bars'] = self.getSignalBars()
        info['operator'] = self.getOperator()
        info['battery'] = self.getCBC()
        
        return info
