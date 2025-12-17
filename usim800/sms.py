"""
SMS Management for SIM800

Features:
- Text mode send/read/list/delete
- Unicode-safe sending via UCS2 (text mode)
- Backward-compatible readAll()/deleteAllReadMsg() helpers
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import List, Optional

from .at import ATChannel
from .exceptions import SMSError


@dataclass
class SMSMessage:
    """SMS message structure."""
    index: int
    status: str
    sender: str
    timestamp: str
    text: str


def _try_decode_utf16_encoded_string(s):
    """
    Decode UTF-16 hex string if valid, otherwise return as-is.
    
    From original usim800 library (community contribution).
    """
    prepared = s.strip().lower()
    if len(prepared) % 4 != 0:
        return s
    for c in prepared:
        if c not in '0123456789abcdef':
            return s
    
    # It is a UTF-16 encoded string, decode it
    result_str = ''
    for i in range(len(prepared) // 4):
        decoded_char = chr(int(prepared[i*4:(i+1)*4], 16))
        result_str += decoded_char
    return result_str


def _parse_cmgl_response(cmgl_response_str):
    """
    Parse AT+CMGL response.
    
    From original usim800 library (community contribution).
    Handles multiple SMS entries with proper parsing.
    """
    ENTRY_HEADLINE_PREFIX = '+CMGL: '
    result_dict = {}
    curr_entry = None
    
    for line in cmgl_response_str.replace('\r', '\n').split('\n'):
        if line.startswith(ENTRY_HEADLINE_PREFIX):
            # New entry starts - save previous
            if curr_entry is not None:
                result_dict[curr_entry[0]] = curr_entry
                curr_entry = None
            
            # Parse headline: +CMGL: ID,"STATUS","NUMBER",,"DATETIME"
            headline_fields = line.split(',"')
            if len(headline_fields) != 5:
                continue
            
            headline_fields = [f.strip('"') for f in headline_fields]
            msg_id = headline_fields[0][len(ENTRY_HEADLINE_PREFIX):]
            
            curr_entry = headline_fields
            curr_entry[0] = msg_id
            curr_entry.append('')  # Body text
        else:
            # Body line
            if curr_entry is None:
                continue
            if line.strip() == '':
                continue
            if line.strip().lower() == 'ok':
                break
            
            # Add text to current entry
            curr_entry[-1] += _try_decode_utf16_encoded_string(line) + '\n'
    
    # Add last entry
    if curr_entry is not None:
        result_dict[curr_entry[0]] = curr_entry
    
    return result_dict


class SMS:
    """
    SMS text-mode helper.
    
    Features:
    - send() - Send SMS
    - readAll() - Read all messages (from original lib)
    - list_messages() - List messages by status
    - read() - Read specific message
    - delete() - Delete message
    - deleteAllReadMsg() - Delete all read messages (from original lib)
    """

    def __init__(self, at: ATChannel):
        self.at = at

    def text_mode(self) -> None:
        """Set SMS text mode."""
        self.at.command("AT+CMGF=1", timeout_s=5)

    def _needs_ucs2(self, text: str) -> bool:
        """Return True if text contains non-GSM-7 characters (rough heuristic)."""
        try:
            text.encode("gsm0338")  # type: ignore[attr-defined]
            return False
        except Exception:
            # Python doesn't ship gsm0338 codec by default; fallback heuristic
            return any(ord(ch) > 127 for ch in text)

    def _set_charset(self, charset: str) -> None:
        """Set TE character set."""
        self.at.command(f'AT+CSCS="{charset}"', timeout_s=5)

    def set_new_message_indication(self, mode: int = 2, mt: int = 1) -> None:
        """
        Configure new SMS indication URC.
        
        Common: AT+CNMI=2,1,0,0,0 -> +CMTI on new SMS.
        """
        self.at.command(f"AT+CNMI={mode},{mt},0,0,0", timeout_s=5)

    def send(self, number: str, text: str, timeout_s: float = 60.0) -> bool:
        """
        Send SMS in text mode.
        
        Args:
            number: Phone number
            text: Message text
            timeout_s: Timeout
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            self.text_mode()

            # If message contains non-ASCII, use UCS2 text mode.
            # This is widely supported on SIM800 for Unicode SMS.
            use_ucs2 = self._needs_ucs2(text) or self._needs_ucs2(number)
            if use_ucs2:
                self._set_charset("UCS2")
                number_to_send = number.encode("utf-16-be").hex().upper()
                text_bytes = text.encode("utf-16-be").hex().upper().encode("ascii")
            else:
                self._set_charset("GSM")
                number_to_send = number
                text_bytes = text.encode("ascii", errors="ignore")
            
            with self.at.lock.acquire():
                self.at.write_raw(self.at.sleep_wake_char)
                time.sleep(self.at.sleep_wake_delay_s)

                cmd = f'AT+CMGS="{number_to_send}"\r\n'.encode("ascii", errors="ignore")
                self.at.write_raw(cmd)

                # Wait for '>' prompt
                deadline = time.time() + 10.0
                got_prompt = False
                
                while time.time() < deadline:
                    chunk = self.at.ser.read(self.at.ser.in_waiting or 1)
                    if chunk:
                        if b">" in chunk:
                            got_prompt = True
                            break
                    else:
                        time.sleep(0.05)
                
                if not got_prompt:
                    raise SMSError("No '>' prompt from AT+CMGS")

                # Send body + Ctrl+Z
                body = text_bytes + b"\x1A"
                self.at.write_raw(body)

                # Wait for OK/ERROR
                resp = self.at._read_until_terminal(timeout_s=timeout_s)
                self.at._raise_if_error("AT+CMGS", resp)
            
            return True
            
        except Exception as e:
            if self.at.logger:
                self.at.logger.error(f"SMS send failed: {e}")
            return False

    def readAll(self, index=None):
        """
        Read all SMS messages.
        
        Original implementation from usim800 library (community contribution).
        
        Returns:
            Dictionary of messages: {msg_id: [id, status, sender, "", timestamp, text]}
        """
        try:
            self.text_mode()

            # Use the robust ATChannel reader (handles timeouts, locking, errors)
            resp = self.at.command('AT+CMGL="ALL"', timeout_s=20, expect_ok=True)
            raw_text = resp.raw.decode(errors="ignore")
            return _parse_cmgl_response(raw_text)

        except Exception as e:
            if self.at.logger:
                self.at.logger.error(f"readAll failed: {e}")
            return {}

    def list_messages(self, status: str = "ALL") -> List[SMSMessage]:
        """
        List messages using AT+CMGL.
        
        Args:
            status: "ALL", "REC UNREAD", "REC READ", "STO UNSENT", "STO SENT"
            
        Returns:
            List of SMSMessage objects
        """
        self.text_mode()
        resp = self.at.command(f'AT+CMGL="{status}"', timeout_s=10, expect_ok=True)
        return self._parse_cmgl(resp.lines)

    def read(self, index: int) -> SMSMessage:
        """
        Read specific SMS message.
        
        Args:
            index: Message index
            
        Returns:
            SMSMessage
            
        Raises:
            SMSError: If message not found
        """
        self.text_mode()
        resp = self.at.command(f"AT+CMGR={index}", timeout_s=10, expect_ok=True)
        msgs = self._parse_cmgr(resp.lines, index=index)
        
        if not msgs:
            raise SMSError(f"No SMS at index {index}")
        
        return msgs[0]

    def delete(self, index: int, delflag: int = 0) -> None:
        """
        Delete SMS message.
        
        Args:
            index: Message index
            delflag: Delete flag (0=delete index only, 1=delete all read, etc.)
        """
        self.text_mode()
        self.at.command(f"AT+CMGD={index},{delflag}", timeout_s=10)

    def deleteAllReadMsg(self, index=None):
        """
        Delete all read messages. Leave unread and outgoing messages untouched.
        
        Original implementation from usim800 library (community contribution).
        
        Args:
            index: Index of any existing message (speeds up operation)
        """
        try:
            # API requires an index, so read all if not provided
            if index is None:
                msgs = self.readAll()
                if len(msgs) == 0:
                    return
                index = list(msgs.keys())[0]
            
            if not isinstance(index, str):
                index = str(index)
            
            cmd = f"AT+CMGD={index},1"
            self.at.command(cmd, timeout_s=10)
            
        except Exception as e:
            if self.at.logger:
                self.at.logger.error(f"deleteAllReadMsg failed: {e}")

    # ---------------- parsing helpers ----------------

    def _parse_cmgl(self, lines: list[str]) -> List[SMSMessage]:
        """Parse AT+CMGL response lines."""
        out: List[SMSMessage] = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            if line.startswith("+CMGL:"):
                # +CMGL: <index>,"<stat>","<oa>",,"<scts>"
                match = re.search(
                    r'\+CMGL:\s*(\d+),\"([^\"]+)\",\"([^\"]*)\".*\"([^\"]*)\"', 
                    line
                )
                idx = int(match.group(1)) if match else -1
                stat = match.group(2) if match else ""
                sender = match.group(3) if match else ""
                ts = match.group(4) if match else ""
                
                text = ""
                if i + 1 < len(lines) and \
                   not lines[i + 1].startswith("+CMGL:") and \
                   lines[i + 1] not in ("OK", "ERROR"):
                    text = lines[i + 1]
                    i += 1
                
                out.append(SMSMessage(
                    index=idx, 
                    status=stat, 
                    sender=sender, 
                    timestamp=ts, 
                    text=text
                ))
            i += 1
        
        return out

    def _parse_cmgr(self, lines: list[str], index: int) -> List[SMSMessage]:
        """Parse AT+CMGR response lines."""
        out: List[SMSMessage] = []
        header = None
        text = ""
        
        for line in lines:
            if line.startswith("+CMGR:"):
                header = line
            elif line not in ("OK", "ERROR") and not line.startswith("+"):
                text = line
        
        if header:
            match = re.search(
                r'\+CMGR:\s*\"([^\"]+)\",\"([^\"]*)\".*\"([^\"]*)\"', 
                header
            )
            stat = match.group(1) if match else ""
            sender = match.group(2) if match else ""
            ts = match.group(3) if match else ""
            
            out.append(SMSMessage(
                index=index, 
                status=stat, 
                sender=sender, 
                timestamp=ts, 
                text=text
            ))
        
        return out
