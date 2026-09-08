#include <Arduino.h>

// =====================================================
// GPIO TEST PAIRS
// =====================================================

#define GPIO1_OUT 25
#define GPIO1_IN  26

#define GPIO2_OUT 27
#define GPIO2_IN  32

#define GPIO3_OUT 33
#define GPIO3_IN  23


// =====================================================
// CONFIGURATION
// =====================================================

#define REPETITIONS 3
#define PATTERN_COUNT 4

const char *patterns[] =
{
    "0000",
    "1111",
    "0101",
    "1010"
};


// =====================================================
// RUN GPIO TEST
// =====================================================

void runGPIOTest()
{
    int outputPins[] =
    {
        GPIO1_OUT,
        GPIO2_OUT,
        GPIO3_OUT
    };

    int inputPins[] =
    {
        GPIO1_IN,
        GPIO2_IN,
        GPIO3_IN
    };

    const int pairCount = 3;

    int testID = 1;


    // =================================================
    // CONFIGURE PINS
    // =================================================

    for (int i = 0; i < pairCount; i++)
    {
        pinMode(
            outputPins[i],
            OUTPUT
        );

        pinMode(
            inputPins[i],
            INPUT
        );
    }


    // =================================================
    // TEST EACH PAIR
    // =================================================

    for (int pair = 0; pair < pairCount; pair++)
    {

        // =============================================
        // EACH PATTERN
        // =============================================

        for (
            int pattern = 0;
            pattern < PATTERN_COUNT;
            pattern++
        )
        {

            // =========================================
            // REPETITIONS
            // =========================================

            for (
                int repetition = 1;
                repetition <= REPETITIONS;
                repetition++
            )
            {

                const char *expected =
                    patterns[pattern];

                String actual = "";


                // =====================================
                // START TIMING
                // =====================================

                unsigned long startTime =
                    micros();


                // =====================================
                // APPLY PATTERN
                // =====================================

                for (int bit = 0; bit < 4; bit++)
                {

                    int state =
                        expected[bit] - '0';


                    digitalWrite(
                        outputPins[pair],
                        state
                    );


                    delayMicroseconds(100);


                    int received =
                        digitalRead(
                            inputPins[pair]
                        );


                    actual +=
                        String(received);


                    delayMicroseconds(100);
                }


                // =====================================
                // END TIMING
                // =====================================

                unsigned long executionTime =
                    micros() - startTime;


                // =====================================
                // SEND RESULT
                // =====================================

                Serial.print(
                    "GPIO_RESULT,"
                );

                Serial.print(testID);

                Serial.print(",");

                Serial.print(
                    outputPins[pair]
                );

                Serial.print(",");

                Serial.print(
                    inputPins[pair]
                );

                Serial.print(",");

                Serial.print(
                    expected
                );

                Serial.print(",");

                Serial.print(
                    actual
                );

                Serial.print(",");

                Serial.print(
                    repetition
                );

                Serial.print(",");

                Serial.println(
                    executionTime
                );


                testID++;
            }
        }
    }


    // =================================================
    // TEST COMPLETE
    // =================================================

    Serial.println(
        "GPIO_TEST_COMPLETE"
    );
}


// =====================================================
// SETUP
// =====================================================

void setup()
{
    Serial.begin(115200);

    delay(1500);

    Serial.println(
        "DUT_READY"
    );
}


// =====================================================
// LOOP
// =====================================================

void loop()
{
    if (Serial.available())
    {
        String command =
            Serial.readStringUntil('\n');

        command.trim();


        if (
            command ==
            "RUN_GPIO_TEST"
        )
        {
            runGPIOTest();
        }
    }
}