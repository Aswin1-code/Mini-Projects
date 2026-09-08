import serial
import time
import sys


# =====================================================
# CONFIGURATION
# =====================================================

PORT = "COM5"
BAUDRATE = 115200

DUT_READY_TIMEOUT = 5
TEST_TIMEOUT = 10

EXPECTED_PATTERNS = [
    "MINIATE_UART",
    "1234567890",
    "ABCDEF123456"
]


# =====================================================
# OPEN DUT
# =====================================================

try:

    dut = serial.Serial(
        PORT,
        BAUDRATE,
        timeout=0.5
    )

except Exception:

    print("ATE ERROR: Cannot open DUT")
    sys.exit()


# ESP32 resets when COM port opens
time.sleep(2)


# =====================================================
# WAIT FOR DUT_READY
# =====================================================

ready = False

start = time.time()

while time.time() - start < DUT_READY_TIMEOUT:

    line = dut.readline().decode(
        errors="ignore"
    ).strip()

    if line == "DUT_READY":

        ready = True
        break


if not ready:

    print("ATE ERROR: DUT not ready")

    dut.close()
    sys.exit()


# =====================================================
# START UART TEST
# =====================================================

dut.write(b"RUN_UART_TEST\n")
dut.flush()


# =====================================================
# RECEIVE RESULTS
# =====================================================

results = []

start = time.time()

while time.time() - start < TEST_TIMEOUT:

    line = dut.readline().decode(
        errors="ignore"
    ).strip()

    if not line:
        continue


    # -----------------------------------------------
    # TEST RESULT
    # -----------------------------------------------

    if line.startswith("RESULT,"):

        fields = line.split(",")

        if len(fields) != 7:
            continue


        test_id = int(fields[1])

        tx_pin = int(fields[2])

        rx_pin = int(fields[3])

        expected = fields[4]

        actual = fields[5]

        transfer_time_us = int(fields[6])


        # -------------------------------------------
        # PYTHON EVALUATION
        # -------------------------------------------

        if actual == expected:

            result = "PASS"
            reason = "Data matched"

        else:

            result = "FAIL"

            if actual == "":
                reason = "Timeout / no data received"

            else:
                reason = "Received data mismatch"


        # -------------------------------------------
        # STORE RESULT
        # -------------------------------------------

        results.append({

            "test_id": test_id,

            "tx": tx_pin,

            "rx": rx_pin,

            "expected": expected,

            "actual": actual,

            "time_us": transfer_time_us,

            "result": result,

            "reason": reason

        })


    # -----------------------------------------------
    # TEST COMPLETE
    # -----------------------------------------------

    elif line == "UART_TEST_COMPLETE":

        break


# =====================================================
# RESULT SUMMARY
# =====================================================

print()
print("========== MINI ATE UART SUMMARY ==========")

for r in results:

    print(
        f"Test {r['test_id']}: "
        f"GPIO{r['tx']} TX -> "
        f"GPIO{r['rx']} RX | "
        f"{r['result']} | "
        f"{r['time_us']} us"
    )

    if r["result"] == "FAIL":

        print(
            f"  Expected : {r['expected']}"
        )

        print(
            f"  Actual   : {r['actual']}"
        )

        print(
            f"  Reason   : {r['reason']}"
        )


# =====================================================
# OVERALL RESULT
# =====================================================

if len(results) == 6:

    failed_tests = [
        r for r in results
        if r["result"] == "FAIL"
    ]

    if len(failed_tests) == 0:

        print("------------------------------------------")
        print("Overall Result : PASS")

    else:

        print("------------------------------------------")
        print("Overall Result : FAIL")

else:

    print("------------------------------------------")
    print("Overall Result : FAIL")
    print("Reason : Incomplete test execution")


# =====================================================
# CLOSE
# =====================================================

dut.close()