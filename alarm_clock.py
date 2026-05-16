import time
from datetime import datetime
from luma.core.interface.serial import spi, noop
from luma.led_matrix.device import max7219
from luma.core.render import canvas
from luma.core.legacy import text
from luma.core.legacy.font import proportional, CP437_FONT

# Setup SPI connection to MAX7219
serial = spi(port=0, device=0, gpio=noop())
device = max7219(serial, cascaded=4, block_orientation=90, rotate=0)

# Set brightness (0-15)
device.contrast(8)

print("Clock running...")

while True:
    now = datetime.now().strftime("%H:%M")
    
    with canvas(device) as draw:
        text(draw, (0, 0), now, fill="white", font=proportional(CP437_FONT))
    
    time.sleep(1)