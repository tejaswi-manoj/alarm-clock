from gpiozero import Button
from signal import pause

# Define the GPIO pin your button is connected to
button = Button(22)

# Define actions for button events
button.when_pressed = lambda: print("Button was pressed!")
button.when_released = lambda: print("Button was released.")

# Keep the program running to listen for events
pause()

