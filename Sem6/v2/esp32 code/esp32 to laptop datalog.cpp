#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <MPU6050.h>
#include <math.h>

MPU6050 mpu;

// =====================================================
// BADMINTON SWING ANALYZER
// SAME STABLE LOGIC + SIMPLE WEB UI + CSV DOWNLOAD
// =====================================================

// ---------------- WiFi AP ----------------
const char* ssid = "ESP32_Swing";
const char* password = "12345678";

WebServer server(80);

// ---------------- LED ----------------
#define LED_PIN 2

// ---------------- Detection Thresholds ----------------
float START_THRESHOLD = 15.0;
float END_THRESHOLD   = 7.0;

float MIN_DURATION = 0.20;
unsigned long COOLDOWN = 400;

// ---------------- Offsets ----------------
float axO = 0;
float ayO = 0;
float azO = 0;

float gxO = 0;
float gyO = 0;
float gzO = 0;

// ---------------- Swing State ----------------
bool swing = false;

unsigned long swingStart = 0;
unsigned long lastSwingEnd = 0;

float peakSpeed = 0;
float maxImpact = 0;

// ---------------- Gravity Filter ----------------
float gravity = 0;
float alpha = 0.95;

// ---------------- Live Data ----------------
float live_ax = 0;
float live_ay = 0;
float live_az = 0;

float live_gx = 0;
float live_gy = 0;
float live_gz = 0;

float live_speed = 0;
float live_impact = 0;
float live_duration = 0;

unsigned long live_time = 0;
int swingCount = 0;

// ---------------- CSV Storage ----------------
String csvData =
"timestamp,ax,ay,az,gx,gy,gz,speed,impact,duration\n";

// =====================================================
// SIMPLE FAST HTML DASHBOARD
// =====================================================
const char htmlPage[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Badminton Swing Dashboard</title>

<style>
body {
  font-family: Arial;
  background: #111;
  color: white;
  text-align: center;
  padding: 20px;
}

.box {
  background: #1f1f1f;
  padding: 20px;
  border-radius: 10px;
  display: inline-block;
  text-align: left;
  min-width: 420px;
}

p {
  font-size: 18px;
  margin: 8px 0;
}

button {
  margin-top: 20px;
  padding: 10px 20px;
  font-size: 16px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}
</style>
</head>
<body>

<h1>🏸 Badminton Swing Dashboard</h1>

<div class="box">

  <p id="time">Timestamp : --</p>

  <p id="ax">AX : --</p>
  <p id="ay">AY : --</p>
  <p id="az">AZ : --</p>

  <p id="gx">GX : --</p>
  <p id="gy">GY : --</p>
  <p id="gz">GZ : --</p>

  <p id="speed">Speed : -- km/h</p>
  <p id="impact">Impact : -- m/s²</p>
  <p id="duration">Duration : -- sec</p>

  <p id="count">Swing Count : 0</p>

  <button onclick="downloadCSV()">Download CSV</button>

</div>

<script>
async function updateData() {
  const res = await fetch('/data');
  const data = await res.json();

  document.getElementById("time").innerText =
    "Timestamp : " + data.time;

  document.getElementById("ax").innerText =
    "AX : " + data.ax.toFixed(2);

  document.getElementById("ay").innerText =
    "AY : " + data.ay.toFixed(2);

  document.getElementById("az").innerText =
    "AZ : " + data.az.toFixed(2);

  document.getElementById("gx").innerText =
    "GX : " + data.gx.toFixed(2);

  document.getElementById("gy").innerText =
    "GY : " + data.gy.toFixed(2);

  document.getElementById("gz").innerText =
    "GZ : " + data.gz.toFixed(2);

  document.getElementById("speed").innerText =
    "Speed : " + data.speed.toFixed(2) + " km/h";

  document.getElementById("impact").innerText =
    "Impact : " + data.impact.toFixed(2) + " m/s²";

  document.getElementById("duration").innerText =
    "Duration : " + data.duration.toFixed(2) + " sec";

  document.getElementById("count").innerText =
    "Swing Count : " + data.count;
}

// Fast refresh with low lag
setInterval(updateData, 100);

function downloadCSV() {
  window.location.href = "/download";
}
</script>

</body>
</html>
)rawliteral";

// =====================================================
// WEB HANDLERS
// =====================================================
void handleRoot() {
  server.send(200, "text/html", htmlPage);
}

void handleData() {
  String json = "{";

  json += "\"time\":" + String(live_time) + ",";

  json += "\"ax\":" + String(live_ax) + ",";
  json += "\"ay\":" + String(live_ay) + ",";
  json += "\"az\":" + String(live_az) + ",";

  json += "\"gx\":" + String(live_gx) + ",";
  json += "\"gy\":" + String(live_gy) + ",";
  json += "\"gz\":" + String(live_gz) + ",";

  json += "\"speed\":" + String(live_speed) + ",";
  json += "\"impact\":" + String(live_impact) + ",";
  json += "\"duration\":" + String(live_duration) + ",";

  json += "\"count\":" + String(swingCount);

  json += "}";

  server.send(200, "application/json", json);
}

void handleDownload() {
  server.sendHeader(
    "Content-Disposition",
    "attachment; filename=badminton_data.csv"
  );

  server.send(200, "text/csv", csvData);
}

// =====================================================
// SETUP
// =====================================================
void setup() {
  Serial.begin(115200);
  Wire.begin(26, 25);

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  mpu.initialize();

  if (!mpu.testConnection()) {
    Serial.println("MPU6050 FAILED");
    while (1);
  }

  Serial.println("Calibrating... keep racket still for 3 sec");

  // ---------------- Calibration ----------------
  long ax = 0, ay = 0, az = 0;
  long gx = 0, gy = 0, gz = 0;
  int n = 0;

  unsigned long t = millis();

  while (millis() - t < 3000) {
    int16_t a, b, c, d, e, f;
    mpu.getMotion6(&a, &b, &c, &d, &e, &f);

    ax += a;
    ay += b;
    az += c;

    gx += d;
    gy += e;
    gz += f;

    n++;
    delay(2);
  }

  axO = ax / (float)n;
  ayO = ay / (float)n;
  azO = az / (float)n;

  gxO = gx / (float)n;
  gyO = gy / (float)n;
  gzO = gz / (float)n;

  Serial.println("Calibration Done");

  // ---------------- WiFi ----------------
  WiFi.softAP(ssid, password);

  Serial.println("WiFi Started");
  Serial.print("Connect to IP: ");
  Serial.println(WiFi.softAPIP());

  // ---------------- Server ----------------
  server.on("/", handleRoot);
  server.on("/data", handleData);
  server.on("/download", handleDownload);

  server.begin();

  Serial.println(
    "timestamp,ax,ay,az,gx,gy,gz,speed,impact,duration"
  );
}

// =====================================================
// LOOP
// =====================================================
void loop() {
  server.handleClient();

  int16_t ax, ay, az, gx, gy, gz;
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

  // ---------- Accelerometer ----------
  float Ax = (ax - axO) / 16384.0;
  float Ay = (ay - ayO) / 16384.0;
  float Az = (az - azO) / 16384.0;

  // ---------- Gyroscope ----------
  float Gx = (gx - gxO) / 131.0;
  float Gy = (gy - gyO) / 131.0;
  float Gz = (gz - gzO) / 131.0;

  // ---------- Gravity Removal ----------
  gravity = alpha * gravity + (1 - alpha) * Az;

  float linAccX = Ax * 9.81;
  float linAccY = Ay * 9.81;
  float linAccZ = (Az - gravity) * 9.81;

  float totalAcc = sqrt(
    linAccX * linAccX +
    linAccY * linAccY +
    linAccZ * linAccZ
  );

  // ---------- Peak Rotational Speed ----------
  float angularVelocity = sqrt(
    Gx * Gx +
    Gy * Gy +
    Gz * Gz
  );

  // Same stable speed logic
  float instantSpeed = angularVelocity * 0.12;

  unsigned long now = millis();

  // =================================================
  // START SWING
  // =================================================
  if (!swing &&
      totalAcc > START_THRESHOLD &&
      (now - lastSwingEnd > COOLDOWN)) {

    swing = true;
    swingStart = now;

    peakSpeed = instantSpeed;
    maxImpact = totalAcc;

    digitalWrite(LED_PIN, HIGH);
  }

  // =================================================
  // DURING SWING
  // =================================================
  if (swing) {

    if (instantSpeed > peakSpeed)
      peakSpeed = instantSpeed;

    if (totalAcc > maxImpact)
      maxImpact = totalAcc;

    float duration = (now - swingStart) / 1000.0;

    // =================================================
    // END SWING
    // =================================================
    if (totalAcc < END_THRESHOLD &&
        duration > MIN_DURATION) {

      swingCount++;

      // update live data
      live_time = now;

      live_ax = Ax;
      live_ay = Ay;
      live_az = Az;

      live_gx = Gx;
      live_gy = Gy;
      live_gz = Gz;

      live_speed = peakSpeed;
      live_impact = maxImpact;
      live_duration = duration;

      // ---------- Serial Output ----------
      Serial.print(now); Serial.print(",");
      Serial.print(Ax, 2); Serial.print(",");
      Serial.print(Ay, 2); Serial.print(",");
      Serial.print(Az, 2); Serial.print(",");
      Serial.print(Gx, 2); Serial.print(",");
      Serial.print(Gy, 2); Serial.print(",");
      Serial.print(Gz, 2); Serial.print(",");
      Serial.print(peakSpeed, 2); Serial.print(",");
      Serial.print(maxImpact, 2); Serial.print(",");
      Serial.println(duration, 2);

      // ---------- CSV Save ----------
      csvData += String(now) + ",";
      csvData += String(Ax) + ",";
      csvData += String(Ay) + ",";
      csvData += String(Az) + ",";
      csvData += String(Gx) + ",";
      csvData += String(Gy) + ",";
      csvData += String(Gz) + ",";
      csvData += String(peakSpeed) + ",";
      csvData += String(maxImpact) + ",";
      csvData += String(duration) + "\n";

      swing = false;
      lastSwingEnd = now;

      digitalWrite(LED_PIN, LOW);
    }
  }

  delay(10);
}