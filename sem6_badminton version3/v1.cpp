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

// ================= THRESHOLDS =================
float START_THRESHOLD = 17.0;
float END_THRESHOLD   = 8.5;
float MIN_DURATION = 0.25;
unsigned long COOLDOWN = 350;

// ================= SENSOR VALUES =================
float Ax, Ay, Az, Gx, Gy, Gz;
float Ax_f, Ay_f, Az_f, Gx_f, Gy_f, Gz_f;

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

// ================= LOW PASS =================
float alpha = 0.8;

// ================= CSV BUFFER =================
String csvData = "";

// ================= SETUP =================
void setup() {
  Serial.begin(115200);
  Wire.begin();

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }

  server.on("/data", handleData);
  server.on("/download", handleDownload);

  server.begin();
}

// ================= SENSOR READ =================
void readSensor() {
  int16_t ax, ay, az, gx, gy, gz;

  Wire.beginTransmission(0x68);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(0x68, 14, true);

  ax = Wire.read() << 8 | Wire.read();
  ay = Wire.read() << 8 | Wire.read();
  az = Wire.read() << 8 | Wire.read();
  Wire.read(); Wire.read();
  gx = Wire.read() << 8 | Wire.read();
  gy = Wire.read() << 8 | Wire.read();
  gz = Wire.read() << 8 | Wire.read();

  Ax = ax / 16384.0;
  Ay = ay / 16384.0;
  Az = az / 16384.0;

  Gx = gx / 16.4;
  Gy = gy / 16.4;
  Gz = gz / 16.4;

  // LOW PASS FILTER
  Ax_f = alpha * Ax_f + (1 - alpha) * Ax;
  Ay_f = alpha * Ay_f + (1 - alpha) * Ay;
  Az_f = alpha * Az_f + (1 - alpha) * Az;

  Gx_f = alpha * Gx_f + (1 - alpha) * Gx;
  Gy_f = alpha * Gy_f + (1 - alpha) * Gy;
  Gz_f = alpha * Gz_f + (1 - alpha) * Gz;
}

// ================= SWING DETECTION =================
void detectSwing() {

  unsigned long now = millis();

  float accMag = sqrt(Ax_f*Ax_f + Ay_f*Ay_f + Az_f*Az_f);
  float gyroMag = sqrt(Gx_f*Gx_f + Gy_f*Gy_f + Gz_f*Gz_f);

  // START
  if (!swing &&
      accMag > START_THRESHOLD &&
      gyroMag > 120 &&
      (now - lastSwingEnd > COOLDOWN)) {

    swing = true;
    swingStart = now;

    peak_acc = 0;
    peak_gyro = 0;
  }

  // ACTIVE SWING
  if (swing) {

    if (accMag > peak_acc) peak_acc = accMag;
    if (gyroMag > peak_gyro) peak_gyro = gyroMag;

    duration = (now - swingStart) / 1000.0;

    // END
    if ((accMag < END_THRESHOLD && gyroMag < 60) &&
        duration > MIN_DURATION) {

      endSwing();
    }

    // safety timeout
    if (duration > 1.5) {
      endSwing();
    }
  }
}

// ================= END SWING =================
void endSwing() {

  swing_id++;

  // SPI (DISPLAY ONLY)
  SPI = 0.7 * peak_gyro + 0.3 * peak_acc;

  sendData();

  swing = false;
  lastSwingEnd = millis();
}

// ================= SEND DATA =================
void sendData() {

  unsigned long t = millis();

  // JSON for dashboard
  StaticJsonDocument<256> doc;

  doc["swing_id"] = swing_id;
  doc["duration"] = duration;
  doc["peak_acc"] = peak_acc;
  doc["peak_gyro"] = peak_gyro;
  doc["spi"] = SPI;

  String output;
  serializeJson(doc, output);

  server.send(200, "application/json", output);

  // CSV (ONLY ML DATA)
  csvData += String(swing_id) + ",";
  csvData += String(t) + ",";
  csvData += String(Ax_f) + ",";
  csvData += String(Ay_f) + ",";
  csvData += String(Az_f) + ",";
  csvData += String(Gx_f) + ",";
  csvData += String(Gy_f) + ",";
  csvData += String(Gz_f) + ",";
  csvData += String(peak_acc) + ",";
  csvData += String(peak_gyro) + ",";
  csvData += String(duration) + "\n";
}

// ================= HTTP HANDLERS =================
void handleData() {
  server.send(200, "text/plain", csvData);
}

void handleDownload() {
  server.send(200, "text/csv", csvData);
}

// ================= LOOP =================
void loop() {
  server.handleClient();

  readSensor();
  detectSwing();

  delay(10);
}