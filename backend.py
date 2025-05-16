from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app) #erlaubt Anfragen von der HTML-Datei (z.B. lokal geöffnet mit file://)

#--- POST /start_mix ---
@app.route('/start_mix', methods=['POST'])
def start_mix():
    data = request.get_json()
    name = data.get('name', 'Unbekannt')    #Name wird empfangen
    print(f"Mixvorgang gestartet von: {name}")       #wird im Terminal ausgegeben

    #später einfügen:
    #ESP ansteuern (z.b. über wlan), name aulesen: name = request.get_json().get('name'), vorgang in datenbank schreiben

    return jsonify({'status': 'ok'}) #Antwort an die webseite zurückgeben

#--- GET /statistik ---
@app.route('/statistik', methods=['GET'])
def statistik():
    return jsonify({
        'gesamt': 5,                                #erstmal Platzhalter damit später echte daten aus datenbank kommt
        'highscore': [
            {'name': 'Patrice', 'anzahl': 13},
            {'name': 'Ufuk', 'anzahl': 2},
            {'name': 'Yatheesh', 'anzahl': 0},
        ]
    })

#--- GET /status ---
@app.route('/status', methods=['GET'])
def status():
    #Platzhalter für die echten Sensordaten vom ESP
    return jsonify({
        'glas': True,       #wenn gewicht vom glas erreicht wird
        'gin': True,        #KAPA sensor gibt meldung dass genug da ist
        'tonic': True       #KAPA meldet genug tonic da
    })

#---Flask-Server starten ---
if __name__ == '__main__':
    app.run(debug=True)

@app.route('/log', methods=['POST'])
def log_mix():
    data = request.get_json()
    name = data.get('name', 'Unbekannt')

    print(f"GinTonic abgefüllt für: {name}")

    #Datenbank: 1 Eintrag speichern