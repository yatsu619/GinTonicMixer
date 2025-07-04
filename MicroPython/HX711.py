
# ------  HX711-Treiberklasse

from machine import Pin
class HX711:
    def __init__(self, dt_pin, sck_pin, gain=128):
        self.dt = Pin(dt_pin, Pin.IN, pull=Pin.PULL_UP)
        self.sck = Pin(sck_pin, Pin.OUT)
        self.gain = gain
        self.set_gain(gain)

    def set_gain(self, gain):
        if gain == 128:
            self._gain_pulses = 1
        elif gain == 64:
            self._gain_pulses = 3
        elif gain == 32:
            self._gain_pulses = 2
        else:
            raise ValueError("Gain muss 128, 64 oder 32 sein")
        self.gain = gain

    def read_raw(self):
        # warte auf Datenbereit
        while self.dt.value() == 1:
            pass
        count = 0
        for _ in range(24):
            self.sck.value(1)
            count = (count << 1) | self.dt.value()
            self.sck.value(0)
        # Gain & Kanal auswählen
        for _ in range(self._gain_pulses):
            self.sck.value(1)
            self.sck.value(0)
        # Zweierkomplement konvertieren
        if count & 0x800000:
            count |= ~0xffffff
        return count
"""
    def read_weight(self, scale, offset=0):			#Das braucht es nicht, weil wir keinen Offset benötigen, wir arbeiten immer mit dem selben Faktor
        raw = self.read_raw()
        return (raw - offset) * scale
"""    
