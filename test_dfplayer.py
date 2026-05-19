import serial
import time

# Initialize UART
uart = serial.Serial("/dev/ttyAMA0", baudrate=9600, timeout=1)

def send_command(command, parameter1=0, parameter2=0):
    version = 0xFF
    length = 0x06
    feedback = 0x00 # 0x00 = No feedback, 0x01 = Feedback requested
    
    # Calculate checksum: 0 - (version + length + command + feedback + param1 + param2)
    checksum = 0 - (version + length + command + feedback + parameter1 + parameter2)
    
    # Split the 16-bit checksum into two 8-bit bytes
    checksum_high = (checksum >> 8) & 0xFF
    # Python handles negative bitwise shifts gracefully like this
    checksum_low = checksum & 0xFF
    
    # Construct the full 10-byte packet
    query = bytearray([
        0x7E,          # Start Byte
        version,       # Version
        length,        # Data Length (always 6 bytes after this)
        command,       # Command
        feedback,      # Feedback byte
        parameter1,    # Parameter High Byte
        parameter2,    # Parameter Low Byte
        checksum_high, # Checksum High Byte
        checksum_low,  # Checksum Low Byte
        0x03,          # Some modules prefer 0xEF, others accept 0x03 as End Byte. Let's stick to standard 0xEF below
    ])
    # Correction for strict standard compatibility:
    query[9] = 0xEF    # End Byte
    
    uart.write(query)

print("Waiting for DFPlayer to boot...")
time.sleep(2)  # Give it an extra second just in case

# Set volume (0 to 30)
print("Setting volume...")
send_command(0x06, 0, 20)
time.sleep(0.5) # Give the DFPlayer processing breathing room

# Play track 1
print("Sending play command for Track 0001...")
send_command(0x03, 0, 1)

# KEEP THE SCRIPT ALIVE
# Without this loop, the script terminates and closes the serial line immediately!
try:
    print("Playing Track 0001... Press Ctrl+C to stop.")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping script.")
