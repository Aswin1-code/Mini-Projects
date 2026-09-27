#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <RTClib.h>
#include <Preferences.h>

// =====================================================
// PIN CONFIGURATION
// =====================================================

const int I2C_SDA = 27;
const int I2C_SCL = 26;

const int BUZZER_PIN = 33;
const int LED_PIN = 25;

const int ALARM_OFF_PIN = 16;

// =====================================================
// RTC
// =====================================================

RTC_DS3231 rtc;

// =====================================================
// WIFI AP
// =====================================================

const char* ssid = "smartAlarm";
const char* password = "hello123";

WebServer server(80);

// =====================================================
// PREFERENCES
// =====================================================

Preferences preferences;

// =====================================================
// ALARM CONFIGURATION
// =====================================================

const int MAX_ALARMS = 10;

struct Alarm {
  int hour;
  int minute;

  bool enabled;
  bool daily;

  // Prevent the same alarm from triggering repeatedly
  // during the same minute.
  int lastTriggeredYear;
  int lastTriggeredMonth;
  int lastTriggeredDay;
};

Alarm alarms[MAX_ALARMS];

// =====================================================
// SYSTEM STATE
// =====================================================

enum AlarmState {
  ALARM_IDLE,
  ALARM_RINGING,
  ALARM_ESCALATED,
  ALARM_DISMISSED
};

AlarmState alarmState = ALARM_IDLE;

// Index of currently active alarm
int activeAlarmIndex = -1;

// =====================================================
// ALARM TIMING
// =====================================================

// Initial alarm escalation period.
// Currently 3 minutes.
//
// Example:
//
// 07:00:00 -> normal alarm
// 07:03:00 -> escalation
// 07:06:00 -> another escalation
// etc.

const unsigned long ESCALATION_INTERVAL_MS = 3UL * 60UL * 1000UL;

// =====================================================
// ALARM OUTPUT STATE
// =====================================================

bool buzzerState = false;
bool ledState = false;

unsigned long alarmStartedMillis = 0;
unsigned long lastPatternMillis = 0;

int currentAlarmLevel = 0;

// =====================================================
// BUZZER PATTERN
// =====================================================
//
// We are NOT implementing actual music yet.
//
// Instead, different levels use different beep patterns.
//
// Level 0 = normal
// Level 1 = faster
// Level 2 = faster still
// Level 3+ = repeating rapid pattern
//
// Later this can be replaced with more interesting
// random sound/music patterns.
// =====================================================

void buzzerOn() {
  digitalWrite(BUZZER_PIN, HIGH);
  buzzerState = true;
}

void buzzerOff() {
  digitalWrite(BUZZER_PIN, LOW);
  buzzerState = false;
}

void ledOn() {
  digitalWrite(LED_PIN, HIGH);
  ledState = true;
}

void ledOff() {
  digitalWrite(LED_PIN, LOW);
  ledState = false;
}

// =====================================================
// ALARM PATTERN
// =====================================================

void updateAlarmPattern() {

  unsigned long nowMillis = millis();

  unsigned long interval;

  if (currentAlarmLevel == 0) {
    // Normal alarm
    interval = 1000;
  }
  else if (currentAlarmLevel == 1) {
    // Faster
    interval = 500;
  }
  else if (currentAlarmLevel == 2) {
    // Faster again
    interval = 250;
  }
  else {
    // Rapid
    interval = 120;
  }

  if (nowMillis - lastPatternMillis >= interval) {

    lastPatternMillis = nowMillis;

    buzzerState = !buzzerState;
    ledState = buzzerState;

    if (buzzerState) {
      buzzerOn();
      ledOn();
    }
    else {
      buzzerOff();
      ledOff();
    }
  }
}

// =====================================================
// CLEAR ALARM OUTPUT
// =====================================================

void stopAlarmOutput() {

  buzzerOff();
  ledOff();

  currentAlarmLevel = 0;
}

// =====================================================
// ALARM STATE TEXT
// =====================================================

String getAlarmStateText() {

  switch (alarmState) {

    case ALARM_IDLE:
      return "IDLE";

    case ALARM_RINGING:
      return "RINGING";

    case ALARM_ESCALATED:
      return "ESCALATED";

    case ALARM_DISMISSED:
      return "DISMISSED";
  }

  return "UNKNOWN";
}

// =====================================================
// FORMAT ALARM TIME
// =====================================================

String formatAlarmTime(int hour, int minute) {

  char buffer[10];

  sprintf(buffer, "%02d:%02d", hour, minute);

  return String(buffer);
}

// =====================================================
// SAVE ALARMS TO PREFERENCES
// =====================================================

void saveAlarms() {

  preferences.begin("alarmData", false);

  preferences.putUInt("count", MAX_ALARMS);

  for (int i = 0; i < MAX_ALARMS; i++) {

    String keyHour = "h" + String(i);
    String keyMin  = "m" + String(i);
    String keyEn   = "e" + String(i);
    String keyDaily = "d" + String(i);

    preferences.putInt(keyHour.c_str(), alarms[i].hour);
    preferences.putInt(keyMin.c_str(), alarms[i].minute);
    preferences.putBool(keyEn.c_str(), alarms[i].enabled);
    preferences.putBool(keyDaily.c_str(), alarms[i].daily);
  }

  preferences.end();
}

// =====================================================
// LOAD ALARMS FROM PREFERENCES
// =====================================================

void loadAlarms() {

  preferences.begin("alarmData", true);

  for (int i = 0; i < MAX_ALARMS; i++) {

    String keyHour = "h" + String(i);
    String keyMin  = "m" + String(i);
    String keyEn   = "e" + String(i);
    String keyDaily = "d" + String(i);

    alarms[i].hour =
      preferences.getInt(keyHour.c_str(), -1);

    alarms[i].minute =
      preferences.getInt(keyMin.c_str(), -1);

    alarms[i].enabled =
      preferences.getBool(keyEn.c_str(), false);

    alarms[i].daily =
      preferences.getBool(keyDaily.c_str(), true);

    alarms[i].lastTriggeredYear = -1;
    alarms[i].lastTriggeredMonth = -1;
    alarms[i].lastTriggeredDay = -1;
  }

  preferences.end();
}

// =====================================================
// FIND EMPTY ALARM SLOT
// =====================================================

int findEmptyAlarmSlot() {

  for (int i = 0; i < MAX_ALARMS; i++) {

    if (alarms[i].hour < 0) {
      return i;
    }
  }

  return -1;
}

// =====================================================
// START ALARM
// =====================================================

void startAlarm(int index) {

  if (index < 0 || index >= MAX_ALARMS) {
    return;
  }

  activeAlarmIndex = index;

  alarmState = ALARM_RINGING;

  alarmStartedMillis = millis();
  lastPatternMillis = millis();

  currentAlarmLevel = 0;

  buzzerOff();
  ledOff();

  Serial.println();
  Serial.println("=================================");
  Serial.println("ALARM STARTED");
  Serial.print("Alarm: ");
  Serial.println(formatAlarmTime(
    alarms[index].hour,
    alarms[index].minute
  ));
  Serial.println("=================================");
}

// =====================================================
// ESCALATE ALARM
// =====================================================

void escalateAlarm() {

  currentAlarmLevel++;

  if (currentAlarmLevel > 3) {
    currentAlarmLevel = 3;
  }

  alarmState = ALARM_ESCALATED;

  Serial.print("Alarm escalated. Level: ");
  Serial.println(currentAlarmLevel);

  // Reset pattern timer so new pattern starts immediately
  lastPatternMillis = millis();
}

// =====================================================
// DISMISS ALARM
// =====================================================

void dismissAlarm() {

  Serial.println();
  Serial.println("=================================");
  Serial.println("ALARM DISMISSED");
  Serial.println("Transition ready for PHASE 1");
  Serial.println("=================================");

  stopAlarmOutput();

  alarmState = ALARM_DISMISSED;

  activeAlarmIndex = -1;

  // IMPORTANT:
  //
  // Phase 1 is NOT implemented yet.
  //
  // Later we will replace this point with:
  //
  // startPhase1();
}

// =====================================================
// CHECK ALARM OFF BUTTON
// =====================================================

void checkAlarmOffButton() {

  static bool previousState = HIGH;

  bool currentState = digitalRead(ALARM_OFF_PIN);

  // Detect HIGH -> LOW transition
  if (previousState == HIGH && currentState == LOW) {

    delay(20);

    if (digitalRead(ALARM_OFF_PIN) == LOW) {

      if (alarmState == ALARM_RINGING ||
          alarmState == ALARM_ESCALATED) {

        dismissAlarm();
      }
    }
  }

  previousState = currentState;
}

// =====================================================
// CHECK ALARM TIME
// =====================================================

void checkScheduledAlarms() {

  if (alarmState != ALARM_IDLE &&
      alarmState != ALARM_DISMISSED) {
    return;
  }

  DateTime now = rtc.now();

  if (!now.isValid()) {
    return;
  }

  for (int i = 0; i < MAX_ALARMS; i++) {

    if (!alarms[i].enabled) {
      continue;
    }

    if (alarms[i].hour != now.hour()) {
      continue;
    }

    if (alarms[i].minute != now.minute()) {
      continue;
    }

    // Prevent repeated triggering during the same minute/day

    bool alreadyTriggered =
      alarms[i].lastTriggeredYear == now.year() &&
      alarms[i].lastTriggeredMonth == now.month() &&
      alarms[i].lastTriggeredDay == now.day();

    if (alreadyTriggered) {
      continue;
    }

    // One-time alarm
    if (!alarms[i].daily) {

      // Trigger it now
      alarms[i].lastTriggeredYear = now.year();
      alarms[i].lastTriggeredMonth = now.month();
      alarms[i].lastTriggeredDay = now.day();

      alarms[i].enabled = false;

      saveAlarms();

      startAlarm(i);

      return;
    }

    // Daily alarm
    alarms[i].lastTriggeredYear = now.year();
    alarms[i].lastTriggeredMonth = now.month();
    alarms[i].lastTriggeredDay = now.day();

    startAlarm(i);

    return;
  }
}

// =====================================================
// UPDATE ACTIVE ALARM
// =====================================================

void updateActiveAlarm() {

  if (alarmState != ALARM_RINGING &&
      alarmState != ALARM_ESCALATED) {
    return;
  }

  unsigned long elapsed =
    millis() - alarmStartedMillis;

  // Escalate every configured interval
  if (elapsed >=
      ((unsigned long)(currentAlarmLevel + 1) *
       ESCALATION_INTERVAL_MS)) {

    escalateAlarm();
  }

  updateAlarmPattern();
}

// =====================================================
// HTML DASHBOARD
// =====================================================

const char htmlPage[] PROGMEM = R"rawliteral(

<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<title>Smart Alarm</title>

<style>

body {
  font-family: Arial, sans-serif;
  background: #111;
  color: white;
  margin: 0;
  padding: 20px;
}

.container {
  max-width: 700px;
  margin: auto;
}

h1 {
  text-align: center;
}

.section {
  background: #1f1f1f;
  padding: 20px;
  margin-top: 15px;
  border-radius: 8px;
}

.big-time {
  font-size: 42px;
  text-align: center;
  margin: 15px 0;
  font-family: monospace;
}

.status {
  font-size: 18px;
  margin: 8px 0;
}

button {
  padding: 10px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 15px;
}

.add-button {
  background: #28a745;
  color: white;
}

.sync-button {
  background: #007bff;
  color: white;
  width: 100%;
}

.delete-button {
  background: #dc3545;
  color: white;
}

.toggle-button {
  background: #555;
  color: white;
}

input, select {
  padding: 9px;
  font-size: 16px;
  border-radius: 5px;
  border: 1px solid #555;
  background: #333;
  color: white;
}

.alarm-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 0;
  border-bottom: 1px solid #444;
}

.add-form {
  margin-top: 15px;
  display: none;
}

.warning {
  color: #ffcc00;
}

</style>

</head>

<body>

<div class="container">

<h1>Smart Alarm</h1>


<!-- RTC SECTION -->

<div class="section">

<h2>RTC</h2>

<div id="rtc-time"
     class="big-time">
Loading...
</div>

<div id="rtc-status"
     class="status">
Status: Loading...
</div>

<button class="sync-button"
        onclick="syncRTC()">

Sync RTC to Current Time

</button>

</div>


<!-- ALARM SECTION -->

<div class="section">

<h2>Alarms</h2>

<div id="alarm-list">

Loading...

</div>


<button class="add-button"
        onclick="showAddForm()">

+ Add Alarm

</button>


<div id="add-form"
     class="add-form">

<h3>Add Alarm</h3>

<p>

Time:

<input type="time"
       id="alarm-time">

</p>


<p>

Repeat:

<select id="alarm-repeat">

<option value="daily">
Daily
</option>

<option value="once">
One Time
</option>

</select>

</p>


<button class="add-button"
        onclick="addAlarm()">

Save

</button>

<button onclick="hideAddForm()">

Cancel

</button>

</div>

</div>


<!-- STATUS SECTION -->

<div class="section">

<h2>Current Status</h2>

<div class="status">
System:
<strong id="system-status">
Loading...
</strong>
</div>

<div class="status">
Alarm:
<strong id="alarm-status">
Loading...
</strong>
</div>

<div class="status">
Output:
<strong id="output-status">
Loading...
</strong>
</div>

</div>


</div>


<script>


// =====================================================
// UPDATE DASHBOARD
// =====================================================

async function updateDashboard() {

  try {

    const response =
      await fetch('/data');

    const data =
      await response.json();


    document.getElementById(
      'rtc-time'
    ).innerText =
      data.rtcTime;


    document.getElementById(
      'rtc-status'
    ).innerText =
      'Status: ' + data.rtcStatus;


    document.getElementById(
      'system-status'
    ).innerText =
      data.systemStatus;


    document.getElementById(
      'alarm-status'
    ).innerText =
      data.alarmStatus;


    document.getElementById(
      'output-status'
    ).innerText =
      data.outputStatus;


    renderAlarms(data.alarms);

  }

  catch(error) {

    console.log(error);

  }

}


// =====================================================
// RENDER ALARMS
// =====================================================

function renderAlarms(alarms) {

  const container =
    document.getElementById(
      'alarm-list'
    );


  if (alarms.length === 0) {

    container.innerHTML =
      '<p>No alarms configured.</p>';

    return;
  }


  let html = '';


  alarms.forEach(function(alarm) {

    html += '<div class="alarm-row">';


    html +=
      '<span><strong>' +
      alarm.time +
      '</strong> ';


    html +=
      '(' +
      alarm.repeat +
      ')</span>';


    html +=
      '<span>' +
      (alarm.enabled
        ? 'ON'
        : 'OFF') +
      '</span>';


    html +=
      '<span>';


    html +=
      '<button class="toggle-button" ' +
      'onclick="toggleAlarm(' +
      alarm.index +
      ')">' +
      (alarm.enabled
        ? 'Disable'
        : 'Enable') +
      '</button>';


    html +=
      ' ';


    html +=
      '<button class="delete-button" ' +
      'onclick="deleteAlarm(' +
      alarm.index +
      ')">' +
      'Delete' +
      '</button>';


    html += '</span>';

    html += '</div>';

  });


  container.innerHTML = html;

}


// =====================================================
// SHOW ADD FORM
// =====================================================

function showAddForm() {

  document.getElementById(
    'add-form'
  ).style.display = 'block';

}


// =====================================================
// HIDE ADD FORM
// =====================================================

function hideAddForm() {

  document.getElementById(
    'add-form'
  ).style.display = 'none';

}


// =====================================================
// ADD ALARM
// =====================================================

async function addAlarm() {

  const time =
    document.getElementById(
      'alarm-time'
    ).value;


  const repeat =
    document.getElementById(
      'alarm-repeat'
    ).value;


  if (!time) {

    alert('Please select a time.');

    return;
  }


  const response =
    await fetch(
      '/add-alarm?time=' +
      encodeURIComponent(time) +
      '&repeat=' +
      encodeURIComponent(repeat)
    );


  alert(await response.text());


  hideAddForm();

  updateDashboard();

}


// =====================================================
// DELETE ALARM
// =====================================================

async function deleteAlarm(index) {

  if (!confirm(
    'Delete this alarm?'
  )) {

    return;
  }


  const response =
    await fetch(
      '/delete-alarm?index=' +
      index
    );


  alert(await response.text());


  updateDashboard();

}


// =====================================================
// TOGGLE ALARM
// =====================================================

async function toggleAlarm(index) {

  const response =
    await fetch(
      '/toggle-alarm?index=' +
      index
    );


  alert(await response.text());


  updateDashboard();

}


// =====================================================
// RTC SYNC
// =====================================================

async function syncRTC() {

  const now =
    new Date();


  const time =
    now.toTimeString()
       .slice(0, 8);


  const date =
    now.toISOString()
       .slice(0, 10);


  const response =
    await fetch(
      '/set-rtc?time=' +
      encodeURIComponent(time) +
      '&date=' +
      encodeURIComponent(date)
    );


  alert(await response.text());


  updateDashboard();

}


// =====================================================
// UPDATE EVERY SECOND
// =====================================================

setInterval(
  updateDashboard,
  1000
);


updateDashboard();

</script>

</body>

</html>

)rawliteral";


// =====================================================
// WEB: ROOT
// =====================================================

void handleRoot() {

  server.send(
    200,
    "text/html",
    htmlPage
  );
}


// =====================================================
// WEB: DATA
// =====================================================

void handleData() {

  DateTime now = rtc.now();

  String rtcTime;
  String rtcStatus;

  if (now.isValid()) {

    char buffer[16];

    sprintf(
      buffer,
      "%02d:%02d:%02d",
      now.hour(),
      now.minute(),
      now.second()
    );

    rtcTime = String(buffer);

    rtcStatus = "OK";

  }
  else {

    rtcTime = "--:--:--";

    rtcStatus = "ERROR";
  }


  String json = "{";


  json +=
    "\"rtcTime\":\"" +
    rtcTime +
    "\",";


  json +=
    "\"rtcStatus\":\"" +
    rtcStatus +
    "\",";


  json +=
    "\"systemStatus\":\"" +
    getAlarmStateText() +
    "\",";


  String alarmStatus = "Not Ringing";


  if (alarmState == ALARM_RINGING) {

    alarmStatus = "RINGING";

  }
  else if (alarmState == ALARM_ESCALATED) {

    alarmStatus = "ESCALATED";

  }
  else if (alarmState == ALARM_DISMISSED) {

    alarmStatus = "DISMISSED";

  }


  json +=
    "\"alarmStatus\":\"" +
    alarmStatus +
    "\",";


  String outputStatus =
    (buzzerState || ledState)
      ? "ON"
      : "OFF";


  json +=
    "\"outputStatus\":\"" +
    outputStatus +
    "\",";


  json += "\"alarms\":[";


  bool first = true;


  for (int i = 0; i < MAX_ALARMS; i++) {

    if (alarms[i].hour < 0) {
      continue;
    }


    if (!first) {
      json += ",";
    }


    first = false;


    json += "{";


    json +=
      "\"index\":" +
      String(i) +
      ",";


    json +=
      "\"time\":\"" +
      formatAlarmTime(
        alarms[i].hour,
        alarms[i].minute
      ) +
      "\",";


    json +=
      "\"enabled\":" +
      String(
        alarms[i].enabled
          ? "true"
          : "false"
      ) +
      ",";


    json +=
      "\"repeat\":\"" +
      String(
        alarms[i].daily
          ? "Daily"
          : "One Time"
      ) +
      "\"";


    json += "}";

  }


  json += "]";

  json += "}";


  server.send(
    200,
    "application/json",
    json
  );
}


// =====================================================
// WEB: SET RTC
// =====================================================

void handleSetRTC() {

  if (!server.hasArg("time") ||
      !server.hasArg("date")) {

    server.send(
      400,
      "text/plain",
      "Missing time/date."
    );

    return;
  }


  String timeString =
    server.arg("time");


  String dateString =
    server.arg("date");


  int year =
    dateString.substring(0, 4).toInt();


  int month =
    dateString.substring(5, 7).toInt();


  int day =
    dateString.substring(8, 10).toInt();


  int hour =
    timeString.substring(0, 2).toInt();


  int minute =
    timeString.substring(3, 5).toInt();


  int second =
    timeString.substring(6, 8).toInt();


  rtc.adjust(
    DateTime(
      year,
      month,
      day,
      hour,
      minute,
      second
    )
  );


  alarmState = ALARM_IDLE;

  activeAlarmIndex = -1;

  stopAlarmOutput();


  server.send(
    200,
    "text/plain",
    "RTC synchronized successfully."
  );
}


// =====================================================
// WEB: ADD ALARM
// =====================================================

void handleAddAlarm() {

  if (!server.hasArg("time")) {

    server.send(
      400,
      "text/plain",
      "Missing alarm time."
    );

    return;
  }


  int slot =
    findEmptyAlarmSlot();


  if (slot < 0) {

    server.send(
      400,
      "text/plain",
      "Maximum number of alarms reached."
    );

    return;
  }


  String inputTime =
    server.arg("time");


  int hour =
    inputTime.substring(0, 2).toInt();


  int minute =
    inputTime.substring(3, 5).toInt();


  bool daily = true;


  if (server.hasArg("repeat")) {

    daily =
      server.arg("repeat") == "daily";
  }


  alarms[slot].hour = hour;

  alarms[slot].minute = minute;

  alarms[slot].enabled = true;

  alarms[slot].daily = daily;

  alarms[slot].lastTriggeredYear = -1;

  alarms[slot].lastTriggeredMonth = -1;

  alarms[slot].lastTriggeredDay = -1;


  saveAlarms();


  server.send(
    200,
    "text/plain",
    "Alarm added successfully."
  );
}


// =====================================================
// WEB: DELETE ALARM
// =====================================================

void handleDeleteAlarm() {

  if (!server.hasArg("index")) {

    server.send(
      400,
      "text/plain",
      "Missing alarm index."
    );

    return;
  }


  int index =
    server.arg("index").toInt();


  if (index < 0 ||
      index >= MAX_ALARMS) {

    server.send(
      400,
      "text/plain",
      "Invalid alarm index."
    );

    return;
  }


  alarms[index].hour = -1;

  alarms[index].minute = -1;

  alarms[index].enabled = false;

  alarms[index].daily = true;

  alarms[index].lastTriggeredYear = -1;

  alarms[index].lastTriggeredMonth = -1;

  alarms[index].lastTriggeredDay = -1;


  saveAlarms();


  server.send(
    200,
    "text/plain",
    "Alarm deleted."
  );
}


// =====================================================
// WEB: TOGGLE ALARM
// =====================================================

void handleToggleAlarm() {

  if (!server.hasArg("index")) {

    server.send(
      400,
      "text/plain",
      "Missing alarm index."
    );

    return;
  }


  int index =
    server.arg("index").toInt();


  if (index < 0 ||
      index >= MAX_ALARMS ||
      alarms[index].hour < 0) {

    server.send(
      400,
      "text/plain",
      "Invalid alarm."
    );

    return;
  }


  alarms[index].enabled =
    !alarms[index].enabled;


  saveAlarms();


  server.send(
    200,
    "text/plain",
    alarms[index].enabled
      ? "Alarm enabled."
      : "Alarm disabled."
  );
}


// =====================================================
// SETUP
// =====================================================

void setup() {

  Serial.begin(115200);


  // -------------------------------------------------
  // GPIO
  // -------------------------------------------------

  pinMode(
    BUZZER_PIN,
    OUTPUT
  );

  pinMode(
    LED_PIN,
    OUTPUT
  );

  pinMode(
    ALARM_OFF_PIN,
    INPUT_PULLUP
  );


  buzzerOff();

  ledOff();


  // -------------------------------------------------
  // I2C
  // -------------------------------------------------

  Wire.begin(
    I2C_SDA,
    I2C_SCL
  );


  // -------------------------------------------------
  // RTC
  // -------------------------------------------------

  if (!rtc.begin()) {

    Serial.println(
      "ERROR: DS3231 not detected."
    );

    while (true) {

      delay(1000);
    }
  }


  if (rtc.lostPower()) {

    Serial.println();
    Serial.println(
      "WARNING: RTC lost power."
    );

    Serial.println(
      "Use dashboard to synchronize RTC."
    );
  }


  DateTime now =
    rtc.now();


  if (now.isValid()) {

    Serial.printf(
      "RTC: %04d-%02d-%02d %02d:%02d:%02d\n",

      now.year(),
      now.month(),
      now.day(),

      now.hour(),
      now.minute(),
      now.second()
    );
  }


  // -------------------------------------------------
  // LOAD SAVED ALARMS
  // -------------------------------------------------

  loadAlarms();


  // -------------------------------------------------
  // WIFI ACCESS POINT
  // -------------------------------------------------

  WiFi.softAP(
    ssid,
    password
  );


  Serial.println();
  Serial.println(
    "WiFi Access Point started."
  );

  Serial.print(
    "SSID: "
  );

  Serial.println(
    ssid
  );

  Serial.print(
    "Dashboard: http://"
  );

  Serial.println(
    WiFi.softAPIP()
  );


  // -------------------------------------------------
  // WEB SERVER
  // -------------------------------------------------

  server.on(
    "/",
    handleRoot
  );


  server.on(
    "/data",
    handleData
  );


  server.on(
    "/set-rtc",
    handleSetRTC
  );


  server.on(
    "/add-alarm",
    handleAddAlarm
  );


  server.on(
    "/delete-alarm",
    handleDeleteAlarm
  );


  server.on(
    "/toggle-alarm",
    handleToggleAlarm
  );


  server.begin();


  Serial.println(
    "Web server started."
  );


  Serial.println();
  Serial.println(
    "Alarm module ready."
  );
}


// =====================================================
// LOOP
// =====================================================

void loop() {

  // Handle browser requests
  server.handleClient();


  // Check physical Alarm OFF button
  checkAlarmOffButton();


  // Check scheduled alarms
  checkScheduledAlarms();


  // Update currently ringing alarm
  updateActiveAlarm();


  // Small yield
  delay(1);
}