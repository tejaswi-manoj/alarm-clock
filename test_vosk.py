import vosk 
import sounddevice as sd
import json


model = vosk.Model("vosk-model-small-en-us-0.15")
rec = vosk.KaldiRecognizer(model, 16000)

print("Listening.. Say something!")

def callback(indata, frames, time, status):
    if rec.AcceptWaveform(bytes(indata)):
        result = json.loads(rec.Result())
        if result["text"]:
            print("Heard:", result["text"])

with sd.RawInputStream(samplerate=16000, blocksize=8192, device=0, dtype='int16', channels=1, callback=callback):
    while True:
        sd.sleep(100)