"""
Power Management for SIM800

Handles:
- Sleep modes (AT+CSCLK)
- Functionality modes (AT+CFUN)
- Power down (AT+CPOWD)
"""
from __future__ import annotations

from .at import ATChannel
from .exceptions import PowerError


class Power:
    """
    Power and sleep management.
    
    Features:
    - CSCLK sleep modes (0=disable, 1=DTR, 2=automatic)
    - CFUN functionality modes (0=minimum, 1=full)
    - Power down command
    """
    
    def __init__(self, at: ATChannel):
        self.at = at

    def set_functionality(self, fun: int) -> None:
        """
        Set functionality mode (AT+CFUN).
        
        Args:
            fun: Functionality mode
                 0 = minimum functionality (RF off)
                 1 = full functionality
                 4 = disable phone transmit/receive
                 
        Raises:
            PowerError: If unsupported mode
        """
        if fun not in (0, 1, 4):
            raise PowerError(f"CFUN mode {fun} not supported")
        
        self.at.command(f"AT+CFUN={fun}", timeout_s=10)

    def set_sleep(self, mode: int) -> None:
        """
        Set sleep mode (AT+CSCLK).
        
        Args:
            mode: Sleep mode
                  0 = disable sleep
                  1 = sleep controlled by DTR pin (hardware)
                  2 = automatic sleep (no DTR required)
                  
        Raises:
            PowerError: If invalid mode
        """
        if mode not in (0, 1, 2):
            raise PowerError("CSCLK mode must be 0, 1 or 2")
        
        self.at.command(f"AT+CSCLK={mode}", timeout_s=5)

    def enable_auto_sleep(self) -> None:
        """
        Enable automatic sleep mode (CSCLK=2).
        
        Modem will automatically enter sleep to save power.
        Library will wake it before each command.
        """
        self.set_sleep(2)

    def disable_sleep(self) -> None:
        """Disable sleep mode (CSCLK=0)."""
        self.set_sleep(0)

    def power_down(self, urgent: bool = False) -> None:
        """
        Power down the module (AT+CPOWD).
        
        Args:
            urgent: If True, use urgent power down (mode 0)
                   If False, use normal power down (mode 1)
        
        Note:
            Module might power off before responding.
        """
        mode = 0 if urgent else 1
        try:
            self.at.command(f"AT+CPOWD={mode}", timeout_s=5, expect_ok=False)
        except:
            pass  # Module might power off before responding

    def minimum_functionality(self) -> None:
        """
        Set minimum functionality (RF off).
        
        Useful for power saving while keeping module responsive.
        """
        self.set_functionality(0)

    def full_functionality(self) -> None:
        """Set full functionality (normal operation)."""
        self.set_functionality(1)
