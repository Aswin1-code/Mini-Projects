#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <MPU6050.h>
#include <math.h>

// =====================================================
// HARDWARE
// =====================================================

MPU6050 mpu;

#define SDA_PIN 26
#define SCL_PIN 25
#define LED_PIN 2


// =====================================================
// WIFI ACCESS POINT
// =====================================================

const char* AP_SSID = "Badminton AI";
const char* AP_PASSWORD = "hello123";

WebServer server(80);


// =====================================================
// MPU6050 SETTINGS
// =====================================================

const float ACCEL_SCALE = 4096.0;   // ±8g
const float GYRO_SCALE  = 16.4;     // ±2000 deg/s

const float GRAVITY = 9.81;


// =====================================================
// SWING DETECTION PARAMETERS
// =====================================================

const float START_THRESHOLD = 17.0;
const float START_GYRO_THRESHOLD = 120.0;

const float END_THRESHOLD = 8.5;

const unsigned long MIN_SWING_DURATION = 200;
const unsigned long MAX_SWING_DURATION = 1500;

const unsigned long END_CONFIRM_TIME = 100;

// Short protection against immediate return movement
const unsigned long COOLDOWN = 200;


// =====================================================
// GRAVITY FILTER
// =====================================================

const float GRAVITY_ALPHA = 0.95;

float gravityX = 0;
float gravityY = 0;
float gravityZ = 0;


// =====================================================
// GYRO CALIBRATION
// =====================================================

float gyroBiasX = 0;
float gyroBiasY = 0;
float gyroBiasZ = 0;

const int CALIBRATION_SAMPLES = 800;


// =====================================================
// LIVE SENSOR VALUES
// =====================================================

float ax = 0;
float ay = 0;
float az = 0;

float gx = 0;
float gy = 0;
float gz = 0;

float linearAccX = 0;
float linearAccY = 0;
float linearAccZ = 0;

float totalAcceleration = 0;

float angularVelocity = 0;

float instantSpeed = 0;


// =====================================================
// SWING DATA
// =====================================================

float peakSpeed = 0;
float peakAcceleration = 0;

unsigned long swingStartTime = 0;
unsigned long endConditionStartTime = 0;
unsigned long cooldownStartTime = 0;

unsigned long lastSwingDuration = 0;

unsigned long swingCount = 0;


// =====================================================
// STATE MACHINE
// =====================================================

enum SwingState
{
    IDLE,
    ACTIVE,
    COOLDOWN_STATE
};

SwingState swingState = IDLE;


// =====================================================
// CSV STORAGE
// =====================================================

// Stores completed swing records in RAM.
//
// timestamp, ax, ay, az, gx, gy, gz,
// speed, impact, duration

struct SwingRecord
{
    unsigned long timestamp;

    float ax;
    float ay;
    float az;

    float gx;
    float gy;
    float gz;

    float speed;
    float impact;

    float duration;
};

const int MAX_RECORDS = 500;

SwingRecord records[MAX_RECORDS];

int recordCount = 0;


// =====================================================
// FUNCTION DECLARATIONS
// =====================================================

void calibrateGyro();
void readSensor();

bool startCondition();
bool endCondition();

void processSwing();
void completeSwing(float speed, float impact, unsigned long duration);

String stateToString();

void handleRoot();
void handleData();
void handleDownload();


// =====================================================
// SETUP
// =====================================================

void setup()
{
    Serial.begin(115200);

    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);


    // =================================================
    // I2C
    // =================================================

    Wire.begin(SDA_PIN, SCL_PIN);


    // =================================================
    // MPU6050
    // =================================================

    Serial.println();
    Serial.println("====================================");
    Serial.println(" BADMINTON AI - ESP32");
    Serial.println("====================================");

    Serial.println("Initializing MPU6050...");

    mpu.initialize();

    if (!mpu.testConnection())
    {
        Serial.println("MPU6050 connection FAILED!");

        while (1)
        {
            digitalWrite(LED_PIN, !digitalRead(LED_PIN));
            delay(300);
        }
    }

    Serial.println("MPU6050 connected.");


    // =================================================
    // SENSOR RANGE
    // =================================================

    // ±8g
    mpu.setFullScaleAccelRange(MPU6050_ACCEL_FS_8);

    // ±2000 deg/s
    mpu.setFullScaleGyroRange(MPU6050_GYRO_FS_2000);


    // =================================================
    // GYRO CALIBRATION
    // =================================================

    Serial.println();
    Serial.println("Keep racket COMPLETELY STILL.");
    Serial.println("Calibrating gyro...");

    calibrateGyro();

    Serial.println("Gyro calibration complete.");

    Serial.print("Gyro bias X = ");
    Serial.println(gyroBiasX);

    Serial.print("Gyro bias Y = ");
    Serial.println(gyroBiasY);

    Serial.print("Gyro bias Z = ");
    Serial.println(gyroBiasZ);


    // =================================================
    // INITIAL GRAVITY ESTIMATE
    // =================================================

    int16_t rawAx, rawAy, rawAz;
    int16_t rawGx, rawGy, rawGz;

    mpu.getMotion6(
        &rawAx,
        &rawAy,
        &rawAz,
        &rawGx,
        &rawGy,
        &rawGz
    );

    gravityX = (float)rawAx / ACCEL_SCALE;
    gravityY = (float)rawAy / ACCEL_SCALE;
    gravityZ = (float)rawAz / ACCEL_SCALE;


    // =================================================
    // WIFI ACCESS POINT
    // =================================================

    WiFi.mode(WIFI_AP);

    WiFi.softAP(AP_SSID, AP_PASSWORD);

    Serial.println();
    Serial.println("WiFi Access Point started.");

    Serial.print("SSID: ");
    Serial.println(AP_SSID);

    Serial.print("IP address: ");
    Serial.println(WiFi.softAPIP());


    // =================================================
    // WEB SERVER ROUTES
    // =================================================

    server.on("/", handleRoot);

    server.on("/data", handleData);

    server.on("/download", handleDownload);


    server.begin();

    Serial.println("Web server started.");

    Serial.println();
    Serial.println("====================================");
    Serial.println(" SYSTEM READY");
    Serial.println("====================================");


    digitalWrite(LED_PIN, HIGH);

    delay(500);

    digitalWrite(LED_PIN, LOW);
}


// =====================================================
// GYRO CALIBRATION
// =====================================================

void calibrateGyro()
{
    long sumX = 0;
    long sumY = 0;
    long sumZ = 0;

    for (int i = 0; i < CALIBRATION_SAMPLES; i++)
    {
        int16_t rawAx;
        int16_t rawAy;
        int16_t rawAz;

        int16_t rawGx;
        int16_t rawGy;
        int16_t rawGz;

        mpu.getMotion6(
            &rawAx,
            &rawAy,
            &rawAz,
            &rawGx,
            &rawGy,
            &rawGz
        );

        sumX += rawGx;
        sumY += rawGy;
        sumZ += rawGz;


        // LED blinking during calibration
        if ((i % 50) == 0)
        {
            digitalWrite(
                LED_PIN,
                !digitalRead(LED_PIN)
            );
        }

        delay(2);
    }


    gyroBiasX =
        ((float)sumX / CALIBRATION_SAMPLES) / GYRO_SCALE;

    gyroBiasY =
        ((float)sumY / CALIBRATION_SAMPLES) / GYRO_SCALE;

    gyroBiasZ =
        ((float)sumZ / CALIBRATION_SAMPLES) / GYRO_SCALE;


    digitalWrite(LED_PIN, LOW);
}


// =====================================================
// READ SENSOR
// =====================================================

void readSensor()
{
    int16_t rawAx;
    int16_t rawAy;
    int16_t rawAz;

    int16_t rawGx;
    int16_t rawGy;
    int16_t rawGz;


    mpu.getMotion6(
        &rawAx,
        &rawAy,
        &rawAz,
        &rawGx,
        &rawGy,
        &rawGz
    );


    // =================================================
    // ACCELERATION → g
    // =================================================

    ax = (float)rawAx / ACCEL_SCALE;
    ay = (float)rawAy / ACCEL_SCALE;
    az = (float)rawAz / ACCEL_SCALE;


    // =================================================
    // GYRO → deg/s
    // =================================================

    gx =
        ((float)rawGx / GYRO_SCALE)
        - gyroBiasX;

    gy =
        ((float)rawGy / GYRO_SCALE)
        - gyroBiasY;

    gz =
        ((float)rawGz / GYRO_SCALE)
        - gyroBiasZ;


    // =================================================
    // VECTOR GRAVITY FILTER
    // =================================================

    gravityX =
        GRAVITY_ALPHA * gravityX
        + (1.0 - GRAVITY_ALPHA) * ax;

    gravityY =
        GRAVITY_ALPHA * gravityY
        + (1.0 - GRAVITY_ALPHA) * ay;

    gravityZ =
        GRAVITY_ALPHA * gravityZ
        + (1.0 - GRAVITY_ALPHA) * az;


    // =================================================
    // REMOVE GRAVITY
    // =================================================

    linearAccX =
        (ax - gravityX) * GRAVITY;

    linearAccY =
        (ay - gravityY) * GRAVITY;

    linearAccZ =
        (az - gravityZ) * GRAVITY;


    // =================================================
    // TOTAL LINEAR ACCELERATION
    // =================================================

    totalAcceleration =
        sqrt(
            linearAccX * linearAccX +
            linearAccY * linearAccY +
            linearAccZ * linearAccZ
        );


    // =================================================
    // ANGULAR VELOCITY
    // =================================================

    angularVelocity =
        sqrt(
            gx * gx +
            gy * gy +
            gz * gz
        );


    // =================================================
    // PROJECT SPEED SCORE
    // =================================================
    //
    // This is NOT physical racket velocity.
    //
    // It is a gyro-derived project score.
    //
    // speed = angular velocity × 0.03
    //
    // Example:
    // 100 deg/s → 3.0
    // 300 deg/s → 9.0
    // 500 deg/s → 15.0
    //
    // =================================================

    instantSpeed =
        angularVelocity * 0.03;
}


// =====================================================
// START CONDITION
// =====================================================

bool startCondition()
{
    return (
        totalAcceleration > START_THRESHOLD ||
        angularVelocity > START_GYRO_THRESHOLD
    );
}


// =====================================================
// END CONDITION
// =====================================================

bool endCondition()
{
    return (
        totalAcceleration < END_THRESHOLD
    );
}


// =====================================================
// PROCESS SWING
// =====================================================

void processSwing()
{
    unsigned long now = millis();


    // =================================================
    // IDLE
    // =================================================

    if (swingState == IDLE)
    {
        if (startCondition())
        {
            swingState = ACTIVE;

            swingStartTime = now;

            endConditionStartTime = 0;

            peakSpeed = instantSpeed;

            peakAcceleration = totalAcceleration;


            Serial.println();
            Serial.println(">>> SWING STARTED");
        }
    }


    // =================================================
    // ACTIVE
    // =================================================

    else if (swingState == ACTIVE)
    {
        // ---------------------------------------------
        // Track peak speed
        // ---------------------------------------------

        if (instantSpeed > peakSpeed)
        {
            peakSpeed = instantSpeed;
        }


        // ---------------------------------------------
        // Track peak acceleration
        // ---------------------------------------------

        if (totalAcceleration > peakAcceleration)
        {
            peakAcceleration = totalAcceleration;
        }


        // ---------------------------------------------
        // Check end condition
        // ---------------------------------------------

        if (endCondition())
        {
            if (endConditionStartTime == 0)
            {
                endConditionStartTime = now;
            }


            // Acceleration must remain low continuously
            if (
                now - endConditionStartTime
                >= END_CONFIRM_TIME
            )
            {
                unsigned long duration =
                    now - swingStartTime;


                if (duration >= MIN_SWING_DURATION)
                {
                    completeSwing(
                        peakSpeed,
                        peakAcceleration,
                        duration
                    );
                }


                swingState = COOLDOWN_STATE;

                cooldownStartTime = now;

                endConditionStartTime = 0;


                Serial.println(">>> SWING ENDED");
                Serial.print("Peak speed: ");
                Serial.println(peakSpeed);

                Serial.print("Peak acceleration: ");
                Serial.println(peakAcceleration);

                Serial.print("Duration: ");
                Serial.println(duration);
            }
        }
        else
        {
            // Movement came back
            endConditionStartTime = 0;
        }


        // ---------------------------------------------
        // Maximum safety duration
        // ---------------------------------------------

        if (
            now - swingStartTime
            >= MAX_SWING_DURATION
        )
        {
            unsigned long duration =
                now - swingStartTime;


            completeSwing(
                peakSpeed,
                peakAcceleration,
                duration
            );


            swingState = COOLDOWN_STATE;

            cooldownStartTime = now;

            endConditionStartTime = 0;


            Serial.println(">>> MAX DURATION FORCED END");
        }
    }


    // =================================================
    // COOLDOWN
    // =================================================

    else if (swingState == COOLDOWN_STATE)
    {
        /*
         * IMPORTANT:
         *
         * We do NOT wait for the racket to become
         * perfectly stationary here.
         *
         * Only a short fixed lockout is used.
         */

        if (
            now - cooldownStartTime
            >= COOLDOWN
        )
        {
            swingState = IDLE;

            Serial.println(">>> READY FOR NEXT SWING");
        }
    }
}


// =====================================================
// COMPLETE SWING
// =====================================================

void completeSwing(
    float speed,
    float impact,
    unsigned long duration
)
{
    swingCount++;

    lastSwingDuration = duration;


    // =================================================
    // STORE RECORD
    // =================================================

    if (recordCount < MAX_RECORDS)
    {
        records[recordCount].timestamp =
            millis();

        records[recordCount].ax = ax;
        records[recordCount].ay = ay;
        records[recordCount].az = az;

        records[recordCount].gx = gx;
        records[recordCount].gy = gy;
        records[recordCount].gz = gz;

        records[recordCount].speed = speed;

        records[recordCount].impact = impact;

        records[recordCount].duration =
            duration / 1000.0;

        recordCount++;
    }


    // =================================================
    // SERIAL OUTPUT
    // =================================================

    Serial.println();
    Serial.println("------------------------------------");

    Serial.print("SWING #");
    Serial.println(swingCount);

    Serial.print("Speed: ");
    Serial.println(speed);

    Serial.print("Impact: ");
    Serial.println(impact);

    Serial.print("Duration: ");
    Serial.print(duration / 1000.0);
    Serial.println(" s");

    Serial.println("------------------------------------");
}


// =====================================================
// STATE STRING
// =====================================================

String stateToString()
{
    switch (swingState)
    {
        case IDLE:
            return "IDLE";

        case ACTIVE:
            return "ACTIVE";

        case COOLDOWN_STATE:
            return "COOLDOWN";
    }

    return "UNKNOWN";
}


// =====================================================
// WEB DASHBOARD
// =====================================================

void handleRoot()
{
    String html = R"rawliteral(

<!DOCTYPE html>

<html>

<head>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<title>Badminton AI</title>

<style>

body {
    font-family: Arial, sans-serif;
    background: #f2f2f2;
    margin: 0;
    padding: 20px;
}

.container {
    max-width: 900px;
    margin: auto;
}

h1 {
    text-align: center;
}

.card {
    background: white;
    padding: 20px;
    margin: 15px 0;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.value {
    font-size: 22px;
    font-weight: bold;
}

button {
    padding: 12px 20px;
    font-size: 16px;
    border: none;
    border-radius: 8px;
    cursor: pointer;
}

</style>

</head>


<body>

<div class="container">

<h1>🏸 Badminton AI</h1>


<div class="card">

<h2>Live Sensor</h2>

<p>
Acceleration:
<span id="acceleration" class="value">0</span>
m/s²
</p>

<p>
Angular Velocity:
<span id="gyro" class="value">0</span>
deg/s
</p>

<p>
Instant Speed:
<span id="speed" class="value">0</span>
</p>

</div>


<div class="card">

<h2>Swing Detection</h2>

<p>
State:
<span id="state" class="value">IDLE</span>
</p>

<p>
Swing Count:
<span id="count" class="value">0</span>
</p>

<p>
Peak Speed:
<span id="peakSpeed" class="value">0</span>
</p>

<p>
Peak Impact:
<span id="impact" class="value">0</span>
</p>

<p>
Duration:
<span id="duration" class="value">0</span>
s
</p>

</div>


<div class="card">

<h2>Current Peaks</h2>

<p>
Current Peak Acceleration:
<span id="currentPeakAcc">0</span>
m/s²
</p>

<p>
Current Peak Speed:
<span id="currentPeakSpeed">0</span>
</p>

</div>


<div class="card">

<a href="/download">

<button>
Download CSV
</button>

</a>

</div>

</div>


<script>

async function updateData()
{
    try
    {
        const response =
            await fetch(
                '/data?ts=' + Date.now(),
                {
                    cache: 'no-store'
                }
            );

        const d =
            await response.json();


        document.getElementById(
            'acceleration'
        ).innerText =
            Number(d.acceleration).toFixed(2);


        document.getElementById(
            'gyro'
        ).innerText =
            Number(d.gyro).toFixed(1);


        document.getElementById(
            'speed'
        ).innerText =
            Number(d.speed).toFixed(2);


        document.getElementById(
            'state'
        ).innerText =
            d.state;


        document.getElementById(
            'count'
        ).innerText =
            d.count;


        document.getElementById(
            'peakSpeed'
        ).innerText =
            Number(d.peakSpeed).toFixed(2);


        document.getElementById(
            'impact'
        ).innerText =
            Number(d.impact).toFixed(2);


        document.getElementById(
            'duration'
        ).innerText =
            Number(d.duration).toFixed(2);


        document.getElementById(
            'currentPeakAcc'
        ).innerText =
            Number(d.currentPeakAcc).toFixed(2);


        document.getElementById(
            'currentPeakSpeed'
        ).innerText =
            Number(d.currentPeakSpeed).toFixed(2);
    }
    catch(error)
    {
        console.log(error);
    }
}


// Update immediately
updateData();


// Update every 100 ms
setInterval(
    updateData,
    100
);

</script>


</body>

</html>

)rawliteral";


    server.sendHeader(
        "Cache-Control",
        "no-cache, no-store, must-revalidate"
    );

    server.send(
        200,
        "text/html",
        html
    );
}


// =====================================================
// JSON DATA
// =====================================================

void handleData()
{
    String json = "{";


    json += "\"acceleration\":";
    json += String(totalAcceleration, 2);

    json += ",\"gyro\":";
    json += String(angularVelocity, 2);

    json += ",\"speed\":";
    json += String(instantSpeed, 2);

    json += ",\"state\":\"";
    json += stateToString();
    json += "\"";

    json += ",\"count\":";
    json += String(swingCount);

    json += ",\"peakSpeed\":";
    json += String(peakSpeed, 2);

    json += ",\"impact\":";
    json += String(peakAcceleration, 2);

    json += ",\"duration\":";
    json += String(lastSwingDuration / 1000.0, 2);

    json += ",\"currentPeakAcc\":";
    json += String(peakAcceleration, 2);

    json += ",\"currentPeakSpeed\":";
    json += String(peakSpeed, 2);

    json += "}";


    server.sendHeader(
        "Cache-Control",
        "no-cache, no-store, must-revalidate"
    );

    server.send(
        200,
        "application/json",
        json
    );
}


// =====================================================
// CSV DOWNLOAD
// =====================================================

void handleDownload()
{
    String csv = "";

    csv +=
        "timestamp,"
        "ax,ay,az,"
        "gx,gy,gz,"
        "speed,"
        "impact,"
        "duration\n";


    for (int i = 0; i < recordCount; i++)
    {
        csv += String(
            records[i].timestamp
        );

        csv += ",";

        csv += String(
            records[i].ax,
            2
        );

        csv += ",";

        csv += String(
            records[i].ay,
            2
        );

        csv += ",";

        csv += String(
            records[i].az,
            2
        );

        csv += ",";

        csv += String(
            records[i].gx,
            2
        );

        csv += ",";

        csv += String(
            records[i].gy,
            2
        );

        csv += ",";

        csv += String(
            records[i].gz,
            2
        );

        csv += ",";

        csv += String(
            records[i].speed,
            2
        );

        csv += ",";

        csv += String(
            records[i].impact,
            2
        );

        csv += ",";

        csv += String(
            records[i].duration,
            2
        );

        csv += "\n";
    }


    server.sendHeader(
        "Content-Disposition",
        "attachment; filename=badminton_data.csv"
    );

    server.sendHeader(
        "Cache-Control",
        "no-cache"
    );

    server.send(
        200,
        "text/csv",
        csv
    );
}


// =====================================================
// MAIN LOOP
// =====================================================

void loop()
{
    // Handle web requests
    server.handleClient();


    // Read MPU6050
    readSensor();


    // Process swing detector
    processSwing();


    // Small sampling delay
    delay(2);
}