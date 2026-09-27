#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <RTClib.h>

// ---------------- I2C Pin Custom Mapping (DS3231) ----------------
const int I2C_SDA = 27;
const int I2C_SCL = 26;

RTC_DS3231 rtc;

// ---------------- WiFi AP Config ----------------
const char* ssid = "Badminton AI";
const char* password = "hello123";

WebServer server(80);

// ---------------- LED Pin Config ----------------
const int LED_PIN = 33;
const int LED_BRIGHTNESS = 50;      // out of 255
const int LED_PWM_FREQ = 5000;      // 5 kHz
const int LED_PWM_RESOLUTION = 8;   // 0-255

// ---------------- Alarm & Blink State ----------------
int alarmHour = -1;
int alarmMinute = -1;
bool alarmActive = false;

bool isLedBlinking = false;
unsigned long alarmStartMillis = 0;
const unsigned long ALARM_DURATION_MS = 60000;  // 1 minute
const unsigned long BLINK_INTERVAL_MS = 500;    // 500ms ON, 500ms OFF
bool ledState = false;
unsigned long lastBlinkToggle = 0;

// =====================================================
// HTML DASHBOARD
// =====================================================
const char htmlPage[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Badminton LED Alarm Dashboard</title>
<style>
body { font-family: Arial; background: #111; color: white; text-align: center; padding: 20px; }
.box { background: #1f1f1f; padding: 25px; border-radius: 10px; display: inline-block; text-align: left; min-width: 420px; }
p { font-size: 18px; margin: 12px 0; }
input[type="time"] { background: #333; color: white; border: 1px solid #555; padding: 8px; font-size: 16px; border-radius: 6px; width: 100%; box-sizing: border-box; }
button { margin-top: 20px; padding: 10px 20px; font-size: 16px; border: none; border-radius: 8px; cursor: pointer; color: white; width: 100%; }
.btn-green { background: #28a745; }
.btn-green:hover { background: #218838; }
.btn-blue { background: #007bff; }
.btn-blue:hover { background: #0069d9; }
hr { border: 0; border-top: 1px solid #444; margin: 20px 0; }
</style>
</head>
<body>

<h1>🏸 Badminton System Controls</h1>

<div class="box">
  <p id="clock-status">RTC Time: Loading...</p>
  <p id="alarm-status">Alarm Config: Not Set</p>
  <p id="led-status">LED: OFF</p>
  <hr>

  <p style="font-size:15px; color:#aaa;">Sync RTC clock to your laptop's current time:</p>
  <button class="btn-blue" onclick="syncRtc()">Sync RTC to Laptop Time</button>
  <hr>

  <label style="font-size: 16px;" for="alarm-time">Set Alarm Trigger Time:</label>
  <input type="time" id="alarm-time" required>
  <button class="btn-green" onclick="saveAlarm()">Save Alarm</button>
</div>

<script>
async function updateData() {
  try {
    const res = await fetch('/data');
    const data = await res.json();
    document.getElementById("clock-status").innerText = "RTC Time: " + data.currentTime;
    document.getElementById("alarm-status").innerText = "Alarm Config: " + data.activeAlarm;
    document.getElementById("led-status").innerText = "LED: " + data.ledState;
  } catch(e) { }
}

setInterval(updateData, 1000);

async function syncRtc() {
  const now = new Date();
  const timeVal = now.toTimeString().slice(0, 8);   // "HH:MM:SS"
  const dateVal = now.toISOString().slice(0, 10);   // "YYYY-MM-DD"
  const res = await fetch('/set-rtc?time=' + timeVal + '&date=' + dateVal);
  alert(await res.text());
}

async function saveAlarm() {
  const timeVal = document.getElementById("alarm-time").value;
  if(!timeVal) {
    alert("Please select a time first.");
    return;
  }
  const res = await fetch('/set-alarm?time=' + timeVal);
  alert(await res.text());
}
</script>

</body>
</html>
)rawliteral";

// =====================================================
// LED HELPERS  (must be called AFTER ledcAttach in setup)
// =====================================================
void ledOn() {
  ledcWrite(LED_PIN, LED_BRIGHTNESS);
}

void ledOff() {
  ledcWrite(LED_PIN, 0);
}

// =====================================================
// WEB HANDLERS
// =====================================================
void handleRoot() {
  server.send(200, "text/html", htmlPage);
}

void handleData() {
  DateTime now = rtc.now();

  char timeStr[32];
  if (now.isValid()) {
    sprintf(timeStr, "%02d:%02d:%02d", now.hour(), now.minute(), now.second());
  } else {
    sprintf(timeStr, "RTC ERROR");
  }

  String alarmStr = "Not Set";
  if (alarmHour != -1) {
    char aStr[16];
    sprintf(aStr, "%02d:%02d", alarmHour, alarmMinute);
    alarmStr = String(aStr);
  }

  String ledStr = (isLedBlinking || ledState) ? "BLINKING" : "OFF";

  String json = "{";
  json += "\"currentTime\":\"" + String(timeStr) + "\",";
  json += "\"activeAlarm\":\"" + alarmStr + "\",";
  json += "\"ledState\":\"" + ledStr + "\"";
  json += "}";

  server.send(200, "application/json", json);
}

void handleSetRtc() {
  if (server.hasArg("time") && server.hasArg("date")) {
    String t = server.arg("time");
    String d = server.arg("date");

    int year   = d.substring(0, 4).toInt();
    int month  = d.substring(5, 7).toInt();
    int day    = d.substring(8, 10).toInt();
    int hour   = t.substring(0, 2).toInt();
    int minute = t.substring(3, 5).toInt();
    int second = t.substring(6, 8).toInt();

    rtc.adjust(DateTime(year, month, day, hour, minute, second));
    server.send(200, "text/plain", "RTC synced to laptop time!");
  } else {
    server.send(400, "text/plain", "Error: Missing time/date parameter.");
  }
}

void handleSetAlarm() {
  if (server.hasArg("time")) {
    String inputTime = server.arg("time");

    alarmHour   = inputTime.substring(0, 2).toInt();
    alarmMinute = inputTime.substring(3, 5).toInt();
    alarmActive = true;

    isLedBlinking = false;
    ledState = false;
    ledOff();

    server.send(200, "text/plain", "Alarm configuration saved successfully!");
  } else {
    server.send(400, "text/plain", "Error: Missing time parameter.");
  }
}

// =====================================================
// SETUP
// =====================================================
void setup() {
  Serial.begin(115200);

  // 1. I2C
  Wire.begin(I2C_SDA, I2C_SCL);

  // 2. RTC
  if (!rtc.begin()) {
    Serial.println("Couldn't find RTC! Check wiring (SDA->27, SCL->26).");
    while (1) delay(10);
  }

  if (rtc.lostPower()) {
    Serial.println("RTC lost power — sync time from the dashboard!");
  }

  DateTime now = rtc.now();
  if (now.isValid()) {
    Serial.printf("Current RTC time: %02d:%02d:%02d\n",
                  now.hour(), now.minute(), now.second());
  }

  // 3. LED — attach FIRST, then write (core 3.x API)
  ledcAttach(LED_PIN, LED_PWM_FREQ, LED_PWM_RESOLUTION);
  ledOff();

  // 4. WiFi AP
  WiFi.softAP(ssid, password);
  Serial.println("Access Point Started.");

  // 5. Web server
  server.on("/", handleRoot);
  server.on("/data", handleData);
  server.on("/set-rtc", handleSetRtc);
  server.on("/set-alarm", handleSetAlarm);
  server.begin();
  Serial.println("Web Server running.");
}

// =====================================================
// LOOP
// =====================================================
void loop() {
  server.handleClient();

  unsigned long currentMillis = millis();

  // ---- Read RTC safely ----
  DateTime now = rtc.now();
  if (!now.isValid()) {
    return;  // RTC not responding — skip this cycle
  }

  // ---- Alarm trigger ----
  if (alarmActive && now.hour() == alarmHour && now.minute() == alarmMinute) {
    isLedBlinking = true;
    alarmStartMillis = currentMillis;
    lastBlinkToggle = currentMillis;
    ledState = true;
    ledOn();
    alarmActive = false;
    Serial.println("Alarm triggered! LED blinking for 1 minute.");
  }

  // ---- Non-blocking blink for 1 minute ----
  if (isLedBlinking) {
    if (currentMillis - alarmStartMillis >= ALARM_DURATION_MS) {
      isLedBlinking = false;
      ledOff();
      ledState = false;
      Serial.println("Alarm duration over. LED OFF.");
    }
    else if (currentMillis - lastBlinkToggle >= BLINK_INTERVAL_MS) {
      lastBlinkToggle = currentMillis;
      ledState = !ledState;
      if (ledState) {
        ledOn();
      } else {
        ledOff();
      }
    }
  }
}