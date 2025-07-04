import threading
import json
import time
import paho.mqtt.client as mqtt

BROKER          = "192.168.137.1"
PORT            = 1883
TOPIC_CMD_PUMP  = "cocktail/cmd/pump"
TOPIC_CMD_SENSOR= "cocktail/cmd/sensor"   # neu
TOPIC_WEIGHT    = "cocktail/event/weight"
TOPIC_SENSOR_EVT= "cocktail/event/sensor"
TOPIC_SENSOR_RESP = "cocktail/resp/sensor"  # neu

# 1) Callback: Verbindung aufgebaut
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✓ MQTT verbunden")
        # alle relevanten Topics subscribenC
        client.subscribe([
            (TOPIC_WEIGHT, 0),
            (TOPIC_SENSOR_EVT, 0),
            (TOPIC_SENSOR_RESP, 0)   # neu
        ])
    else:
        print("⚠️ Verbindung fehlgeschlagen, Code =", rc)

# 2) Callback: Nachricht empfangen
def on_message(client, userdata, msg):
    topic   = msg.topic
    payload = msg.payload.decode()

    if topic == TOPIC_WEIGHT:
        print(f"[Gewicht] {payload} g")

    elif topic == TOPIC_SENSOR_EVT:
        # Flankenwechsel-Events
        try:
            data = json.loads(payload)
            s = data.get("sensor")
            t = data.get("time")
            st = data.get("state", "?")
            print(f"[Sensor{s} Event] state={st} bei {t} ms")
        except:
            print(f"[{TOPIC_SENSOR_EVT}] Unbekanntes Payload: {payload}")

    elif topic == TOPIC_SENSOR_RESP:
        # Antwort auf explizite Abfrage
        try:
            data = json.loads(payload)
            s = data.get("sensor")
            st = data.get("state")
            if st =='empty':           # Musste wegen Erweiterter Schaltung verändert werden. -> Logik wurde invertiert!
                print(f"[Sensor{s} Status] filled")
                print(f"--> DEBUG: st={st!r}")      # das !r heist gib mir den inthalt RAW (roh) aus
            else:
                print(f"[Sensor{s} Status] empty")
                print(f"--> DEBUG: st={st!r}")
        except:
            print(f"[{TOPIC_SENSOR_RESP}] Unbekanntes Payload: {payload}")

    else:
        print(f"[{topic}] {payload}")

# 3) Thread: Nutzer-Eingabe schleife
def input_loop(client):
    """
    - Pumpenbefehl: '1 2000'
    - Sensor-Abfrage: 's 0' (Sensor 0), 's 1' oder 's all' (beide)
    - 'q' beendet das Programm.
    """
    while True:
        txt = input("Eingabe (z.B. '1 2000' für Pumpe, 's 0' für Sensor): ").strip()
        if txt.lower() == 'q':
            print("Beende...")
            client.disconnect()
            break

        parts = txt.split()
        # Sensor-Abfrage
        if parts[0].lower() == 's':
            if len(parts) != 2:
                print("❌ Bitte 's 0', 's 1' oder 's all' eingeben.")
                continue
            arg = parts[1].lower()
            if arg == 'all':
                payload = json.dumps({"sensor": -1})
            elif arg in ('0', '1'):
                payload = json.dumps({"sensor": int(arg)})
            else:
                print("❌ Ungültiger Sensor. Nur 0, 1 oder all.")
                continue
            client.publish(TOPIC_CMD_SENSOR, payload)
            print(f"→ Sensor-Abfrage gesendet: {payload}")
            continue

        # Pumpenbefehl
        if len(parts) != 2:
            print("❌ Bitte '1 2000' für Pumpe oder 's 0' für Sensor-Abfrage.")
            continue
        try:
            pump     = int(parts[0])
            duration = int(parts[1])
            if pump not in (1,2) or duration <= 0:
                raise ValueError
        except ValueError:
            print("❌ Ungültige Eingabe. Pumpennr. muss 1 oder 2 sein, Dauer >0.")
            continue

        cmd = {"pump": pump, "duration": duration}
        client.publish(TOPIC_CMD_PUMP, json.dumps(cmd))
        print(f"→ Pumpensteuerung gesendet: Pumpe {pump} für {duration} ms")

# 4) Hauptprogramm
def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Verbinde mit MQTT-Broker {BROKER}:{PORT} …")
    client.connect(BROKER, PORT, keepalive=60)

    thread = threading.Thread(target=input_loop, args=(client,), daemon=True)
    thread.start()

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Abbruch per Strg+C")

if __name__ == "__main__":
    main()