# boot.py
import network
import time
import ujson


# bekannte Netzwerke: SSID: Passwort
known_networks = {
    "pat115": "12345678",
    "Yathissh": "123"
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




