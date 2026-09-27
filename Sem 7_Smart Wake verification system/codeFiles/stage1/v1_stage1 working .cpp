#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>

// ============================================================
// WIFI
// ============================================================

const char* ssid     = "smartStage1";
const char* password = "hello123";

WebServer server(80);


// ============================================================
// PIN CONFIGURATION
// ============================================================

// LEDs
const int LED1_PIN = 33;
const int LED2_PIN = 32;

// IMPORTANT:
// GPIO34 and GPIO35 are INPUT ONLY on classic ESP32.
// Therefore LED3/LED4 are moved to GPIO26/27.
const int LED3_PIN = 26;
const int LED4_PIN = 27;

const int LED_PINS[4] = {
  LED1_PIN,
  LED2_PIN,
  LED3_PIN,
  LED4_PIN
};


// Buttons
const int BUTTON1_PIN = 17;
const int BUTTON2_PIN = 5;
const int BUTTON3_PIN = 18;
const int BUTTON4_PIN = 19;

const int ENTER_BUTTON_PIN = 21;
const int RESET_BUTTON_PIN = 22;

// Simulates the Alarm OFF switch.
// Later this will be connected to the real Alarm module.
const int ALARM_OFF_PIN = 16;

// Buzzer
const int BUZZER_PIN = 25;


// ============================================================
// STAGE 1 CONFIGURATION
// ============================================================

// Every sequence contains exactly 4 LED events.
const int SEQUENCE_LENGTH = 4;

// Five consecutive successful rounds required.
const int REQUIRED_CONSECUTIVE_SUCCESSES = 5;

// LED ON duration during sequence playback.
const unsigned long LED_ON_TIME_MS = 500;

// Small gap between LED events.
const unsigned long LED_GAP_TIME_MS = 100;

// User gets this much quiet time after sequence playback.
const unsigned long INPUT_GRACE_PERIOD_MS = 5000;

// Button debounce.
const unsigned long DEBOUNCE_MS = 50;


// ============================================================
// FAILURE LED FEEDBACK
// ============================================================

const int FAILURE_BLINK_COUNT = 3;

// Higher ON time, lower OFF time as requested.
const unsigned long FAILURE_LED_ON_MS = 350;
const unsigned long FAILURE_LED_OFF_MS = 80;


// ============================================================
// NORMAL STAGE 1 BUZZER
// ============================================================

const int NORMAL_BUZZER_LEVEL = 45;

const unsigned long NORMAL_BEEP_ON_MS = 100;
const unsigned long NORMAL_BEEP_INTERVAL_MS = 1500;

const int NORMAL_BUZZER_FREQUENCY = 1800;


// ============================================================
// FAILURE BUZZER LEVELS
// ============================================================

const int FAILURE_LEVELS[] = {
  80,
  130,
  180,
  230,
  255
};

const int FAILURE_FREQUENCIES[] = {
  1000,
  800,
  650,
  500,
  400
};

const int FAILURE_LEVEL_COUNT = 5;


// ============================================================
// INACTIVITY BUZZER
// ============================================================

// Controlled random ranges.
// These are intentionally bounded rather than completely random.

const int INACTIVITY_MIN_FREQUENCY = 700;
const int INACTIVITY_MAX_FREQUENCY = 2500;

const int INACTIVITY_MIN_LEVEL = 80;
const int INACTIVITY_MAX_LEVEL = 255;

const unsigned long INACTIVITY_MIN_BEEP_ON_MS = 100;
const unsigned long INACTIVITY_MAX_BEEP_ON_MS = 400;

const unsigned long INACTIVITY_MIN_GAP_MS = 100;
const unsigned long INACTIVITY_MAX_GAP_MS = 900;


// ============================================================
// PWM
// ============================================================

const int BUZZER_PWM_FREQUENCY = 2000;
const int BUZZER_PWM_RESOLUTION = 8;


// ============================================================
// STAGE 1 STATES
// ============================================================

enum Stage1State {

  STAGE1_IDLE,

  // Playing the generated sequence.
  STAGE1_PLAYBACK,

  // Sequence has finished and user is entering answer.
  STAGE1_INPUT,

  // Wrong-answer LED feedback.
  STAGE1_FAILURE_FEEDBACK,

  // Stage 1 has completed 5 consecutive successes.
  STAGE1_COMPLETE
};

Stage1State stage1State = STAGE1_IDLE;


// ============================================================
// SEQUENCE DATA
// ============================================================

// Values are 1,2,3,4.
int expectedSequence[SEQUENCE_LENGTH];

int userSequence[SEQUENCE_LENGTH];

int userInputCount = 0;


// ============================================================
// ROUND / ATTEMPT DATA
// ============================================================

int currentRound = 0;

int consecutiveSuccesses = 0;

int currentAttempt = 0;

int totalFailures = 0;


// ============================================================
// PLAYBACK CONTROL
// ============================================================

int playbackIndex = 0;

bool playbackLEDOn = false;

unsigned long playbackTimer = 0;


// ============================================================
// INPUT / INACTIVITY CONTROL
// ============================================================

unsigned long inputStartTime = 0;

bool inactivityStarted = false;

unsigned long inactivityTimer = 0;


// ============================================================
// BUZZER CONTROL
// ============================================================

bool buzzerActive = false;

unsigned long buzzerTimer = 0;

unsigned long nextNormalBeepTime = 0;

int currentBuzzerLevel = 0;


// ============================================================
// FAILURE FEEDBACK CONTROL
// ============================================================

int failureBlinkCount = 0;

bool failureLEDOn = false;

unsigned long failureFeedbackTimer = 0;


// ============================================================
// BUTTON DEBOUNCE
// ============================================================

struct ButtonState {

  int pin;

  bool stableState;
  bool lastReading;

  unsigned long lastChangeTime;
};


ButtonState button1 = {
  BUTTON1_PIN,
  HIGH,
  HIGH,
  0
};

ButtonState button2 = {
  BUTTON2_PIN,
  HIGH,
  HIGH,
  0
};

ButtonState button3 = {
  BUTTON3_PIN,
  HIGH,
  HIGH,
  0
};

ButtonState button4 = {
  BUTTON4_PIN,
  HIGH,
  HIGH,
  0
};

ButtonState enterButton = {
  ENTER_BUTTON_PIN,
  HIGH,
  HIGH,
  0
};

ButtonState resetButton = {
  RESET_BUTTON_PIN,
  HIGH,
  HIGH,
  0
};

ButtonState alarmOffButton = {
  ALARM_OFF_PIN,
  HIGH,
  HIGH,
  0
};


// ============================================================
// HELPER FUNCTIONS
// ============================================================

void allLEDsOff() {

  for (int i = 0; i < 4; i++) {
    digitalWrite(LED_PINS[i], LOW);
  }
}


void lightLED(int ledNumber) {

  allLEDsOff();

  if (ledNumber >= 1 && ledNumber <= 4) {
    digitalWrite(LED_PINS[ledNumber - 1], HIGH);
  }
}


void stopBuzzer() {

  ledcWrite(BUZZER_PIN, 0);

  buzzerActive = false;

  currentBuzzerLevel = 0;
}


void startBuzzer(int frequency, int level) {

  ledcWriteTone(BUZZER_PIN, frequency);

  ledcWrite(BUZZER_PIN, level);

  buzzerActive = true;

  currentBuzzerLevel = level;

  buzzerTimer = millis();
}


void stopAllOutputs() {

  allLEDsOff();
  stopBuzzer();
}


// ============================================================
// BUTTON HANDLING
// ============================================================

bool buttonPressed(ButtonState &button) {

  bool reading = digitalRead(button.pin);

  if (reading != button.lastReading) {

    button.lastChangeTime = millis();

    button.lastReading = reading;
  }

  if ((millis() - button.lastChangeTime) > DEBOUNCE_MS) {

    if (reading != button.stableState) {

      button.stableState = reading;

      // INPUT_PULLUP:
      // LOW = pressed
      if (button.stableState == LOW) {
        return true;
      }
    }
  }

  return false;
}


// ============================================================
// RANDOM SEQUENCE GENERATION
// ============================================================

void generateSequence() {

  while (true) {

    for (int i = 0; i < SEQUENCE_LENGTH; i++) {

      expectedSequence[i] = random(1, 5);
    }

    // --------------------------------------------------------
    // Avoid sequences where all four LEDs are identical.
    // Also avoid 3 or more identical consecutive LEDs.
    // --------------------------------------------------------

    bool valid = true;

    if (
      expectedSequence[0] == expectedSequence[1] &&
      expectedSequence[1] == expectedSequence[2] &&
      expectedSequence[2] == expectedSequence[3]
    ) {

      valid = false;
    }

    int consecutiveCount = 1;

    for (int i = 1; i < SEQUENCE_LENGTH; i++) {

      if (expectedSequence[i] == expectedSequence[i - 1]) {

        consecutiveCount++;

        if (consecutiveCount >= 3) {
          valid = false;
        }

      } else {

        consecutiveCount = 1;
      }
    }

    if (valid) {
      break;
    }
  }
}


// ============================================================
// START NEW ROUND
// ============================================================

void startNewRound() {

  currentRound++;

  currentAttempt = 1;

  userInputCount = 0;

  inactivityStarted = false;

  generateSequence();

  playbackIndex = 0;

  playbackLEDOn = false;

  playbackTimer = millis();

  stage1State = STAGE1_PLAYBACK;

  stopBuzzer();

  allLEDsOff();
}


// ============================================================
// START STAGE 1
// ============================================================

void startStage1() {

  if (
    stage1State == STAGE1_PLAYBACK ||
    stage1State == STAGE1_INPUT ||
    stage1State == STAGE1_FAILURE_FEEDBACK
  ) {
    return;
  }

  currentRound = 0;

  consecutiveSuccesses = 0;

  currentAttempt = 0;

  totalFailures = 0;

  userInputCount = 0;

  inactivityStarted = false;

  stopAllOutputs();

  startNewRound();
}


// ============================================================
// STOP STAGE 1
// ============================================================

void stopStage1() {

  stage1State = STAGE1_IDLE;

  currentRound = 0;

  consecutiveSuccesses = 0;

  currentAttempt = 0;

  userInputCount = 0;

  totalFailures = 0;

  inactivityStarted = false;

  stopAllOutputs();
}


// ============================================================
// PLAY SEQUENCE
// ============================================================

void updatePlayback() {

  unsigned long now = millis();

  // --------------------------------------------------------
  // LED currently ON
  // --------------------------------------------------------

  if (playbackLEDOn) {

    if (now - playbackTimer >= LED_ON_TIME_MS) {

      allLEDsOff();

      playbackLEDOn = false;

      playbackTimer = now;
    }

    return;
  }


  // --------------------------------------------------------
  // LED currently OFF
  // --------------------------------------------------------

  if (now - playbackTimer >= LED_GAP_TIME_MS) {

    if (playbackIndex < SEQUENCE_LENGTH) {

      lightLED(expectedSequence[playbackIndex]);

      playbackLEDOn = true;

      playbackTimer = now;

      playbackIndex++;

    } else {

      // Sequence completely played.

      allLEDsOff();

      stage1State = STAGE1_INPUT;

      userInputCount = 0;

      inputStartTime = now;

      inactivityStarted = false;

      nextNormalBeepTime = now + NORMAL_BEEP_INTERVAL_MS;
    }
  }
}


// ============================================================
// NORMAL INPUT BUZZER
// ============================================================

void updateNormalInputBuzzer() {

  unsigned long now = millis();

  if (inactivityStarted) {
    return;
  }

  // Small, low-volume periodic beep.
  if (!buzzerActive && now >= nextNormalBeepTime) {

    startBuzzer(
      NORMAL_BUZZER_FREQUENCY,
      NORMAL_BUZZER_LEVEL
    );

    buzzerTimer = now;
  }

  if (buzzerActive) {

    if (now - buzzerTimer >= NORMAL_BEEP_ON_MS) {

      stopBuzzer();

      nextNormalBeepTime =
        now + NORMAL_BEEP_INTERVAL_MS;
    }
  }
}


// ============================================================
// INACTIVITY BUZZER
// ============================================================

void startRandomInactivityBeep() {

  int frequency = random(
    INACTIVITY_MIN_FREQUENCY,
    INACTIVITY_MAX_FREQUENCY + 1
  );

  int level = random(
    INACTIVITY_MIN_LEVEL,
    INACTIVITY_MAX_LEVEL + 1
  );

  unsigned long beepTime = random(
    INACTIVITY_MIN_BEEP_ON_MS,
    INACTIVITY_MAX_BEEP_ON_MS + 1
  );

  startBuzzer(
    frequency,
    level
  );

  buzzerTimer = millis();

  // Store the beep duration using inactivityTimer.
  inactivityTimer = beepTime;
}


void updateInactivityBuzzer() {

  unsigned long now = millis();

  if (!inactivityStarted) {

    // User has been given the initial 5-second grace period.

    if (now - inputStartTime >= INPUT_GRACE_PERIOD_MS) {

      inactivityStarted = true;

      stopBuzzer();

      startRandomInactivityBeep();
    }

    return;
  }


  // --------------------------------------------------------
  // Buzzer currently ON
  // --------------------------------------------------------

  if (buzzerActive) {

    if (now - buzzerTimer >= inactivityTimer) {

      stopBuzzer();

      // Random OFF interval.
      inactivityTimer = random(
        INACTIVITY_MIN_GAP_MS,
        INACTIVITY_MAX_GAP_MS + 1
      );

      buzzerTimer = now;
    }

    return;
  }


  // --------------------------------------------------------
  // Buzzer currently OFF
  // --------------------------------------------------------

  if (now - buzzerTimer >= inactivityTimer) {

    startRandomInactivityBeep();
  }
}


// ============================================================
// RECORD USER BUTTON
// ============================================================

void recordUserInput(int ledNumber) {

  if (stage1State != STAGE1_INPUT) {
    return;
  }

  // User has started interacting.
  inactivityStarted = false;

  stopBuzzer();

  if (userInputCount < SEQUENCE_LENGTH) {

    userSequence[userInputCount] = ledNumber;

    userInputCount++;
  }
}


// ============================================================
// RESET CURRENT ANSWER
// ============================================================

void resetCurrentInput() {

  if (stage1State != STAGE1_INPUT) {
    return;
  }

  stopBuzzer();

  userInputCount = 0;

  inactivityStarted = false;

  // Replay SAME sequence.
  playbackIndex = 0;

  playbackLEDOn = false;

  playbackTimer = millis();

  allLEDsOff();

  stage1State = STAGE1_PLAYBACK;
}


// ============================================================
// CHECK ANSWER
// ============================================================

bool checkAnswer() {

  if (userInputCount != SEQUENCE_LENGTH) {
    return false;
  }

  for (int i = 0; i < SEQUENCE_LENGTH; i++) {

    if (userSequence[i] != expectedSequence[i]) {

      return false;
    }
  }

  return true;
}


// ============================================================
// FAILURE BUZZER
// ============================================================

void playFailureBuzzer() {

  int index = currentAttempt - 1;

  if (index >= FAILURE_LEVEL_COUNT) {
    index = FAILURE_LEVEL_COUNT - 1;
  }

  startBuzzer(
    FAILURE_FREQUENCIES[index],
    FAILURE_LEVELS[index]
  );
}


// ============================================================
// FAILURE LED FEEDBACK
// ============================================================

void startFailureFeedback() {

  stopBuzzer();

  allLEDsOff();

  failureBlinkCount = 0;

  failureLEDOn = false;

  failureFeedbackTimer = millis();

  stage1State = STAGE1_FAILURE_FEEDBACK;
}


void updateFailureFeedback() {

  unsigned long now = millis();

  if (failureLEDOn) {

    if (now - failureFeedbackTimer >= FAILURE_LED_ON_MS) {

      allLEDsOff();

      failureLEDOn = false;

      failureFeedbackTimer = now;

      failureBlinkCount++;
    }

  } else {

    if (failureBlinkCount >= FAILURE_BLINK_COUNT) {

      // LED feedback finished.

      playFailureBuzzer();

      delay(180);

      stopBuzzer();

      // Same sequence again.
      userInputCount = 0;

      playbackIndex = 0;

      playbackLEDOn = false;

      playbackTimer = millis();

      stage1State = STAGE1_PLAYBACK;

      currentAttempt++;

      return;
    }


    if (now - failureFeedbackTimer >= FAILURE_LED_OFF_MS) {

      lightLED(1);
      digitalWrite(LED2_PIN, HIGH);
      digitalWrite(LED3_PIN, HIGH);
      digitalWrite(LED4_PIN, HIGH);

      failureLEDOn = true;

      failureFeedbackTimer = now;
    }
  }
}


// ============================================================
// SUBMIT ANSWER
// ============================================================

void submitAnswer() {

  if (stage1State != STAGE1_INPUT) {
    return;
  }

  // Don't evaluate incomplete input.
  if (userInputCount != SEQUENCE_LENGTH) {
    return;
  }

  stopBuzzer();

  if (checkAnswer()) {

    // --------------------------------------------------------
    // CORRECT
    // --------------------------------------------------------

    consecutiveSuccesses++;

    // Immediately continue to next sequence.
    if (
      consecutiveSuccesses >=
      REQUIRED_CONSECUTIVE_SUCCESSES
    ) {

      stage1State = STAGE1_COMPLETE;

      allLEDsOff();

      stopBuzzer();

      return;
    }

    // No special positive feedback.
    // Start next sequence immediately.
    startNewRound();

  } else {

    // --------------------------------------------------------
    // WRONG
    // --------------------------------------------------------

    consecutiveSuccesses = 0;

    totalFailures++;

    startFailureFeedback();
  }
}


// ============================================================
// HANDLE BUTTONS
// ============================================================

void updateButtons() {

  // ----------------------------------------------------------
  // ALARM OFF BUTTON
  // ----------------------------------------------------------

  if (buttonPressed(alarmOffButton)) {

    if (stage1State == STAGE1_IDLE) {

      startStage1();
    }
  }


  // ----------------------------------------------------------
  // STAGE 1 BUTTONS
  // ----------------------------------------------------------

  if (buttonPressed(button1)) {
    recordUserInput(1);
  }

  if (buttonPressed(button2)) {
    recordUserInput(2);
  }

  if (buttonPressed(button3)) {
    recordUserInput(3);
  }

  if (buttonPressed(button4)) {
    recordUserInput(4);
  }


  // ----------------------------------------------------------
  // RESET
  // ----------------------------------------------------------

  if (buttonPressed(resetButton)) {

    resetCurrentInput();
  }


  // ----------------------------------------------------------
  // ENTER
  // ----------------------------------------------------------

  if (buttonPressed(enterButton)) {

    submitAnswer();
  }
}


// ============================================================
// SEQUENCE TO STRING
// ============================================================

String getSequenceString() {

  String result = "";

  for (int i = 0; i < SEQUENCE_LENGTH; i++) {

    result += String(expectedSequence[i]);

    if (i < SEQUENCE_LENGTH - 1) {
      result += " → ";
    }
  }

  return result;
}


String getUserInputString() {

  String result = "";

  for (int i = 0; i < userInputCount; i++) {

    result += String(userSequence[i]);

    if (i < userInputCount - 1) {
      result += " → ";
    }
  }

  if (userInputCount == 0) {
    result = "—";
  }

  return result;
}


String getStateString() {

  switch (stage1State) {

    case STAGE1_IDLE:
      return "READY";

    case STAGE1_PLAYBACK:
      return "PLAYING SEQUENCE";

    case STAGE1_INPUT:
      if (inactivityStarted) {
        return "WAITING — NO INPUT / BUZZER ESCALATING";
      }

      return "WAITING FOR INPUT";

    case STAGE1_FAILURE_FEEDBACK:
      return "WRONG — FAILURE FEEDBACK";

    case STAGE1_COMPLETE:
      return "STAGE 1 COMPLETE";
  }

  return "UNKNOWN";
}


String getCurrentlyGlowing() {

  if (stage1State != STAGE1_PLAYBACK) {
    return "None";
  }

  if (!playbackLEDOn) {
    return "None";
  }

  if (playbackIndex <= 0) {
    return "None";
  }

  return "LED " + String(
    expectedSequence[playbackIndex - 1]
  );
}


// ============================================================
// DASHBOARD HTML
// ============================================================

const char MAIN_PAGE[] PROGMEM = R"rawliteral(

<!DOCTYPE html>

<html>

<head>

<meta name="viewport"
      content="width=device-width,initial-scale=1">

<title>Stage 1 Cognitive Test</title>

<style>

body {
  font-family: Arial, sans-serif;
  background: #111;
  color: #eee;
  margin: 0;
  padding: 20px;
}

.container {
  max-width: 700px;
  margin: auto;
}

.card {
  background: #1e1e1e;
  border-radius: 14px;
  padding: 20px;
  margin-bottom: 15px;
}

h1 {
  margin-top: 0;
}

.value {
  font-size: 22px;
  font-weight: bold;
}

.sequence {
  font-size: 28px;
  font-weight: bold;
  letter-spacing: 3px;
  margin-top: 10px;
}

.input {
  font-size: 24px;
  margin-top: 10px;
}

button {
  padding: 14px 20px;
  margin: 5px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
}

.start {
  background: #2e7d32;
  color: white;
}

.stop {
  background: #c62828;
  color: white;
}

.label {
  color: #aaa;
  margin-top: 12px;
}

</style>

</head>

<body>

<div class="container">

<div class="card">

<h1>Stage 1 — Cognitive Test</h1>

<div class="label">Status</div>
<div class="value" id="status">---</div>

<div class="label">Round</div>
<div class="value" id="round">---</div>

<div class="label">Consecutive Success</div>
<div class="value" id="success">---</div>

<div class="label">Current Attempt</div>
<div class="value" id="attempt">---</div>

<div class="label">Total Failures</div>
<div class="value" id="failures">---</div>

</div>


<div class="card">

<div class="label">LED Sequence</div>

<div class="sequence" id="sequence">
---
</div>

<div class="label">Currently Glowing</div>

<div class="value" id="glowing">
---
</div>

</div>


<div class="card">

<div class="label">User Input</div>

<div class="input" id="input">
---
</div>

<div class="label">Inactivity</div>

<div class="value" id="inactivity">
---
</div>

<div class="label">Buzzer</div>

<div class="value" id="buzzer">
---
</div>

</div>


<div class="card">

<button class="start"
        onclick="startStage()">

START STAGE 1

</button>

<button class="stop"
        onclick="stopStage()">

STOP STAGE 1

</button>

</div>

</div>


<script>

function updateData() {

  fetch('/data')
    .then(response => response.json())
    .then(data => {

      document.getElementById('status').innerText =
        data.status;

      document.getElementById('round').innerText =
        data.round + " / 5";

      document.getElementById('success').innerText =
        data.success + " / 5";

      document.getElementById('attempt').innerText =
        data.attempt;

      document.getElementById('failures').innerText =
        data.failures;

      document.getElementById('sequence').innerText =
        data.sequence;

      document.getElementById('glowing').innerText =
        data.glowing;

      document.getElementById('input').innerText =
        data.input;

      document.getElementById('inactivity').innerText =
        data.inactivity;

      document.getElementById('buzzer').innerText =
        data.buzzer;
    });
}


function startStage() {

  fetch('/start-stage1')
    .then(() => updateData());
}


function stopStage() {

  fetch('/stop-stage1')
    .then(() => updateData());
}


setInterval(updateData, 300);

updateData();

</script>

</body>

</html>

)rawliteral";


// ============================================================
// DASHBOARD DATA
// ============================================================

void handleData() {

  String json = "{";

  json += "\"status\":\"";
  json += getStateString();
  json += "\",";

  json += "\"round\":";
  json += String(currentRound);
  json += ",";

  json += "\"success\":";
  json += String(consecutiveSuccesses);
  json += ",";

  json += "\"attempt\":";
  json += String(currentAttempt);
  json += ",";

  json += "\"failures\":";
  json += String(totalFailures);
  json += ",";

  json += "\"sequence\":\"";
  json += getSequenceString();
  json += "\",";

  json += "\"glowing\":\"";
  json += getCurrentlyGlowing();
  json += "\",";

  json += "\"input\":\"";
  json += getUserInputString();
  json += "\",";

  json += "\"inactivity\":\"";

  if (inactivityStarted) {
    json += "ESCALATING";
  } else if (stage1State == STAGE1_INPUT) {
    json += String(
      (millis() - inputStartTime) / 1000
    );
    json += " s";
  } else {
    json += "—";
  }

  json += "\",";

  json += "\"buzzer\":\"";

  if (buzzerActive) {
    json += "ON / Level ";
    json += String(currentBuzzerLevel);
  } else {
    json += "OFF";
  }

  json += "\"";

  json += "}";

  server.send(
    200,
    "application/json",
    json
  );
}


// ============================================================
// WEB ROUTES
// ============================================================

void handleRoot() {

  server.send_P(
    200,
    "text/html",
    MAIN_PAGE
  );
}


void handleStartStage() {

  startStage1();

  server.send(
    200,
    "text/plain",
    "Stage 1 started"
  );
}


void handleStopStage() {

  stopStage1();

  server.send(
    200,
    "text/plain",
    "Stage 1 stopped"
  );
}


// ============================================================
// SETUP
// ============================================================

void setup() {

  Serial.begin(115200);

  delay(500);

  Serial.println();
  Serial.println("==============================");
  Serial.println(" STAGE 1 COGNITIVE TEST");
  Serial.println("==============================");


  // ----------------------------------------------------------
  // LED OUTPUTS
  // ----------------------------------------------------------

  for (int i = 0; i < 4; i++) {

    pinMode(
      LED_PINS[i],
      OUTPUT
    );
  }

  allLEDsOff();


  // ----------------------------------------------------------
  // BUTTON INPUTS
  // ----------------------------------------------------------

  pinMode(
    BUTTON1_PIN,
    INPUT_PULLUP
  );

  pinMode(
    BUTTON2_PIN,
    INPUT_PULLUP
  );

  pinMode(
    BUTTON3_PIN,
    INPUT_PULLUP
  );

  pinMode(
    BUTTON4_PIN,
    INPUT_PULLUP
  );

  pinMode(
    ENTER_BUTTON_PIN,
    INPUT_PULLUP
  );

  pinMode(
    RESET_BUTTON_PIN,
    INPUT_PULLUP
  );

  pinMode(
    ALARM_OFF_PIN,
    INPUT_PULLUP
  );


  // ----------------------------------------------------------
  // BUZZER PWM
  // ----------------------------------------------------------

  ledcAttach(
    BUZZER_PIN,
    BUZZER_PWM_FREQUENCY,
    BUZZER_PWM_RESOLUTION
  );

  ledcWrite(
    BUZZER_PIN,
    0
  );


  // ----------------------------------------------------------
  // RANDOM SEED
  // ----------------------------------------------------------

  randomSeed(
    micros()
  );


  // ----------------------------------------------------------
  // WIFI ACCESS POINT
  // ----------------------------------------------------------

  WiFi.mode(WIFI_AP);

  WiFi.softAP(
    ssid,
    password
  );

  Serial.println();

  Serial.print(
    "WiFi AP: "
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


  // ----------------------------------------------------------
  // WEB SERVER
  // ----------------------------------------------------------

  server.on(
    "/",
    handleRoot
  );

  server.on(
    "/data",
    handleData
  );

  server.on(
    "/start-stage1",
    handleStartStage
  );

  server.on(
    "/stop-stage1",
    handleStopStage
  );

  server.begin();

  Serial.println(
    "Stage 1 server started."
  );

  Serial.println();
  Serial.println(
    "Press Alarm OFF button or"
  );

  Serial.println(
    "use START STAGE 1 on dashboard."
  );
}


// ============================================================
// MAIN LOOP
// ============================================================

void loop() {

  server.handleClient();

  updateButtons();


  switch (stage1State) {

    case STAGE1_IDLE:

      // Nothing to do.
      break;


    case STAGE1_PLAYBACK:

      updatePlayback();

      break;


    case STAGE1_INPUT:

      updateNormalInputBuzzer();

      updateInactivityBuzzer();

      break;


    case STAGE1_FAILURE_FEEDBACK:

      updateFailureFeedback();

      break;


    case STAGE1_COMPLETE:

      // Everything remains stopped.
      break;
  }
}