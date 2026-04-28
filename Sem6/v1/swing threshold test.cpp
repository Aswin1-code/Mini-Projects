#include <Wire.h>
#include <MPU6050.h>
#include <math.h>

MPU6050 mpu;

#define LED_PIN 2

// =====================================================
// FINAL STABLE SWING CLASSIFICATION CODE
// Uses PEAK SPEED + PEAK IMPACT (NO velocity integration)
// =====================================================

// ---------- Detection Thresholds ----------
float START_THRESHOLD = 15.0;   // swing start detect
float END_THRESHOLD   = 7.0;    // swing end detect

float MIN_DURATION = 0.20;      // minimum valid swing
unsigned long COOLDOWN = 400;   // avoid double detection

// ---------- Classification Thresholds ----------

// WEAK:
// speed  : 10 – 20
// impact : 12 – 25

// MEDIUM:
// speed  : 20 – 40
// impact : 25 – 40

// STRONG:
// speed  : > 40
// impact : > 40

// ---------- Offsets ----------
float axO = 0;
float ayO = 0;
float azO = 0;

float gxO = 0;
float gyO = 0;
float gzO = 0;

// ---------- Swing State ----------
bool swing = false;

unsigned long swingStart = 0;
unsigned long lastSwingEnd = 0;

float peakSpeed = 0;
float maxImpact = 0;

// ---------- Gravity Filter ----------
float gravity = 0;
float alpha = 0.95;

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

  // ---------- Calibration ----------
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

  Serial.println("timestamp,speed,impact,duration,swing_type");
}

// =====================================================

void loop() {

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

  // ---------- Peak rotational speed ----------
  float angularVelocity = sqrt(
    Gx * Gx +
    Gy * Gy +
    Gz * Gz
  );

  // convert to rough swing speed (km/h)
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

    // =============================================
    // END SWING
    // =============================================

    if (totalAcc < END_THRESHOLD &&
        duration > MIN_DURATION) {

String swingType = "WEAK";

if (peakSpeed >= 50.5 && maxImpact >= 42) {
    swingType = "STRONG";
}
else if (peakSpeed >= 44) {
    swingType = "MEDIUM";
}
else {
    swingType = "WEAK";
}

      // ---------- Serial Output ----------
      Serial.print(now);
      Serial.print(",");

      Serial.print(peakSpeed, 2);
      Serial.print(",");

      Serial.print(maxImpact, 2);
      Serial.print(",");

      Serial.print(duration, 2);
      Serial.print(",");

      Serial.println(swingType);

      swing = false;
      lastSwingEnd = now;

      digitalWrite(LED_PIN, LOW);
    }
  }

  delay(10);
}


