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

// MPU6050 INT connected to ESP32 GPIO 4
#define INT_PIN 4


// =====================================================
// WIFI ACCESS POINT
// =====================================================

const char* AP_SSID = "Badminton AI";
const char* AP_PASSWORD = "hello123";

WebServer server(80);


// =====================================================
// MPU6050 SETTINGS
// =====================================================

const float ACCEL_SCALE = 4096.0;   // ±8g (baseline)
const float GYRO_SCALE  = 16.4;     // ±2000 deg/s

const float GRAVITY = 9.81;


// =====================================================
// MPU6050 I2C AND SAMPLE RATE SETTINGS
// Extracted from INT code
// =====================================================

const uint32_t I2C_CLOCK_HZ = 400000;

const uint8_t MPU_SAMPLE_RATE_DIVIDER = 0;
const uint8_t MPU_DLPF_CONFIG = 1;


// =====================================================
// MPU6050 REGISTER DEFINITIONS
// =====================================================

const uint8_t MPU6050_ADDRESS = 0x68;

const uint8_t REG_SMPLRT_DIV = 0x19;
const uint8_t REG_CONFIG = 0x1A;
const uint8_t REG_INT_ENABLE = 0x38;
const uint8_t REG_INT_STATUS = 0x3A;
const uint8_t REG_MOT_THR = 0x1F;
const uint8_t REG_MOT_DUR = 0x20;

const uint8_t MPU_MOTION_INT_BIT = 0x40;


// =====================================================
// MPU6050 MOTION INTERRUPT SETTINGS
// =====================================================

uint8_t motThr = 30;
uint8_t motDur = 1;

// ISR only sets this flag.
// I2C operations are performed in loop().
volatile bool mpuIntPending = false;

// At most one accepted INT per active swing.
bool swingIntFlag = false;

// Most recent MPU interrupt status.
uint8_t lastMpuIntStatus = 0;


// =====================================================
// SWING DETECTION PARAMETERS
// BASELINE — UNCHANGED
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
// BASELINE — UNCHANGED
// =====================================================

const float GRAVITY_ALPHA = 0.95;

float gravityX = 0;
float gravityY = 0;
float gravityZ = 0;


// =====================================================
// GYRO CALIBRATION
// BASELINE — UNCHANGED
// =====================================================

float gyroBiasX = 0;
float gyroBiasY = 0;
float gyroBiasZ = 0;

const int CALIBRATION_SAMPLES = 800;


// =====================================================
// LIVE SENSOR VALUES
// BASELINE — UNCHANGED
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
// BASELINE — UNCHANGED
// =====================================================

float peakSpeed = 0;
float peakAcceleration = 0;

unsigned long swingStartTime = 0;
unsigned long endConditionStartTime = 0;
unsigned long cooldownStartTime = 0;

unsigned long lastSwingDuration = 0;

unsigned long swingCount = 0;


// =====================================================
// SESSION-RELATIVE TIMING
// Extracted from INT code
// =====================================================

// Session begins at the first detected swing.
bool sessionStarted = false;
unsigned long sessionStartMillis = 0;

unsigned long getSessionMillis()
{
    if (!sessionStarted)
    {
        return 0;
    }

    return millis() - sessionStartMillis;
}

unsigned long toSessionMillis(unsigned long rawTime)
{
    if (!sessionStarted)
    {
        return 0;
    }

    return rawTime - sessionStartMillis;
}


// =====================================================
// STATE MACHINE
// BASELINE — UNCHANGED
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

// Exact requested CSV fields:
//
// swing_count,timestamp,start_time,end_time,duration,
// ax,ay,az,gx,gy,gz,speed,impact,int_flag

struct SwingRecord
{
    unsigned long swing_count;

    unsigned long timestamp;
    unsigned long start_time;
    unsigned long end_time;
    unsigned long duration;

    float ax;
    float ay;
    float az;

    float gx;
    float gy;
    float gz;

    float speed;
    float impact;

    int int_flag;
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
void completeSwing(
    float speed,
    float impact,
    unsigned long duration
);

String stateToString();

void handleRoot();
void handleData();
void handleDownload();
void handleSettings();

// MPU6050 INT functions
void IRAM_ATTR onMpuInterrupt();

bool writeMpuRegister(uint8_t reg, uint8_t value);
uint8_t readMpuRegister(uint8_t reg);

void configureMpuSampleRate();
void configureMpuMotionInterrupt();

void clearMpuInterruptStatus();
void discardPendingInterrupt();
void serviceMpuInterrupt();


// =====================================================
// SETUP
// =====================================================

void setup()
{
    Serial.begin(115200);

    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);

    // =================================================
    // MPU INT PIN
    // =================================================

    pinMode(INT_PIN, INPUT);


    // =================================================
    // I2C
    // =================================================

    Wire.begin(SDA_PIN, SCL_PIN);

    // Extracted from INT code
    Wire.setClock(I2C_CLOCK_HZ);


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
    // BASELINE — UNCHANGED
    // =================================================

    // ±8g
    mpu.setFullScaleAccelRange(MPU6050_ACCEL_FS_8);

    // ±2000 deg/s
    mpu.setFullScaleGyroRange(MPU6050_GYRO_FS_2000);


    // =================================================
    // SAMPLE RATE CONFIGURATION
    // Extracted from INT code
    // =================================================

    configureMpuSampleRate();


    // =================================================
    // GYRO CALIBRATION
    // BASELINE — UNCHANGED
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
    // BASELINE — UNCHANGED
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
    // MPU MOTION INTERRUPT CONFIGURATION
    // =================================================

    configureMpuMotionInterrupt();

    attachInterrupt(
        digitalPinToInterrupt(INT_PIN),
        onMpuInterrupt,
        RISING
    );

    Serial.print("MPU6050 INT connected to ESP32 GPIO ");
    Serial.println(INT_PIN);

    Serial.print("Initial MOT_THR = ");
    Serial.println(motThr);

    Serial.print("Initial MOT_DUR = ");
    Serial.println(motDur);


    // =================================================
    // WIFI ACCESS POINT
    // BASELINE — UNCHANGED
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

    // Added for INT threshold/duration settings
    server.on("/settings", handleSettings);

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
// MPU6050 REGISTER WRITE
// Extracted from INT code
// =====================================================

bool writeMpuRegister(uint8_t reg, uint8_t value)
{
    Wire.beginTransmission(MPU6050_ADDRESS);

    Wire.write(reg);
    Wire.write(value);

    uint8_t result = Wire.endTransmission();

    return (result == 0);
}


// =====================================================
// MPU6050 REGISTER READ
// Extracted from INT code
// =====================================================

uint8_t readMpuRegister(uint8_t reg)
{
    Wire.beginTransmission(MPU6050_ADDRESS);

    Wire.write(reg);

    uint8_t result = Wire.endTransmission(false);

    if (result != 0)
    {
        return 0;
    }

    Wire.requestFrom(
        MPU6050_ADDRESS,
        (uint8_t)1,
        (uint8_t)true
    );

    if (Wire.available())
    {
        return Wire.read();
    }

    return 0;
}


// =====================================================
// MPU6050 SAMPLE RATE CONFIGURATION
// Extracted from INT code
// =====================================================

void configureMpuSampleRate()
{
    // CONFIG DLPF_CFG = 1.
    // With DLPF enabled, sample-rate base is 1 kHz.
    bool configOk = writeMpuRegister(
        REG_CONFIG,
        MPU_DLPF_CONFIG
    );

    // SMPLRT_DIV = 0 -> 1 kHz output rate.
    bool dividerOk = writeMpuRegister(
        REG_SMPLRT_DIV,
        MPU_SAMPLE_RATE_DIVIDER
    );

    Serial.println();
    Serial.println("MPU6050 sample-rate configuration:");

    Serial.print("I2C clock: ");
    Serial.print(I2C_CLOCK_HZ);
    Serial.println(" Hz");

    Serial.print("DLPF config write: ");
    Serial.println(configOk ? "OK" : "FAILED");

    Serial.print("Sample divider write: ");
    Serial.println(dividerOk ? "OK" : "FAILED");

    Serial.println("Requested MPU output rate: 1000 Hz");
}


// =====================================================
// MPU6050 MOTION INTERRUPT CONFIGURATION
// Extracted from INT code
// =====================================================

void configureMpuMotionInterrupt()
{
    // Disable MPU interrupts while configuring.
    writeMpuRegister(REG_INT_ENABLE, 0x00);

    // Clear any pending MPU interrupt status.
    clearMpuInterruptStatus();

    // Motion threshold register.
    writeMpuRegister(REG_MOT_THR, motThr);

    // Motion duration register.
    writeMpuRegister(REG_MOT_DUR, motDur);

    // Enable motion interrupt only (bit 6).
    writeMpuRegister(
        REG_INT_ENABLE,
        MPU_MOTION_INT_BIT
    );

    // Clear any status produced during setup.
    clearMpuInterruptStatus();

    noInterrupts();
    mpuIntPending = false;
    interrupts();
}


// =====================================================
// CLEAR MPU INTERRUPT STATUS
// =====================================================

void clearMpuInterruptStatus()
{
    // Reading INT_STATUS clears the latched status bits.
    lastMpuIntStatus = readMpuRegister(REG_INT_STATUS);
}


// =====================================================
// DISCARD PENDING INTERRUPTS
// =====================================================

void discardPendingInterrupt()
{
    noInterrupts();
    mpuIntPending = false;
    interrupts();

    clearMpuInterruptStatus();
}


// =====================================================
// MPU INTERRUPT SERVICE ROUTINE
// =====================================================

void IRAM_ATTR onMpuInterrupt()
{
    // Do not perform I2C operations inside this ISR.
    mpuIntPending = true;
}


// =====================================================
// SERVICE MPU INTERRUPT IN MAIN LOOP
// =====================================================

void serviceMpuInterrupt()
{
    bool pending = false;

    noInterrupts();

    if (mpuIntPending)
    {
        pending = true;
        mpuIntPending = false;
    }

    interrupts();

    if (!pending)
    {
        return;
    }

    // Read actual MPU6050 status in normal loop context.
    lastMpuIntStatus = readMpuRegister(REG_INT_STATUS);

    // Accept at most one motion INT per ACTIVE swing.
    if (
        swingState == ACTIVE &&
        !swingIntFlag &&
        (lastMpuIntStatus & MPU_MOTION_INT_BIT)
    )
    {
        swingIntFlag = true;

        Serial.println(">>> MPU6050 MOTION INT ACCEPTED");
    }
}


// =====================================================
// GYRO CALIBRATION
// BASELINE — UNCHANGED
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
// BASELINE — UNCHANGED
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
    // BASELINE — UNCHANGED
    // =================================================

    instantSpeed =
        angularVelocity * 0.03;
}


// =====================================================
// START CONDITION
// BASELINE — UNCHANGED
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
// BASELINE — UNCHANGED
// =====================================================

bool endCondition()
{
    return (
        totalAcceleration < END_THRESHOLD
    );
}


// =====================================================
// PROCESS SWING
// BASELINE FSM PRESERVED
// INT FLAG ADDED
// =====================================================

void processSwing()
{
    unsigned long now = millis();


    // =================================================
    // IDLE
    // =================================================

    if (swingState == IDLE)
    {
        // Ignore and clear MPU interrupt events outside
        // an active swing so stale events are not reused.
        discardPendingInterrupt();

        if (startCondition())
        {
            // Start session timer at first detected swing.
            if (!sessionStarted)
            {
                sessionStartMillis = now;
                sessionStarted = true;
            }

            swingState = ACTIVE;

            swingStartTime = now;

            endConditionStartTime = 0;

            peakSpeed = instantSpeed;

            peakAcceleration = totalAcceleration;

            // Reset INT flag for this swing.
            swingIntFlag = false;

            // Clear any old event immediately before
            // beginning a new active swing.
            discardPendingInterrupt();

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
        // BASELINE — UNCHANGED
        // ---------------------------------------------

        if (instantSpeed > peakSpeed)
        {
            peakSpeed = instantSpeed;
        }


        // ---------------------------------------------
        // Track peak acceleration
        // BASELINE — UNCHANGED
        // ---------------------------------------------

        if (totalAcceleration > peakAcceleration)
        {
            peakAcceleration = totalAcceleration;
        }


        // ---------------------------------------------
        // Check end condition
        // BASELINE — UNCHANGED
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
        // BASELINE — UNCHANGED
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
    // =====================================================

    else if (swingState == COOLDOWN_STATE)
    {
        // Discard interrupt events during cooldown.
        discardPendingInterrupt();

        /*
         * BASELINE behavior:
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
// BASELINE RECORDING PRESERVED
// =====================================================

void completeSwing(
    float speed,
    float impact,
    unsigned long duration
)
{
    swingCount++;

    lastSwingDuration = duration;

    unsigned long completionTime = millis();


    // =================================================
    // STORE RECORD
    // =================================================

    if (recordCount < MAX_RECORDS)
    {
        records[recordCount].swing_count =
            swingCount;

        // Session-relative times in milliseconds.
        records[recordCount].timestamp =
            toSessionMillis(completionTime);

        records[recordCount].start_time =
            toSessionMillis(swingStartTime);

        records[recordCount].end_time =
            toSessionMillis(completionTime);

        records[recordCount].duration =
            duration;

        // Baseline live sensor values at completion.
        records[recordCount].ax = ax;
        records[recordCount].ay = ay;
        records[recordCount].az = az;

        records[recordCount].gx = gx;
        records[recordCount].gy = gy;
        records[recordCount].gz = gz;

        records[recordCount].speed = speed;

        records[recordCount].impact = impact;

        records[recordCount].int_flag =
            swingIntFlag ? 1 : 0;

        recordCount++;
    }


    // =================================================
    // SERIAL OUTPUT
    // BASELINE OUTPUT PRESERVED + INT STATUS
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

    Serial.print("MPU INT flag: ");
    Serial.println(swingIntFlag ? 1 : 0);

    Serial.println("------------------------------------");
}


// =====================================================
// STATE STRING
// BASELINE — UNCHANGED
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
// BASELINE DESIGN PRESERVED
// INT STATUS AND SETTINGS ADDED
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

input {
    padding: 10px;
    margin: 5px 0 12px 0;
    font-size: 16px;
    width: 100%;
    box-sizing: border-box;
}

label {
    font-weight: bold;
}

.status {
    font-weight: bold;
    color: #2457a7;
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

<p>
MPU INT detected for current swing:
<span id="intFlag" class="value">0</span>
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

<h2>MPU6050 Motion INT Calibration</h2>

<p>
MOT_THR and MOT_DUR configure the MPU6050 motion
interrupt. They are separate from the swing FSM thresholds.
</p>

<label for="motThr">MOT_THR (0-255)</label>

<input
    type="number"
    id="motThr"
    min="0"
    max="255"
    value="30">

<label for="motDur">MOT_DUR (0-255 ms)</label>

<input
    type="number"
    id="motDur"
    min="0"
    max="255"
    value="1">

<button onclick="applySettings()">
Apply INT settings
</button>

<p id="settingsStatus" class="status">
Current settings loaded from ESP32.
</p>

<p>
GPIO 4 is used for the MPU6050 INT input.
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

let settingsInitialized = false;

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


        document.getElementById(
            'intFlag'
        ).innerText =
            d.intFlag;


        if (!settingsInitialized)
        {
            document.getElementById(
                'motThr'
            ).value = d.motThr;

            document.getElementById(
                'motDur'
            ).value = d.motDur;

            settingsInitialized = true;
        }
    }
    catch(error)
    {
        console.log(error);
    }
}


async function applySettings()
{
    const thr =
        document.getElementById('motThr').value;

    const dur =
        document.getElementById('motDur').value;

    const status =
        document.getElementById('settingsStatus');

    try
    {
        const response = await fetch(
            '/settings?thr=' +
            encodeURIComponent(thr) +
            '&dur=' +
            encodeURIComponent(dur) +
            '&ts=' + Date.now(),
            {
                cache: 'no-store'
            }
        );

        const result = await response.json();

        if (result.ok)
        {
            status.innerText =
                'Applied. MOT_THR=' + result.motThr +
                ', MOT_DUR=' + result.motDur;
        }
        else
        {
            status.innerText =
                'Settings were not applied. Check values.';
        }
    }
    catch(error)
    {
        status.innerText =
            'Could not contact ESP32.';
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
// BASELINE FIELDS PRESERVED + INT STATUS
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

    // Added INT information
    json += ",\"intFlag\":";
    json += String(swingIntFlag ? 1 : 0);

    json += ",\"motThr\":";
    json += String(motThr);

    json += ",\"motDur\":";
    json += String(motDur);

    json += ",\"mpuIntStatus\":";
    json += String(lastMpuIntStatus);

    json += ",\"sessionElapsedMs\":";
    json += String(getSessionMillis());

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
// APPLY DASHBOARD INT SETTINGS
// =====================================================

void handleSettings()
{
    bool valid = true;

    uint8_t requestedThr = motThr;
    uint8_t requestedDur = motDur;


    // ---------------------------------------------
    // MOT_THR
    // ---------------------------------------------

    if (server.hasArg("thr"))
    {
        long value = server.arg("thr").toInt();

        if (value >= 0 && value <= 255)
        {
            requestedThr = (uint8_t)value;
        }
        else
        {
            valid = false;
        }
    }


    // ---------------------------------------------
    // MOT_DUR
    // ---------------------------------------------

    if (server.hasArg("dur"))
    {
        long value = server.arg("dur").toInt();

        if (value >= 0 && value <= 255)
        {
            requestedDur = (uint8_t)value;
        }
        else
        {
            valid = false;
        }
    }


    // ---------------------------------------------
    // Apply settings if valid
    // ---------------------------------------------

    if (valid)
    {
        motThr = requestedThr;
        motDur = requestedDur;

        configureMpuMotionInterrupt();
    }


    // ---------------------------------------------
    // Return JSON
    // ---------------------------------------------

    String json = "{";

    json += "\"ok\":";
    json += valid ? "true" : "false";

    json += ",\"motThr\":";
    json += String(motThr);

    json += ",\"motDur\":";
    json += String(motDur);

    json += "}";


    server.sendHeader(
        "Cache-Control",
        "no-cache, no-store, must-revalidate"
    );

    server.send(
        valid ? 200 : 400,
        "application/json",
        json
    );


    if (valid)
    {
        Serial.println();
        Serial.println("Dashboard INT settings applied.");

        Serial.print("MOT_THR = ");
        Serial.println(motThr);

        Serial.print("MOT_DUR = ");
        Serial.println(motDur);
    }
}


// =====================================================
// CSV DOWNLOAD
// EXACT REQUESTED COLUMN ORDER
// =====================================================

void handleDownload()
{
    String csv = "";

    csv +=
        "swing_count,"
        "timestamp,"
        "start_time,"
        "end_time,"
        "duration,"
        "ax,ay,az,"
        "gx,gy,gz,"
        "speed,"
        "impact,"
        "int_flag\n";


    for (int i = 0; i < recordCount; i++)
    {
        csv += String(
            records[i].swing_count
        );

        csv += ",";

        csv += String(
            records[i].timestamp
        );

        csv += ",";

        csv += String(
            records[i].start_time
        );

        csv += ",";

        csv += String(
            records[i].end_time
        );

        csv += ",";

        csv += String(
            records[i].duration
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
            records[i].int_flag
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
// BASELINE LOOP PRESERVED + INT SERVICE
// =====================================================

void loop()
{
    // Handle web requests
    server.handleClient();

    // Read MPU6050
    readSensor();

    // Service MPU interrupt in normal loop context.
    serviceMpuInterrupt();

    // Process swing detector
    processSwing();

    // Small sampling delay
    delay(2);
}


