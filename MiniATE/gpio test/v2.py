import serial
import time
import sys


# =====================================================
# CONFIGURATION
# =====================================================

PORT = "COM5"
BAUDRATE = 115200

DUT_READY_TIMEOUT = 5
TEST_TIMEOUT = 30

EXPECTED_TRANSACTIONS = 36


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


    if line == "DUT_READY":

        ready = True
        break


if not ready:

    print(
        "ATE ERROR: DUT not ready"
    )

    dut.close()

    sys.exit()


# =====================================================
# START TEST
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

    if line.startswith(
        "GPIO_RESULT,"
    ):

        fields = line.split(",")


        # GPIO_RESULT
        # TEST_ID
        # OUTPUT
        # INPUT
        # EXPECTED
        # ACTUAL
        # REPETITION
        # TIME_US

        if len(fields) != 8:
            continue


        try:

            test_id = int(
                fields[1]
            )

            output_pin = int(
                fields[2]
            )

            input_pin = int(
                fields[3]
            )

            expected = fields[4]

            actual = fields[5]

            repetition = int(
                fields[6]
            )

            execution_time = int(
                fields[7]
            )

        except ValueError:

            continue


        # =================================================
        # PYTHON DECISION
        # =================================================

        if actual == expected:

            result = "PASS"

        else:

            result = "FAIL"


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

            "repetition":
                repetition,

            "time":
                execution_time,

            "result":
                result
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
# PRINT DETAILED RESULTS
# =====================================================

print()

print(
    "========== MINI ATE GPIO V3 =========="
)


for r in results:

    print(
        f"Test {r['test_id']:02d} | "
        f"GPIO{r['output']} OUT -> "
        f"GPIO{r['input']} IN | "
        f"{r['expected']} | "
        f"Rep {r['repetition']} | "
        f"{r['time']} us | "
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


# =====================================================
# TIMING STATISTICS
# =====================================================

if results:

    times = [
        r["time"]
        for r in results
    ]

    min_time = min(times)

    max_time = max(times)

    avg_time = sum(times) / len(times)

else:

    min_time = 0
    max_time = 0
    avg_time = 0


# =====================================================
# PATH STATISTICS
# =====================================================

paths = {}

for r in results:

    path = (
        f"GPIO{r['output']}"
        f" -> "
        f"GPIO{r['input']}"
    )

    if path not in paths:

        paths[path] = {
            "total": 0,
            "pass": 0,
            "fail": 0
        }


    paths[path]["total"] += 1


    if r["result"] == "PASS":

        paths[path]["pass"] += 1

    else:

        paths[path]["fail"] += 1


# =====================================================
# SUMMARY
# =====================================================

print()

print(
    "---------- PATH STATISTICS ----------"
)


for path, data in paths.items():

    print(
        f"{path} | "
        f"Total: {data['total']} | "
        f"PASS: {data['pass']} | "
        f"FAIL: {data['fail']}"
    )


# =====================================================
# TEST STATISTICS
# =====================================================

print()

print(
    "---------- TEST STATISTICS ----------"
)

print(
    f"Total Tests : {total}"
)

print(
    f"PASS        : {passed}"
)

print(
    f"FAIL        : {failed}"
)


if total > 0:

    pass_rate = (
        passed / total
    ) * 100

else:

    pass_rate = 0


print(
    f"Pass Rate   : "
    f"{pass_rate:.2f}%"
)


# =====================================================
# TIMING
# =====================================================

print()

print(
    "---------- TIMING STATISTICS --------"
)

print(
    f"Minimum     : {min_time} us"
)

print(
    f"Maximum     : {max_time} us"
)

print(
    f"Average     : {avg_time:.2f} us"
)


# =====================================================
# FINAL RESULT
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

else:

    print(
        "Overall Result : FAIL"
    )


    if total != EXPECTED_TRANSACTIONS:

        print(
            "Diagnosis : "
            "Incomplete GPIO test execution"
        )

    else:

        print(
            "Diagnosis : "
            "One or more GPIO tests failed"
        )


# =====================================================
# CLOSE
# =====================================================

dut.close()