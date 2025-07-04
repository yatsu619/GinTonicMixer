console.log("script.js wurde gelesen");

function pruefeName(){
    const name = document.getElementById("nameInput").value.trim();
    const button = document.getElementById("startBtn");
    button.disabled = name === "";
}

function zeigeStatusanzeige() {
    aktualisiereStatus();
    document.getElementById("start-screen").style.display = "none";
    document.getElementById("status-screen").style.display = "block";

    // Hinweisbereich zurücksetzen
    document.getElementById("hinweis").style.display = "none";

    fetch('http://192.168.137.1:5000/status')
        .then(response => response.json())
        .then(data => {                       //richtige Sensorwerte
            const glasErkannt = data.glas;   
            const ginOk = data.gin;
            const tonicOk = data.tonic;

            document.getElementById("glasStatus").textContent = glasErkannt ? "✅ Glas erkannt" : "❌ Glas nicht erkannt";
            document.getElementById("ginStatus").textContent = ginOk ? "✅ Genug Gin" : "❌ Nicht genug Gin";
            document.getElementById("tonicStatus").textContent = tonicOk ? "✅ Genug Tonic" : "❌ Nicht genug Tonic";

             // Hinweis anzeigen, wenn etwas fehlt
            if (!glasErkannt) {
                zeigeHinweis("⚠️ Bitte ein Glas bereitstellen");
            } else if (!ginOk) {
                zeigeHinweis("⚠️ Bitte Gin nachfüllen");
            } else if (!tonicOk) {
                zeigeHinweis("⚠️ Bitte Tonic nachfüllen");
            }

            const startBtn = document.getElementById("startMix");   //Bedingung um Mischvorgang zu starten
            if(glasErkannt && ginOk && tonicOk) {
                startBtn.disabled = false;
            } else {
                startBtn.disabled = true;
            }
        })
        .catch(error => {
            console.error("Fehler beim Laden des Status:", error);
            zeigeHinweis("❌ Fehler beim Abrufen des Status");
            document.getElementById("startMix").disabled = true;
        });
}

function zeigeStart(){
    document.getElementById("status-screen").style.display = "none";
    document.getElementById("start-screen").style.display = "block";
}

function zeigeHinweis(text) {
    document.getElementById("hinweisText").textContent = text;
    document.getElementById("hinweis").style.display = "block";
}

function mixerStarten(){
    console.log("mixerStarten() wurde ausgeführt");

    const name = document.getElementById("nameInput").value.trim()
    console.log("MQTT-Befehl an /start_mix gesendet für:", name);
    // Hier wird der Startbefehl an den Server geschickt

    fetch('http://192.168.137.1:5000/start_mix', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name: name})            
    })

    .then(response => response.json())
    .then(data => {
        if(data.status === 'ok'){
            document.getElementById("status-screen").style.display = "none";
            document.getElementById("lade-screen").style.display = "block";

            
            const dauer = 52;
            const balken = document.getElementById("ladebalken");
            const startZeit = Date.now();

            const intervall = setInterval(() => {
                const vergangen = (Date.now() - startZeit) / 1000; // in Sekunden
                const prozent = Math.min((vergangen / dauer) * 100, 100);

                balken.style.width = prozent + "%";
                document.getElementById("ladeStatusText").textContent = `Ladevorgang: ${Math.round(prozent)}%`;

                if (vergangen >= dauer) {
                    clearInterval(intervall);
                    document.getElementById("lade-screen").style.display = "none";
                    document.getElementById("final-screen").style.display = "block";

                    const name = document.getElementById("nameInput").value;
                    console.log("Logging an /log gesendet für:", name);


                    //Hier werden die Daten an Server geschickt
                    fetch('http://192.168.137.1:5000/log', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({name: name,})
                    });

                    setTimeout(() => {
                        console.log("Rücksprung läuft:");
                        document.getElementById("final-screen").style.display = "none";
                        document.getElementById("start-screen").style.display = "block";

                        //Name zurücksetzen
                        document.getElementById("nameInput").value = "";
                        document.getElementById("startBtn").disabled = true;

                        //Status zurücksetzen
                        document.getElementById("glasStatus").textContent = "❌ Glas nicht erkannt";
                        document.getElementById("ginStatus").textContent = "❌ Nicht genug Gin";
                        document.getElementById("tonicStatus").textContent = "❌ Nicht genug Tonic";
                        document.getElementById("startMix").disabled = true;
                    }, 5000); //50000 Millisekunden 
                }
            }, 100);

        }
    })
    .catch(error => {
        console.error("Fehler bei /start_mix", error);
    }); 

    
}

function ladeStatistik() {
  fetch('http://192.168.137.1:5000/statistik') 
    .then(res => res.json())
    .then(data => {
      // Gesamtmenge anzeigen
      document.getElementById("menge").textContent = "Anzahl der Drinks:" + data.gesamt;

      // Highscore anzeigen
      const liste = document.getElementById("Highscore-Liste");
      liste.innerHTML = "";

      data.highscore.forEach(eintrag => {
        const li = document.createElement("li");
        li.textContent = `${eintrag.name} (${eintrag.anzahl})`;
        liste.appendChild(li);
      });
    })
    .catch(error => {
      console.error("Fehler beim Laden der Statistik:", error);
    });
}

function aktualisiereStatus() {
  fetch('/status')
    .then(response => response.json())
    .then(data => {
      document.getElementById("glasStatus").textContent = data.glas ? "✅ Glas erkannt" : "❌ Glas nicht erkannt";
      document.getElementById("ginStatus").textContent = data.gin ? "✅ Genug Gin" : "❌ Nicht genug Gin";
      document.getElementById("tonicStatus").textContent = data.tonic ? "✅ Genug Tonic" : "❌ Nicht genug Tonic";

      // Button freigeben, wenn alles erfüllt
      const startMixBtn = document.getElementById("startMix");
      if (data.glas && data.gin && data.tonic) {
        startMixBtn.disabled = false;
        document.getElementById("hinweis").style.display = "none";  // Hinweis ausblenden, wenn alles erfüllt ist
      } else {
        startMixBtn.disabled = true;

        // Dynamischer Hinweis, abhängig vom Fehler
        if (!data.glas) {
          zeigeHinweis("Bitte ein Glas bereitstellen!");
        } else if (!data.gin) {
          zeigeHinweis("Bitte Gin nachfüllen!");
        } else if (!data.tonic) {
          zeigeHinweis("Bitte Tonic nachfüllen!");
        }
      }
    })
    .catch(error => {
      console.error("Fehler beim Abrufen von /status:", error);
    });
}

document.addEventListener("DOMContentLoaded", () => {
    ladeStatistik();
    aktualisiereStatus();
});


setInterval(ladeStatistik, 5000); // alle 5 Sekunden Statistik aktualisieren
setInterval(aktualisiereStatus, 2000); // alle 2 Sekunden

