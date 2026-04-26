#include <Wire.h>
#include <MPU6050.h>
#include <math.h>

MPU6050 mpu;

#define LED_PIN 2

// ---------------- SETTINGS ----------------

// Weak test → 12
// Medium test → 15
// Strong test -> 20
float START_THRESHOLD = 15;

float END_THRESHOLD = 7;
float MIN_DURATION = 0.25;
unsigned long COOLDOWN = 400;

// ---------------- OFFSETS ----------------

float axO = 0, ayO = 0, azO = 0;

// ---------------- SWING STATE ----------------

bool swing = false;
unsigned long swingStart = 0;
unsigned long lastSwingEnd = 0;

float velocity = 0;
float maxImpact = 0;

// ---------------- FILTER ----------------

float gravity = 0;
float alpha = 0.95;

unsigned long lastTime = 0;

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

  // -------- Calibration --------

  long ax = 0, ay = 0, az = 0;
  int n = 0;

  unsigned long t = millis();

  while (millis() - t < 3000) {
    int16_t a, b, c, d, e, f;
    mpu.getMotion6(&a, &b, &c, &d, &e, &f);

    ax += a;
    ay += b;
    az += c;
    n++;

    delay(2);
  }

  axO = ax / (float)n;
  ayO = ay / (float)n;
  azO = az / (float)n;

  lastTime = millis();

  Serial.println("timestamp,speed,impact,duration");
}

void loop() {

  int16_t ax, ay, az, gx, gy, gz;
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

  float Ax = (ax - axO) / 16384.0;
  float Ay = (ay - ayO) / 16384.0;
  float Az = (az - azO) / 16384.0;

  // -------- Gravity Removal --------

  gravity = alpha * gravity + (1 - alpha) * Az;

  float linAccX = Ax * 9.81;
  float linAccY = Ay * 9.81;
  float linAccZ = (Az - gravity) * 9.81;

  float totalAcc = sqrt(
    linAccX * linAccX +
    linAccY * linAccY +
    linAccZ * linAccZ
  );

  unsigned long now = millis();
  float dt = (now - lastTime) / 1000.0;
  lastTime = now;

  // ---------------- START SWING ----------------

  if (!swing &&
      totalAcc > START_THRESHOLD &&
      (now - lastSwingEnd > COOLDOWN)) {

    swing = true;
    swingStart = now;
    velocity = 0;
    maxImpact = totalAcc;

    digitalWrite(LED_PIN, HIGH);
  }

  // ---------------- DURING SWING ----------------

  if (swing) {

    // TRUE 3-axis speed estimate
    velocity += totalAcc * dt;

    if (totalAcc > maxImpact)
      maxImpact = totalAcc;

    float duration = (now - swingStart) / 1000.0;

    // ---------------- END SWING ----------------

    if (totalAcc < END_THRESHOLD &&
        duration > MIN_DURATION) {

      float speed = fabs(velocity) * 3.6;

      Serial.print(now);
      Serial.print(",");

      Serial.print(speed, 2);
      Serial.print(",");

      Serial.print(maxImpact, 2);
      Serial.print(",");

      Serial.println(duration, 2);

      swing = false;
      lastSwingEnd = now;

      digitalWrite(LED_PIN, LOW);
    }
  }

  delay(10);
}

/*
speed: 6 -17
impact: 4-7
duration: 0.25 - 0.4s

*/
