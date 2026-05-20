#!/usr/bin/env python
import time
import serial
import threading
import json
import re
import numpy as np
from datetime import datetime
from gpiozero import Button

from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.legacy import text, show_message
from luma.core.legacy.font import proportional, CP437_FONT, TINY_FONT

import vosk
import sounddevice as sd
from scipy.signal import resample_poly

# ─── ALARM SETTINGS ───────────────────────────────────────────────────────────
ALARM_HOUR             = None
ALARM_MINUTE           = None
ALARM_DURATION_SECONDS = 20
# ──────────────────────────────────────────────────────────────────────────────

# --- DFPlayer setup ---
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
    print(f"Alarm started. Playing for {ALARM_DURATION_SECONDS} seconds...")
    
    # 1. Specify volume (0x06) to level 15
    send_command(0x06, 0, 15)
    time.sleep(0.2)
    
    # 2. Play the first track (0x03)
    send_command(0x03, 0, 1)
    
    # 3. Wait out the duration threshold
    time.sleep(ALARM_DURATION_SECONDS)
    
    # 4. Enforce Pause command (0x0E) - far more reliable than 0x16 Stop on DFPlayer
    print("Attempting to pause track...")
    send_command(0x0E) 
    time.sleep(0.1)
    
    # Double down: send Stop (0x16) immediately after to flush the buffer
    send_command(0x16)
    print("Alarm stopped.")

# --- Vosk setup ---
model = vosk.Model("vosk-model-small-en-us-0.15")
rec = vosk.KaldiRecognizer(model, 16000)

triggers = ["can you wake me up at", "can you get me up at", "can you set an alarm for", "wake me up at", "i want to get up at", "need to get up at",
            "i need to get up at", "set alarm for", "set an alarm for",
            "get me up at", "alarm at"]
hours_words = ["one","two","three","four","five","six","seven",
               "eight","nine","ten","eleven","twelve"]
minutes_words = [
    "", " oh one", " oh two", " oh three", " oh four", " oh five",
    " oh six", " oh seven", " oh eight", " oh nine", " ten", " eleven",
    " twelve", " thirteen", " fourteen", " fifteen", " sixteen", " seventeen",
    " eighteen", " nineteen", " twenty", " twenty one", " twenty two",
    " twenty three", " twenty four", " twenty five", " twenty six",
    " twenty seven", " twenty eight", " twenty nine", " thirty",
    " thirty one", " thirty two", " thirty three", " thirty four",
    " thirty five", " thirty six", " thirty seven", " thirty eight",
    " thirty nine", " forty", " forty one", " forty two", " forty three",
    " forty four", " forty five", " forty six", " forty seven", " forty eight",
    " forty nine", " fifty", " fifty one", " fifty two", " fifty three",
    " fifty four", " fifty five", " fifty six", " fifty seven", " fifty eight",
    " fifty nine"
]
periods = ["am", "pm"]

phrases = []
for trigger in triggers:
    for hour in hours_words:
        for minute in minutes_words:
            for period in periods:
                phrases.append(f"{trigger} {hour}{minute} {period}")
phrases.append("[unk]")
rec.SetGrammar(json.dumps(phrases))

HOUR_MAP   = {"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,
              "seven":7,"eight":8,"nine":9,"ten":10,"eleven":11,"twelve":12}
MINUTE_MAP = {
    "oh one":1, "oh two":2, "oh three":3, "oh four":4, "oh five":5,
    "oh six":6, "oh seven":7, "oh eight":8, "oh nine":9, "ten":10,
    "eleven":11, "twelve":12, "thirteen":13, "fourteen":14, "fifteen":15,
    "sixteen":16, "seventeen":17, "eighteen":18, "nineteen":19, "twenty":20,
    "twenty one":21, "twenty two":22, "twenty three":23, "twenty four":24,
    "twenty five":25, "twenty six":26, "twenty seven":27, "twenty eight":28,
    "twenty nine":29, "thirty":30, "thirty one":31, "thirty two":32,
    "thirty three":33, "thirty four":34, "thirty five":35, "thirty six":36,
    "thirty seven":37, "thirty eight":38, "thirty nine":39, "forty":40,
    "forty one":41, "forty two":42, "forty three":43, "forty four":44,
    "forty five":45, "forty six":46, "forty seven":47, "forty eight":48,
    "forty nine":49, "fifty":50, "fifty one":51, "fifty two":52,
    "fifty three":53, "fifty four":54, "fifty five":55, "fifty six":56,
    "fifty seven":57, "fifty eight":58, "fifty nine":59
}


def parse_time(text):
    period = "am" if "am" in text else "pm"

    hour = None
    matched_hour_word = None
    matched_hour_pos  = None
    for w in sorted(HOUR_MAP, key=len, reverse=True):
        m = re.search(rf'\b{w}\b', text)
        if m:
            hour = HOUR_MAP[w]
            matched_hour_word = w
            matched_hour_pos  = m.start()
            break

    minute = 0
    if matched_hour_pos is not None:
        text_after_hour = text[matched_hour_pos + len(matched_hour_word):]
        for w in sorted(MINUTE_MAP, key=len, reverse=True):
            if re.search(rf'\b{w}\b', text_after_hour):
                minute = MINUTE_MAP[w]
                break

    if hour is None:
        return None, None
    if period == "pm" and hour != 12:
        hour += 12
    if period == "am" and hour == 12:
        hour = 0
    return hour, minute  


def vosk_callback(indata, frames, time_info, status):
    global ALARM_HOUR, ALARM_MINUTE
    if not listening:
        return
    audio     = np.frombuffer(bytes(indata), dtype=np.int16).astype(np.float32)
    resampled = resample_poly(audio, up=1, down=3)
    resampled_bytes = resampled.astype(np.int16).tobytes()
    if rec.AcceptWaveform(resampled_bytes):
        result = json.loads(rec.Result())
        text   = result["text"]
        if text and text != "[unk]":
            hour, minute = parse_time(text)
            if hour is not None:
                ALARM_HOUR   = hour
                ALARM_MINUTE = minute
                print(f"Alarm set for {hour:02d}:{minute:02d}")
            else:
                print("Didn't understand the time, try again...")
        else:
            print("Didn't understand, try again...")

# --- LED display functions ---
def minute_change(device):
    hours   = datetime.now().strftime('%H')
    minutes = datetime.now().strftime('%M')

    def helper(current_y):
        with canvas(device) as draw:
            text(draw, (0, 1),          hours,   fill="white", font=proportional(CP437_FONT))
            text(draw, (15, 1),         ":",     fill="white", font=proportional(TINY_FONT))
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


button = Button(17)
listening = False

# --- Main ---
def main():
    serial_iface = spi(port=0, device=0, gpio=noop())
    device = max7219(serial_iface, cascaded=4, block_orientation=-90,
                     blocks_arranged_in_reverse_order=False)
    device.contrast(8)

    print("Waiting for DFPlayer to boot...")
    time.sleep(2)

    stream = sd.RawInputStream(samplerate=48000, blocksize=8192, device=0,
                                dtype='int16', channels=1, callback=vosk_callback)
    stream.start()

    def on_press():
        global listening
        listening = True
        print("Listening...")

    def on_release():
        global listening
        listening = False
        print("Stopped listening.")

    button.when_pressed = on_press
    button.when_released = on_release
    animation(device, 8, 1)

    alarm_fired = False
    toggle      = False

    while True:
        now    = datetime.now()
        toggle = not toggle
        sec    = now.second

        # ── Alarm check ───────────────────────────────────────────────────────
        if (ALARM_HOUR is not None and
                now.hour == ALARM_HOUR and
                now.minute == ALARM_MINUTE and
                not alarm_fired):
            print("ALARM! Playing track...")
            alarm_fired = True
            threading.Thread(target=play_alarm, daemon=True).start()

        if not (ALARM_HOUR is not None and
                now.hour == ALARM_HOUR and
                now.minute == ALARM_MINUTE):
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
                text(draw, (0, 1),  hours,                  fill="white", font=proportional(CP437_FONT))
                text(draw, (15, 1), ":" if toggle else " ", fill="white", font=proportional(TINY_FONT))
                text(draw, (17, 1), minutes,                fill="white", font=proportional(CP437_FONT))
            time.sleep(0.5)

if __name__ == "__main__":
    main()
