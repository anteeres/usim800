from usim800.Sms import sms
from usim800.Communicate import communicate
from usim800.Request import request
from usim800.Info import info
from usim800.session import Sim800Session

import serial

class sim800(communicate):
    TIMMEOUT = 1
    TIMEOUT = 1

    def __init__(self, baudrate, path):
        self.port = serial.Serial(path, baudrate, timeout=sim800.TIMMEOUT)
        super().__init__(self.port)
        self.requests = request(self.port)
        self.info = info(self.port)
        self.sms = sms(self.port)

    def session(self, apn, lockfile="/tmp/usim800.lock"):
        return Sim800Session(self, apn=apn, lockfile=lockfile)
