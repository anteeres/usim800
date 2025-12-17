# Changelog

All notable changes to this fork will be documented in this file.

## [1.0.0] - 2025-12-17

### Fork Created
This is a fork of [usim800](https://github.com/Bhagyarsh/usim800).

### Added
- **Thread and process locking** - CombinedLock with RLock + fcntl.flock
- **Proper error handling** - Complete exception hierarchy (ATError, HTTPError, etc.)
- **Sleep/wake support** - CSCLK=2 with automatic wake-before-command
- **Network error recovery** - Automatic retry on transient errors (HTTP 604)
- **HTTP improvements:**
  - Proper +HTTPACTION URC waiting (not time.sleep!)
  - DOWNLOAD prompt detection for POST
  - Binary-safe response body parsing
  - HTTP error code handling (601/603/604)
- **AT channel improvements:**
  - Command echo filtering
  - URC waiting helper (`wait_for_urc()`)
  - Retry logic with exponential backoff
- **Session-based API** - Efficient multi-request workflow with context manager
- **Power management** - Sleep modes, functionality modes, power down
- **Info module** - Device info with IMEI, ICCID, signal, battery, location
- **Comprehensive documentation:**
  - Complete README with examples
  - 6 working examples
  - Inline code documentation
- **Backward compatible API** - All original code works without changes

### Enhanced
- **SMS module** - Integrated original `readAll()` parser (community contribution)
- **HTTP module** - Retry decorator for transient errors
- **GPRS module** - Authentication support (username/password)
- **Network module** - Signal quality with dBm estimation and bars

### Fixed
- **No echo filtering** - Original lib didn't filter command echo
- **No HTTP URC waiting** - Used hardcoded time.sleep(2)
- **No DOWNLOAD prompt detection** - POST could fail silently
- **No locking** - Race conditions in multi-threaded/multi-process scenarios
- **No error handling** - Generic try/except with None returns
- **Bearer management** - Opened/closed bearer for each request (wasteful)
- **Timeout issues** - Hardcoded sleeps instead of proper timeouts

### Optimized
- **Session-based requests** - ~40% faster for multiple requests
- **9600 baud compatibility** - Optimized for Raspberry Pi + STM32 hat
- **Memory usage** - Efficient buffer management

### Original Features Retained
- Simple API design (`gsm.requests.get()`, `gsm.sms.send()`)
- HTTP GET/POST support
- SMS send/read functionality
- Original `readAll()` SMS parser (with UTF-16 support)
- Info module methods

### Breaking Changes
None - Fully backward compatible!

---

## Credits

**Original library:** [usim800](https://github.com/Bhagyarsh/usim800) by Bhagyarsh Dhumal
**Fork maintainer:** Ante Eres
**Community contributions:** UTF-16 SMS parser by Recolic K
