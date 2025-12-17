from usim800.Parser.ATParser import Parser
from usim800.Parser import JsonParser
from usim800.Communicate import communicate

import time
import re


class request(communicate):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._status_code = None
        self._json = None
        self._text = None
        self._content = None
        self._url = None
        self._IP = None
        self._APN = None

    def init(self):
        self._status_code = None
        self._json = None
        self._text = None
        self._content = None
        self._url = None
        self._IP = None

    @property
    def text(self):
        return self._text

    @property
    def content(self):
        return self._content

    @property
    def json(self):
        return self._json

    @property
    def status_code(self):
        return self._status_code

    @property
    def IP(self):
        return self._IP

    @property
    def APN(self):
        return self._APN

    @APN.setter
    def APN(self, APN):
        self._APN = APN

    @property
    def url(self):
        return self._url

    # ------------------------------------------------------------------
    # Bearer & HTTP helpers
    # ------------------------------------------------------------------

    def _bearer(self, apn=None):
        if apn:
            self._APN = apn
        if not self._APN:
            raise ValueError("APN is not set on request object")

        # CONTYPE / APN
        self._send_cmd('AT+SAPBR=3,1,"CONTYPE","GPRS"')
        self._send_cmd(f'AT+SAPBR=3,1,"APN","{self._APN}"')

        # Otvori bearer
        self._send_cmd("AT+SAPBR=1,1")
        data = self._send_cmd("AT+SAPBR=2,1", return_data=True)

        if data:
            # očekivani format: +SAPBR: 1,1,"10.123.45.67"
            m = re.search(rb'"([^"]+)"', data)
            if m:
                self._IP = m.group(1).decode(errors="ignore")

        return self._IP

    def _close_bearer(self):
        self._send_cmd("AT+SAPBR=0,1")

    def _http_init(self):
        # best effort cleanup
        self._send_cmd("AT+HTTPTERM")
        self._send_cmd("AT+HTTPINIT")
        self._send_cmd('AT+HTTPPARA="CID",1')

    def _http_term(self):
        self._send_cmd("AT+HTTPTERM")

    # ------------------------------------------------------------------
    # Internnal GET/POST for session
    # ------------------------------------------------------------------

    def _http_get_internal(self, url, header=None):
        self._url = url

        # URL
        self._send_cmd(f'AT+HTTPPARA="URL","{url}"')

        if header:
            header_str = "\\r\\n".join(f"{k}: {v}" for k, v in header.items())
            self._send_cmd(f'AT+HTTPPARA="USERDATA","{header_str}"')

        # HTTPACTION=0 (GET)
        self._send_cmd("AT+HTTPACTION=0")
        time.sleep(2)

        self._send_cmd("AT+HTTPREAD", get_decode_data=True)
        data = self._getdata(
            data_to_decode=[],
            string_to_decode=None,
            till=b"\n",
            count=2,
            counter=0,
        )

        tk = Parser(data)
        token = tk.tokenizer()
        self._content = tk.parser

        if len(token) == 4:
            self._status_code = token[2]
            read_bytes = int(token[3])

            string = self._read_sent_data(read_bytes + 1000)
            tk2 = Parser(string)
            self._content = tk2.bytesparser
            self._text = tk2.parser

            jph = JsonParser.ATJSONObjectParser(string)
            self._json = jph.JSONObject

        return self._status_code

    def _http_post_internal(
        self,
        url,
        data,
        bytes_data=None,
        waittime=3000,
        content_type="application/json",
    ):

        self._url = url

        if isinstance(data, str):
            body = data.encode("utf-8")
        else:
            body = data

        if bytes_data is None:
            bytes_data = len(body)

        # URL + CONTENT-TYPE
        self._send_cmd(f'AT+HTTPPARA="URL","{url}"')
        self._send_cmd(f'AT+HTTPPARA="CONTENT","{content_type}"')

        # HTTPDATA
        cmd = f"AT+HTTPDATA={bytes_data},{waittime}"
        self._send_cmd(cmd)

        self._port.write(body)
        time.sleep(4)

        # HTTPACTION=1 (POST)
        self._send_cmd("AT+HTTPACTION=1")
        time.sleep(4)

        # HTTPREAD
        self._send_cmd("AT+HTTPREAD", get_decode_data=True)
        data_resp = self._getdata(
            data_to_decode=[],
            string_to_decode=None,
            till=b"\n",
            count=2,
            counter=0,
        )

        tk = Parser(data_resp)
        self._content = tk.parser
        token = tk.tokenizer()

        if len(token) == 4:
            self._status_code = token[2]
            read_bytes = int(token[3])
            string = self._read_sent_data(read_bytes + 1000)

            tk2 = Parser(string)
            self._content = tk2.bytesparser
            self._text = tk2.parser

            jph = JsonParser.ATJSONObjectParser(string)
            self._json = jph.JSONObject

        return self._status_code

    def get(self, url, header=None):
        self.init()
        self._IP = self._bearer(self._APN)
        self._http_init()
        try:
            return self._http_get_internal(url, header=header)
        finally:
            # cleanup
            self._http_term()
            self._close_bearer()

    def post(self, url, data, bytes_data, waittime=3000):
        self.init()
        self._IP = self._bearer(self._APN)
        self._http_init()
        try:
            return self._http_post_internal(
                url=url,
                data=data,
                bytes_data=bytes_data,
                waittime=waittime,
            )
        finally:
            self._http_term()
            self._close_bearer()
