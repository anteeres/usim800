"""
Example 06: Sleep and Power Management

Example showing how to manage power and sleep modes.
Perfect for battery-powered IoT applications.
"""

from usim800 import sim800
import time

# Initialize
gsm = sim800(baudrate=9600, path="/dev/ttyUSB0")

print("=== Power Management Demo ===\n")

# ============================================
# AUTOMATIC SLEEP MODE
# ============================================
print("1. Enabling automatic sleep mode (CSCLK=2)")
gsm.power.enable_auto_sleep()
print("   ✓ Module will automatically sleep to save power")
print("   ✓ Library will wake it before each command")

# Test that module still works after sleep
time.sleep(5)  # Let it sleep
print("\n2. Testing module after sleep...")
imei = gsm.info.getIMEI()
print(f"   ✓ IMEI: {imei}")
print("   (Module woke up automatically!)")

# ============================================
# DISABLE SLEEP FOR HIGH-PERFORMANCE TASKS
# ============================================
print("\n3. Disabling sleep for intensive operations...")
gsm.power.disable_sleep()

# Do intensive operations here
gsm.requests.APN = "www"
print("   Sending HTTP request...")
status = gsm.requests.get(url="http://httpbin.org/get")
print(f"   ✓ Status: {gsm.requests.status_code}")

# ============================================
# MINIMUM FUNCTIONALITY MODE
# ============================================
print("\n4. Setting minimum functionality (RF off)...")
gsm.power.minimum_functionality()
print("   ✓ Radio off - low power mode")
print("   ✓ Module still responsive to AT commands")

time.sleep(2)

print("\n5. Restoring full functionality...")
gsm.power.full_functionality()
print("   ✓ Back to normal operation")

# ============================================
# POWER DOWN (UNCOMMENT TO TEST)
# ============================================
# print("\n6. Powering down module...")
# gsm.power.power_down(urgent=False)
# print("   ✓ Module powered down")

print("\n=== Demo Complete ===")
gsm.close()
