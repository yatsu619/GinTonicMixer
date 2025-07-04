import uasyncio as asyncio
import machine
from machine import Pin
import network
import time
import ubinascii
import ujson
from umqtt.robust import MQTTClient
from HX711 import HX711 

#-----------------------------------------------------

# -------- Konfiguration
MQTT_BROKER = "192.168.137.1"   # IP oder Hostname  Laptops/Servers
CLIENT_ID  = b"esp8266-" + ubinascii.hexlify(machine.unique_id())       

TOPIC_CMD_PUMP =   b"cocktail/cmd/pump"           # {"pump":1,"duration":2000} EVT HIER FEHLER wegen einzug
TOPIC_EVT_WEIGHT = b"cocktail/event/weight"     # z.B. "123.45kg"
TOPIC_CMD_SENSOR = b"cocktail/cmd/sensor" # {"sensor":0} oder {"sensor":-1} = alle
TOPIC_EVT_SENSOR = b"cocktail/event/sensor" # {"sensor":1, "time":123456}  Brauchen wir eigentlich nicht
TOPIC_RESP_SENSOR = b"cocktail/resp/sensor" # {"sensor":0, "state":"active"}


# Pin-Definitionen 
HX711_DT_PIN   = 14  # D5
HX711_SCK_PIN  = 12  # D6
#PUMP1_PIN      = 4   # D2 --> ist in boot.py
#PUMP2_PIN      = 5   # D1 --> ist in boot.py
SENSOR1_PIN    = 0   # D3
SENSOR2_PIN    = 2   # D4

#-------- Calibrierfaktor ohne Offsetverrechnung
CAL_FACTOR = 0.000542399  #1/-1843,66 = *.******


# ------------  Initialisierung
hx = HX711(HX711_DT_PIN, HX711_SCK_PIN)
sensor1 = Pin(SENSOR1_PIN, Pin.IN) #Physischen PULL-DOWN eingebaut
sensor2 = Pin(SENSOR2_PIN, Pin.IN) #Physischen PULL-DOWN eingebaut (fehler-> hätte per Software passieren sollen)
#pump1 = Pin(PUMP1_PIN, Pin.OUT, value=0)  --> in Boot.py
#pump2 = Pin(PUMP2_PIN, Pin.OUT, value=0) --> in Boot.py

# MQTT-Client
mqtt = MQTTClient(CLIENT_ID, MQTT_BROKER, keepalive=60)


# Pumphandling: schaltet Pumpe n für ms ein   ------------------------------------------------

async def handle_pump(pump_num, duration_ms):
    pin = pump1 if pump_num == 1 else pump2
    pin.value(1)
    await asyncio.sleep_ms(duration_ms)
    pin.value(0)

# Task: fortlaufende Gewichtsablesung und Publikation ------------------------------------------
async def weight_task():
    while True:
        raw = hx.read_raw()
        w = (raw * CAL_FACTOR) - 17.6	#Manueller Offset
        #w = hx.read_weight(scale=1843.66, offset=0)  # Nur bei Offsetlogik nötig
        print("Aktuelles Gewicht:", w)
        mqtt.publish(TOPIC_EVT_WEIGHT, b"%0.2f" % w)
        await asyncio.sleep(3)  # jede Sekunde

#Sensoren Status Funktion--------------------------------------------------------------------------------
        
def publish_sensor_state(idx):									
    v = sensor1.value() if idx == 0 else sensor2.value()
    state = "empty" if v == 1 else "filled"
    payload = ujson.dumps({"sensor": idx, "state": state})
    mqtt.publish(TOPIC_RESP_SENSOR, payload)
    



# Callback für eingehende MQTT-Nachrichten (pumpen + sensor befehl) ----------------------------------------------------

def mqtt_callback(topic, msg):
    # erwartet JSON: {"pump":1,"duration":2000}
    try:
        cmd = ujson.loads(msg)
    except Exception:
        print("MQTT parse error:", Exception)
        return
        
    #Pumpen-Befehl
    if topic == TOPIC_CMD_PUMP:
        pump = int(cmd.get("pump", 0)) # Die 0 ist dafür da, dass wenn kein "pump" eintrag ankommen würde eine Zahl ausgeben zu können. Sonst würde da "none" stehen
        dur  = int(cmd.get("duration", 0))
        if pump in (1,2) and dur>0:
            # in asyncio-Task auslagern
            asyncio.create_task(handle_pump(pump, dur))
    #Sensor-Abfrage
    elif topic == TOPIC_CMD_SENSOR:
        #sensor == -1 dann alle, sonst nur der spezifisch-e Index
        req = int(cmd.get("sensor", -1))
        if req == -1: 						#-1 ist einfach ein Ersatzwert, wenn über MQTT im cmd keine Zahl mitgeliefert wird. Also wenn ich nicht sag welcher Sensor, gibt er mir einfach beide
            publish_sensor_state(0)
            publish_sensor_state(1)
        elif req in (0,1):
            publish_sensor_state(req)



#Capazitive-Sensoren-Task (Dauerhaftes Abfragen + Nur verschicken bei Flankenwechsel) --------------------------------

async def cap_task():
    prev = [sensor1.value(), sensor2.value()]
    while True:
        for idx, pin in enumerate((sensor1, sensor2)):
            v = pin.value()
            if v != prev[idx]:
                #Flankenwechsel festgestellt
                payload = ujson.dumps({"sensor": idx, "time": time.ticks_ms(), "state": "active" if v else "inactive"})
                mqtt.publish(TOPIC_EVT_SENSOR, payload)
                prev[idx] = v
        await asyncio.sleep_ms(100)

# Task: MQTT-Client am Leben halten ------------------------------------------

async def mqtt_task():
    mqtt.set_callback(mqtt_callback)
    mqtt.connect()
    mqtt.subscribe(TOPIC_CMD_PUMP)
    mqtt.subscribe(TOPIC_CMD_SENSOR)
    print("MQTT verbunden, abonnierte Topics", TOPIC_CMD_PUMP, TOPIC_CMD_SENSOR)
    while True:
        mqtt.check_msg()   # non-blocking auf neue Nachrichten
        await asyncio.sleep_ms(100)
    
# ------ Hauptprogramm als Funktion
async def main():
    # kleine Verzögerung, bis WLAN stabil ist für 10 Sekunden
    await asyncio.sleep(4)
    # Starte alle Tasks
    await asyncio.gather(
        mqtt_task(),
        weight_task(),
        cap_task()
    )

# Starte uasyncio-Schleife
try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()