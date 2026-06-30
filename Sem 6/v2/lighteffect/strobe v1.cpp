#define GREEN 18
#define BLUE  19

unsigned long lastStrobe = 0;
unsigned long interval = 1200;

int greenBrightness = 0;
int fadeDirection = 1;

void setup() {
  pinMode(GREEN, OUTPUT);
  pinMode(BLUE, OUTPUT);

  randomSeed(analogRead(0));
}

// ✨ Smooth PWM fade (breathing effect)
void updateGreenBreathing() {

  greenBrightness += fadeDirection * 3;

  if (greenBrightness >= 255) {
    greenBrightness = 255;
    fadeDirection = -1;
  }
  else if (greenBrightness <= 80) {  // never fully off
    greenBrightness = 80;
    fadeDirection = 1;
  }

  analogWrite(GREEN, greenBrightness);
}

// ⚡ soft flash
void softFlash(int pin, int duration) {
  digitalWrite(pin, HIGH);
  delay(duration);
  digitalWrite(pin, LOW);
}

// ✈️ double strobe
void doubleStrobe() {
  softFlash(BLUE, 40);
  delay(60);
  softFlash(BLUE, 40);
}

// 💥 triple strobe
void tripleStrobe() {
  for (int i = 0; i < 3; i++) {
    softFlash(BLUE, 30);
    delay(50);
  }
}

// 🌊 realistic pattern
void advancedStrobePattern() {

  int pattern = random(0, 3);

  switch(pattern) {

    case 0:
      doubleStrobe();
      break;

    case 1:
      doubleStrobe();
      delay(120);
      softFlash(BLUE, 30);
      break;

    case 2:
      tripleStrobe();
      break;
  }
}

void loop() {

  unsigned long now = millis();

  // 🟢 continuously update green breathing
  //updateGreenBreathing();

  // 🔵 strobe logic
  if (now - lastStrobe > interval) {

    advancedStrobePattern();

    interval = random(900, 1600);
    lastStrobe = now;
  }

  delay(10);
}