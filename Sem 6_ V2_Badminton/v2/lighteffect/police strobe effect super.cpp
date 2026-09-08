#define GREEN 18
#define BLUE  19

unsigned long lastUpdate = 0;
unsigned long modeTimer = 0;

int mode = 0;

// timing control
int step = 0;
unsigned long interval = 50;

// helper
void allOff() {
  digitalWrite(GREEN, LOW);
  digitalWrite(BLUE, LOW);
}

// 🔵 BLUE BURST
void blueBurst() {
  switch(step) {
    case 0: digitalWrite(BLUE, HIGH); interval = 40; break;
    case 1: digitalWrite(BLUE, LOW);  interval = 40; break;
    case 2: digitalWrite(BLUE, HIGH); interval = 40; break;
    case 3: digitalWrite(BLUE, LOW);  interval = 120; break;
  }
  step = (step + 1) % 4;
}

// 🟢 GREEN BURST
void greenBurst() {
  switch(step) {
    case 0: digitalWrite(GREEN, HIGH); interval = 40; break;
    case 1: digitalWrite(GREEN, LOW);  interval = 40; break;
    case 2: digitalWrite(GREEN, HIGH); interval = 40; break;
    case 3: digitalWrite(GREEN, LOW);  interval = 120; break;
  }
  step = (step + 1) % 4;
}

// 🔄 ALTERNATING POLICE (LEFT-RIGHT FEEL)
void alternating() {
  switch(step) {
    case 0: digitalWrite(BLUE, HIGH); digitalWrite(GREEN, LOW); interval = 60; break;
    case 1: allOff(); interval = 40; break;
    case 2: digitalWrite(GREEN, HIGH); digitalWrite(BLUE, LOW); interval = 60; break;
    case 3: allOff(); interval = 40; break;
  }
  step = (step + 1) % 4;
}

// 💥 CHAOTIC STROBE (INTENSE MODE)
void chaosMode() {
  digitalWrite(BLUE, random(0,2));
  digitalWrite(GREEN, random(0,2));
  interval = random(30, 90);
}

// 🚓 SWEEP EFFECT (FAST SIDE SWITCH)
void sweepMode() {
  switch(step) {
    case 0: digitalWrite(BLUE, HIGH); digitalWrite(GREEN, LOW); interval = 30; break;
    case 1: digitalWrite(BLUE, LOW);  digitalWrite(GREEN, HIGH); interval = 30; break;
  }
  step = (step + 1) % 2;
}

void setup() {
  pinMode(GREEN, OUTPUT);
  pinMode(BLUE, OUTPUT);

  randomSeed(analogRead(0));
}

// 🎯 MAIN LOOP
void loop() {

  unsigned long now = millis();

  // 🔁 change mode every 5 seconds
  if (now - modeTimer > 5000) {
    mode = (mode + 1) % 5;
    modeTimer = now;
    step = 0;
  }

  if (now - lastUpdate > interval) {

    switch(mode) {

      case 0: blueBurst(); break;

      case 1: greenBurst(); break;

      case 2: alternating(); break;

      case 3: sweepMode(); break;

      case 4: chaosMode(); break;
    }

    lastUpdate = now;
  }
}