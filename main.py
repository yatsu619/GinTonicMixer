# main.py
import uasyncio as asyncio
import machine
from machine import Pin
import network
import time
import ubinascii
from umqtt.robust import MQTTClient

# === Konfiguration ===
MQTT_BROKER = "192.168.137.1"   # IP oder Hostname deines Laptops/Servers
CLIENT_ID  = b"esp8266-" + ubinascii.hexlify(machine.unique_id())

TOPIC_CMD_PUMP = b"cocktail/cmd/pump"     # erwartet JSON {"pump":1,"duration":2000}
TOPIC_EVT_SENSOR = b"cocktail/event/sensor"
TOPIC_EVT_WEIGHT = b"cocktail/event/weight"

# Pin-Definitionen (anpassen!)
HX711_DT_PIN   = 4   # D2
HX711_SCK_PIN  = 5   # D1
PUMP1_PIN      = 14  # D5
PUMP2_PIN      = 12  # D6
SENSOR1_PIN    = 0   # D3
SENSOR2_PIN    = 2   # D4

# === HX711-Treiberklasse ===
class HX711:
    def __init__(self, dt_pin, sck_pin, gain=128):
        self.dt = Pin(dt_pin, Pin.IN, pull=None)
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

    def read_weight(self, scale=1.0, offset=0):
        raw = self.read_raw()
        return raw * scale + offset

# === Initialisierung ===
hx = HX711(HX711_DT_PIN, HX711_SCK_PIN)
pump1 = Pin(PUMP1_PIN, Pin.OUT, value=0)
pump2 = Pin(PUMP2_PIN, Pin.OUT, value=0)
sensor1 = Pin(SENSOR1_PIN, Pin.IN) #Physischen PULL-DOWN EINBAUEN!!!!!!
sensor2 = Pin(SENSOR2_PIN, Pin.IN) #Physischen PULL-DOWN EINBAUEN!!!!!!

# MQTT-Client
mqtt = MQTTClient(CLIENT_ID, MQTT_BROKER, keepalive=60)

# Pumphandling: schaltet Pumpe n für ms ein
async def handle_pump(pump_num, duration_ms):
    pin = pump1 if pump_num == 1 else pump2
    pin.value(1)
    await asyncio.sleep_ms(duration_ms)
    pin.value(0)

# Task: fortlaufende Gewichtsablesung und Publikation
async def weight_task():
    while True:
        w = hx.read_weight(scale=0.001, offset=0)  # Beispielskalierung
        mqtt.publish(TOPIC_EVT_WEIGHT, b"%0.2f" % w)
        await asyncio.sleep(1)  # jede Sekunde

# Callback für eingehende MQTT-Nachrichten
def mqtt_callback(topic, msg):
    # erwartet JSON: {"pump":1,"duration":2000}
    try:
        import ujson
        cmd = ujson.loads(msg)
        pump = int(cmd.get("pump", 0))
        dur  = int(cmd.get("duration", 0))
        if pump in (1,2) and dur>0:
            # in asyncio-Task auslagern
            asyncio.create_task(handle_pump(pump, dur))
    except Exception as e:
        print("MQTT-Cmd parse error:", e)

# Task: MQTT-Client am Leben halten
async def mqtt_task():
    mqtt.set_callback(mqtt_callback)
    mqtt.connect()
    mqtt.subscribe(TOPIC_CMD_PUMP)
    print("MQTT verbunden, abonnierte Topics")
    while True:
        mqtt.check_msg()   # non-blocking auf neue Nachrichten
        await asyncio.sleep_ms(100)

# IRQ für Sensoren
def sensor_irq(pin):
    # wenn auf High umschaltet, Ereignis senden
    if pin.value():
        mqtt.publish(TOPIC_EVT_SENSOR, b"%d:%d" % (pin.id(), time.ticks_ms()))

# Task: Sensor-Setup (Interrupts)
async def sensor_task():
    sensor1.irq(trigger=Pin.IRQ_RISING, handler=sensor_irq)
    sensor2.irq(trigger=Pin.IRQ_RISING, handler=sensor_irq)
    # nichts weiter tun, IRQs feuern autonom
    while True:
        await asyncio.sleep(10)  # Halte die Task aktiv --- Wird hier nur alle 10sekunden die Sensorwerte abgefragt?

# === Hauptprogramm ===
async def main():
    # kleine Verzögerung, bis WLAN stabil ist
    await asyncio.sleep(5)
    # Starte alle Tasks
    await asyncio.gather(
        mqtt_task(),
        weight_task(),
        sensor_task()
    )

# Starte uasyncio-Schleife
try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
