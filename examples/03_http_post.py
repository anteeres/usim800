"""
Example 03: HTTP POST Request

Example showing how to send JSON data via HTTP POST.
"""

from usim800 import sim800
import json

# Initialize
gsm = sim800(baudrate=9600, path="/dev/ttyUSB0")

# Configure APN
gsm.requests.APN = "www"

# Prepare JSON data
data = {
    "sensor": "temperature",
    "value": 23.5,
    "unit": "celsius",
    "timestamp": "2025-12-17T10:30:00Z"
}

# Send POST request
print("Sending HTTP POST request...")
status = gsm.requests.post(
    url="http://httpbin.org/post",
    data=json.dumps(data)
)

# Access response
r = gsm.requests
print(f"Status Code: {r.status_code}")
print(f"Response:\n{r.text}")

# Parse JSON response
try:
    response_json = r.json()
    print(f"\nParsed JSON: {response_json}")
except:
    print("Could not parse JSON response")

# Close connection
gsm.close()
