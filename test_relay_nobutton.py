from gpiozero import OutputDevice
import time

relay = OutputDevice(13, active_high=False, initial_value=True)

for i in range(2):
    print(f"Cycle {i+1}: Motor ON")
    relay.on()
    time.sleep(3)
    
    print(f"Cycle {i+1}: Motor OFF")
    relay.off()
    time.sleep(1)

print("Done")
