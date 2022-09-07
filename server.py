import serial
import json
import textwrap
import jenkinsclient
import time
from serial.serialutil import SerialException

while True:
    try:
        sender = serial.Serial("COM3", 115200, timeout=1)
        data = jenkinsclient.get_jenkins_state()
        data_json = json.dumps(data)
        # things don't go so well if we send more than 256 characters? 
        for split_json in textwrap.wrap(data_json, 256):
            sender.write(split_json.encode('UTF8'))
        sender.write("\n".encode('UTF8'))
        sender.close()
        print("sent new data!")
    except SerialException:
        pass
    time.sleep(3*60)