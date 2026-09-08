#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <MPU6050.h>
#include <math.h>

MPU6050 mpu;

// =====================================================
// BADMINTON STROKE ML DATA COLLECTOR
// RAW MPU6050 DATA + WEB DASHBOARD + CSV DOWNLOAD
// =====================================================


// =====================================================
// WIFI ACCESS POINT
// =====================================================

const char* ssid = "ESP32_Swing";
const char* password = "12345678";

WebServer server(80);


// =====================================================
// MPU6050 PINS
// =====================================================

#define SDA_PIN 26
#define SCL_PIN 25


// =====================================================
// STROKE LABEL
// =====================================================
//
// Change ONLY this line for each stroke:
//
// smash
// drop
// drive
// clear
// forehand
// backhand
//

const char* STROKE_LABEL = "smash";


// =====================================================
// DATA COLLECTION
// =====================================================

const int TOTAL_SWINGS = 100;


// =====================================================
// DETECTION THRESHOLDS
// =====================================================

float START_THRESHOLD = 17.0;
float END_THRESHOLD   = 8.5;

float MIN_DURATION = 0.25;

unsigned long COOLDOWN = 350;


// =====================================================
// OFFSETS
// =====================================================

float axO = 0;
float ayO = 0;
float azO = 0;

float gxO = 0;
float gyO = 0;
float gzO = 0;


// =====================================================
// SWING STATE
// =====================================================

bool swing = false;

unsigned long swingStart = 0;
unsigned long lastSwingEnd = 0;


// =====================================================
// GRAVITY FILTER
// =====================================================

float gravity = 0;
float alpha = 0.95;


// =====================================================
// LIVE DATA
// =====================================================

float live_ax = 0;
float live_ay = 0;
float live_az = 0;

float live_gx = 0;
float live_gy = 0;
float live_gz = 0;

unsigned long live_timestamp = 0;

int swingCount = 0;


// =====================================================
// CSV STORAGE
// =====================================================

String csvData =
"timestamp,ax,ay,az,gx,gy,gz,stroke\n";


// =====================================================
// WEB DASHBOARD
// =====================================================

const char htmlPage[] PROGMEM = R"rawliteral(

<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>Badminton ML Data Collector</title>

<style>

body {
  font-family: Arial;
  background: #111;
  color: white;
  text-align: center;
  padding: 20px;
}

.box {
  background: #1f1f1f;
  padding: 25px;
  border-radius: 12px;
  display: inline-block;
  text-align: left;
  min-width: 420px;
  max-width: 90%;
}

h1 {
  text-align: center;
}

p {
  font-size: 18px;
  margin: 10px 0;
}

.value {
  font-weight: bold;
}

button {
  margin-top: 20px;
  padding: 12px 20px;
  font-size: 16px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

.status {
  margin-top: 15px;
  padding: 10px;
  background: #333;
  border-radius: 8px;
}

</style>

</head>


<body>

<h1>🏸 Badminton ML Data Collector</h1>


<div class="box">


<p>

Stroke :

<span id="stroke" class="value">
--
</span>

</p>


<p>

Timestamp :

<span id="time" class="value">
--
</span>

</p>


<hr>


<p>

Ax :

<span id="ax" class="value">
--
</span>

</p>


<p>

Ay :

<span id="ay" class="value">
--
</span>

</p>


<p>

Az :

<span id="az" class="value">
--
</span>

</p>


<p>

Gx :

<span id="gx" class="value">
--
</span>

</p>


<p>

Gy :

<span id="gy" class="value">
--
</span>

</p>


<p>

Gz :

<span id="gz" class="value">
--
</span>

</p>


<hr>


<p>

Swing Count :

<span id="count" class="value">
0
</span>

/ 100

</p>


<div class="status">

Status :

<span id="status">
Starting...
</span>

</div>


<button onclick="downloadCSV()">

Download CSV

</button>


</div>


<script>

async function updateData() {

  try {

    const res = await fetch('/data');

    const data = await res.json();


    document.getElementById("stroke").innerText =
      data.stroke;


    document.getElementById("time").innerText =
      data.timestamp;


    document.getElementById("ax").innerText =
      data.ax.toFixed(4);


    document.getElementById("ay").innerText =
      data.ay.toFixed(4);


    document.getElementById("az").innerText =
      data.az.toFixed(4);


    document.getElementById("gx").innerText =
      data.gx.toFixed(4);


    document.getElementById("gy").innerText =
      data.gy.toFixed(4);


    document.getElementById("gz").innerText =
      data.gz.toFixed(4);


    document.getElementById("count").innerText =
      data.count;


    document.getElementById("status").innerText =
      data.status;

  }

  catch(error) {

    console.log(error);

  }

}


setInterval(updateData, 100);


function downloadCSV() {

  window.location.href = "/download";

}

</script>


</body>

</html>

)rawliteral";


// =====================================================
// WEB ROOT
// =====================================================

void handleRoot() {

  server.send(
    200,
    "text/html",
    htmlPage
  );

}


// =====================================================
// WEB DATA
// =====================================================

void handleData() {

  String status;


  if (swingCount >= TOTAL_SWINGS) {

    status = "Collection complete";

  }

  else if (swing) {

    status = "Recording swing";

  }

  else {

    status = "Ready for next swing";

  }


  String json = "{";


  json += "\"stroke\":\"";
  json += STROKE_LABEL;
  json += "\",";


  json += "\"timestamp\":";
  json += String(live_timestamp);
  json += ",";


  json += "\"ax\":";
  json += String(live_ax, 4);
  json += ",";


  json += "\"ay\":";
  json += String(live_ay, 4);
  json += ",";


  json += "\"az\":";
  json += String(live_az, 4);
  json += ",";


  json += "\"gx\":";
  json += String(live_gx, 4);
  json += ",";


  json += "\"gy\":";
  json += String(live_gy, 4);
  json += ",";


  json += "\"gz\":";
  json += String(live_gz, 4);
  json += ",";


  json += "\"count\":";
  json += String(swingCount);
  json += ",";


  json += "\"status\":\"";
  json += status;
  json += "\"";


  json += "}";


  server.send(
    200,
    "application/json",
    json
  );

}


// =====================================================
// CSV DOWNLOAD
// =====================================================

void handleDownload() {

  server.sendHeader(
    "Content-Disposition",
    "attachment; filename=badminton_" +
    String(STROKE_LABEL) +
    ".csv"
  );


  server.send(
    200,
    "text/csv",
    csvData
  );

}


// =====================================================
// MPU6050 CALIBRATION
// =====================================================

void calibrateMPU() {

  long ax = 0;
  long ay = 0;
  long az = 0;

  long gx = 0;
  long gy = 0;
  long gz = 0;

  int n = 0;


  unsigned long t = millis();


  while (millis() - t < 3000) {

    int16_t a, b, c, d, e, f;


    mpu.getMotion6(
      &a,
      &b,
      &c,
      &d,
      &e,
      &f
    );


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

}


// =====================================================
// SAVE RAW SAMPLE
// =====================================================

void saveSample(
  unsigned long timestamp,
  float Ax,
  float Ay,
  float Az,
  float Gx,
  float Gy,
  float Gz
) {


  // ---------------------------------------------------
  // UPDATE DASHBOARD
  // ---------------------------------------------------

  live_timestamp = timestamp;

  live_ax = Ax;
  live_ay = Ay;
  live_az = Az;

  live_gx = Gx;
  live_gy = Gy;
  live_gz = Gz;


  // ---------------------------------------------------
  // SAVE RAW DATA TO CSV
  // ---------------------------------------------------

  csvData += String(timestamp);
  csvData += ",";

  csvData += String(Ax, 4);
  csvData += ",";

  csvData += String(Ay, 4);
  csvData += ",";

  csvData += String(Az, 4);
  csvData += ",";

  csvData += String(Gx, 4);
  csvData += ",";

  csvData += String(Gy, 4);
  csvData += ",";

  csvData += String(Gz, 4);
  csvData += ",";

  csvData += STROKE_LABEL;

  csvData += "\n";


  // ---------------------------------------------------
  // SERIAL OUTPUT
  // ---------------------------------------------------

  Serial.print(timestamp);
  Serial.print(",");

  Serial.print(Ax, 4);
  Serial.print(",");

  Serial.print(Ay, 4);
  Serial.print(",");

  Serial.print(Az, 4);
  Serial.print(",");

  Serial.print(Gx, 4);
  Serial.print(",");

  Serial.print(Gy, 4);
  Serial.print(",");

  Serial.print(Gz, 4);
  Serial.print(",");

  Serial.println(STROKE_LABEL);

}


// =====================================================
// SETUP
// =====================================================

void setup() {

  Serial.begin(115200);


  // ---------------------------------------------------
  // I2C
  // ---------------------------------------------------

  Wire.begin(
    SDA_PIN,
    SCL_PIN
  );


  // ---------------------------------------------------
  // MPU6050
  // ---------------------------------------------------

  mpu.initialize();

  mpu.setFullScaleGyroRange(
    MPU6050_GYRO_FS_2000
  );


  if (!mpu.testConnection()) {

    Serial.println(
      "MPU6050 FAILED"
    );

    while (1);

  }


  // ---------------------------------------------------
  // CALIBRATION
  // ---------------------------------------------------

  Serial.println();

  Serial.println(
    "================================="
  );

  Serial.println(
    "BADMINTON ML DATA COLLECTOR"
  );

  Serial.println(
    "================================="
  );


  Serial.print(
    "Stroke Label : "
  );

  Serial.println(
    STROKE_LABEL
  );


  Serial.println();

  Serial.println(
    "Keep racket STILL..."
  );

  Serial.println(
    "Calibrating for 3 seconds..."
  );


  calibrateMPU();


  Serial.println(
    "Calibration Done"
  );


  // ---------------------------------------------------
  // WIFI
  // ---------------------------------------------------

  WiFi.softAP(
    ssid,
    password
  );


  Serial.println();

  Serial.println(
    "WiFi Started"
  );


  Serial.print(
    "SSID : "
  );

  Serial.println(
    ssid
  );


  Serial.print(
    "IP : "
  );

  Serial.println(
    WiFi.softAPIP()
  );


  // ---------------------------------------------------
  // WEB SERVER
  // ---------------------------------------------------

  server.on(
    "/",
    handleRoot
  );


  server.on(
    "/data",
    handleData
  );


  server.on(
    "/download",
    handleDownload
  );


  server.begin();


  // ---------------------------------------------------
  // START MESSAGE
  // ---------------------------------------------------

  Serial.println();

  Serial.println(
    "================================="
  );

  Serial.println(
    "READY FOR DATA COLLECTION"
  );

  Serial.println(
    "================================="
  );


  Serial.print(
    "Stroke : "
  );

  Serial.println(
    STROKE_LABEL
  );


  Serial.println(
    "Perform your swings..."
  );


  Serial.println(
    "Collecting 100 swings."
  );


  Serial.println();


  Serial.println(
    "timestamp,ax,ay,az,gx,gy,gz,stroke"
  );

}


// =====================================================
// LOOP
// =====================================================

void loop() {


  // ---------------------------------------------------
  // HANDLE WEB SERVER
  // ---------------------------------------------------

  server.handleClient();


  // ---------------------------------------------------
  // STOP AFTER 100 SWINGS
  // ---------------------------------------------------

  if (swingCount >= TOTAL_SWINGS) {

    swing = false;


    delay(100);

    return;

  }


  // ---------------------------------------------------
  // READ MPU6050
  // ---------------------------------------------------

  int16_t ax, ay, az;
  int16_t gx, gy, gz;


  mpu.getMotion6(
    &ax,
    &ay,
    &az,
    &gx,
    &gy,
    &gz
  );


  // ---------------------------------------------------
  // ACCELEROMETER
  // ---------------------------------------------------

  float Ax =
    (ax - axO) / 16384.0;


  float Ay =
    (ay - ayO) / 16384.0;


  float Az =
    (az - azO) / 16384.0;


  // ---------------------------------------------------
  // GYROSCOPE
  // ---------------------------------------------------

  float Gx =
    (gx - gxO) / 16.4;


  float Gy =
    (gy - gyO) / 16.4;


  float Gz =
    (gz - gzO) / 16.4;


  // ---------------------------------------------------
  // UPDATE LIVE DASHBOARD
  // ---------------------------------------------------

  live_timestamp = millis();

  live_ax = Ax;
  live_ay = Ay;
  live_az = Az;

  live_gx = Gx;
  live_gy = Gy;
  live_gz = Gz;


  // ===================================================
  // GRAVITY REMOVAL
  // ===================================================

  gravity =
    alpha * gravity +
    (1 - alpha) * Az;


  float linAccX =
    Ax * 9.81;


  float linAccY =
    Ay * 9.81;


  float linAccZ =
    (Az - gravity) * 9.81;


  float totalAcc =
    sqrt(
      linAccX * linAccX +
      linAccY * linAccY +
      linAccZ * linAccZ
    );


  // ===================================================
  // ANGULAR VELOCITY
  // ===================================================

  float angularVelocity =
    sqrt(
      Gx * Gx +
      Gy * Gy +
      Gz * Gz
    );


  unsigned long now =
    millis();


  // ===================================================
  // START SWING
  // ===================================================

  if (
    !swing &&
    totalAcc > START_THRESHOLD &&
    angularVelocity > 120 &&
    (now - lastSwingEnd > COOLDOWN)
  ) {


    swing = true;

    swingStart = now;


    Serial.println();

    Serial.print(
      "SWING "
    );

    Serial.print(
      swingCount + 1
    );

    Serial.println(
      " START"
    );


    // -------------------------------------------------
    // SAVE FIRST SAMPLE
    // -------------------------------------------------

    saveSample(
      now,
      Ax,
      Ay,
      Az,
      Gx,
      Gy,
      Gz
    );

  }


  // ===================================================
  // DURING SWING
  // ===================================================

  if (swing) {


    // -------------------------------------------------
    // SAVE EVERY RAW IMU SAMPLE
    // -------------------------------------------------

    saveSample(
      now,
      Ax,
      Ay,
      Az,
      Gx,
      Gy,
      Gz
    );


    // -------------------------------------------------
    // SWING DURATION
    // -------------------------------------------------

    float duration =
      (now - swingStart) / 1000.0;


    // -------------------------------------------------
    // SAFETY TIMEOUT
    // -------------------------------------------------

    if (duration > 1.2) {


      swing = false;

      lastSwingEnd = now;

      swingCount++;


      Serial.print(
        "Swing "
      );

      Serial.print(
        swingCount
      );

      Serial.println(
        " completed by timeout"
      );


      delay(100);

      return;

    }


    // -------------------------------------------------
    // NORMAL SWING END
    // -------------------------------------------------

    if (
      totalAcc < END_THRESHOLD &&
      angularVelocity < 60 &&
      duration > 0.25
    ) {


      swing = false;

      lastSwingEnd = now;

      swingCount++;


      Serial.print(
        "Swing "
      );

      Serial.print(
        swingCount
      );

      Serial.println(
        " completed"
      );


      Serial.println();


      delay(100);

    }

  }


  // ---------------------------------------------------
  // SAMPLING DELAY
  // ---------------------------------------------------

  delay(10);

}