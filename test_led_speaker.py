#!/usr/bin/env python
import time
import serial
from datetime import datetime

from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.legacy import text, show_message
from luma.core.legacy.font import proportional, CP437_FONT, TINY_FONT

# ─── ALARM SETTINGS ───────────────────────────────────────────────────────────
ALARM_HOUR   = 17
ALARM_MINUTE = 48
ALARM_DURATION_SECONDS = 20
# ──────────────────────────────────────────────────────────────────────────────

# Initialize UART for DFPlayer
uart = serial.Serial("/dev/ttyAMA0", baudrate=9600, timeout=1)

def send_command(command, parameter1=0, parameter2=0):
    version  = 0xFF
    length   = 0x06
    feedback = 0x00
    checksum = 0 - (version + length + command + feedback + parameter1 + parameter2)
    query = bytearray([
        0x7E,
        version,
        length,
        command,
        feedback,
        parameter1,
        parameter2,
        (checksum >> 8) & 0xFF,
        checksum & 0xFF,
        0xEF,
    ])
    uart.write(query)

def play_alarm():
    send_command(0x06, 0, 15)   # Set volume to 20
    time.sleep(0.5)
    send_command(0x03, 0, 1)    # Play track 0001
    time.sleep(ALARM_DURATION_SECONDS)
    send_command(0x16)          # Stop
    print("Alarm stopped.")

def minute_change(device):
    hours   = datetime.now().strftime('%H')
    minutes = datetime.now().strftime('%M')

    def helper(current_y):
        with canvas(device) as draw:
            text(draw, (0, 1),   hours,   fill="white", font=proportional(CP437_FONT))
            text(draw, (15, 1),  ":",     fill="white", font=proportional(TINY_FONT))
            text(draw, (17, current_y), minutes, fill="white", font=proportional(CP437_FONT))
        time.sleep(0.1)

    for y in range(1, 9): helper(y)
    minutes = datetime.now().strftime('%M')
    for y in range(9, 1, -1): helper(y)

def animation(device, from_y, to_y):
    hourstime = datetime.now().strftime('%H')
    mintime   = datetime.now().strftime('%M')
    current_y = from_y
    while current_y != to_y:
        with canvas(device) as draw:
            text(draw, (0, current_y),  hourstime, fill="white", font=proportional(CP437_FONT))
            text(draw, (15, current_y), ":",       fill="white", font=proportional(TINY_FONT))
            text(draw, (17, current_y), mintime,   fill="white", font=proportional(CP437_FONT))
        time.sleep(0.1)
        current_y += 1 if to_y > from_y else -1

def main():
    serial_iface = spi(port=0, device=0, gpio=noop())
    device = max7219(serial_iface, cascaded=4, block_orientation=-90, blocks_arranged_in_reverse_order=False)
    device.contrast(8)

    print("Waiting for DFPlayer to boot...")
    time.sleep(2)

    animation(device, 8, 1)

    alarm_fired = False
    toggle = False

    while True:
        now    = datetime.now()
        toggle = not toggle
        sec    = now.second

        # ── Alarm check ───────────────────────────────────────────────────────
        if now.hour == ALARM_HOUR and now.minute == ALARM_MINUTE and not alarm_fired:
            print("ALARM! Playing track...")
            alarm_fired = True
            play_alarm()  # blocks for ALARM_DURATION_SECONDS

        # Reset alarm_fired after the alarm minute has passed
        if not (now.hour == ALARM_HOUR and now.minute == ALARM_MINUTE):
            alarm_fired = False

        # ── Display logic ─────────────────────────────────────────────────────
        if sec == 59:
            minute_change(device)
        elif sec == 30:
            full_msg = time.ctime()
            animation(device, 1, 8)
            show_message(device, full_msg, fill="white", font=proportional(CP437_FONT))
            animation(device, 8, 1)
        else:
            hours   = now.strftime('%H')
            minutes = now.strftime('%M')
            with canvas(device) as draw:
                text(draw, (0, 1),  hours,                    fill="white", font=proportional(CP437_FONT))
                text(draw, (15, 1), ":" if toggle else " ",   fill="white", font=proportional(TINY_FONT))
                text(draw, (17, 1), minutes,                  fill="white", font=proportional(CP437_FONT))
            time.sleep(0.5)

if __name__ == "__main__":
    main()