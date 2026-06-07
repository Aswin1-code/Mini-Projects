#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>

// ================= WIFI =================
const char* ssid = "YOUR_WIFI";
const char* password = "YOUR_PASSWORD";

WebServer server(80);

// ================= MODE =================
enum SystemMode {
  DATA_COLLECTION = 1,
  PLAYER_ASSESSMENT = 2
};

SystemMode mode = DATA_COLLECTION;

// ================= PLAYER / SESSION =================
String player_id = "P001";
String session_id = "S001";

// ================= STRUCTS =================
struct IMUData {
  float ax, ay, az;
  float gx, gy, gz;
  float acc_mag;
  float gyro_mag;
};

struct SwingData {
  int swing_id;
  unsigned long timestamp;
  float peak_acc;
  float peak_gyro;
  float duration;
  float spi;
};

// ================= MPU =================
#define MPU_ADDR 0x68

float Ax, Ay, Az, Gx, Gy, Gz;

float axO = 0, ayO = 0, azO = 0;
float gxO = 0, gyO = 0, gzO = 0;

float Ax_f = 0, Ay_f = 0, Az_f = 0;
float Gx_f = 0, Gy_f = 0, Gz_f = 0;

float alpha = 0.8;

// ================= SWING STATE =================
bool swing = false;
unsigned long swingStart = 0;
unsigned long lastSwingEnd = 0;

int swing_id = 0;

// ================= FEATURES =================
float peak_acc = 0;
float peak_gyro = 0;
float duration = 0;
float SPI = 0;

// ================= THRESHOLDS =================
float START_THRESHOLD = 17.0;
float END_THRESHOLD = 8.5;
float MIN_DURATION = 0.25;
unsigned long COOLDOWN = 350;

// ================= CSV =================
String csvData = "";

// =====================================================
// CALIBRATION
// =====================================================
void calibrateMPU() {

  Serial.println("🚗 Hold racket steady for 3 seconds...");

  long ax = 0, ay = 0, az = 0;
  long gx = 0, gy = 0, gz = 0;
  int n = 0;

  unsigned long start = millis();

  while (millis() - start < 3000) {

    int16_t rawAx, rawAy, rawAz, rawGx, rawGy, rawGz;

    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x3B);
    Wire.endTransmission(false);
    Wire.requestFrom(MPU_ADDR, 14, true);

    rawAx = Wire.read() << 8 | Wire.read();
    rawAy = Wire.read() << 8 | Wire.read();
    rawAz = Wire.read() << 8 | Wire.read();
    Wire.read(); Wire.read();
    rawGx = Wire.read() << 8 | Wire.read();
    rawGy = Wire.read() << 8 | Wire.read();
    rawGz = Wire.read() << 8 | Wire.read();

    ax += rawAx; ay += rawAy; az += rawAz;
    gx += rawGx; gy += rawGy; gz += rawGz;

    n++;
    delay(5);
  }

  axO = ax / (float)n;
  ayO = ay / (float)n;
  azO = az / (float)n;

  gxO = gx / (float)n;
  gyO = gy / (float)n;
  gzO = gz / (float)n;

  Serial.println("✅ Calibration Done");
}

// =====================================================
// SENSOR READ + FILTER
// =====================================================
void readSensor() {

  int16_t rawAx, rawAy, rawAz, rawGx, rawGy, rawGz;

  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 14, true);

  rawAx = Wire.read() << 8 | Wire.read();
  rawAy = Wire.read() << 8 | Wire.read();
  rawAz = Wire.read() << 8 | Wire.read();
  Wire.read(); Wire.read();
  rawGx = Wire.read() << 8 | Wire.read();
  rawGy = Wire.read() << 8 | Wire.read();
  rawGz = Wire.read() << 8 | Wire.read();

  Ax = (rawAx - axO) / 16384.0;
  Ay = (rawAy - ayO) / 16384.0;
  Az = (rawAz - azO) / 16384.0;

  Gx = (rawGx - gxO) / 16.4;
  Gy = (rawGy - gyO) / 16.4;
  Gz = (rawGz - gzO) / 16.4;

  Ax_f = alpha * Ax_f + (1 - alpha) * Ax;
  Ay_f = alpha * Ay_f + (1 - alpha) * Ay;
  Az_f = alpha * Az_f + (1 - alpha) * Az;

  Gx_f = alpha * Gx_f + (1 - alpha) * Gx;
  Gy_f = alpha * Gy_f + (1 - alpha) * Gy;
  Gz_f = alpha * Gz_f + (1 - alpha) * Gz;
}

// =====================================================
// SWING DETECTION (UNCHANGED)
// =====================================================
void detectSwing() {

  unsigned long now = millis();

  float accMag = sqrt(Ax_f*Ax_f + Ay_f*Ay_f + Az_f*Az_f);
  float gyroMag = sqrt(Gx_f*Gx_f + Gy_f*Gy_f + Gz_f*Gz_f);

  if (!swing &&
      accMag > START_THRESHOLD &&
      gyroMag > 120 &&
      (now - lastSwingEnd > COOLDOWN)) {

    swing = true;
    swingStart = now;
    peak_acc = 0;
    peak_gyro = 0;
  }

  if (swing) {

    if (accMag > peak_acc) peak_acc = accMag;
    if (gyroMag > peak_gyro) peak_gyro = gyroMag;

    duration = (now - swingStart) / 1000.0;

    if ((accMag < END_THRESHOLD && gyroMag < 60 && duration > MIN_DURATION) ||
        duration > 1.5) {

      endSwing();
    }
  }
}

// =====================================================
// END SWING
// =====================================================
void endSwing() {

  swing = false;
  lastSwingEnd = millis();
  swing_id++;

  SPI = 0.7 * peak_gyro + 0.3 * peak_acc;

  SwingData s;
  s.swing_id = swing_id;
  s.timestamp = millis();
  s.peak_acc = peak_acc;
  s.peak_gyro = peak_gyro;
  s.duration = duration;
  s.spi = SPI;

  sendData(s);
}

// =====================================================
// MODE BASED DATA BUILDER (NEW CLEAN DESIGN)
// =====================================================
void sendData(SwingData s) {

  StaticJsonDocument<256> doc;
  doc["swing_id"] = s.swing_id;
  doc["duration"] = s.duration;
  doc["peak_acc"] = s.peak_acc;
  doc["peak_gyro"] = s.peak_gyro;
  doc["spi"] = s.spi;

  String out;
  serializeJson(doc, out);
  server.send(200, "application/json", out);

  switch (mode) {

    case DATA_COLLECTION:
      csvData += String(s.swing_id) + ",";
      csvData += String(s.timestamp) + ",";
      csvData += String(Ax_f) + ",";
      csvData += String(Ay_f) + ",";
      csvData += String(Az_f) + ",";
      csvData += String(Gx_f) + ",";
      csvData += String(Gy_f) + ",";
      csvData += String(Gz_f) + ",";
      csvData += String(s.peak_acc) + ",";
      csvData += String(s.peak_gyro) + ",";
      csvData += String(s.duration) + "\n";
      break;

    case PLAYER_ASSESSMENT:
      csvData += player_id + ",";
      csvData += session_id + ",";
      csvData += String(s.swing_id) + ",";
      csvData += String(s.timestamp) + ",";
      csvData += String(Ax_f) + ",";
      csvData += String(Ay_f) + ",";
      csvData += String(Az_f) + ",";
      csvData += String(Gx_f) + ",";
      csvData += String(Gy_f) + ",";
      csvData += String(Gz_f) + ",";
      csvData += String(s.peak_acc) + ",";
      csvData += String(s.peak_gyro) + ",";
      csvData += String(s.duration) + "\n";
      break;
  }
}

// =====================================================
// HTTP
// =====================================================
void handleData() {
  server.send(200, "text/plain", csvData);
}

void setup() {

  Serial.begin(115200);
  Wire.begin(26, 25);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) delay(500);

  server.on("/data", handleData);
  server.begin();

  calibrateMPU();

  Serial.println("🚗 System Ready");
}

void loop() {

  server.handleClient();
  readSensor();
  detectSwing();
  delay(10);
}