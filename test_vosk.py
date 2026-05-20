import vosk 
import sounddevice as sd
import json
import numpy as np
from scipy.signal import resample_poly

model = vosk.Model("vosk-model-small-en-us-0.15")
rec = vosk.KaldiRecognizer(model, 16000)
triggers = [
    "wake me up at",
    "can you wake me up at",
    "i wanna get up at",
    "i want to get up at",
    "need to get up at",
    "i need to get up at",
    "set alarm for",
    "set an alarm for",
    "get me up at",
    "alarm at"
]

hours = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]
minutes = ["", " thirty", " fifteen", " forty five"]
periods = ["am", "pm"]

phrases = []
for trigger in triggers:
    for hour in hours:
        for minute in minutes:
            for period in periods:
                phrases.append(f"{trigger} {hour}{minute} {period}")

phrases.append("[unk]")
grammar = json.dumps(phrases)
rec.SetGrammar(grammar)
print(f"Grammar has {len(phrases)} phrases")

print("Listening... Say something like 'wake me up at seven thirty am'")

def callback(indata, frames, time, status):
    audio = np.frombuffer(bytes(indata), dtype=np.int16).astype(np.float32)
    resampled = resample_poly(audio, up=1, down=3)
    resampled_bytes = resampled.astype(np.int16).tobytes()

    if rec.AcceptWaveform(resampled_bytes):
        result = json.loads(rec.Result())
        text = result["text"]
        if text and text != "[unk]":
            print("Heard:", text)
        else:
            print("Didn't understand, please try again...")

with sd.RawInputStream(samplerate=48000, blocksize=8192, device=0, dtype='int16', channels=1, callback=callback):
    while True:
      pass
