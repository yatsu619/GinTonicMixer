function pruefeName(){
    const name = document.getElementById("nameInput").value.trim();
    const button = document.getElementById("startBtn");
    button.disabled = name === "";
}

function zeigeStatusanzeige() {
    document.getElementById("start-screen").style.display = "none";
    document.getElementById("status-screen").style.display = "block";

    // Hinweisbereich zurücksetzen
    document.getElementById("hinweis").style.display = "none";

    fetch('http://127.0.0.1:5000/status')
        .then(response => response.json())
        .then(data => {
            const glasErkannt = data.glas;   // ← hier simulieren: false = Fehler
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

            const startBtn = document.getElementById("startMix");
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

    const name = document.getElementById("nameInput").value

    fetch('http://127.0.0.1:5000/start_mix', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name: name})            //später: {name: ...}
    })

    .then(response => response.json())
    .then(data => {
        if(data.status === 'ok'){
            document.getElementById("status-screen").style.display = "none";
            document.getElementById("lade-screen").style.display = "block";

            const balken = document.getElementById("ladebalken");
            let sekunden = 0;
            const dauer = 5;

            const intervall = setInterval(() => {
                sekunden++;
                const prozent = Math.min((sekunden / dauer) * 100, 100);
                balken.style.width = prozent + "%";
                document.getElementById("ladeStatusText").textContent = `Ladevorgang: ${Math.round(prozent)}%`;

                if (sekunden >= dauer) {
                    clearInterval(intervall);
                    document.getElementById("lade-screen").style.display = "none";
                    document.getElementById("final-screen").style.display = "block";

                    const name = document.getElementById("nameInput").value;

                    //Hier werden die Daten an Server geschickt
                    fetch('http://127.0.0.1:5000/log', {
                        method: 'POST',
                        headers: {'Content.Type': 'application/json'},
                        body: JSON.stringly({name: name,})
                    });

                    setTimeout(() => {
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
            }, 1000);

        }
    })
    .catch(error => {
        console.error("Fehler bei /start_mix", error);
    }); 

    
}

function ladeStatistik() {
  fetch('http://127.0.0.1:5000/statistik') // dein Python-Server liefert das z. B.
    .then(res => res.json())
    .then(data => {
      // Gesamtmenge anzeigen
      document.getElementById("menge").textContent = `Menge: ${data.gesamt}`;

      // Highscore anzeigen
      const liste = document.getElementById("highscore-liste");
      liste.innerHTML = "";
      data.highscore.forEach(eintrag => {
        const li = document.createElement("li");
        li.textContent = `${eintrag.name} (${eintrag.anzahl})`;
        liste.appendChild(li);
      });
    });
}

// Beim Laden starten
window.onload = ladeStatistik;
