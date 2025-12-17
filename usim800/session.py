"""
Session Management for SIM800

Provides robust session-based workflow with automatic cleanup.
"""
from __future__ import annotations

from dataclasses import dataclass

from .at import ATChannel
from .gprs import GPRS
from .http import HTTP
from .sms import SMS
from .network import Network
from .power import Power


@dataclass
class SessionConfig:
    """Session configuration."""
    apn: str
    cid: int = 1
    # Default: close bearer on exit (safer + consistent with README examples)
    keep_bearer_open: bool = False


class SIM800Session:
    """
    Session for robust multi-request workflow.
    
    Handles:
    - Automatic modem sync
    - Network registration
    - GPRS attachment
    - Bearer management
    - HTTP service lifecycle
    - Cleanup on exit
    
    Usage:
        with SIM800Session(at_channel, config) as session:
            resp1 = session.http.get("http://example.com/1")
            resp2 = session.http.get("http://example.com/2")
    """
    
    def __init__(self, at: ATChannel, cfg: SessionConfig):
        self.at = at
        self.cfg = cfg
        
        # Create module instances
        self.net = Network(at)
        self.gprs = GPRS(at, apn=cfg.apn, cid=cfg.cid)
        self.http = HTTP(at, cid=cfg.cid)
        self.sms = SMS(at)
        self.power = Power(at)

    def __enter__(self) -> 'SIM800Session':
        """
        Enter session context.
        
        Performs:
        1. Sync with modem
        2. Best-effort cleanup from previous run
        3. Wait for network registration
        4. Attach to GPRS
        5. Open bearer
        6. Initialize HTTP service
        """
        # Sync with modem
        self.at.sync()
        
        # Best-effort cleanup from previous run (crash recovery)
        try:
            self.http.term()
        except:
            pass
        
        try:
            self.at.command(
                f"AT+SAPBR=0,{self.cfg.cid}", 
                timeout_s=5, 
                expect_ok=False
            )
        except:
            pass
        
        # Wait for SIM ready
        if not self.net.sim_ready():
            raise Exception("SIM card not ready")
        
        # Wait for network registration
        self.net.wait_registered(timeout_s=60, gprs=False)
        
        # Attach to GPRS
        self.gprs.attach(timeout_s=30)
        
        # Wait for GPRS registration
        self.net.wait_registered(timeout_s=60, gprs=True)
        
        # Open bearer
        self.gprs.open()
        
        # Initialize HTTP service
        self.http.init()
        
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        """
        Exit session context.
        
        Performs cleanup:
        1. Terminate HTTP service
        2. Close bearer (if configured)
        """
        # Always terminate HTTP
        try:
            self.http.term()
        except:
            pass
        
        # Close bearer if configured
        if not self.cfg.keep_bearer_open:
            try:
                self.gprs.close()
            except:
                pass
