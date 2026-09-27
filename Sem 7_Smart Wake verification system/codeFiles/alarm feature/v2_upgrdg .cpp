#include <Arduino.h>
#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <RTClib.h>
#include <Preferences.h>

// ============================================================
//                    PIN CONFIGURATION
// ============================================================

const int I2C_SDA = 27;
const int I2C_SCL = 26;

const int BUZZER_PIN = 25;
const int LED_PIN = 33;

const int ALARM_OFF_PIN = 32;


// ============================================================
//                    WIFI CONFIGURATION
// ============================================================

const char* ssid = "smartAlarm";
const char* password = "hello123";


// ============================================================
//                 ALARM STAGE CONFIGURATION
// ============================================================
//
// Modify these values whenever you want.
//
// Duration:
//     3UL * 60UL * 1000UL = 3 minutes
//
// Buzzer level:
//     0   = OFF
//     50  = low
//     128 = medium
//     255 = maximum
//
// Stage 4 duration is ignored because Stage 4
// continues indefinitely until the OFF switch is activated.
// ============================================================


// -------------------- STAGE 1 --------------------

const unsigned long STAGE_1_DURATION_MS =
    3UL * 60UL * 1000UL;       // 3 minutes

const int STAGE_1_BUZZER_LEVEL =
    50;                        // 0 - 255


// -------------------- STAGE 2 --------------------

const unsigned long STAGE_2_DURATION_MS =
    3UL * 60UL * 1000UL;       // 3 minutes

const int STAGE_2_BUZZER_LEVEL =
    100;                       // 0 - 255


// -------------------- STAGE 3 --------------------

const unsigned long STAGE_3_DURATION_MS =
    3UL * 60UL * 1000UL;       // 3 minutes

const int STAGE_3_BUZZER_LEVEL =
    180;                       // 0 - 255


// -------------------- STAGE 4 --------------------

const unsigned long STAGE_4_DURATION_MS =
    3UL * 60UL * 1000UL;       // Not used

const int STAGE_4_BUZZER_LEVEL =
    255;                       // 0 - 255


// ============================================================
//                 BUZZER PATTERN CONFIGURATION
// ============================================================
//
// Smaller interval = faster beeping.
//
// Stage 1 → slow
// Stage 2 → faster
// Stage 3 → faster
// Stage 4 → very fast
//
// These are also completely independent from
// the stage durations.
// ============================================================

const unsigned long STAGE_1_BEEP_INTERVAL_MS = 1000;
const unsigned long STAGE_2_BEEP_INTERVAL_MS = 500;
const unsigned long STAGE_3_BEEP_INTERVAL_MS = 250;
const unsigned long STAGE_4_BEEP_INTERVAL_MS = 120;


// ============================================================
//                 GENERAL CONFIGURATION
// ============================================================

const int TOTAL_ALARM_STAGES = 4;

const int MAX_ALARMS = 10;


// ============================================================
//                 BUZZER PWM CONFIGURATION
// ============================================================

const int BUZZER_PWM_FREQUENCY = 2000;
const int BUZZER_PWM_RESOLUTION = 8;


// ============================================================
//                 SWITCH CONFIGURATION
// ============================================================
//
// The OFF switch is a normally-ON / NC switch.
//
// Normal condition:
//     GPIO32 = LOW
//
// Switch activated:
//     GPIO32 = HIGH
//
// Therefore:
//     HIGH = Alarm OFF requested
// ============================================================

const int ALARM_OFF_ACTIVE_STATE = HIGH;


// Non-blocking debounce time
const unsigned long SWITCH_DEBOUNCE_MS = 50;


// ============================================================
//                 HARDWARE OBJECTS
// ============================================================

RTC_DS3231 rtc;
WebServer server(80);
Preferences preferences;


// ============================================================
//                 ALARM DATA STRUCTURE
// ============================================================

struct Alarm {

  int hour;
  int minute;

  bool enabled;
  bool daily;

  int lastTriggeredYear;
  int lastTriggeredMonth;
  int lastTriggeredDay;
};


// ============================================================
//                 ALARM STATES
// ============================================================

enum AlarmState {

  ALARM_IDLE,
  ALARM_RINGING,
  ALARM_ESCALATED,
  ALARM_DISMISSED
};


// ============================================================
//                 GLOBAL VARIABLES
// ============================================================

Alarm alarms[MAX_ALARMS];

AlarmState alarmState = ALARM_IDLE;

int activeAlarmIndex = -1;

int currentAlarmStage = 1;

unsigned long alarmStageStartedMillis = 0;

unsigned long lastBuzzerPatternMillis = 0;

bool buzzerPatternState = false;


// ============================================================
//                 SWITCH DEBOUNCE VARIABLES
// ============================================================

int lastRawSwitchState = LOW;

int stableSwitchState = LOW;

unsigned long switchChangedMillis = 0;


// ============================================================
//                 FUNCTION DECLARATIONS
// ============================================================

void loadAlarms();
void saveAlarm(int index);
void clearAlarm(int index);

void checkScheduledAlarms();
void startAlarm(int index);
void stopAlarmOutput();
void dismissAlarm();

void updateAlarmStage();
void updateAlarmOutput();

void updateOffSwitch();

void setBuzzerLevel(int level);
void buzzerOn(int level);
void buzzerOff();

void handleRoot();
void handleData();
void handleSetRTC();

void handleAddAlarm();
void handleDeleteAlarm();
void handleToggleAlarm();

String twoDigits(int value);

unsigned long getCurrentStageDuration();
int getCurrentStageBuzzerLevel();
unsigned long getCurrentStagePatternInterval();


// ============================================================
//                         SETUP
// ============================================================

void setup() {

  Serial.begin(115200);

  delay(500);

  Serial.println();
  Serial.println("======================================");
  Serial.println("       SMART ALARM SYSTEM");
  Serial.println("======================================");


  // ----------------------------------------------------------
  // I2C
  // ----------------------------------------------------------

  Wire.begin(I2C_SDA, I2C_SCL);

  if (!rtc.begin()) {

    Serial.println("ERROR: DS3231 not found!");

  } else {

    Serial.println("DS3231 detected.");

    if (rtc.lostPower()) {

      Serial.println("WARNING: RTC lost power.");
      Serial.println("RTC needs synchronization.");

    }
  }


  // ----------------------------------------------------------
  // LED
  // ----------------------------------------------------------

  pinMode(LED_PIN, OUTPUT);

  digitalWrite(LED_PIN, LOW);


  // ----------------------------------------------------------
  // ALARM OFF SWITCH
  // ----------------------------------------------------------
  //
  // Internal pull-up is enabled.
  //
  // Normally-ON NC switch:
  //
  // GPIO32 ---- switch ---- GND
  //
  // Normal:
  // switch closed → LOW
  //
  // Activated:
  // switch open → HIGH
  //

  pinMode(ALARM_OFF_PIN, INPUT_PULLUP);

  lastRawSwitchState = digitalRead(ALARM_OFF_PIN);
  stableSwitchState = lastRawSwitchState;

  switchChangedMillis = millis();


  // ----------------------------------------------------------
  // BUZZER PWM
  // ----------------------------------------------------------

  if (!ledcAttach(
        BUZZER_PIN,
        BUZZER_PWM_FREQUENCY,
        BUZZER_PWM_RESOLUTION)) {

    Serial.println("ERROR: Failed to attach buzzer PWM.");

  } else {

    Serial.println("Buzzer PWM ready.");
  }

  buzzerOff();


  // ----------------------------------------------------------
  // LOAD STORED ALARMS
  // ----------------------------------------------------------

  loadAlarms();


  // ----------------------------------------------------------
  // WIFI ACCESS POINT
  // ----------------------------------------------------------

  WiFi.mode(WIFI_AP);

  WiFi.softAP(ssid, password);

  Serial.println();
  Serial.println("WiFi Access Point started.");

  Serial.print("SSID: ");
  Serial.println(ssid);

  Serial.print("IP Address: ");
  Serial.println(WiFi.softAPIP());


  // ----------------------------------------------------------
  // WEB SERVER ROUTES
  // ----------------------------------------------------------

  server.on("/", handleRoot);

  server.on("/data", handleData);

  server.on("/set-rtc", HTTP_GET, handleSetRTC);

  server.on("/add-alarm", HTTP_GET, handleAddAlarm);

  server.on("/delete-alarm", HTTP_GET, handleDeleteAlarm);

  server.on("/toggle-alarm", HTTP_GET, handleToggleAlarm);


  server.begin();

  Serial.println("Web server started.");

  Serial.println("======================================");
  Serial.println("SYSTEM READY");
  Serial.println("======================================");
}


// ============================================================
//                         LOOP
// ============================================================

void loop() {

  server.handleClient();


  // ----------------------------------------------------------
  // Check scheduled alarms
  // ----------------------------------------------------------

  checkScheduledAlarms();


  // ----------------------------------------------------------
  // Update physical OFF switch
  // ----------------------------------------------------------

  updateOffSwitch();


  // ----------------------------------------------------------
  // If alarm is active, update stage
  // ----------------------------------------------------------

  if (alarmState == ALARM_RINGING ||
      alarmState == ALARM_ESCALATED) {

    updateAlarmStage();

    updateAlarmOutput();
  }
}


// ============================================================
//                 ALARM STORAGE
// ============================================================

void loadAlarms() {

  preferences.begin("alarms", true);

  for (int i = 0; i < MAX_ALARMS; i++) {

    String prefix = "a" + String(i) + "_";

    alarms[i].hour =
        preferences.getInt((prefix + "hour").c_str(), -1);

    alarms[i].minute =
        preferences.getInt((prefix + "min").c_str(), -1);

    alarms[i].enabled =
        preferences.getBool((prefix + "en").c_str(), false);

    alarms[i].daily =
        preferences.getBool((prefix + "daily").c_str(), true);

    alarms[i].lastTriggeredYear =
        preferences.getInt((prefix + "ly").c_str(), 0);

    alarms[i].lastTriggeredMonth =
        preferences.getInt((prefix + "lm").c_str(), 0);

    alarms[i].lastTriggeredDay =
        preferences.getInt((prefix + "ld").c_str(), 0);
  }

  preferences.end();


  Serial.println("Stored alarms loaded.");

  for (int i = 0; i < MAX_ALARMS; i++) {

    if (alarms[i].hour >= 0) {

      Serial.print("Alarm ");
      Serial.print(i);
      Serial.print(": ");

      Serial.print(twoDigits(alarms[i].hour));
      Serial.print(":");
      Serial.print(twoDigits(alarms[i].minute));

      Serial.print("  ");

      Serial.print(
          alarms[i].daily ? "Daily" : "One-Time"
      );

      Serial.print("  ");

      Serial.println(
          alarms[i].enabled ? "ON" : "OFF"
      );
    }
  }
}


// ============================================================
//                 SAVE ONE ALARM
// ============================================================

void saveAlarm(int index) {

  if (index < 0 || index >= MAX_ALARMS) {
    return;
  }

  preferences.begin("alarms", false);

  String prefix = "a" + String(index) + "_";

  preferences.putInt(
      (prefix + "hour").c_str(),
      alarms[index].hour
  );

  preferences.putInt(
      (prefix + "min").c_str(),
      alarms[index].minute
  );

  preferences.putBool(
      (prefix + "en").c_str(),
      alarms[index].enabled
  );

  preferences.putBool(
      (prefix + "daily").c_str(),
      alarms[index].daily
  );

  preferences.putInt(
      (prefix + "ly").c_str(),
      alarms[index].lastTriggeredYear
  );

  preferences.putInt(
      (prefix + "lm").c_str(),
      alarms[index].lastTriggeredMonth
  );

  preferences.putInt(
      (prefix + "ld").c_str(),
      alarms[index].lastTriggeredDay
  );

  preferences.end();
}


// ============================================================
//                 CLEAR ONE ALARM
// ============================================================

void clearAlarm(int index) {

  if (index < 0 || index >= MAX_ALARMS) {
    return;
  }

  alarms[index].hour = -1;
  alarms[index].minute = -1;

  alarms[index].enabled = false;
  alarms[index].daily = true;

  alarms[index].lastTriggeredYear = 0;
  alarms[index].lastTriggeredMonth = 0;
  alarms[index].lastTriggeredDay = 0;

  saveAlarm(index);
}


// ============================================================
//                 CHECK SCHEDULED ALARMS
// ============================================================

void checkScheduledAlarms() {

  if (alarmState == ALARM_RINGING ||
      alarmState == ALARM_ESCALATED) {

    return;
  }


  DateTime now = rtc.now();


  for (int i = 0; i < MAX_ALARMS; i++) {

    if (!alarms[i].enabled) {
      continue;
    }

    if (alarms[i].hour < 0) {
      continue;
    }


    if (now.hour() != alarms[i].hour) {
      continue;
    }

    if (now.minute() != alarms[i].minute) {
      continue;
    }


    // --------------------------------------------------------
    // Prevent repeated triggering during the same minute/day
    // --------------------------------------------------------

    if (alarms[i].lastTriggeredYear == now.year() &&
        alarms[i].lastTriggeredMonth == now.month() &&
        alarms[i].lastTriggeredDay == now.day()) {

      continue;
    }


    // --------------------------------------------------------
    // Mark as triggered
    // --------------------------------------------------------

    alarms[i].lastTriggeredYear = now.year();
    alarms[i].lastTriggeredMonth = now.month();
    alarms[i].lastTriggeredDay = now.day();

    saveAlarm(i);


    // --------------------------------------------------------
    // One-time alarm → disable after triggering
    // --------------------------------------------------------

    if (!alarms[i].daily) {

      alarms[i].enabled = false;

      saveAlarm(i);
    }


    // --------------------------------------------------------
    // Start alarm
    // --------------------------------------------------------

    startAlarm(i);

    break;
  }
}


// ============================================================
//                 START ALARM
// ============================================================

void startAlarm(int index) {

  activeAlarmIndex = index;

  currentAlarmStage = 1;

  alarmStageStartedMillis = millis();

  lastBuzzerPatternMillis = millis();

  buzzerPatternState = false;

  alarmState = ALARM_RINGING;


  Serial.println();
  Serial.println("======================================");
  Serial.println("ALARM STARTED");
  Serial.println("Stage 1");
  Serial.println("======================================");
}


// ============================================================
//                 UPDATE ALARM STAGE
// ============================================================

void updateAlarmStage() {

  if (currentAlarmStage >= TOTAL_ALARM_STAGES) {

    alarmState = ALARM_ESCALATED;

    return;
  }


  unsigned long duration =
      getCurrentStageDuration();


  unsigned long elapsed =
      millis() - alarmStageStartedMillis;


  if (elapsed >= duration) {

    currentAlarmStage++;

    alarmStageStartedMillis = millis();

    lastBuzzerPatternMillis = millis();

    buzzerPatternState = false;


    if (currentAlarmStage >= TOTAL_ALARM_STAGES) {

      alarmState = ALARM_ESCALATED;

    } else {

      alarmState = ALARM_ESCALATED;
    }


    Serial.println();
    Serial.println("--------------------------------------");

    Serial.print("ALARM ESCALATED TO STAGE ");
    Serial.println(currentAlarmStage);

    Serial.print("Buzzer level: ");
    Serial.println(getCurrentStageBuzzerLevel());

    Serial.println("--------------------------------------");
  }
}


// ============================================================
//                 UPDATE ALARM OUTPUT
// ============================================================

void updateAlarmOutput() {

  unsigned long now = millis();

  unsigned long interval =
      getCurrentStagePatternInterval();


  if (now - lastBuzzerPatternMillis >= interval) {

    lastBuzzerPatternMillis = now;

    buzzerPatternState = !buzzerPatternState;


    if (buzzerPatternState) {

      buzzerOn(getCurrentStageBuzzerLevel());

      digitalWrite(LED_PIN, HIGH);

    } else {

      buzzerOff();

      digitalWrite(LED_PIN, LOW);
    }
  }
}


// ============================================================
//                 GET CURRENT STAGE DURATION
// ============================================================

unsigned long getCurrentStageDuration() {

  switch (currentAlarmStage) {

    case 1:
      return STAGE_1_DURATION_MS;

    case 2:
      return STAGE_2_DURATION_MS;

    case 3:
      return STAGE_3_DURATION_MS;

    case 4:
      return STAGE_4_DURATION_MS;

    default:
      return STAGE_4_DURATION_MS;
  }
}


// ============================================================
//                 GET CURRENT STAGE BUZZER LEVEL
// ============================================================

int getCurrentStageBuzzerLevel() {

  switch (currentAlarmStage) {

    case 1:
      return STAGE_1_BUZZER_LEVEL;

    case 2:
      return STAGE_2_BUZZER_LEVEL;

    case 3:
      return STAGE_3_BUZZER_LEVEL;

    case 4:
      return STAGE_4_BUZZER_LEVEL;

    default:
      return STAGE_4_BUZZER_LEVEL;
  }
}


// ============================================================
//                 GET CURRENT BEEP INTERVAL
// ============================================================

unsigned long getCurrentStagePatternInterval() {

  switch (currentAlarmStage) {

    case 1:
      return STAGE_1_BEEP_INTERVAL_MS;

    case 2:
      return STAGE_2_BEEP_INTERVAL_MS;

    case 3:
      return STAGE_3_BEEP_INTERVAL_MS;

    case 4:
      return STAGE_4_BEEP_INTERVAL_MS;

    default:
      return STAGE_4_BEEP_INTERVAL_MS;
  }
}


// ============================================================
//                 BUZZER ON
// ============================================================

void buzzerOn(int level) {

  level = constrain(level, 0, 255);

  ledcWrite(BUZZER_PIN, level);
}


// ============================================================
//                 BUZZER OFF
// ============================================================

void buzzerOff() {

  ledcWrite(BUZZER_PIN, 0);
}


// ============================================================
//                 SET BUZZER LEVEL
// ============================================================

void setBuzzerLevel(int level) {

  level = constrain(level, 0, 255);

  ledcWrite(BUZZER_PIN, level);
}


// ============================================================
//                 STOP ALARM OUTPUT
// ============================================================

void stopAlarmOutput() {

  buzzerOff();

  digitalWrite(LED_PIN, LOW);

  buzzerPatternState = false;
}


// ============================================================
//                 DISMISS ALARM
// ============================================================

void dismissAlarm() {

  if (alarmState == ALARM_IDLE) {
    return;
  }


  stopAlarmOutput();

  alarmState = ALARM_DISMISSED;

  activeAlarmIndex = -1;

  currentAlarmStage = 1;


  Serial.println();
  Serial.println("======================================");
  Serial.println("ALARM DISMISSED");
  Serial.println("Transition ready for PHASE 1");
  Serial.println("======================================");
}


// ============================================================
//                 OFF SWITCH
// ============================================================
//
// Normally-ON NC switch:
//
// Normal → LOW
// Activated → HIGH
//
// HIGH means OFF requested.
// ============================================================

void updateOffSwitch() {

  int rawState = digitalRead(ALARM_OFF_PIN);


  // ----------------------------------------------------------
  // Raw state changed
  // ----------------------------------------------------------

  if (rawState != lastRawSwitchState) {

    switchChangedMillis = millis();

    lastRawSwitchState = rawState;
  }


  // ----------------------------------------------------------
  // Wait for stable state
  // ----------------------------------------------------------

  if ((millis() - switchChangedMillis) >=
      SWITCH_DEBOUNCE_MS) {

    if (rawState != stableSwitchState) {

      stableSwitchState = rawState;


      // ------------------------------------------------------
      // Switch activated
      // ------------------------------------------------------

      if (stableSwitchState ==
          ALARM_OFF_ACTIVE_STATE) {

        if (alarmState == ALARM_RINGING ||
            alarmState == ALARM_ESCALATED) {

          dismissAlarm();
        }
      }
    }
  }
}


// ============================================================
//                 FORMAT TWO DIGITS
// ============================================================

String twoDigits(int value) {

  if (value < 10) {
    return "0" + String(value);
  }

  return String(value);
}


// ============================================================
//                 WEB DASHBOARD
// ============================================================

void handleRoot() {

  String html = R"rawliteral(

<!DOCTYPE html>

<html>

<head>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<title>Smart Alarm</title>

<style>

body {
  font-family: Arial, sans-serif;
  margin: 20px;
  background: #f4f4f4;
}

.container {
  max-width: 700px;
  margin: auto;
}

.card {
  background: white;
  padding: 18px;
  margin-bottom: 15px;
  border-radius: 10px;
}

h1 {
  margin-top: 0;
}

h2 {
  margin-bottom: 10px;
}

.time {
  font-size: 42px;
  font-weight: bold;
}

button {
  padding: 10px 15px;
  margin: 4px;
  cursor: pointer;
}

input, select {
  padding: 8px;
  margin: 4px;
}

.alarmRow {
  padding: 10px;
  border-bottom: 1px solid #ddd;
}

.status {
  font-weight: bold;
}

</style>

</head>


<body>

<div class="container">

<div class="card">

<h1>SMART ALARM</h1>

<h2>RTC</h2>

<div id="rtcTime" class="time">
--:--:--
</div>

<p id="rtcStatus">
Checking...
</p>

<button onclick="syncRTC()">
SYNC RTC TO CURRENT TIME
</button>

</div>


<div class="card">

<h2>ALARMS</h2>

<div id="alarmList">
Loading...
</div>

<br>

<h3>Add Alarm</h3>

<form onsubmit="addAlarm(); return false;">

Time:

<input
  type="time"
  id="alarmTime"
  required
>


<br>

Repeat:

<select id="alarmRepeat">

<option value="daily">
Daily
</option>

<option value="once">
One Time
</option>

</select>

<br>

<button type="submit">
Save Alarm
</button>

</form>

</div>


<div class="card">

<h2>CURRENT STATUS</h2>

<p>
System:
<span id="systemStatus"
      class="status">
-
</span>
</p>

<p>
Alarm:
<span id="alarmStatus"
      class="status">
-
</span>
</p>

<p>
Stage:
<span id="alarmStage"
      class="status">
-
</span>
</p>

<p>
Buzzer:
<span id="buzzerStatus"
      class="status">
-
</span>
</p>

</div>

</div>


<script>


function updateData() {

  fetch('/data')

    .then(response => response.json())

    .then(data => {

      document.getElementById(
        'rtcTime'
      ).innerText = data.time;


      document.getElementById(
        'rtcStatus'
      ).innerText = data.rtcStatus;


      document.getElementById(
        'systemStatus'
      ).innerText = data.system;


      document.getElementById(
        'alarmStatus'
      ).innerText = data.alarm;


      document.getElementById(
        'alarmStage'
      ).innerText = data.stage;


      document.getElementById(
        'buzzerStatus'
      ).innerText = data.buzzer;


      let list = "";

      data.alarms.forEach(
        function(a, index) {

          if (a.hour < 0) {
            return;
          }


          let time =
            String(a.hour).padStart(2, '0')
            + ":"
            +
            String(a.minute).padStart(2, '0');


          let type =
            a.daily ? "Daily" : "One Time";


          let status =
            a.enabled ? "ON" : "OFF";


          list +=
            '<div class="alarmRow">'
            +
            '<b>' + time + '</b>'
            +
            ' &nbsp; '
            +
            type
            +
            ' &nbsp; '
            +
            status
            +
            '<br>'
            +
            '<button onclick="toggleAlarm('
            + index +
            ')">'
            +
            (a.enabled ? "Disable" : "Enable")
            +
            '</button>'
            +
            '<button onclick="deleteAlarm('
            + index +
            ')">'
            +
            'Delete'
            +
            '</button>'
            +
            '</div>';
        }
      );


      if (list === "") {

        list =
          "<p>No alarms configured.</p>";
      }


      document.getElementById(
        'alarmList'
      ).innerHTML = list;

    })

    .catch(error => {

      console.log(error);

    });
}


// ============================================================
//                 SYNC RTC
// ============================================================

function syncRTC() {

  const now = new Date();

  const pad =
    n => String(n).padStart(2, '0');


  const time =
    pad(now.getHours())
    + ":"
    + pad(now.getMinutes())
    + ":"
    + pad(now.getSeconds());


  const date =
    now.getFullYear()
    + "-"
    + pad(now.getMonth() + 1)
    + "-"
    + pad(now.getDate());


  fetch(
    '/set-rtc?date='
    + date
    + '&time='
    + time
  )

  .then(() => {

    alert("RTC synchronized.");

    updateData();

  });
}


// ============================================================
//                 ADD ALARM
// ============================================================

function addAlarm() {

  const time =
    document.getElementById(
      'alarmTime'
    ).value;


  const repeat =
    document.getElementById(
      'alarmRepeat'
    ).value;


  if (!time) {
    return;
  }


  fetch(
    '/add-alarm?time='
    + time
    + '&daily='
    + (repeat === "daily" ? "1" : "0")
  )

  .then(() => {

    document.getElementById(
      'alarmTime'
    ).value = "";


    updateData();

  });
}


// ============================================================
//                 DELETE ALARM
// ============================================================

function deleteAlarm(index) {

  fetch(
    '/delete-alarm?index='
    + index
  )

  .then(() => {

    updateData();

  });
}


// ============================================================
//                 TOGGLE ALARM
// ============================================================

function toggleAlarm(index) {

  fetch(
    '/toggle-alarm?index='
    + index
  )

  .then(() => {

    updateData();

  });
}


// ============================================================
//                 LIVE UPDATE
// ============================================================

setInterval(
  updateData,
  1000
);

updateData();


</script>

</body>

</html>

)rawliteral";


  server.send(
    200,
    "text/html",
    html
  );
}


// ============================================================
//                 WEB DATA
// ============================================================

void handleData() {

  DateTime now = rtc.now();


  String json = "{";


  // ----------------------------------------------------------
  // RTC TIME
  // ----------------------------------------------------------

  json += "\"time\":\"";

  json += twoDigits(now.hour());
  json += ":";
  json += twoDigits(now.minute());
  json += ":";
  json += twoDigits(now.second());

  json += "\",";


  // ----------------------------------------------------------
  // RTC STATUS
  // ----------------------------------------------------------

  json += "\"rtcStatus\":\"";

  if (rtc.lostPower()) {

    json += "NEEDS SYNC";

  } else {

    json += "OK";
  }

  json += "\",";


  // ----------------------------------------------------------
  // SYSTEM STATUS
  // ----------------------------------------------------------

  json += "\"system\":\"";

  switch (alarmState) {

    case ALARM_IDLE:
      json += "IDLE";
      break;

    case ALARM_RINGING:
      json += "ALARM / RINGING";
      break;

    case ALARM_ESCALATED:
      json += "ALARM / ESCALATED";
      break;

    case ALARM_DISMISSED:
      json += "ALARM / DISMISSED";
      break;
  }

  json += "\",";


  // ----------------------------------------------------------
  // ALARM STATUS
  // ----------------------------------------------------------

  json += "\"alarm\":\"";

  if (alarmState == ALARM_RINGING ||
      alarmState == ALARM_ESCALATED) {

    json += "RINGING";

  } else if (alarmState == ALARM_DISMISSED) {

    json += "DISMISSED";

  } else {

    json += "Not Ringing";
  }

  json += "\",";


  // ----------------------------------------------------------
  // STAGE
  // ----------------------------------------------------------

  json += "\"stage\":\"";

  if (alarmState == ALARM_RINGING ||
      alarmState == ALARM_ESCALATED) {

    json += String(currentAlarmStage);

  } else {

    json += "-";
  }

  json += "\",";


  // ----------------------------------------------------------
  // BUZZER
  // ----------------------------------------------------------

  json += "\"buzzer\":\"";

  if (alarmState == ALARM_RINGING ||
      alarmState == ALARM_ESCALATED) {

    json += String(
      getCurrentStageBuzzerLevel()
    );

    json += " / 255";

  } else {

    json += "OFF";
  }

  json += "\",";


  // ----------------------------------------------------------
  // ALARM ARRAY
  // ----------------------------------------------------------

  json += "\"alarms\":[";


  for (int i = 0; i < MAX_ALARMS; i++) {

    if (i > 0) {
      json += ",";
    }


    json += "{";

    json += "\"hour\":";
    json += String(alarms[i].hour);

    json += ",";

    json += "\"minute\":";
    json += String(alarms[i].minute);

    json += ",";

    json += "\"enabled\":";
    json += alarms[i].enabled ? "true" : "false";

    json += ",";

    json += "\"daily\":";
    json += alarms[i].daily ? "true" : "false";

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


// ============================================================
//                 SET RTC
// ============================================================

void handleSetRTC() {

  if (!server.hasArg("date") ||
      !server.hasArg("time")) {

    server.send(
      400,
      "text/plain",
      "Missing date/time"
    );

    return;
  }


  String date = server.arg("date");
  String time = server.arg("time");


  int year =
      date.substring(0, 4).toInt();

  int month =
      date.substring(5, 7).toInt();

  int day =
      date.substring(8, 10).toInt();


  int hour =
      time.substring(0, 2).toInt();

  int minute =
      time.substring(3, 5).toInt();

  int second =
      time.substring(6, 8).toInt();


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


  // ----------------------------------------------------------
  // Reset current alarm state during RTC setup
  // ----------------------------------------------------------

  if (alarmState == ALARM_RINGING ||
      alarmState == ALARM_ESCALATED) {

    stopAlarmOutput();
  }


  alarmState = ALARM_IDLE;

  activeAlarmIndex = -1;

  currentAlarmStage = 1;


  Serial.println("RTC synchronized.");

  Serial.print("New RTC time: ");

  Serial.print(year);
  Serial.print("-");
  Serial.print(month);
  Serial.print("-");
  Serial.print(day);

  Serial.print(" ");

  Serial.print(hour);
  Serial.print(":");
  Serial.print(minute);
  Serial.print(":");
  Serial.println(second);


  server.send(
    200,
    "text/plain",
    "RTC synchronized"
  );
}


// ============================================================
//                 ADD ALARM
// ============================================================

void handleAddAlarm() {

  if (!server.hasArg("time") ||
      !server.hasArg("daily")) {

    server.send(
      400,
      "text/plain",
      "Missing parameters"
    );

    return;
  }


  String time = server.arg("time");

  bool daily =
      server.arg("daily") == "1";


  int hour =
      time.substring(0, 2).toInt();

  int minute =
      time.substring(3, 5).toInt();


  int freeIndex = -1;


  for (int i = 0; i < MAX_ALARMS; i++) {

    if (alarms[i].hour < 0) {

      freeIndex = i;

      break;
    }
  }


  if (freeIndex == -1) {

    server.send(
      400,
      "text/plain",
      "Maximum alarms reached"
    );

    return;
  }


  alarms[freeIndex].hour = hour;
  alarms[freeIndex].minute = minute;

  alarms[freeIndex].enabled = true;
  alarms[freeIndex].daily = daily;

  alarms[freeIndex].lastTriggeredYear = 0;
  alarms[freeIndex].lastTriggeredMonth = 0;
  alarms[freeIndex].lastTriggeredDay = 0;


  saveAlarm(freeIndex);


  Serial.print("Alarm added: ");

  Serial.print(twoDigits(hour));

  Serial.print(":");

  Serial.print(twoDigits(minute));

  Serial.print(" ");

  Serial.println(
    daily ? "Daily" : "One-Time"
  );


  server.send(
    200,
    "text/plain",
    "Alarm added"
  );
}


// ============================================================
//                 DELETE ALARM
// ============================================================

void handleDeleteAlarm() {

  if (!server.hasArg("index")) {

    server.send(
      400,
      "text/plain",
      "Missing index"
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
      "Invalid index"
    );

    return;
  }


  clearAlarm(index);


  server.send(
    200,
    "text/plain",
    "Alarm deleted"
  );
}


// ============================================================
//                 TOGGLE ALARM
// ============================================================

void handleToggleAlarm() {

  if (!server.hasArg("index")) {

    server.send(
      400,
      "text/plain",
      "Missing index"
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
      "Invalid index"
    );

    return;
  }


  if (alarms[index].hour < 0) {

    server.send(
      400,
      "text/plain",
      "Alarm does not exist"
    );

    return;
  }


  alarms[index].enabled =
      !alarms[index].enabled;


  saveAlarm(index);


  server.send(
    200,
    "text/plain",
    "Alarm toggled"
  );
}