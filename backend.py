from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import threading
import paho.mqtt.client as mqtt
import sqlite3
import os

app = Flask(__name__, static_url_path='/static')
CORS(app) #erlaubt Anfragen von der HTML-Datei (z.B. lokal geöffnet mit file://)

# Live-Daten speichern
sensor_status = {
    'glas': False,  # Status des Glas-Sensors
    'gin': False,   # Status des Gin-Sensors
    'tonic': False,  # Status des Tonic-Sensors
    'gewicht': 0.0  # Gewicht des Glases
}

# MQTT-Komfiguration
MQTT_BROKER = "localhost"  # MQTT-Broker-Adresse
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

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()
    print(f"\U0001f4e8 Empfangen: {topic} → {payload}")

    if topic == MQTT_TOPIC_WEIGHT:
        try:
            sensor_status['gewicht'] = float(payload)
            sensor_status['glas'] = sensor_status['gewicht'] > 20
        except:
            pass
    elif topic == MQTT_TOPIC_SENSOR:
        sensor_id = int(payload.split(":")[0])
        if sensor_id == 0:
            sensor_status['gin'] = True
        elif sensor_id == 2:
            sensor_status['tonic'] = True
    elif topic == MQTT_TOPIC_STATUS:
        print("\U0001f4ac Status-Rückmeldung vom ESP:", payload)
    elif topic.startswith("cocktail/event/status/"):
        pump_id = topic.rsplit("/", 1)[-1]
        print(f"💬 Rückmeldung Pumpe {pump_id}:", payload)
    # Optional: Status zwischenspeichern, an Webseite senden, loggen


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

#--- POST /start_mix ---
@app.route('/start_mix', methods=['POST'])
def start_mix():
    data = request.get_json()
    name = data.get('name', 'Unbekannt')    #Name wird empfangen
    print(f"Mixvorgang gestartet von: {name}")       #wird im Terminal ausgegeben

    # Pumpenbefehl via MQTT
    client = request.get_json()
    client.conncet(MQTT_BROKER, 1883, 60)

    client.publish(MQTT_TOPIC_CMD, '{"pump":1, "duration": 3000}')
    client.publish(MQTT_TOPIC_CMD, '{"pump":2, "duration": 3000}')
    client.disconnect()

    return jsonify({'status': 'ok'}) #Antwort an die webseite zurückgeben

#--- GET /statistik ---
@app.route('/statistik', methods=['GET'])
def statistik():
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute('SELECT benutzername, userscore FROM users ORDER BY userscore DESC LIMIT 3')
        top3 = [{'name': row[0], 'anzahl': row[1]} for row in c.fetchall()]

        c.execute('SELECT SUM(userscore) FROM users')
        gesamt = c.fetchone()[0] or 0

    return jsonify({
        'gesamt': gesamt,                                #erstmal Platzhalter damit später echte daten aus datenbank kommt
        'highscore': top3
    })

#--- GET /status ---
@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        'glas': sensor_status['glas'],       #wenn gewicht vom glas erreicht wird
        'gin': sensor_status['gin'],        #KAPA sensor gibt meldung dass genug gin da ist
        'tonic': sensor_status['tonic'],    #KAPA meldet genug tonic da
        'gewicht': sensor_status['gewicht']  #aktuelles gewicht des glases
    })

@app.route('/log', methods=['POST'])
def log_mix():
    data = request.get_json()
    name = data.get('name', 'Unbekannt')
    print(f"GinTonic abgefüllt für: {name}")

    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users benutzername = ?", (name,))
        row = c.fetchone()
        if row:
            c.execute("UPDATE users SET userscore = userscore + 1 WHERE benutzername =?", (name,))
        else:
            c.execute("INSERT INTO users (benutzername, userscore) VALUES (?, 1)", (name,))
        conn.commit()

    return jsonify({'status': 'ok'})

    #---Flask-Server starten ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) #debug=True: Fehler werden im Browser angezeigt, host='