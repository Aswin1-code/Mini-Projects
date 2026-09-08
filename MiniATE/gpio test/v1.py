import serial
import time
import sys


# =====================================================
# CONFIGURATION
# =====================================================

PORT = "COM5"
BAUDRATE = 115200

DUT_READY_TIMEOUT = 5
TEST_TIMEOUT = 20

EXPECTED_TRANSACTIONS = 6


# =====================================================
# OPEN DUT
# =====================================================

try:

    dut = serial.Serial(
        PORT,
        BAUDRATE,
        timeout=0.5
    )

except Exception as e:

    print("ATE ERROR: Cannot open DUT")
    print(e)

    sys.exit()


time.sleep(2)


# =====================================================
# WAIT FOR DUT
# =====================================================

ready = False

start = time.time()

while (
    time.time() - start
    < DUT_READY_TIMEOUT
):

    line = dut.readline().decode(
        errors="ignore"
    ).strip()
    print("ESP32 ->", repr(line))

    if line == "DUT_READY":

        ready = True
        break


if not ready:

    print("ATE ERROR: DUT not ready")

    dut.close()

    sys.exit()


# =====================================================
# START GPIO TEST
# =====================================================

dut.write(
    b"RUN_GPIO_TEST\n"
)

dut.flush()


# =====================================================
# RECEIVE RESULTS
# =====================================================

results = []

start = time.time()

while (
    time.time() - start
    < TEST_TIMEOUT
):

    line = dut.readline().decode(
        errors="ignore"
    ).strip()


    if not line:
        continue


    # =================================================
    # GPIO RESULT
    # =================================================

    if line.startswith("GPIO_RESULT,"):

        fields = line.split(",")


        if len(fields) != 6:
            continue


        try:

            test_id = int(fields[1])

            output_pin = int(fields[2])

            input_pin = int(fields[3])

            expected = int(fields[4])

            actual = int(fields[5])

        except ValueError:

            continue


        # =================================================
        # PYTHON DECISION
        # =================================================

        if actual == expected:

            result = "PASS"

            reason = "LOGIC LEVEL MATCH"


        else:

            result = "FAIL"

            reason = (
                "OUTPUT/INPUT LOGIC MISMATCH"
            )


        results.append({

            "test_id":
                test_id,

            "output":
                output_pin,

            "input":
                input_pin,

            "expected":
                expected,

            "actual":
                actual,

            "result":
                result,

            "reason":
                reason
        })


    # =================================================
    # COMPLETE
    # =================================================

    elif (
        line ==
        "GPIO_TEST_COMPLETE"
    ):

        break


# =====================================================
# SUMMARY
# =====================================================

print()

print(
    "========== MINI ATE GPIO V1 =========="
)


for r in results:

    state = (
        "HIGH"
        if r["expected"] == 1
        else "LOW"
    )


    print(
        f"Test {r['test_id']} | "
        f"GPIO{r['output']} OUT -> "
        f"GPIO{r['input']} IN | "
        f"{state} | "
        f"{r['result']}"
    )


    if r["result"] == "FAIL":

        print(
            f"    Expected : "
            f"{r['expected']}"
        )

        print(
            f"    Actual   : "
            f"{r['actual']}"
        )

        print(
            f"    Reason   : "
            f"{r['reason']}"
        )


# =====================================================
# STATISTICS
# =====================================================

total = len(results)

passed = sum(
    1
    for r in results
    if r["result"] == "PASS"
)

failed = sum(
    1
    for r in results
    if r["result"] == "FAIL"
)


print()

print(
    "---------- TEST STATISTICS ----------"
)

print(
    f"Total : {total}"
)

print(
    f"PASS  : {passed}"
)

print(
    f"FAIL  : {failed}"
)


# =====================================================
# FINAL DECISION
# =====================================================

print()

print(
    "---------- FINAL RESULT -------------"
)


if (
    total == EXPECTED_TRANSACTIONS
    and failed == 0
):

    print(
        "Overall Result : PASS"
    )

elif total != EXPECTED_TRANSACTIONS:

    print(
        "Overall Result : FAIL"
    )

    print(
        "Diagnosis : "
        "Incomplete GPIO test execution"
    )

else:

    print(
        "Overall Result : FAIL"
    )

    print(
        "Diagnosis : "
        "One or more GPIO paths failed"
    )


# =====================================================
# CLOSE
# =====================================================

dut.close()