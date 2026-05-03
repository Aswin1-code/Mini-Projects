#define BLUE  19
unsigned long lastStrobe = 0;
unsigned long interval = 1200;
void setup() {
  //pinMode(GREEN, OUTPUT);
  pinMode(BLUE, OUTPUT);

  randomSeed(analogRead(0));
}
void softFlash(int pin, int duration) {
  analogWrite(pin,2);
  delay(duration);
  analogWrite(pin, 0);
}
void tripleStrobe() {
  for (int i = 0; i < 3; i++) {
    softFlash(BLUE, 40);
    delay(50);
  }
}
void loop() {

  unsigned long now = millis();
  if (now - lastStrobe > interval) {

    tripleStrobe();
    interval = random(900, 1600);
    lastStrobe = now;
  }

  delay(10);
}