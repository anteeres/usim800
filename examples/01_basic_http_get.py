"""
Example 01: Basic HTTP GET Request

Simple example showing how to send a single HTTP GET request
using the backward-compatible API.
"""

from usim800 import sim800

# Initialize (baudrate 9600 for your STM32 hat setup)
gsm = sim800(baudrate=9600, path="/dev/ttyUSB0")

# Configure APN (change to your operator's APN)
gsm.requests.APN = "www"  # Example: "internet", "web.gprs.mtnnigeria.net", etc.

# Send GET request
print("Sending HTTP GET request...")
status = gsm.requests.get(url="http://httpbin.org/get")

# Access response
r = gsm.requests
print(f"Status Code: {r.status_code}")
print(f"IP Address: {r.IP}")
print(f"Content Length: {len(r.content)} bytes")
print(f"Response Text:\n{r.text}")

# Close connection
gsm.close()
