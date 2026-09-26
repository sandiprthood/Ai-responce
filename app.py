from flask import Flask, request, jsonify, render_template_string
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime

app = Flask(__name__)

# ============================================================
# DEMO DATA
# ============================================================

hospitals = [
    {
        "id": 1,
        "name": "CityCare Emergency Hospital",
        "lat": 18.5204,
        "lon": 73.8567,
        "type": ["General", "Trauma", "Cardiac"],
        "icu": 8,
        "beds": 25,
        "emergency": True
    },
    {
        "id": 2,
        "name": "Metro General Hospital",
        "lat": 18.5314,
        "lon": 73.8446,
        "type": ["General", "Trauma"],
        "icu": 5,
        "beds": 18,
        "emergency": True
    },
    {
        "id": 3,
        "name": "LifeLine Multi-Speciality Hospital",
        "lat": 18.5074,
        "lon": 73.8077,
        "type": ["General", "Cardiac"],
        "icu": 10,
        "beds": 30,
        "emergency": True
    },
    {
        "id": 4,
        "name": "District Trauma Centre",
        "lat": 18.5590,
        "lon": 73.7868,
        "type": ["Trauma"],
        "icu": 6,
        "beds": 20,
        "emergency": True
    }
]

ambulances = [
    {"id": "AMB-101", "status": "Available"},
    {"id": "AMB-102", "status": "On Route"},
    {"id": "AMB-103", "status": "Available"},
    {"id": "AMB-104", "status": "At Hospital"}
]

alerts = []


# ============================================================
# DISTANCE CALCULATION
# ============================================================

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


# ============================================================
# AI EMERGENCY SEVERITY ASSESSMENT
# ============================================================

def assess_emergency(data):

    age = int(data.get("age", 0))
    symptoms = data.get("symptoms", [])

    score = 0
    reasons = []

    severity_points = {
        "Unconscious": 5,
        "Severe bleeding": 5,
        "Breathing difficulty": 5,
        "Seizure": 5,
        "Chest pain": 4,
        "Major injury": 4,
        "Burns": 3,
        "Fracture": 2,
        "Minor injury": 1
    }

    for symptom in symptoms:

        if symptom in severity_points:
            score += severity_points[symptom]
            reasons.append(
                f"{symptom} (+{severity_points[symptom]})"
            )

    if age >= 65:
        score += 1
        reasons.append("Age 65+ (+1)")

    if 0 < age < 5:
        score += 1
        reasons.append("Child patient (+1)")

    if score >= 8:
        severity = "CRITICAL"

    elif score >= 5:
        severity = "HIGH"

    elif score >= 2:
        severity = "MODERATE"

    else:
        severity = "LOW"

    return severity, score, reasons


# ============================================================
# HOSPITAL RECOMMENDATION
# ============================================================

def recommend_hospitals(lat, lon, emergency_type):

    recommendations = []

    for hospital in hospitals:

        distance = calculate_distance(
            lat,
            lon,
            hospital["lat"],
            hospital["lon"]
        )

        score = distance

        # Suitable emergency department
        if emergency_type in hospital["type"]:
            score -= 3

        # ICU availability
        if hospital["icu"] > 0:
            score -= 1

        recommendations.append({
            "id": hospital["id"],
            "name": hospital["name"],
            "distance": round(distance, 2),
            "icu": hospital["icu"],
            "beds": hospital["beds"],
            "types": hospital["type"],
            "score": round(score, 2),
            "lat": hospital["lat"],
            "lon": hospital["lon"]
        })

    recommendations.sort(key=lambda x: x["score"])

    return recommendations


# ============================================================
# MAIN WEBPAGE
# ============================================================

HTML = """

<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1.0">

<title>AI Emergency Response</title>

<link rel="stylesheet"
href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>

<style>

*{
    box-sizing:border-box;
}

body{
    margin:0;
    font-family:Arial, sans-serif;
    background:#f4f7fb;
    color:#1f2937;
}

header{
    background:#b91c1c;
    color:white;
    padding:20px;
    text-align:center;
}

header h1{
    margin:0;
}

header p{
    margin:8px 0 0;
}

.container{
    width:95%;
    max-width:1200px;
    margin:20px auto;
}

.dashboard{
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:15px;
    margin-bottom:20px;
}

.card{
    background:white;
    padding:20px;
    border-radius:12px;
    box-shadow:0 3px 10px rgba(0,0,0,.08);
}

.card h3{
    margin-top:0;
}

.number{
    font-size:30px;
    font-weight:bold;
    color:#dc2626;
}

.form-card{
    background:white;
    padding:25px;
    border-radius:12px;
    box-shadow:0 3px 10px rgba(0,0,0,.08);
}

input, select{
    width:100%;
    padding:12px;
    margin:8px 0 15px;
    border:1px solid #d1d5db;
    border-radius:8px;
}

.symptoms{
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:10px;
    margin-bottom:20px;
}

.symptoms label{
    background:#f3f4f6;
    padding:10px;
    border-radius:8px;
}

button{
    border:0;
    padding:12px 18px;
    border-radius:8px;
    cursor:pointer;
    font-weight:bold;
}

.primary{
    background:#dc2626;
    color:white;
}

.secondary{
    background:#2563eb;
    color:white;
}

.success{
    background:#16a34a;
    color:white;
}

.result{
    margin-top:20px;
}

.severity{
    padding:20px;
    border-radius:12px;
    color:white;
    margin-bottom:20px;
}

.critical{
    background:#991b1b;
}

.high{
    background:#dc2626;
}

.moderate{
    background:#d97706;
}

.low{
    background:#16a34a;
}

.hospital{
    background:white;
    padding:18px;
    margin:10px 0;
    border-radius:10px;
    border-left:5px solid #2563eb;
    box-shadow:0 2px 7px rgba(0,0,0,.08);
}

.hospital button{
    margin-top:10px;
}

#map{
    height:450px;
    border-radius:12px;
    margin-top:20px;
}

.alert{
    background:white;
    padding:15px;
    margin:10px 0;
    border-left:5px solid #dc2626;
    border-radius:8px;
}

.hidden{
    display:none;
}

footer{
    text-align:center;
    padding:30px;
    color:#6b7280;
}

@media(max-width:800px){

    .dashboard{
        grid-template-columns:repeat(2,1fr);
    }

    .symptoms{
        grid-template-columns:1fr;
    }

}

@media(max-width:500px){

    .dashboard{
        grid-template-columns:1fr;
    }

}

</style>

</head>


<body>

<header>

<h1>🚑 AI Emergency Response</h1>

<p>Emergency Detection • Hospital Recommendation • Route Coordination</p>

</header>


<div class="container">


<!-- DASHBOARD -->

<div class="dashboard">

<div class="card">

<h3>🚨 Emergency Alerts</h3>

<div class="number" id="alertCount">0</div>

</div>


<div class="card">

<h3>🚑 Available Ambulances</h3>

<div class="number" id="ambulanceCount">0</div>

</div>


<div class="card">

<h3>🏥 Connected Hospitals</h3>

<div class="number" id="hospitalCount">0</div>

</div>


<div class="card">

<h3>🔔 Pre-Alerts Sent</h3>

<div class="number" id="preAlertCount">0</div>

</div>

</div>


<!-- EMERGENCY FORM -->

<div class="form-card">

<h2>🚨 Emergency Request</h2>

<label>Patient Name</label>

<input id="patientName"
placeholder="Enter patient name">


<label>Age</label>

<input id="age"
type="number"
placeholder="Enter age">


<label>Emergency Type</label>

<select id="emergencyType">

<option value="General">General</option>

<option value="Trauma">Road Accident / Trauma</option>

<option value="Cardiac">Cardiac Emergency</option>

</select>


<h3>Symptoms</h3>

<div class="symptoms">

<label>
<input type="checkbox" value="Unconscious">
Unconscious
</label>

<label>
<input type="checkbox" value="Severe bleeding">
Severe bleeding
</label>

<label>
<input type="checkbox" value="Breathing difficulty">
Breathing difficulty
</label>

<label>
<input type="checkbox" value="Chest pain">
Chest pain
</label>

<label>
<input type="checkbox" value="Major injury">
Major injury
</label>

<label>
<input type="checkbox" value="Seizure">
Seizure
</label>

<label>
<input type="checkbox" value="Burns">
Burns
</label>

<label>
<input type="checkbox" value="Fracture">
Fracture
</label>

<label>
<input type="checkbox" value="Minor injury">
Minor injury
</label>

</div>


<button class="primary"
onclick="analyzeEmergency()">

🤖 Analyze Emergency

</button>

</div>


<!-- RESULT -->

<div id="result"
class="result hidden">


<div id="severityBox"
class="severity">

<h2 id="severityText"></h2>

<p id="scoreText"></p>

<p id="reasonText"></p>

</div>


<h2>🏥 Recommended Hospitals</h2>

<div id="hospitals"></div>


<h2>🚑 Ambulance Assignment</h2>

<div class="card">

<p id="ambulanceText"></p>

<button class="secondary"
onclick="sendRoute()">

🗺️ Show Emergency Route

</button>

</div>


<button class="success"
onclick="sendPreAlert()">

🔔 Send Hospital Pre-Alert

</button>


<div id="map"></div>


</div>


<!-- ALERT HISTORY -->

<div class="form-card"
style="margin-top:20px">

<h2>🔔 Hospital Alert History</h2>

<div id="alerts"></div>

</div>


</div>


<footer>

AI Emergency Response Platform — Hackathon Prototype

<br>

⚠️ Demo system only. Not a clinical diagnostic system.

</footer>


<script
src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js">
</script>


<script>

let currentData = null;

let selectedHospital = null;

let map = null;

let routeLine = null;


// ============================================================
// MAP
// ============================================================

function initializeMap(){

    map = L.map("map").setView(
        [18.5204,73.8567],
        12
    );

    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            attribution:"© OpenStreetMap contributors"
        }
    ).addTo(map);
}


// ============================================================
// DASHBOARD
// ============================================================

async function loadDashboard(){

    const response =
        await fetch("/api/dashboard");

    const data =
        await response.json();

    document.getElementById("alertCount")
        .innerText = data.stats.alerts;

    document.getElementById("ambulanceCount")
        .innerText = data.stats.available_ambulances;

    document.getElementById("hospitalCount")
        .innerText = data.stats.hospitals;

    document.getElementById("preAlertCount")
        .innerText = data.stats.pre_alerts;


    const alertsDiv =
        document.getElementById("alerts");

    alertsDiv.innerHTML = "";

    data.alerts.forEach(alert => {

        alertsDiv.innerHTML += `

        <div class="alert">

        <b>🚨 ${alert.severity}</b>

        <br>

        Patient: ${alert.patient}

        <br>

        Hospital: ${alert.hospital}

        <br>

        Ambulance: ${alert.ambulance}

        <br>

        ${alert.time}

        </div>

        `;

    });

}


// ============================================================
// ANALYZE EMERGENCY
// ============================================================

async function analyzeEmergency(){

    const patientName =
        document.getElementById("patientName").value;

    const age =
        document.getElementById("age").value;

    const emergencyType =
        document.getElementById("emergencyType").value;


    if(!patientName || !age){

        alert("Please enter patient name and age.");

        return;

    }


    const checked =
        document.querySelectorAll(
            ".symptoms input:checked"
        );


    const symptoms =
        Array.from(checked)
        .map(x => x.value);


    const data = {

        patient_name:patientName,

        age:parseInt(age),

        emergency_type:emergencyType,

        symptoms:symptoms,

        latitude:18.5204,

        longitude:73.8567

    };


    const response =
        await fetch(
            "/api/assess",
            {
                method:"POST",

                headers:{
                    "Content-Type":
                    "application/json"
                },

                body:JSON.stringify(data)
            }
        );


    currentData =
        await response.json();


    document
        .getElementById("result")
        .classList.remove("hidden");


    const severity =
        currentData.severity.toLowerCase();


    const box =
        document.getElementById("severityBox");


    box.className =
        "severity " + severity;


    document.getElementById("severityText")
        .innerText =
        "AI Severity: " +
        currentData.severity;


    document.getElementById("scoreText")
        .innerText =
        "Severity Score: " +
        currentData.score;


    document.getElementById("reasonText")
        .innerText =
        "Reasons: " +
        currentData.reasons.join(", ");


    // Hospitals

    const hospitalDiv =
        document.getElementById("hospitals");

    hospitalDiv.innerHTML = "";


    currentData.hospitals.forEach(
        (hospital,index) => {

        hospitalDiv.innerHTML += `

        <div class="hospital">

        <h3>
        ${index === 0 ? "⭐ " : ""}
        ${hospital.name}
        </h3>

        <p>
        📍 Distance:
        ${hospital.distance} km
        </p>

        <p>
        🛏️ Beds:
        ${hospital.beds}
        </p>

        <p>
        🏥 ICU:
        ${hospital.icu}
        </p>

        <p>
        Emergency:
        ${hospital.types.join(", ")}
        </p>

        <button
        class="secondary"
        onclick="selectHospital(${hospital.id})">

        Select Hospital

        </button>

        </div>

        `;

    });


    document.getElementById("ambulanceText")
        .innerText =
        currentData.ambulance
        ? "Assigned Ambulance: " +
        currentData.ambulance.id
        : "No ambulance currently available.";

}


// ============================================================
// SELECT HOSPITAL
// ============================================================

function selectHospital(id){

    selectedHospital =
        currentData.hospitals.find(
            h => h.id === id
        );


    alert(
        "Selected Hospital: " +
        selectedHospital.name
    );

}


// ============================================================
// ROUTE
// ============================================================

async function sendRoute(){

    if(!currentData){

        alert("Analyze emergency first.");

        return;

    }


    if(!selectedHospital){

        selectedHospital =
            currentData.hospitals[0];

    }


    const response =
        await fetch(
            "/api/route",
            {
                method:"POST",

                headers:{
                    "Content-Type":
                    "application/json"
                },

                body:JSON.stringify({

                    patient_lat:
                    currentData.patient_location.lat,

                    patient_lon:
                    currentData.patient_location.lon,

                    hospital_lat:
                    selectedHospital.lat,

                    hospital_lon:
                    selectedHospital.lon

                })

            }
        );


    const data =
        await response.json();


    if(routeLine){

        map.removeLayer(routeLine);

    }


    routeLine =
        L.polyline(
            data.route,
            {
                weight:6
            }
        ).addTo(map);


    map.fitBounds(
        routeLine.getBounds()
    );


    L.marker(
        [
            currentData.patient_location.lat,
            currentData.patient_location.lon
        ]
    )
    .addTo(map)
    .bindPopup("🚑 Emergency Location")
    .openPopup();


    L.marker(
        [
            selectedHospital.lat,
            selectedHospital.lon
        ]
    )
    .addTo(map)
    .bindPopup(
        "🏥 " +
        selectedHospital.name
    );


    alert(
        "Route calculated! ETA: " +
        data.eta +
        " minutes"
    );

}


// ============================================================
// PRE ALERT
// ============================================================

async function sendPreAlert(){

    if(!currentData){

        alert("Analyze emergency first.");

        return;

    }


    if(!selectedHospital){

        selectedHospital =
            currentData.hospitals[0];

    }


    const ambulance =
        currentData.ambulance;


    const response =
        await fetch(
            "/api/pre-alert",
            {
                method:"POST",

                headers:{
                    "Content-Type":
                    "application/json"
                },

                body:JSON.stringify({

                    patient:
                    currentData.patient_name,

                    severity:
                    currentData.severity,

                    hospital:
                    selectedHospital.name,

                    ambulance:
                    ambulance
                    ? ambulance.id
                    : "Not Available"

                })

            }
        );


    const data =
        await response.json();


    alert(data.message);

    loadDashboard();

}


// ============================================================
// START
// ============================================================

initializeMap();

loadDashboard();

</script>


</body>

</html>

"""


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def home():

    return render_template_string(HTML)


@app.route("/api/dashboard")
def dashboard():

    available =
        sum(
            1 for ambulance in ambulances
            if ambulance["status"] == "Available"
        )

    return jsonify({

        "hospitals": hospitals,

        "ambulances": ambulances,

        "alerts": alerts,

        "stats": {

            "alerts": len(alerts),

            "available_ambulances":
            available,

            "hospitals":
            len(hospitals),

            "pre_alerts":
            len(alerts)

        }

    })


@app.route("/api/assess", methods=["POST"])
def assess():

    data = request.json

    severity, score, reasons = \
        assess_emergency(data)


    lat = float(
        data.get("latitude", 18.5204)
    )

    lon = float(
        data.get("longitude", 73.8567)
    )


    recommendations = \
        recommend_hospitals(
            lat,
            lon,
            data.get(
                "emergency_type",
                "General"
            )
        )


    available_ambulance = next(

        (
            ambulance
            for ambulance in ambulances
            if ambulance["status"]
            == "Available"
        ),

        None

    )


    return jsonify({

        "patient_name":
        data.get("patient_name"),

        "severity":
        severity,

        "score":
        score,

        "reasons":
        reasons,

        "hospitals":
        recommendations,

        "ambulance":
        available_ambulance,

        "patient_location":{

            "lat":lat,

            "lon":lon

        }

    })


@app.route("/api/route", methods=["POST"])
def route():

    data = request.json


    lat1 =
        float(data["patient_lat"])

    lon1 =
        float(data["patient_lon"])

    lat2 =
        float(data["hospital_lat"])

    lon2 =
        float(data["hospital_lon"])


    distance =
        calculate_distance(
            lat1,
            lon1,
            lat2,
            lon2
        )


    # Demo ETA
    eta =
        max(
            3,
            round(
                distance / 0.6
            )
        )


    route = [

        [lat1, lon1],

        [
            (lat1 + lat2) / 2,
            (lon1 + lon2) / 2
        ],

        [lat2, lon2]

    ]


    return jsonify({

        "distance":
        round(distance, 2),

        "eta":
        eta,

        "route":
        route

    })


@app.route("/api/pre-alert", methods=["POST"])
def pre_alert():

    data = request.json


    alert = {

        "patient":
        data.get("patient"),

        "severity":
        data.get("severity"),

        "hospital":
        data.get("hospital"),

        "ambulance":
        data.get("ambulance"),

        "time":
        datetime.now().strftime(
            "%d-%m-%Y %H:%M:%S"
        )

    }


    alerts.append(alert)


    # Update ambulance
    for ambulance in ambulances:

        if ambulance["id"] == \
                data.get("ambulance"):

            ambulance["status"] = \
                "On Route"


    return jsonify({

        "success":True,

        "message":
        "Hospital pre-alert sent successfully!"

    })


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
