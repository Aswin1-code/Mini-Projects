#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <MPU6050.h>
#include <math.h>
#include <string.h>

// =====================================================
// HARDWARE
// =====================================================

MPU6050 mpu;

#define SDA_PIN 26
#define SCL_PIN 25
#define LED_PIN 2

// MPU6050 INT is connected to ESP32 GPIO 4.
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

//const float ACCEL_SCALE = 4096.0;   // ±8g
const float ACCEL_SCALE = 2048.0;  // ±16g
const float GYRO_SCALE  = 16.4;     // ±2000 deg/s

const float GRAVITY = 9.81;

// I2C and sample-rate configuration.
// With DLPF enabled, the MPU6050 sample-rate base is 1 kHz.
// SMPLRT_DIV = 0 requests 1 kHz sensor output rate.
const uint32_t I2C_CLOCK_HZ = 400000;
const uint8_t MPU_SAMPLE_RATE_DIVIDER = 0;
const uint8_t MPU_DLPF_CONFIG = 1;

// =====================================================
// MPU6050 REGISTER DEFINITIONS
// =====================================================

const uint8_t MPU6050_ADDRESS = 0x68;

const uint8_t REG_SMPLRT_DIV  = 0x19;
const uint8_t REG_CONFIG      = 0x1A;
const uint8_t REG_INT_PIN_CFG = 0x37;
const uint8_t REG_INT_ENABLE  = 0x38;
const uint8_t REG_INT_STATUS  = 0x3A;
const uint8_t REG_MOT_THR     = 0x1F;
const uint8_t REG_MOT_DUR     = 0x20;
const uint8_t REG_PWR_MGMT_1  = 0x6B;

const uint8_t MPU_MOTION_INT_BIT = 0x40;

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
// Raw accelerometer readings (signed register counts)
int16_t rawAx = 0;
int16_t rawAy = 0;
int16_t rawAz = 0;

// Raw readings captured at peak impact
int16_t impactRawAx = 0;
int16_t impactRawAy = 0;
int16_t impactRawAz = 0;

int16_t impactRawAz = 0;

// =====================================================
// CLIPPING-AWARE SNAPSHOT RING BUFFER
// =====================================================
// Stores recent sensor samples so completeSwing() can select
// the sample nearest the midpoint from peak impact to completion.
const int SAMPLE_BUFFER_CAPACITY = 2048;
const int16_t CLIP_RAW_THRESHOLD = 32760;

struct SensorSample
{
    unsigned long timestamp;
    float ax, ay, az;       // acceleration in g
    float gx, gy, gz;       // bias-corrected deg/s
    int16_t rawAx, rawAy, rawAz;
    int16_t rawGx, rawGy, rawGz;
    bool clipped;
};

SensorSample sampleBuffer[SAMPLE_BUFFER_CAPACITY];
int sampleWriteIndex = 0;
int sampleStoredCount = 0;

struct SnapshotSelection
{
    bool found;
    bool clipped;
    unsigned long timestamp;
    float ax, ay, az;
    float gx, gy, gz;
    const char* source;
};

bool rawValueClipped(int16_t value)
{
    return value >= CLIP_RAW_THRESHOLD ||
           value <= -CLIP_RAW_THRESHOLD;
}

void storeSensorSample(
    unsigned long timestamp,
    int16_t rax, int16_t ray, int16_t raz,
    int16_t rgx, int16_t rgy, int16_t rgz)
{
    SensorSample &s = sampleBuffer[sampleWriteIndex];
    s.timestamp = timestamp;
    s.ax = ax; s.ay = ay; s.az = az;
    s.gx = gx; s.gy = gy; s.gz = gz;
    s.rawAx = rax; s.rawAy = ray; s.rawAz = raz;
    s.rawGx = rgx; s.rawGy = rgy; s.rawGz = rgz;
    s.clipped =
        rawValueClipped(rax) || rawValueClipped(ray) ||
        rawValueClipped(raz) || rawValueClipped(rgx) ||
        rawValueClipped(rgy) || rawValueClipped(rgz);

    sampleWriteIndex = (sampleWriteIndex + 1) % SAMPLE_BUFFER_CAPACITY;
    if (sampleStoredCount < SAMPLE_BUFFER_CAPACITY) sampleStoredCount++;
}

// Select closest non-clipped sample to midpoint within the interval
// [peakImpactTime, completionTime]. If none is valid, retain the closest
// available sample but explicitly mark it clipped/unusable.
SnapshotSelection selectMidpointSnapshot(
    unsigned long peakTime,
    unsigned long completionTime)
{
    SnapshotSelection result;
    result.found = false;
    result.clipped = true;
    result.timestamp = 0;
    result.ax = result.ay = result.az = 0;
    result.gx = result.gy = result.gz = 0;
    result.source = "NONE";

    const unsigned long interval = completionTime - peakTime;
    const unsigned long midpointOffset = interval / 2;

    unsigned long bestValidDistance = 0xFFFFFFFFUL;
    unsigned long bestAnyDistance = 0xFFFFFFFFUL;
    bool foundValid = false;
    SensorSample bestValid;
    SensorSample bestAny;

    for (int n = 0; n < sampleStoredCount; n++)
    {
        int idx = sampleWriteIndex - 1 - n;
        while (idx < 0) idx += SAMPLE_BUFFER_CAPACITY;
        const SensorSample &s = sampleBuffer[idx];

        // Unsigned subtraction remains safe across millis() rollover
        // for this short, bounded swing interval.
        unsigned long offset = s.timestamp - peakTime;
        if (offset > interval) continue;

        unsigned long distance =
            (offset > midpointOffset)
            ? (offset - midpointOffset)
            : (midpointOffset - offset);

        if (distance < bestAnyDistance)
        {
            bestAnyDistance = distance;
            bestAny = s;
        }

        if (!s.clipped && distance < bestValidDistance)
        {
            bestValidDistance = distance;
            bestValid = s;
            foundValid = true;
        }
    }

    if (foundValid)
    {
        result.found = true;
        result.clipped = false;
        result.timestamp = bestValid.timestamp;
        result.ax = bestValid.ax; result.ay = bestValid.ay; result.az = bestValid.az;
        result.gx = bestValid.gx; result.gy = bestValid.gy; result.gz = bestValid.gz;
        result.source = (bestValidDistance == 0) ? "MIDPOINT" : "NEARBY_VALID";
    }
    else if (bestAnyDistance != 0xFFFFFFFFUL)
    {
        result.found = true;
        result.clipped = true;
        result.timestamp = bestAny.timestamp;
        result.ax = bestAny.ax; result.ay = bestAny.ay; result.az = bestAny.az;
        result.gx = bestAny.gx; result.gy = bestAny.gy; result.gz = bestAny.gz;
        result.source = "NO_VALID_CLIPPED";
    }

    return result;
}

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
// SESSION-RELATIVE MILLIS TIMING
// =====================================================

// Session begins at the first detected swing.
bool sessionStarted = false;
unsigned long sessionStartMillis = 0;

// Convert raw ESP32 millis() to session-relative time.
unsigned long getSessionMillis()
{
    if (!sessionStarted)
    {
        return 0;
    }

    return millis() - sessionStartMillis;
}

// Convert a previously captured raw millis() timestamp.
unsigned long toSessionMillis(unsigned long rawTime)
{
    if (!sessionStarted)
    {
        return 0;
    }

    return rawTime - sessionStartMillis;
}

// Peak-event snapshots.
// Speed and acceleration peaks may happen at different samples.
float spax = 0;
float spay = 0;
float spaz = 0;
float spgx = 0;
float spgy = 0;
float spgz = 0;

float imax = 0;
float imay = 0;
float imaz = 0;
float imgx = 0;
float imgy = 0;
float imgz = 0;

unsigned long peakSpeedTime = 0;
unsigned long peakImpactTime = 0;

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
// MPU6050 MOTION INTERRUPT CALIBRATION
// =====================================================

// Initial configurable values.
// These are starting values for testing, not universally
// calibrated values for every racket/mounting condition.
uint8_t motThr = 30;                        //    
uint8_t motDur = 1;                         //
//==============================================
// The dashboard sets this once for a batch:
// 0 = free swing
// 1 = real shuttle hit
int hitLabel = 0;

// ISR only sets this flag. I2C operations happen in loop().
volatile bool mpuIntPending = false;

// At most one accepted motion interrupt per active swing.
bool swingIntFlag = false;

// Track the most recent MPU interrupt status for dashboard.
uint8_t lastMpuIntStatus = 0;

// =====================================================
// CSV STORAGE
// =====================================================

// Stores completed swing records in RAM.
//
// CSV columns:
// swing_count,timestamp_ms,start_time_ms,end_time_ms,
// duration_ms,
// spax,spay,spaz,spgx,spgy,spgz,peak_speed,
// imax,imay,imaz,imgx,imgy,imgz,peak_impact,
// hit_label,int_flag,mot_thr,mot_dur

struct SwingRecord
{
    unsigned long swing_count;

    unsigned long timestamp_ms;
    unsigned long start_time_ms;
    unsigned long end_time_ms;
    unsigned long duration_ms;

    float spax;
    float spay;
    float spaz;

    float spgx;
    float spgy;
    float spgz;

    float peak_speed;

    float imax;
    float imay;
    float imaz;

    float imgx;
    float imgy;
    float imgz;

    float peak_impact;

    int hit_label;
    int int_flag;

    uint8_t mot_thr;
    uint8_t mot_dur;
    
    // Raw accelerometer values at peak impact
    int16_t raw_ax;
    int16_t raw_ay;
    int16_t raw_az;

    // Selected sample near midpoint between peak impact and swing completion
    unsigned long snapshot_timestamp_ms;
    float snapshot_ax, snapshot_ay, snapshot_az;
    float snapshot_gx, snapshot_gy, snapshot_gz;
    char snapshot_source[20];
    int snapshot_clipped;
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
void handleSettings();

void onMpuInterrupt();

bool writeMpuRegister(uint8_t reg, uint8_t value);
uint8_t readMpuRegister(uint8_t reg);
void configureMpuSampleRate();
void configureMpuMotionInterrupt();
void clearMpuInterruptStatus();
void discardPendingInterrupt();
void serviceMpuInterrupt();
void resetPeakSnapshots();
void captureSpeedPeak();
void captureImpactPeak();
void storeSensorSample(unsigned long timestamp, int16_t rax, int16_t ray, int16_t raz, int16_t rgx, int16_t rgy, int16_t rgz);
SnapshotSelection selectMidpointSnapshot(unsigned long peakTime, unsigned long completionTime);

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

    // Set I2C clock to 400 kHz.
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
    // =================================================

    // ±8g
    //mpu.setFullScaleAccelRange(MPU6050_ACCEL_FS_8);
mpu.setFullScaleAccelRange(MPU6050_ACCEL_FS_16);
    // ±2000 deg/s
    mpu.setFullScaleGyroRange(MPU6050_GYRO_FS_2000);

    // =================================================
    // SAMPLE RATE CONFIGURATION
    // =================================================

    configureMpuSampleRate();

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
    // MPU MOTION INTERRUPT
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

    // Read the actual MPU6050 status in normal loop context.
    lastMpuIntStatus = readMpuRegister(REG_INT_STATUS);

    // Accept at most one MPU motion interrupt per ACTIVE swing.
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
    // RAW ACCELEROMETER VALUES
    // =================================================
    // rawAx, rawAy, rawAz remain in original sensor counts.

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
    instantSpeed = angularVelocity * 0.03;

    // Save each reading for later midpoint/nearby-valid selection.
    storeSensorSample(
        millis(),
        rawAx, rawAy, rawAz,
        rawGx, rawGy, rawGz
    );
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
// RESET PEAK SNAPSHOTS
// =====================================================

void resetPeakSnapshots()
{
    peakSpeed = instantSpeed;
    peakAcceleration = totalAcceleration;

    spax = ax;
    spay = ay;
    spaz = az;

    spgx = gx;
    spgy = gy;
    spgz = gz;

    imax = ax;
    imay = ay;
    imaz = az;

    imgx = gx;
    imgy = gy;
    imgz = gz;

    impactRawAx = rawAx;
    impactRawAy = rawAy;
    impactRawAz = rawAz;

    peakSpeedTime = millis();
    peakImpactTime = millis();
}

// =====================================================
// CAPTURE PEAK SPEED AXES
// =====================================================

void captureSpeedPeak()
{
    spax = ax;
    spay = ay;
    spaz = az;

    spgx = gx;
    spgy = gy;
    spgz = gz;

    peakSpeedTime = millis();
}

// =====================================================
// CAPTURE PEAK IMPACT AXES
// =====================================================

void captureImpactPeak()
{
    imax = ax;
    imay = ay;
    imaz = az;

    imgx = gx;
    imgy = gy;
    imgz = gz;

    impactRawAx = rawAx;
    impactRawAy = rawAy;
    impactRawAz = rawAz;

    peakImpactTime = millis();
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
        // Ignore and clear MPU interrupt events outside
        // an active swing so stale events are not reused.
        discardPendingInterrupt();

        if (startCondition())
        {
            // Start session timer at the first detected swing.
            if (!sessionStarted)
            {
                sessionStartMillis = now;
                sessionStarted = true;
            }

            swingState = ACTIVE;

            // Keep raw millis() internally for FSM calculations.
            swingStartTime = now;

            endConditionStartTime = 0;

            swingIntFlag = false;

            // Clear any old event immediately before
            // beginning a new active swing.
            discardPendingInterrupt();

            resetPeakSnapshots();

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
        // Track peak speed and its six sensor values
        // ---------------------------------------------

        if (instantSpeed > peakSpeed)
        {
            peakSpeed = instantSpeed;

            captureSpeedPeak();
        }

        // ---------------------------------------------
        // Track peak acceleration and its six values
        // ---------------------------------------------

        if (totalAcceleration > peakAcceleration)
        {
            peakAcceleration = totalAcceleration;

            captureImpactPeak();
        }

        // ---------------------------------------------
        // Check end condition
        // ---------------------------------------------

        bool swingCompleted = false;

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

                swingCompleted = true;

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
            !swingCompleted &&
            swingState == ACTIVE &&
            now - swingStartTime >= MAX_SWING_DURATION
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
        // Discard interrupt events during cooldown.
        discardPendingInterrupt();

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

    unsigned long completionTime = millis();

    // Reference is the peak-impact timestamp (not peak-speed timestamp).
    SnapshotSelection snapshot =
        selectMidpointSnapshot(peakImpactTime, completionTime);

    // =================================================
    // STORE RECORD
    // =================================================

    if (recordCount < MAX_RECORDS)
    {
        records[recordCount].swing_count =
            swingCount;

        // Session-relative timestamps in milliseconds.
        records[recordCount].timestamp_ms =
            toSessionMillis(completionTime);

        records[recordCount].start_time_ms =
            toSessionMillis(swingStartTime);

        records[recordCount].end_time_ms =
            toSessionMillis(completionTime);

        // Duration is still calculated using raw millis().
        records[recordCount].duration_ms =
            duration;

        // Peak-speed event axes.
        records[recordCount].spax = spax;
        records[recordCount].spay = spay;
        records[recordCount].spaz = spaz;

        records[recordCount].spgx = spgx;
        records[recordCount].spgy = spgy;
        records[recordCount].spgz = spgz;

        records[recordCount].peak_speed =
            speed;

        // Peak-impact event axes.
        records[recordCount].imax = imax;
        records[recordCount].imay = imay;
        records[recordCount].imaz = imaz;

        records[recordCount].imgx = imgx;
        records[recordCount].imgy = imgy;
        records[recordCount].imgz = imgz;

        records[recordCount].peak_impact =
            impact;

        // Batch label and MPU interrupt result.
        records[recordCount].hit_label =
            hitLabel;

        records[recordCount].int_flag =
            swingIntFlag ? 1 : 0;

        // Store the settings used for this swing.
        records[recordCount].mot_thr =
            motThr;

        records[recordCount].mot_dur =
            motDur;
        // Raw accelerometer readings at peak impact
        records[recordCount].raw_ax = impactRawAx;
        records[recordCount].raw_ay = impactRawAy;
        records[recordCount].raw_az = impactRawAz;

        records[recordCount].snapshot_timestamp_ms =
            snapshot.found ? toSessionMillis(snapshot.timestamp) : 0;
        records[recordCount].snapshot_ax = snapshot.ax;
        records[recordCount].snapshot_ay = snapshot.ay;
        records[recordCount].snapshot_az = snapshot.az;
        records[recordCount].snapshot_gx = snapshot.gx;
        records[recordCount].snapshot_gy = snapshot.gy;
        records[recordCount].snapshot_gz = snapshot.gz;
        strncpy(records[recordCount].snapshot_source, snapshot.source,
                sizeof(records[recordCount].snapshot_source) - 1);
        records[recordCount].snapshot_source[
            sizeof(records[recordCount].snapshot_source) - 1] = '\\0';
        records[recordCount].snapshot_clipped =
            snapshot.found ? (snapshot.clipped ? 1 : 0) : -1;

        recordCount++;
    }
    else
    {
        Serial.println("WARNING: CSV RAM storage is full.");
    }

    // =================================================
    // SERIAL OUTPUT
    // =================================================

    Serial.println();
    Serial.println("------------------------------------");

    Serial.print("SWING #");
    Serial.println(swingCount);

    Serial.print("Session timestamp (ms): ");
    Serial.println(toSessionMillis(completionTime));

    Serial.print("Swing start (session ms): ");
    Serial.println(toSessionMillis(swingStartTime));

    Serial.print("Swing end (session ms): ");
    Serial.println(toSessionMillis(completionTime));

    Serial.print("Swing duration (ms): ");
    Serial.println(duration);

    Serial.print("Speed: ");
    Serial.println(speed);

    Serial.print("Impact: ");
    Serial.println(impact);

    Serial.print("Snapshot source: ");
    Serial.println(snapshot.source);
    Serial.print("Snapshot clipped flag: ");
    Serial.println(snapshot.found ? (snapshot.clipped ? 1 : 0) : -1);
    if (snapshot.found)
    {
        Serial.print("Snapshot session timestamp (ms): ");
        Serial.println(toSessionMillis(snapshot.timestamp));
    }

    Serial.print("Duration: ");
    Serial.print(duration / 1000.0);
    Serial.println(" s");

    Serial.print("Hit label: ");
    Serial.println(hitLabel);

    Serial.print("MPU INT flag: ");
    Serial.println(swingIntFlag ? 1 : 0);

    Serial.print("MOT_THR: ");
    Serial.println(motThr);

    Serial.print("MOT_DUR: ");
    Serial.println(motDur);

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

input, select {
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
    Raw Accelerometer X:
    <span id="rawAx" class="value">0</span>
</p>

<p>
    Raw Accelerometer Y:
    <span id="rawAy" class="value">0</span>
</p>

<p>
    Raw Accelerometer Z:
    <span id="rawAz" class="value">0</span>
</p>

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
Session Elapsed:
<span id="sessionElapsed" class="value">0</span>
ms
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

<h2>Batch Label</h2>

<p>
Set the label once before recording a batch.
</p>

<label for="hitLabel">Swing label</label>

<select id="hitLabel">
    <option value="0">0 - Free swing</option>
    <option value="1">1 - Real shuttle hit</option>
</select>

<button onclick="applySettings()">
Apply label and INT settings
</button>

<p id="settingsStatus" class="status">
Current settings loaded from ESP32.
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

        document.getElementById('rawAx').innerText = d.rawAx;
        document.getElementById('rawAy').innerText = d.rawAy;
        document.getElementById('rawAz').innerText = d.rawAz;
        
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
            'sessionElapsed'
        ).innerText = d.sessionElapsedMs;

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
                'hitLabel'
            ).value = String(d.hitLabel);

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
    const hit =
        document.getElementById('hitLabel').value;

    const thr =
        document.getElementById('motThr').value;

    const dur =
        document.getElementById('motDur').value;

    const status =
        document.getElementById('settingsStatus');

    try
    {
        const response = await fetch(
            '/settings?hit=' +
            encodeURIComponent(hit) +
            '&thr=' +
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
                'Applied. hit_label=' + result.hitLabel +
                ', MOT_THR=' + result.motThr +
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

    json += ",\"sessionElapsedMs\":";
    json += String(getSessionMillis());

    json += ",\"currentPeakAcc\":";
    json += String(peakAcceleration, 2);

    json += ",\"currentPeakSpeed\":";
    json += String(peakSpeed, 2);

    json += ",\"hitLabel\":";
    json += String(hitLabel);

    json += ",\"intFlag\":";
    json += String(swingIntFlag ? 1 : 0);

    json += ",\"motThr\":";
    json += String(motThr);

    json += ",\"motDur\":";
    json += String(motDur);

    json += ",\"mpuIntStatus\":";
    json += String(lastMpuIntStatus);
    
    json += ",\"rawAx\":";
    json += String(rawAx);

    json += ",\"rawAy\":";
    json += String(rawAy);

    json += ",\"rawAz\":";
    json += String(rawAz);

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
// APPLY DASHBOARD SETTINGS
// =====================================================

void handleSettings()
{
    bool valid = true;

    // ---------------------------------------------
    // Batch hit label
    // ---------------------------------------------

    if (server.hasArg("hit"))
    {
        int requestedHit =
            server.arg("hit").toInt();

        if (
            requestedHit == 0 ||
            requestedHit == 1
        )
        {
            hitLabel = requestedHit;
        }
        else
        {
            valid = false;
        }
    }

    // ---------------------------------------------
    // MOT_THR
    // ---------------------------------------------

    if (server.hasArg("thr"))
    {
        long requestedThr =
            server.arg("thr").toInt();

        if (
            requestedThr >= 0 &&
            requestedThr <= 255
        )
        {
            motThr = (uint8_t)requestedThr;
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
        long requestedDur =
            server.arg("dur").toInt();

        if (
            requestedDur >= 0 &&
            requestedDur <= 255
        )
        {
            motDur = (uint8_t)requestedDur;
        }
        else
        {
            valid = false;
        }
    }

    // ---------------------------------------------
    // Apply sensor interrupt configuration
    // ---------------------------------------------

    if (valid)
    {
        configureMpuMotionInterrupt();

        // Do not erase an already accepted active-swing
        // interrupt flag when settings are changed.
    }

    // ---------------------------------------------
    // Return updated settings as JSON
    // ---------------------------------------------

    String json = "{";

    json += "\"ok\":";
    json += valid ? "true" : "false";

    json += ",\"hitLabel\":";
    json += String(hitLabel);

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
        Serial.println("Dashboard settings applied.");

        Serial.print("hit_label = ");
        Serial.println(hitLabel);

        Serial.print("MOT_THR = ");
        Serial.println(motThr);

        Serial.print("MOT_DUR = ");
        Serial.println(motDur);
    }
}

// =====================================================
// CSV DOWNLOAD
// =====================================================

void handleDownload()
{
    String csv = "";

    csv +=
        "swing_count,"
        "timestamp_ms,"
        "start_time_ms,"
        "end_time_ms,"
        "duration_ms,"
        "spax,spay,spaz,"
        "spgx,spgy,spgz,"
        "peak_speed,"
        "imax,imay,imaz,"
        "imgx,imgy,imgz,"
        "peak_impact,"
        "hit_label,"
        "int_flag,"
        "mot_thr,"
        "mot_dur,"
        "raw_ax,"
        "raw_ay,"
        "raw_az,"
        "snapshot_timestamp_ms,"
        "snapshot_ax,snapshot_ay,snapshot_az,"
        "snapshot_gx,snapshot_gy,snapshot_gz,"
        "snapshot_source,"
        "snapshot_clipped\n";

    for (int i = 0; i < recordCount; i++)
    {
        csv += String(
            records[i].swing_count
        );

        csv += ",";

        csv += String(
            records[i].timestamp_ms
        );

        csv += ",";

        csv += String(
            records[i].start_time_ms
        );

        csv += ",";

        csv += String(
            records[i].end_time_ms
        );

        csv += ",";

        csv += String(
            records[i].duration_ms
        );

        csv += ",";

        csv += String(
            records[i].spax,
            4
        );

        csv += ",";

        csv += String(
            records[i].spay,
            4
        );

        csv += ",";

        csv += String(
            records[i].spaz,
            4
        );

        csv += ",";

        csv += String(
            records[i].spgx,
            4
        );

        csv += ",";

        csv += String(
            records[i].spgy,
            4
        );

        csv += ",";

        csv += String(
            records[i].spgz,
            4
        );

        csv += ",";

        csv += String(
            records[i].peak_speed,
            4
        );

        csv += ",";

        csv += String(
            records[i].imax,
            4
        );

        csv += ",";

        csv += String(
            records[i].imay,
            4
        );

        csv += ",";

        csv += String(
            records[i].imaz,
            4
        );

        csv += ",";

        csv += String(
            records[i].imgx,
            4
        );

        csv += ",";

        csv += String(
            records[i].imgy,
            4
        );

        csv += ",";

        csv += String(
            records[i].imgz,
            4
        );

        csv += ",";

        csv += String(
            records[i].peak_impact,
            4
        );

        csv += ",";

        csv += String(
            records[i].hit_label
        );

        csv += ",";

        csv += String(
            records[i].int_flag
        );

        csv += ",";

        csv += String(
            records[i].mot_thr
        );

        csv += ",";

        csv += String(
            records[i].mot_dur
        );
        
        csv += ",";
        csv += String(records[i].raw_ax);

        csv += ",";
        csv += String(records[i].raw_ay);

        csv += ",";
        csv += String(records[i].raw_az);

        csv += ",";
        csv += String(records[i].snapshot_timestamp_ms);

        csv += ",";
        csv += String(records[i].snapshot_ax, 4);
        csv += ",";
        csv += String(records[i].snapshot_ay, 4);
        csv += ",";
        csv += String(records[i].snapshot_az, 4);

        csv += ",";
        csv += String(records[i].snapshot_gx, 4);
        csv += ",";
        csv += String(records[i].snapshot_gy, 4);
        csv += ",";
        csv += String(records[i].snapshot_gz, 4);

        csv += ",";
        csv += String(records[i].snapshot_source);

        csv += ",";
        csv += String(records[i].snapshot_clipped);

        csv += "\n";
    }

    server.sendHeader(
        "Content-Disposition",
        "attachment; filename=badminton_int_calibration.csv"
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

    // Service interrupt flag in normal loop context.
    serviceMpuInterrupt();

    // Process swing detector
    processSwing();

    // Small sampling delay retained from original code.
    delay(2);
}
