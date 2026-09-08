#include <Arduino.h>

#define PIN_A 17
#define PIN_B 16

#define PIN_C 14
#define PIN_D 12

#define UART_BAUD 115200
#define UART_TIMEOUT_MS 1000

// Existing UART
HardwareSerial TestUART(2);

// Additional UART
HardwareSerial TestUART2(1);


// =====================================================
// TEST PATTERNS
// =====================================================

const uint8_t pattern1[] = {
    'M','I','N','I','A','T','E','_','U','A','R','T'
};

const uint8_t pattern2[] = {
    0xAA, 0xAA, 0xAA, 0xAA,
    0xAA, 0xAA, 0xAA, 0xAA
};

const uint8_t pattern3[] = {
    0x55, 0x55, 0x55, 0x55,
    0x55, 0x55, 0x55, 0x55
};

const uint8_t pattern4[] = {
    0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00
};

const uint8_t pattern5[] = {
    0xFF, 0xFF, 0xFF, 0xFF,
    0xFF, 0xFF, 0xFF, 0xFF
};

const uint8_t pattern6[] = {
    0xA5, 0x3C, 0x7E, 0x19,
    0xF0, 0x55, 0xAA, 0x81,
    0x12, 0x34, 0xC7, 0x00,
    0xFE, 0x68, 0x91, 0xD2
};


// =====================================================
// PATTERN TABLE
// =====================================================

struct TestPattern
{
    const uint8_t *data;
    size_t length;
    const char *name;
};

TestPattern patterns[] =
{
    {pattern1, sizeof(pattern1), "ASCII"},
    {pattern2, sizeof(pattern2), "0xAA"},
    {pattern3, sizeof(pattern3), "0x55"},
    {pattern4, sizeof(pattern4), "0x00"},
    {pattern5, sizeof(pattern5), "0xFF"},
    {pattern6, sizeof(pattern6), "MIXED"}
};

const int NUM_PATTERNS = 6;

const int REPETITIONS = 1;


// =====================================================
// CLEAR RX BUFFER
// =====================================================

void clearRX(HardwareSerial &uart)
{
    while (uart.available())
    {
        uart.read();
    }
}


// =====================================================
// PRINT BYTES AS HEX
// =====================================================

void printHex(
    const uint8_t *data,
    size_t length
)
{
    for (size_t i = 0; i < length; i++)
    {
        if (data[i] < 0x10)
        {
            Serial.print("0");
        }

        Serial.print(data[i], HEX);

        if (i < length - 1)
        {
            Serial.print(" ");
        }
    }
}


// =====================================================
// PERFORM ONE TRANSACTION
// =====================================================

void performUARTTest(
    HardwareSerial &uart,
    int uartNumber,
    int testID,
    int txPin,
    int rxPin,
    int patternID,
    int repetition
)
{
    const uint8_t *expected =
        patterns[patternID].data;

    size_t expectedLength =
        patterns[patternID].length;


    // -------------------------------------------------
    // Configure UART
    // -------------------------------------------------

    uart.end();

    uart.begin(
        UART_BAUD,
        SERIAL_8N1,
        rxPin,
        txPin
    );

    delay(5);

    clearRX(uart);


    // -------------------------------------------------
    // RX buffer
    // -------------------------------------------------

    uint8_t received[64];

    size_t receivedLength = 0;


    // -------------------------------------------------
    // START TIMER
    // -------------------------------------------------

    unsigned long startTime = micros();


    // -------------------------------------------------
    // TRANSMIT
    // -------------------------------------------------

    uart.write(
        expected,
        expectedLength
    );

    uart.flush();


    // -------------------------------------------------
    // RECEIVE
    // -------------------------------------------------

    unsigned long timeoutStart =
        millis();


    while (
        millis() - timeoutStart
        <
        UART_TIMEOUT_MS
    )
    {
        while (uart.available())
        {
            if (receivedLength < sizeof(received))
            {
                received[receivedLength++] =
                    uart.read();
            }
            else
            {
                uart.read();
            }
        }


        if (
            receivedLength >=
            expectedLength
        )
        {
            break;
        }
    }


    // -------------------------------------------------
    // END TIMER
    // -------------------------------------------------

    unsigned long endTime = micros();

    unsigned long transferTime =
        endTime - startTime;


    // -------------------------------------------------
    // RETURN RAW EVIDENCE
    // -------------------------------------------------

    Serial.print("RESULT,");

    Serial.print(uartNumber);

    Serial.print(",");

    Serial.print(testID);

    Serial.print(",");

    Serial.print(txPin);

    Serial.print(",");

    Serial.print(rxPin);

    Serial.print(",");

    Serial.print(
        patterns[patternID].name
    );

    Serial.print(",");

    Serial.print(repetition);

    Serial.print(",");

    Serial.print(expectedLength);

    Serial.print(",");

    Serial.print(receivedLength);

    Serial.print(",");

    Serial.print(transferTime);

    Serial.print(",");

    printHex(
        expected,
        expectedLength
    );

    Serial.print(",");

    printHex(
        received,
        receivedLength
    );

    Serial.println();
}


// =====================================================
// RUN COMPLETE UART TEST
// =====================================================

void runUARTTest()
{
    int testID = 1;


    // =================================================
    // UART2
    //
    // GPIO17 TX → GPIO16 RX
    // =================================================

    for (
        int pattern = 0;
        pattern < NUM_PATTERNS;
        pattern++
    )
    {
        for (
            int rep = 1;
            rep <= REPETITIONS;
            rep++
        )
        {
            performUARTTest(
                TestUART,
                2,
                testID,
                PIN_A,
                PIN_B,
                pattern,
                rep
            );

            testID++;
        }
    }


    // =================================================
    // UART2
    //
    // GPIO16 TX → GPIO17 RX
    // =================================================

    for (
        int pattern = 0;
        pattern < NUM_PATTERNS;
        pattern++
    )
    {
        for (
            int rep = 1;
            rep <= REPETITIONS;
            rep++
        )
        {
            performUARTTest(
                TestUART,
                2,
                testID,
                PIN_B,
                PIN_A,
                pattern,
                rep
            );

            testID++;
        }
    }


    // =================================================
    // UART1
    //
    // GPIO14 TX → GPIO12 RX
    // =================================================

    for (
        int pattern = 0;
        pattern < NUM_PATTERNS;
        pattern++
    )
    {
        for (
            int rep = 1;
            rep <= REPETITIONS;
            rep++
        )
        {
            performUARTTest(
                TestUART2,
                1,
                testID,
                PIN_C,
                PIN_D,
                pattern,
                rep
            );

            testID++;
        }
    }


    // =================================================
    // UART1
    //
    // GPIO12 TX → GPIO14 RX
    // =================================================

    for (
        int pattern = 0;
        pattern < NUM_PATTERNS;
        pattern++
    )
    {
        for (
            int rep = 1;
            rep <= REPETITIONS;
            rep++
        )
        {
            performUARTTest(
                TestUART2,
                1,
                testID,
                PIN_D,
                PIN_C,
                pattern,
                rep
            );

            testID++;
        }
    }


    // =================================================
    // COMPLETE
    // =================================================

    Serial.println(
        "UART_TEST_COMPLETE"
    );
}


// =====================================================
// SETUP
// =====================================================

void setup()
{
    Serial.begin(115200);

    delay(1500);

    Serial.println("DUT_READY");
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
            "RUN_UART_TEST"
        )
        {
            runUARTTest();
        }
    }
}