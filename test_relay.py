import time
from gpiozero import Button, OutputDevice
from signal import pause

time.sleep(1)
# 1. Initialize the Relay (GPIO 13)
# active_high=False maps relay.on() to pulling the GPIO pin LOW (matching the 'L' jumper)
relay = OutputDevice(13, active_high=False, initial_value=True)
# 2. Initialize the Button (GPIO 22)
# Uses internal pull-up resistor by default (expects button wired to GND)
button = Button(22, bounce_time=0.2)
# Global tracking variable for the motor state
motor_running = False
def toggle_motor():
    global motor_running

    if not motor_running:
        print("Button pressed: Turning motor ON")
        relay.on()
        motor_running = True
    else:
        print("Button pressed: Turning motor OFF")
        relay.off()
        motor_running = False

# Attach the toggle function to the button press event
time.sleep(0.5)
button.when_pressed = toggle_motor

try:
    print("System active! Press the button on GPIO 22 to toggle the motor.")
    print("Press Ctrl+C to exit safely.")

    # Keeps the script running in the background listening for events
    pause()
except KeyboardInterrupt:
    print("\nShutting down safely...")
    relay.off()
    print("Motor turned off. Goodbye!")

