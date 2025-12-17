"""
Example 05: Device Information

Example showing how to read device and network information.
"""

from usim800 import sim800

# Initialize
gsm = sim800(baudrate=9600, path="/dev/ttyUSB0")

print("=== SIM800 Device Information ===\n")

# Get all information at once
info = gsm.info.all()

print(f"IMEI:           {info.get('imei', 'N/A')}")
print(f"ICCID:          {info.get('iccid', 'N/A')}")
print(f"Firmware:       {info.get('module_version', 'N/A')}")
print(f"SIM Status:     {info.get('sim_status', 'N/A')}")
print(f"Operator:       {info.get('operator', 'N/A')}")
print(f"Signal (RSSI):  {info.get('rssi', 'N/A')}")
print(f"Signal (bars):  {info.get('signal_bars', 'N/A')}/5")

# Battery info
battery = info.get('battery')
if battery:
    percent, voltage = battery
    print(f"Battery:        {percent}% ({voltage:.2f}V)")
else:
    print(f"Battery:        N/A")

# Individual methods are also available:
print("\n=== Using Individual Methods ===")
print(f"IMEI: {gsm.info.getIMEI()}")
print(f"Signal bars: {gsm.info.getSignalBars()}/5")

# Close connection
gsm.close()
