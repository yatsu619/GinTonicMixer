from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import threading
import paho.mqtt.client as mqtt
import sqlite3
import os
import time
import json

app = Flask(__name__, static_url_path='/static')
CORS(app) #erlaubt Anfragen von der HTML-Datei (z.B. lokal geöffnet mit file://)

# Live-Daten speichern
sensor_status = {
    'glas': False,  # Status des Glas-Sensors
    'gin': False,   # Status des Gin-Sensors
    'tonic': False,  # Status des Tonic-Sensors
    'gewicht': 0.0  # Gewicht des Glases

}
sensor_live_status = {}

# MQTT-Komfiguration
MQTT_BROKER = "192.168.137.1"  # MQTT-Broker-Adresse
MQTT_TOPIC_WEIGHT = "cocktail/event/weight"
MQTT_TOPIC_SENSOR = "cocktail/event/sensor"
MQTT_TOPIC_CMD = "cocktail/cmd/pump"
MQTT_TOPIC_STATUS = "cocktail/event/status"

# MQTT Callback
def on_connect(client, userdata, flags, rc):
    print("\U0001f4e1 MQTT verbunden mit Code", rc)
    client.subscribe(MQTT_TOPIC_WEIGHT)
    client.subscribe(MQTT_TOPIC_SENSOR)
    client.subscribe(MQTT_TOPIC_STATUS)
    client.subscribe("cocktail/event/status/1")
    client.subscribe("cocktail/event/status/2")
    client.subscribe("cocktail/resp/sensor")

    client.publish("cocktail/cmd/sensor", json.dumps({"sensor": -1}))      #-1 = beide Sensoren

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()
    print(f"\U0001f4e8 Empfangen: {topic} → {payload}")

    if topic == MQTT_TOPIC_WEIGHT:
        try:
            sensor_status['gewicht'] = float(payload)                       # wenn Gewicht größer als -10g ist dann wird glas erkannt
            sensor_status['glas'] = sensor_status['gewicht'] < -10          #-10 wegen invertierendem Verstärker
        except:
            pass
    elif topic == MQTT_TOPIC_SENSOR or topic == "cocktail/resp/sensor": 
        print("SENSOR-DATEN WERDEN VERARBEITET")
        try:
            data = json.loads(payload)
            print("JSON:", data)
            sensor_id = int(data.get("sensor", -1))
            state = data.get("state", "").lower()
            sensor_live_status[sensor_id] = state
            print(f"Antwort vom ESP: Sensor {sensor_id} = {state}")

            if sensor_id == 0:
                sensor_status['gin'] = (state == "empty")           #durch Bauteil, Logik invertiert
            elif sensor_id == 1:
                sensor_status['tonic'] = (state == "empty")

        except Exception as e:
            print("Fehler beim Verarbeiten von SENSOR-JSON:", e)

    elif topic == MQTT_TOPIC_STATUS:
        print("\U0001f4ac Status-Rückmeldung vom ESP:", payload)
    elif topic.startswith("cocktail/event/status/"):
        pump_id = topic.rsplit("/", 1)[-1]
        print(f"💬 Rückmeldung Pumpe {pump_id}:", payload)
    # Optional: Status zwischenspeichern, an Webseite senden, loggen

    print("Sensorstatus (nach update):", sensor_status)



# MQTT starten
def mqtt_thread():
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_BROKER, 1883, 60)
    mqtt_client.loop_forever()

threading.Thread(target=mqtt_thread, daemon=True).start()


#Datenbankpfad
db_path = os.path.join("db", "cocktail.db")

# Flask-Routen
@app.route('/')
def index():
    return render_template('index.html')

#/start_mix Befehl aus der Webseite 
@app.route('/start_mix', methods=['POST'])
def start_mix():
    data = request.get_json()   #holt JSON-Daten aus dem HTTP-Post_Request der Webseite
    name = data.get('name', 'Unbekannt')    #Name wird empfangen
    print(f"Mixvorgang gestartet von: {name}")       #wird im Terminal ausgegeben

    # Pumpenbefehl via MQTT
    mqtt_temp = mqtt.Client()   #neuer MQTT-Client wird erstellt
    mqtt_temp.connect(MQTT_BROKER, 1883, 60)        #verbindet sich mit MQTT-Broker auf dem Laptop
    mqtt_temp.publish(MQTT_TOPIC_CMD, '{"pump":1, "duration": 12000}')   #Zeit in ms     wie lange Pumpen laufen soll
    mqtt_temp.publish(MQTT_TOPIC_CMD, '{"pump":2, "duration": 50000}')  #Tonic
    time.sleep(0.5)         #Timesleep, damit die MQTT-Nachrichten sicher gesendet werden
    print("MQTT-Befehle gesendet")
    mqtt_temp.disconnect()  #MQTT-Verbindung wird getrennt, um Ressourcen zu sparen

    return jsonify({'status': 'ok'}) #Antwort an die Webseite zurückgeben

#/statistik: Anfrage von der Webseite 
@app.route('/statistik', methods=['GET'])
def statistik():
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute('SELECT benutzername, userscore FROM users ORDER BY userscore DESC LIMIT 3')
        top3 = [{'name': row[0], 'anzahl': row[1]} for row in c.fetchall()]

        c.execute('SELECT SUM(userscore) FROM users')
        gesamt = c.fetchone()[0] or 0

    return jsonify({
        'gesamt': gesamt,                                
        'highscore': top3
    })

#/status: Anfrage über die Sensorwerte + ob Glas steht
@app.route('/status', methods=['GET'])
def status():
    try:
        #Sensorstatus im Backend zurücksetzen
        sensor_live_status[0] = None
        sensor_live_status[1] = None
        
        #Anfrage an ESP senden
        mqtt_client = mqtt.Client()
        mqtt_client.connect(MQTT_BROKER, 1883, 60)
        mqtt_client.publish("cocktail/cmd/sensor", json.dumps({"sensor": -1}))
        mqtt_client.disconnect()

        for _ in range(20):             #wartezeit auf 2 sekunden anstatt 1 damit die mqtt weiterleitung ankommt
            time.sleep(0.1)
            s0 = sensor_live_status.get(0)
            s1 = sensor_live_status.get(1)
            if s0 in ("filled", "empty") and s1 in ("filled", "empty"):         #durch Bauteil invertierte logik
                sensor_status['gin'] = (s0 == "empty")
                sensor_status['tonic'] = (s1 == "empty")
                break
        

    except Exception as e:
        print("Fehler bei /status:", e)

    return jsonify({
        'glas': sensor_status['glas'],       #wenn gewicht vom glas erreicht wird
        'gin': sensor_status['gin'],        #KAPA sensor gibt meldung dass genug gin da ist
        'tonic': sensor_status['tonic'],    #KAPA meldet genug tonic da
        'gewicht': sensor_status['gewicht']  #aktuelles gewicht des glases
    })

# /log: benutzer mit der Anzahl der Drinks
@app.route('/log', methods=['POST'])
def log_mix():
    data = request.get_json()
    original_name = data.get('name', 'Unbekannt')
    namekey = original_name.lower()
    print(f"GinTonic abgefüllt für: {namekey}")

    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE namekey = ?", (namekey,))
        row = c.fetchone()
        if row:
            c.execute("UPDATE users SET userscore = userscore + 1 WHERE namekey = ?", (namekey,))   #wenn user bereits existiert, dann score +1
        else:
            c.execute("INSERT INTO users (benutzername, namekey, userscore) VALUES (?, ?, 1)", (original_name, namekey))    #neuer user setzen und score auf 1
        conn.commit()

    return jsonify({'status': 'ok'})

#dauerhafte Abfrage für live-werte
@app.route('/abfrage_sensor', methods=['POST'])
def abfrage_sensor():
    data = request.get_json()
    sensor_id = int(data.get('sensor', -1))

    if sensor_id not in (0, 1):
        return jsonify({'error': 'Ungültiger Sensor'}), 400
    
    #Rücksetzpunkt
    sensor_live_status[sensor_id] = None

    #Anfrage an ESP senden
    mqtt_temp = mqtt.Client()
    mqtt_temp.connect(MQTT_BROKER, 1883, 60)
    mqtt_temp.publish("cocktail/cmd/sensor", json.dumps({"sensor": sensor_id}))
    mqtt_temp.disconnect()

    #Warten auf Antwort (max. 1 Sekunde)
    for _ in range(10):
        time.sleep(0.1)
        state = sensor_live_status.get(sensor_id)
        if state in ("active", "inactive", "empty", "filled"):
            return jsonify({
                "sensor": sensor_id,
                "state": state
            })
    return jsonify({
        "sensor": sensor_id,
        "state": "timeout"
    })

# Flask-Server starten
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 