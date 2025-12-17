"""
Example 04: SMS Send and Read

Example showing how to send and read SMS messages.
"""

from usim800 import sim800

# Initialize
gsm = sim800(baudrate=9600, path="/dev/ttyUSB0")

# ============================================
# SEND SMS
# ============================================
print("=== Sending SMS ===")
recipient = "+1234567890"  # Replace with actual number
message = "Hello from usim800! Test message."

success = gsm.sms.send(recipient, message)
if success:
    print(f"✓ SMS sent to {recipient}")
else:
    print("✗ Failed to send SMS")

# ============================================
# READ ALL SMS
# ============================================
print("\n=== Reading All SMS ===")
messages = gsm.sms.readAll()

if messages:
    print(f"Found {len(messages)} message(s):\n")
    for msg_id, msg_data in messages.items():
        # msg_data format: [id, status, sender, "", timestamp, text]
        print(f"Message ID: {msg_data[0]}")
        print(f"  Status: {msg_data[1]}")
        print(f"  From: {msg_data[2]}")
        print(f"  Time: {msg_data[4]}")
        print(f"  Text: {msg_data[5]}")
        print()
else:
    print("No messages found")

# ============================================
# DELETE ALL READ MESSAGES
# ============================================
print("=== Cleaning up ===")
if messages:
    # Get first message ID for deleteAllReadMsg
    first_id = list(messages.keys())[0]
    gsm.sms.deleteAllReadMsg(index=first_id)
    print("✓ Deleted all read messages")

# Close connection
gsm.close()
