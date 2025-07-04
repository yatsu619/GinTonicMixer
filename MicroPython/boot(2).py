# boot.py

import network
import time
import ujson
from machine import Pin

#Pumpe 1 und 2 sofort nach Bootloader auf LOW ziehen (sonst fharen die  pumpen kurz an bei stromanschließne)
PUMP1_PIN = 4 #D2
PUMP2_PIN = 5 #D1

pump1 = Pin(PUMP1_PIN, Pin.OUT, value=0)
pump2 = Pin(PUMP2_PIN, Pin.OUT, value=0)


# bekannte Netzwerke: SSID: Passwort
known_networks = {
    "pat115": "12345678",
    "LAPTOP_HOTSPOT_YS": "yatheesh14"
}

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# versuche, eines der bekannten Netze zu verbinden
for ssid, pwd in known_networks.items():
    print("Versuche Verbindung zu", ssid)
    wlan.connect(ssid, pwd)
    for _ in range(20):
        if wlan.isconnected():
            break
        time.sleep(1)
    if wlan.isconnected():
        print("Verbunden mit", ssid, "– IP:", wlan.ifconfig()[0])
        break
else:
    print("Kein bekanntes WLAN gefunden!")

