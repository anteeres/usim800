import serial
import time
import re
import json

class communicate:

    cmd_list = []

    def __init__(self, port):
        self._port = port

    def _setcmd(self, cmd, end='\r\n'):
        return cmd + end

    def _readtill(self, till="OK", timeout=5.0):
        buf = b""
        start = time.time()
        while True:
            chunk = self._port.read(1)
            if chunk:
                buf += chunk
                try:
                    text = buf.decode(errors="ignore")
                except Exception:
                    text = ""
                if till in text or "ERROR" in text:
                    return buf
            else:
                if time.time() - start > timeout:
                    return buf

    def _send_cmd(
        self,
        cmd,
        t=0.1,
        bytes=14816,
        return_data=False,
        printio=False,
        get_decode_data=False,
        read=True,
    ):
        out = self._setcmd(cmd)
        if printio:
            print(">>", out.strip())
        self._port.write(out.encode("ascii", errors="ignore"))

        data = None

        if read:
            if t:
                time.sleep(t)

            if get_decode_data:
                data = None
            else:
                data = self._port.read(bytes)
                if printio and data:
                    try:
                        print("<<", data.decode(errors="ignore"))
                    except Exception:
                        print("<<", data)

        if return_data:
            return data

    def _read_sent_data(self, size, t=0.1):
        if t:
            time.sleep(t)
        return self._port.read(size)

    def _getdata(
        self,
        data_to_decode=None,
        string_to_decode=None,
        till=b"\n",
        count=2,
        counter=0,
        timeout=5.0,
    ):
        if data_to_decode is None:
            data_to_decode = []

        occurrences = counter
        start = time.time()

        while True:
            rcv = self._port.read(1)
            if not rcv:
                if time.time() - start > timeout:
                    break
                else:
                    continue

            data_to_decode.append(rcv)

            if rcv == till:
                occurrences += 1
                if occurrences >= count:
                    break

        return b"".join(data_to_decode)
