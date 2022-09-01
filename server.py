import serial
import datetime
import json
import textwrap
from serial.serialutil import SerialException

# modified from https://blog.rareschool.com/2021/01/controlling-raspberry-pi-pico-using.html
class SerialSender:
    TERMINATOR = '\n'.encode('UTF8')

    def __init__(self, device='COM3', baud=115200, timeout=1):
        self.serial = serial.Serial(device, baud, timeout=timeout)

    def receive(self) -> str:
        line = self.serial.read_until(self.TERMINATOR)
        return line.decode('UTF8').strip()

    def send(self, text: str):
        line = '%s\n' % text
        self.serial.write(line.encode('UTF8'))

    def close(self):
        self.serial.close()

try:
    sender = serial.Serial("COM3", 115200, timeout=1)
    data = {"machines": [
        {
            "machine": "N1",
            "build": "Health: PX-trunk-PS5-EU-Debug",
            "changelist": 24876,
            "step": "Editmode-Tests",
            "duration": 200
        },
        {
            "machine": "N2",
        },
        {
            "machine": "N3",
            "build": "Deploy: PX-trunk-PC-WW-Debug",
            "changelist": 24544,
            "step": "Deploy-Steam",
            "duration": 6340
        },
    ]}
    data_json = json.dumps(data)
    # things don't go so well if we send more than 256 characters? 
    for split_json in textwrap.wrap(data_json, 256):
        sender.write(split_json.encode('UTF8'))
    sender.write("\n".encode('UTF8'))
    sender.close()
except SerialException:
    raise