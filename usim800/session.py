from usim800.lock import sim800_lock


class Sim800Session:

    def __init__(self, device, apn, lockfile="/tmp/usim800.lock"):
        self.device = device        # instance sim800
        self.requests = device.requests
        self.apn = apn
        self.lockfile = lockfile
        self._lock_ctx = None

    # -------------------- internal helpers --------------------

    def _full_clean_state(self):
        c = self.device
        c._send_cmd("AT")
        c._send_cmd("ATE0")
        c._send_cmd("AT+CMEE=2")
        c._send_cmd("AT+CFUN=1")

        for cmd in ("AT+HTTPTERM", "AT+CIPSHUT", "AT+SAPBR=0,1"):
            try:
                c._send_cmd(cmd)
            except Exception:
                pass

    def _attach_gprs(self):
        self.device._send_cmd("AT+CGATT=1")

    # -------------------- context manager --------------------

    def __enter__(self):
        # lock na razini OS-a (inter-process)
        self._lock_ctx = sim800_lock(self.lockfile)
        self._lock_ctx.__enter__()

        # full clean
        self._full_clean_state()

        # attach + bearer + HTTPINIT
        self._attach_gprs()
        self.requests.APN = self.apn
        self.requests._bearer(self.apn)
        self.requests._http_init()

        return self

    def __exit__(self, exc_type, exc, tb):
        # pokušaj čistog shutdowna
        try:
            self.requests._http_term()
        except Exception:
            pass
        try:
            self.device._send_cmd("AT+SAPBR=0,1")
        except Exception:
            pass
        try:
            self.device._send_cmd("AT+CIPSHUT")
        except Exception:
            pass
        try:
            # RF off / low power; po želji možeš CSCLK=1
            self.device._send_cmd("AT+CFUN=0")
        except Exception:
            pass

        if self._lock_ctx is not None:
            self._lock_ctx.__exit__(exc_type, exc, tb)
