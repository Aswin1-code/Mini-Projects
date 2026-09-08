#include <Arduino.h>

// ============================================================
// MINI ATE - ESP32 PWM TEST FIRMWARE V3
// ============================================================
//
// DUT:
//   ESP32
//
// PWM paths:
//   Path 1: GPIO18 OUT -> GPIO19 IN
//   Path 2: GPIO4  OUT -> GPIO5  IN
//
// Test matrix:
//   Frequency : 500, 1000, 2000, 5000 Hz
//   Duty      : 10, 50, 90 %
//   Repetitions: 3
//
// Total:
//   2 paths x 4 frequencies x 3 duties x 3 repetitions
//   = 72 tests
//
// Communication:
//   USB Serial @ 115200
//
// Arduino ESP32 Core:
//   3.x LEDC API
//
// ============================================================


// ------------------------------------------------------------
// Serial
// ------------------------------------------------------------

#define SERIAL_BAUD 115200


// ------------------------------------------------------------
// PWM configuration
// ------------------------------------------------------------

const uint8_t PWM_RESOLUTION = 12;

// 12-bit duty range
const uint32_t PWM_MAX_DUTY =
    (1UL << PWM_RESOLUTION) - 1;


// ------------------------------------------------------------
// Test frequencies
// ------------------------------------------------------------

const uint32_t TEST_FREQUENCIES[] =
{
    500,
    1000,
    2000,
    5000
};

const uint8_t NUM_FREQUENCIES =
    sizeof(TEST_FREQUENCIES) / sizeof(TEST_FREQUENCIES[0]);


// ------------------------------------------------------------
// Test duty cycles
// ------------------------------------------------------------

const uint8_t TEST_DUTIES[] =
{
    10,
    50,
    90
};

const uint8_t NUM_DUTIES =
    sizeof(TEST_DUTIES) / sizeof(TEST_DUTIES[0]);


// ------------------------------------------------------------
// Repetitions
// ------------------------------------------------------------

const uint8_t REPETITIONS = 3;


// ------------------------------------------------------------
// Measurement timeout
// ------------------------------------------------------------
//
// 500 Hz period = 2000 us
// 1000 Hz      = 1000 us
// 2000 Hz      = 500 us
// 5000 Hz      = 200 us
//
// 20 ms timeout gives plenty of margin.
//

const uint32_t MEASURE_TIMEOUT_US = 20000;


// ------------------------------------------------------------
// PWM paths
// ------------------------------------------------------------

struct PWMPath
{
    uint8_t pathId;
    uint8_t outputPin;
    uint8_t inputPin;
};


PWMPath paths[] =
{
    {1, 18, 19},
    {2, 4, 5}
};


const uint8_t NUM_PATHS =
    sizeof(paths) / sizeof(paths[0]);


// ============================================================
// Utility: Convert duty percentage to LEDC count
// ============================================================

uint32_t dutyPercentToCount(uint8_t dutyPercent)
{
    return (uint32_t)
           ((PWM_MAX_DUTY * dutyPercent + 50) / 100);
}


// ============================================================
// Configure PWM
// ============================================================

bool configurePWM(uint8_t outputPin,
                  uint32_t frequency,
                  uint8_t dutyPercent)
{
    // Detach previous LEDC configuration from this pin.
    ledcDetach(outputPin);

    delay(2);

    // Attach pin with requested frequency and resolution.
    bool attached =
        ledcAttach(
            outputPin,
            frequency,
            PWM_RESOLUTION
        );

    if (!attached)
    {
        return false;
    }

    // Configure duty cycle.
    uint32_t dutyCount =
        dutyPercentToCount(dutyPercent);

    ledcWrite(
        outputPin,
        dutyCount
    );

    // Give LEDC hardware time to start.
    delay(5);

    return true;
}


// ============================================================
// Stop PWM
// ============================================================

void stopPWM(uint8_t outputPin)
{
    ledcWrite(outputPin, 0);

    delay(2);

    ledcDetach(outputPin);

    digitalWrite(outputPin, LOW);
}


// ============================================================
// Measure PWM
// ============================================================
//
// We measure:
//   HIGH time
//   LOW time
//
// Period:
//   T = HIGH + LOW
//
// Frequency:
//   f = 1,000,000 / T
//
// Duty:
//   D = HIGH / T * 100
//
// pulseIn() measures actual signal arriving at the input pin.
//
// ============================================================

bool measurePWM(
    uint8_t inputPin,
    float &measuredFrequency,
    float &measuredDuty,
    unsigned long &highTime,
    unsigned long &lowTime
)
{
    // --------------------------------------------------------
    // Wait for a LOW period first.
    // This helps synchronize measurement with the waveform.
    // --------------------------------------------------------

    pinMode(inputPin, INPUT);

    // Read HIGH duration.
    highTime =
        pulseIn(
            inputPin,
            HIGH,
            MEASURE_TIMEOUT_US
        );

    if (highTime == 0)
    {
        return false;
    }


    // Read LOW duration.
    lowTime =
        pulseIn(
            inputPin,
            LOW,
            MEASURE_TIMEOUT_US
        );

    if (lowTime == 0)
    {
        return false;
    }


    // --------------------------------------------------------
    // Calculate period
    // --------------------------------------------------------

    unsigned long period =
        highTime + lowTime;

    if (period == 0)
    {
        return false;
    }


    // --------------------------------------------------------
    // Calculate frequency
    // --------------------------------------------------------

    measuredFrequency =
        1000000.0f /
        (float)period;


    // --------------------------------------------------------
    // Calculate duty
    // --------------------------------------------------------

    measuredDuty =
        ((float)highTime /
         (float)period) * 100.0f;


    return true;
}


// ============================================================
// Run one PWM test
// ============================================================

void runPWMTest(
    const PWMPath &path,
    uint32_t requestedFrequency,
    uint8_t requestedDuty,
    uint8_t repetition,
    uint16_t testNumber
)
{
    float measuredFrequency = 0.0f;
    float measuredDuty = 0.0f;

    unsigned long highTime = 0;
    unsigned long lowTime = 0;


    // --------------------------------------------------------
    // Configure output pin
    // --------------------------------------------------------

    pinMode(path.outputPin, OUTPUT);

    digitalWrite(path.outputPin, LOW);


    // --------------------------------------------------------
    // Configure PWM
    // --------------------------------------------------------

    bool pwmOK =
        configurePWM(
            path.outputPin,
            requestedFrequency,
            requestedDuty
        );


    // --------------------------------------------------------
    // If PWM configuration failed
    // --------------------------------------------------------

    if (!pwmOK)
    {
        Serial.printf(
            "PWM_RESULT,%u,%u,%lu,%u,%u,0,0,0,0\n",
            testNumber,
            path.pathId,
            requestedFrequency,
            requestedDuty,
            repetition
        );

        stopPWM(path.outputPin);

        return;
    }


    // --------------------------------------------------------
    // Measure actual waveform
    // --------------------------------------------------------

    bool measurementOK =
        measurePWM(
            path.inputPin,
            measuredFrequency,
            measuredDuty,
            highTime,
            lowTime
        );


    // --------------------------------------------------------
    // Measurement failed
    // --------------------------------------------------------

    if (!measurementOK)
    {
        Serial.printf(
            "PWM_RESULT,%u,%u,%lu,%u,%u,0,%lu,%lu,0,0\n",
            testNumber,
            path.pathId,
            requestedFrequency,
            requestedDuty,
            repetition,
            highTime,
            lowTime
        );

        stopPWM(path.outputPin);

        return;
    }


    // --------------------------------------------------------
    // Send result to Python
    // --------------------------------------------------------

    Serial.printf(
        "PWM_RESULT,%u,%u,%lu,%u,%u,%lu,%lu,%.3f,%.3f\n",
        testNumber,
        path.pathId,
        requestedFrequency,
        requestedDuty,
        repetition,
        highTime,
        lowTime,
        measuredFrequency,
        measuredDuty
    );


    // --------------------------------------------------------
    // Stop PWM
    // --------------------------------------------------------

    stopPWM(path.outputPin);
}


// ============================================================
// Run complete PWM test suite
// ============================================================

void runAllPWMTests()
{
    uint16_t testNumber = 1;


    Serial.println("PWM_TEST_START");


    // --------------------------------------------------------
    // Path loop
    // --------------------------------------------------------

    for (uint8_t p = 0;
         p < NUM_PATHS;
         p++)
    {
        const PWMPath &path = paths[p];


        // ----------------------------------------------------
        // Frequency loop
        // ----------------------------------------------------

        for (uint8_t f = 0;
             f < NUM_FREQUENCIES;
             f++)
        {
            uint32_t frequency =
                TEST_FREQUENCIES[f];


            // ------------------------------------------------
            // Duty loop
            // ------------------------------------------------

            for (uint8_t d = 0;
                 d < NUM_DUTIES;
                 d++)
            {
                uint8_t duty =
                    TEST_DUTIES[d];


                // --------------------------------------------
                // Repetition loop
                // --------------------------------------------

                for (uint8_t r = 1;
                     r <= REPETITIONS;
                     r++)
                {
                    runPWMTest(
                        path,
                        frequency,
                        duty,
                        r,
                        testNumber
                    );

                    testNumber++;

                    // Small settling time
                    delay(10);
                }
            }
        }
    }


    Serial.println("PWM_TEST_COMPLETE");
}


// ============================================================
// Setup
// ============================================================

void setup()
{
    Serial.begin(SERIAL_BAUD);

    delay(1000);


    // --------------------------------------------------------
    // Configure input pins
    // --------------------------------------------------------

    pinMode(19, INPUT);
    pinMode(5, INPUT);


    // --------------------------------------------------------
    // Configure output pins
    // --------------------------------------------------------

    pinMode(18, OUTPUT);
    pinMode(4, OUTPUT);

    digitalWrite(18, LOW);
    digitalWrite(4, LOW);


    // --------------------------------------------------------
    // DUT ready
    // --------------------------------------------------------

    Serial.println("DUT_READY");


    // Give Python time to detect DUT_READY.
    delay(500);


    // --------------------------------------------------------
    // Run PWM test automatically
    // --------------------------------------------------------

    runAllPWMTests();
}


// ============================================================
// Main loop
// ============================================================

void loop()
{
    // Nothing required.
}