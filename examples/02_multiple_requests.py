"""
Example 02: Multiple HTTP GET Requests (Your Use Case)

Optimized for sending 4 GET requests efficiently.
This example uses the session-based approach for better performance.
"""

from usim800 import sim800

# Initialize with your baudrate
gsm = sim800(baudrate=9600, path="/dev/ttyUSB0")

urls = [
    "http://your-server.com/api/sensor1",
    "http://your-server.com/api/sensor2",
    "http://your-server.com/api/sensor3",
    "http://your-server.com/api/sensor4",
]

print("Sending 4 GET requests...")

# Option 1: Simple approach (opens/closes bearer for each request)
# -----------------------------------------------------------
# Good for: One-time operations, testing
# gsm.requests.APN = "www"
# 
# for i, url in enumerate(urls, 1):
#     print(f"\n[{i}/4] Requesting: {url}")
#     status = gsm.requests.get(url=url)
#     print(f"  Status: {gsm.requests.status_code}")
#     print(f"  Response: {gsm.requests.text[:100]}...")  # First 100 chars

# Option 2: Session-based approach (MORE EFFICIENT!)
# -----------------------------------------------------------
# Good for: Multiple requests, production use
# Opens bearer once, sends all requests, then closes
with gsm.session(apn="www") as sess:
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/4] Requesting: {url}")
        try:
            resp = sess.http.get(url, timeout_s=60)
            print(f"  Status: {resp.status_code}")
            print(f"  Response: {resp.text[:100]}...")  # First 100 chars
        except Exception as e:
            print(f"  ERROR: {e}")

print("\n✓ All requests completed!")

# Optional: Send SMS notification when done
# gsm.sms.send("+1234567890", "4 GET requests completed successfully!")

# Close connection
gsm.close()
