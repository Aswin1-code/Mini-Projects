#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <MPU6050.h>
#include <math.h>

MPU6050 mpu;

// ================= WiFi =================
const char* ssid = "ESP32_Swing";
const char* password = "12345678";

WebServer server(80);

// ================= Pins =================
#define LED_PIN 2
#define BTN_CALIB 22
#define BTN_GAME  23

// ================= Modes =================
enum Mode {
  IDLE,
  CALIBRATION,
  GAME
};

Mode currentMode = IDLE;

// ================= Detection =================
float START_THRESHOLD = 15.0;
float END_THRESHOLD   = 7.0;

float MIN_DURATION = 0.20;
unsigned long COOLDOWN = 400;

// ================= Offsets =================
float axO=0, ayO=0, azO=0;
float gxO=0, gyO=0, gzO=0;

// ================= Swing =================
bool swing = false;
unsigned long swingStart = 0;
unsigned long lastSwingEnd = 0;

float peakSpeed = 0;
float maxImpact = 0;

// ================= Gravity =================
float gravity = 0;
float alpha = 0.95;

// ================= Live =================
float live_ax=0, live_ay=0, live_az=0;
float live_gx=0, live_gy=0, live_gz=0;
float live_speed=0, live_impact=0, live_duration=0;

unsigned long live_time = 0;
int swingCount = 0;

// ================= CSV =================
String csvData = "timestamp,ax,ay,az,gx,gy,gz,speed,impact,duration\n";

// ================= Button =================
bool lastCalibState = HIGH;
bool lastGameState = HIGH;

// ================= HTML =================
const char htmlPage[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Dashboard</title>
</head>
<body style="background:#111;color:white;text-align:center;">
<h1>🏸 Smart Racket Dashboard</h1>
<p id="mode">Mode: --</p>
<p id="speed">Speed: --</p>
<p id="impact">Impact: --</p>
<p id="count">Swings: --</p>
<button onclick="downloadCSV()">Download CSV</button>

<script>
async function update(){
  let res = await fetch('/data');
  let d = await res.json();

  document.getElementById("mode").innerText="Mode: "+d.mode;
  document.getElementById("speed").innerText="Speed: "+d.speed;
  document.getElementById("impact").innerText="Impact: "+d.impact;
  document.getElementById("count").innerText="Swings: "+d.count;
}
setInterval(update,200);

function downloadCSV(){
  window.location.href="/download/swing data";
}
</script>
</body>
</html>
)rawliteral";

// ================= Web =================
void handleRoot() {
  server.send(200, "text/html", htmlPage);
}

void handleData() {
  String modeStr = (currentMode==CALIBRATION)?"CALIBRATION":
                   (currentMode==GAME)?"GAME":"IDLE";

  String json="{";
  json += "\"mode\":\""+modeStr+"\",";
  json += "\"speed\":"+String(live_speed)+",";
  json += "\"impact\":"+String(live_impact)+",";
  json += "\"count\":"+String(swingCount);
  json += "}";

  server.send(200,"application/json",json);
}

void handleDownload() {
  server.sendHeader("Content-Disposition","attachment; filename=badminton_data.csv");
  server.send(200,"text/csv",csvData);

  // RESET AFTER DOWNLOAD
  csvData = "timestamp,ax,ay,az,gx,gy,gz,speed,impact,duration\n";
  swingCount = 0;
}

// ================= Setup =================
void setup() {
  Serial.begin(115200);
  Wire.begin(26,25);

  pinMode(LED_PIN, OUTPUT);
  pinMode(BTN_CALIB, INPUT_PULLUP);
  pinMode(BTN_GAME, INPUT_PULLUP);

  mpu.initialize();

  WiFi.softAP(ssid,password);

  server.on("/",handleRoot);
  server.on("/data",handleData);
  server.on("/download",handleDownload);
  server.begin();

  Serial.println("READY");
}

// ================= Loop =================
void loop() {
  server.handleClient();

  // ========= BUTTON LOGIC =========
  bool calibState = digitalRead(BTN_CALIB);
  bool gameState  = digitalRead(BTN_GAME);

  // ---- Calibration Button ----
  if (lastCalibState==HIGH && calibState==LOW) {

    if (currentMode != CALIBRATION) {
      currentMode = CALIBRATION;
      Serial.println("CALIBRATION START");
    } else {
      currentMode = IDLE;
      Serial.println("CALIBRATION STOP -> Download");
    }

    delay(300);
  }

  // ---- Game Button ----
  if (lastGameState==HIGH && gameState==LOW) {

    if (currentMode != GAME) {
      currentMode = GAME;
      Serial.println("GAME START");
    } else {
      currentMode = IDLE;
      Serial.println("GAME STOP -> Download");
    }

    delay(300);
  }

  lastCalibState = calibState;
  lastGameState = gameState;

  // ========= SENSOR =========
  int16_t ax,ay,az,gx,gy,gz;
  mpu.getMotion6(&ax,&ay,&az,&gx,&gy,&gz);

  float Ax=(ax-axO)/16384.0;
  float Ay=(ay-ayO)/16384.0;
  float Az=(az-azO)/16384.0;

  float Gx=(gx-gxO)/131.0;
  float Gy=(gy-gyO)/131.0;
  float Gz=(gz-gzO)/131.0;

  gravity = alpha*gravity+(1-alpha)*Az;

  float linAccZ=(Az-gravity)*9.81;

  float totalAcc = sqrt(Ax*Ax+Ay*Ay+linAccZ*linAccZ);
  float angularVelocity = sqrt(Gx*Gx+Gy*Gy+Gz*Gz);
  float instantSpeed = angularVelocity * 0.12;

  unsigned long now = millis();

  // ========= RECORD ONLY IN MODES =========
  if (currentMode == CALIBRATION || currentMode == GAME) {

    if (!swing && totalAcc > START_THRESHOLD) {
      swing = true;
      swingStart = now;
      peakSpeed = instantSpeed;
      maxImpact = totalAcc;
      digitalWrite(LED_PIN,HIGH);
    }

    if (swing) {

      if (instantSpeed > peakSpeed) peakSpeed = instantSpeed;
      if (totalAcc > maxImpact) maxImpact = totalAcc;

      float duration = (now - swingStart)/1000.0;

      if (totalAcc < END_THRESHOLD && duration > MIN_DURATION) {

        swingCount++;

        live_speed = peakSpeed;
        live_impact = maxImpact;

        csvData += String(now)+","+String(Ax)+","+String(Ay)+","+String(Az)+",";
        csvData += String(Gx)+","+String(Gy)+","+String(Gz)+",";
        csvData += String(peakSpeed)+","+String(maxImpact)+","+String(duration)+"\n";

        swing = false;
        digitalWrite(LED_PIN,LOW);
      }
    }
  }

  delay(10);
}