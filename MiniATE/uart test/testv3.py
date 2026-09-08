import serial
import time
import sys


# =====================================================
# MINI ATE - UART V3
# =====================================================

PORT = "COM5"
BAUDRATE = 115200

DUT_READY_TIMEOUT = 5
TEST_TIMEOUT = 180

EXPECTED_TRANSACTIONS = 24   ##-----------repetition count ( min - 24)


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
# WAIT FOR DUT_READY
# =====================================================

ready = False

start = time.time()

while (
    time.time() - start
    <
    DUT_READY_TIMEOUT
):

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

dut.write(
    b"RUN_UART_TEST\n"
)

dut.flush()


# =====================================================
# RECEIVE RESULTS
# =====================================================

results = []

start = time.time()

while (
    time.time() - start
    <
    TEST_TIMEOUT
):

    line = dut.readline().decode(
        errors="ignore"
    ).strip()


    if not line:
        continue


    # =================================================
    # RESULT
    # =================================================

    if line.startswith("RESULT,"):

        fields = line.split(",")


        # RESULT
        # UART
        # TEST_ID
        # TX
        # RX
        # PATTERN
        # REPETITION
        # EXPECTED_LENGTH
        # RECEIVED_LENGTH
        # TIME
        # EXPECTED
        # ACTUAL

        if len(fields) != 12:
            continue


        try:

            uart_number = int(fields[1])

            test_id = int(fields[2])

            tx_pin = int(fields[3])

            rx_pin = int(fields[4])

            pattern = fields[5]

            repetition = int(fields[6])

            expected_length = int(fields[7])

            received_length = int(fields[8])

            transfer_time = int(fields[9])

            expected_hex = fields[10]

            actual_hex = fields[11]


        except ValueError:

            continue


        # =================================================
        # PYTHON VALIDATION
        # =================================================

        if received_length == 0:

            result = "FAIL"

            reason = "RX TIMEOUT"


        elif (
            received_length
            !=
            expected_length
        ):

            result = "FAIL"

            reason = "INCOMPLETE DATA"


        elif (
            actual_hex.upper()
            !=
            expected_hex.upper()
        ):

            result = "FAIL"

            reason = (
                "DATA CORRUPTION / MISMATCH"
            )


        else:

            result = "PASS"

            reason = "DATA MATCH"


        # =================================================
        # STORE RESULT
        # =================================================

        results.append({

            "uart":
                uart_number,

            "test_id":
                test_id,

            "tx":
                tx_pin,

            "rx":
                rx_pin,

            "pattern":
                pattern,

            "repetition":
                repetition,

            "expected_length":
                expected_length,

            "received_length":
                received_length,

            "time_us":
                transfer_time,

            "expected":
                expected_hex,

            "actual":
                actual_hex,

            "result":
                result,

            "reason":
                reason
        })


    # =================================================
    # TEST COMPLETE
    # =================================================

    elif (
        line ==
        "UART_TEST_COMPLETE"
    ):

        break


# =====================================================
# SUMMARY
# =====================================================

print()

print(
    "========== MINI ATE UART V3 =========="
)


# =====================================================
# INDIVIDUAL RESULTS
# =====================================================

for r in results:

    direction = (
        f"GPIO{r['tx']} TX -> "
        f"GPIO{r['rx']} RX"
    )


    print(
        f"UART{r['uart']} | "
        f"Test {r['test_id']:03d} | "
        f"{direction} | "
        f"{r['pattern']:5s} | "
        f"Rep {r['repetition']} | "
        f"{r['result']} | "
        f"{r['time_us']} us"
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

timeouts = sum(
    1
    for r in results
    if r["reason"] == "RX TIMEOUT"
)

mismatches = sum(
    1
    for r in results
    if r["reason"]
    == "DATA CORRUPTION / MISMATCH"
)

incomplete = sum(
    1
    for r in results
    if r["reason"]
    == "INCOMPLETE DATA"
)


# =====================================================
# TIMING STATISTICS
# =====================================================

if results:

    times = [
        r["time_us"]
        for r in results
    ]

    minimum_time = min(times)

    maximum_time = max(times)

    average_time = (
        sum(times) / len(times)
    )

else:

    minimum_time = 0
    maximum_time = 0
    average_time = 0


# =====================================================
# UART STATISTICS
# =====================================================

uart1_results = [
    r for r in results
    if r["uart"] == 1
]

uart2_results = [
    r for r in results
    if r["uart"] == 2
]


def uart_summary(
    uart_name,
    data
):

    if not data:

        print(
            f"{uart_name}: NO DATA"
        )

        return


    passed_count = sum(
        1
        for r in data
        if r["result"] == "PASS"
    )

    failed_count = (
        len(data)
        -
        passed_count
    )


    print(
        f"{uart_name}: "
        f"{passed_count}/{len(data)} PASS, "
        f"{failed_count} FAIL"
    )


# =====================================================
# DIRECTION STATISTICS
# =====================================================

direction_17_16 = [
    r for r in results
    if r["tx"] == 17
    and r["rx"] == 16
]

direction_16_17 = [
    r for r in results
    if r["tx"] == 16
    and r["rx"] == 17
]

direction_14_12 = [
    r for r in results
    if r["tx"] == 14
    and r["rx"] == 12
]

direction_12_14 = [
    r for r in results
    if r["tx"] == 12
    and r["rx"] == 14
]


def direction_summary(
    name,
    data
):

    if not data:

        print(
            f"{name}: NO DATA"
        )

        return


    passed_count = sum(
        1
        for r in data
        if r["result"] == "PASS"
    )

    failed_count = (
        len(data)
        -
        passed_count
    )


    print(
        f"{name}: "
        f"{passed_count}/{len(data)} PASS, "
        f"{failed_count} FAIL"
    )


# =====================================================
# PRINT STATISTICS
# =====================================================

print()

print(
    "---------- TEST STATISTICS ----------"
)

print(
    f"Total transactions : "
    f"{total}"
)

print(
    f"Passed             : "
    f"{passed}"
)

print(
    f"Failed             : "
    f"{failed}"
)

print(
    f"Timeouts           : "
    f"{timeouts}"
)

print(
    f"Data mismatches    : "
    f"{mismatches}"
)

print(
    f"Incomplete data    : "
    f"{incomplete}"
)


print()

print(
    "---------- TRANSFER TIMING ----------"
)

print(
    f"Minimum : "
    f"{minimum_time:.0f} us"
)

print(
    f"Maximum : "
    f"{maximum_time:.0f} us"
)

print(
    f"Average : "
    f"{average_time:.2f} us"
)


print()

print(
    "---------- UART SUMMARY -------------"
)

uart_summary(
    "UART1 (GPIO14/12)",
    uart1_results
)

uart_summary(
    "UART2 (GPIO17/16)",
    uart2_results
)


print()

print(
    "---------- DIRECTION SUMMARY --------"
)

direction_summary(
    "GPIO17 TX -> GPIO16 RX",
    direction_17_16
)

direction_summary(
    "GPIO16 TX -> GPIO17 RX",
    direction_16_17
)

direction_summary(
    "GPIO14 TX -> GPIO12 RX",
    direction_14_12
)

direction_summary(
    "GPIO12 TX -> GPIO14 RX",
    direction_12_14
)


# =====================================================
# FINAL ATE DECISION
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
        "Incomplete test execution"
    )

else:

    print(
        "Overall Result : FAIL"
    )

    print(
        "Diagnosis : "
        "One or more UART transactions failed"
    )


# =====================================================
# CLOSE DUT
# =====================================================

dut.close()