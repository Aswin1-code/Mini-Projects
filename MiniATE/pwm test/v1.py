import serial
import time
import statistics


# ============================================================
# MINI ATE - PWM TEST EXECUTIVE V3
# ============================================================


# ------------------------------------------------------------
# Serial configuration
# ------------------------------------------------------------

COM_PORT = "COM5"       # <<< CHANGE THIS
BAUD_RATE = 115200

SERIAL_TIMEOUT = 1


# ------------------------------------------------------------
# Acceptance limits
# ------------------------------------------------------------

# Frequency tolerance:
# ±5%

FREQUENCY_TOLERANCE_PERCENT = 5.0


# Duty tolerance:
# ±2 percentage points
#
# Example:
# 10% -> 8% to 12%
# 50% -> 48% to 52%
# 90% -> 88% to 92%

DUTY_TOLERANCE_PERCENT = 2.0


# ------------------------------------------------------------
# Expected test configuration
# ------------------------------------------------------------

EXPECTED_FREQUENCIES = [
    500,
    1000,
    2000,
    5000
]

EXPECTED_DUTIES = [
    10,
    50,
    90
]

EXPECTED_REPETITIONS = 3

EXPECTED_PATHS = {
    1: ("GPIO18 OUT -> GPIO19 IN", 18, 19),
    2: ("GPIO4 OUT -> GPIO5 IN", 4, 5)
}


# ============================================================
# Helper functions
# ============================================================

def frequency_limits(target_frequency):
    tolerance = target_frequency * (
        FREQUENCY_TOLERANCE_PERCENT / 100.0
    )

    minimum = target_frequency - tolerance
    maximum = target_frequency + tolerance

    return minimum, maximum


def duty_limits(target_duty):
    minimum = target_duty - DUTY_TOLERANCE_PERCENT
    maximum = target_duty + DUTY_TOLERANCE_PERCENT

    return minimum, maximum


def check_frequency(target, measured):
    minimum, maximum = frequency_limits(target)

    return minimum <= measured <= maximum


def check_duty(target, measured):
    minimum, maximum = duty_limits(target)

    return minimum <= measured <= maximum


# ============================================================
# Failure diagnosis
# ============================================================

def diagnose_failure(
    target_frequency,
    target_duty,
    measured_frequency,
    measured_duty
):

    frequency_ok = check_frequency(
        target_frequency,
        measured_frequency
    )

    duty_ok = check_duty(
        target_duty,
        measured_duty
    )


    if frequency_ok and duty_ok:
        return "PASS"


    problems = []


    if not frequency_ok:

        minimum, maximum = frequency_limits(
            target_frequency
        )

        problems.append(
            f"Frequency outside acceptance limit "
            f"(allowed {minimum:.2f}-{maximum:.2f} Hz)"
        )


    if not duty_ok:

        minimum, maximum = duty_limits(
            target_duty
        )

        problems.append(
            f"Duty cycle outside acceptance limit "
            f"(allowed {minimum:.2f}-{maximum:.2f}%)"
        )


    return " + ".join(problems)


# ============================================================
# Parse PWM_RESULT
# ============================================================

def parse_pwm_result(line):

    parts = line.split(",")


    if len(parts) != 10:
        return None


    if parts[0] != "PWM_RESULT":
        return None


    try:

        result = {
            "test_number": int(parts[1]),
            "path_id": int(parts[2]),
            "target_frequency": int(parts[3]),
            "target_duty": float(parts[4]),
            "repetition": int(parts[5]),
            "high_time": int(parts[6]),
            "low_time": int(parts[7]),
            "measured_frequency": float(parts[8]),
            "measured_duty": float(parts[9])
        }

        return result

    except ValueError:
        return None


# ============================================================
# Open DUT
# ============================================================

print("Opening DUT...")


try:

    ser = serial.Serial(
        COM_PORT,
        BAUD_RATE,
        timeout=SERIAL_TIMEOUT
    )

except serial.SerialException as e:

    print()
    print("ERROR: Could not open serial port.")
    print(f"Port: {COM_PORT}")
    print(f"Reason: {e}")
    print()

    raise SystemExit


# ------------------------------------------------------------
# Give ESP32 time to reboot
# ------------------------------------------------------------

time.sleep(2)


# ------------------------------------------------------------
# Clear old serial data
# ------------------------------------------------------------

ser.reset_input_buffer()


print("Waiting for ESP32...")


# ============================================================
# Wait for DUT_READY
# ============================================================

dut_ready = False

start_time = time.time()


while time.time() - start_time < 15:

    line = ser.readline().decode(
        errors="ignore"
    ).strip()


    if not line:
        continue


    print(f"ESP32 -> '{line}'")


    if line == "DUT_READY":

        dut_ready = True
        break


if not dut_ready:

    print()
    print("ERROR: DUT_READY not received.")
    print("Check:")
    print("  1. COM port")
    print("  2. USB cable")
    print("  3. ESP32 firmware")
    print("  4. Serial baud rate")
    print()

    ser.close()

    raise SystemExit


# ============================================================
# Collect test results
# ============================================================

print("Starting PWM V3 test...")


results = []


test_start_time = time.time()


while True:

    if time.time() - test_start_time > 120:

        print()
        print("ERROR: Test timeout.")
        print()

        break


    line = ser.readline().decode(
        errors="ignore"
    ).strip()


    if not line:
        continue


    print(f"ESP32 -> '{line}'")


    # --------------------------------------------------------
    # PWM result
    # --------------------------------------------------------

    if line.startswith("PWM_RESULT"):

        result = parse_pwm_result(line)


        if result is None:

            print(
                "WARNING: Invalid PWM_RESULT received."
            )

            continue


        results.append(result)


        # ----------------------------------------------------
        # Determine PASS / FAIL
        # ----------------------------------------------------

        diagnosis = diagnose_failure(
            result["target_frequency"],
            result["target_duty"],
            result["measured_frequency"],
            result["measured_duty"]
        )


        status = (
            "PASS"
            if diagnosis == "PASS"
            else "FAIL"
        )


        path_name = EXPECTED_PATHS.get(
            result["path_id"],
            ("UNKNOWN PATH", 0, 0)
        )[0]


        print(
            f"Test {result['test_number']:02d} | "
            f"{path_name} | "
            f"{result['target_frequency']} Hz | "
            f"{result['target_duty']:.0f}% | "
            f"Rep {result['repetition']} | "
            f"{result['measured_frequency']:.2f} Hz | "
            f"{result['measured_duty']:.2f}% | "
            f"{status}"
        )


    # --------------------------------------------------------
    # Complete
    # --------------------------------------------------------

    elif line == "PWM_TEST_COMPLETE":

        break


# ============================================================
# Close serial
# ============================================================

ser.close()


# ============================================================
# Statistics
# ============================================================

print()
print("========== MINI ATE PWM V3 ==========")
print()


# ------------------------------------------------------------
# PASS / FAIL counts
# ------------------------------------------------------------

pass_count = 0
fail_count = 0


for result in results:

    diagnosis = diagnose_failure(
        result["target_frequency"],
        result["target_duty"],
        result["measured_frequency"],
        result["measured_duty"]
    )


    if diagnosis == "PASS":
        pass_count += 1

    else:
        fail_count += 1


total_tests = len(results)


if total_tests > 0:

    pass_rate = (
        pass_count / total_tests
    ) * 100.0

else:

    pass_rate = 0.0


# ============================================================
# PATH STATISTICS
# ============================================================

print("---------- PATH STATISTICS ----------")


for path_id, path_info in EXPECTED_PATHS.items():

    path_name = path_info[0]


    path_results = [
        r for r in results
        if r["path_id"] == path_id
    ]


    path_pass = 0
    path_fail = 0


    for r in path_results:

        diagnosis = diagnose_failure(
            r["target_frequency"],
            r["target_duty"],
            r["measured_frequency"],
            r["measured_duty"]
        )


        if diagnosis == "PASS":
            path_pass += 1

        else:
            path_fail += 1


    print(
        f"{path_name} | "
        f"Total: {len(path_results)} | "
        f"PASS: {path_pass} | "
        f"FAIL: {path_fail}"
    )


# ============================================================
# FREQUENCY STATISTICS
# ============================================================

print()
print("---------- FREQUENCY STATISTICS ----------")


for frequency in EXPECTED_FREQUENCIES:

    frequency_results = [
        r for r in results
        if r["target_frequency"] == frequency
    ]


    measured_values = [
        r["measured_frequency"]
        for r in frequency_results
    ]


    if measured_values:

        minimum = min(measured_values)
        maximum = max(measured_values)
        average = statistics.mean(measured_values)


        print(
            f"{frequency} Hz | "
            f"Min: {minimum:.2f} | "
            f"Max: {maximum:.2f} | "
            f"Avg: {average:.2f}"
        )


# ============================================================
# DUTY STATISTICS
# ============================================================

print()
print("---------- DUTY STATISTICS ----------")


for duty in EXPECTED_DUTIES:

    duty_results = [
        r for r in results
        if r["target_duty"] == duty
    ]


    measured_values = [
        r["measured_duty"]
        for r in duty_results
    ]


    if measured_values:

        minimum = min(measured_values)
        maximum = max(measured_values)
        average = statistics.mean(measured_values)


        print(
            f"{duty}% | "
            f"Min: {minimum:.2f} | "
            f"Max: {maximum:.2f} | "
            f"Avg: {average:.2f}"
        )


# ============================================================
# TEST STATISTICS
# ============================================================

print()
print("---------- TEST STATISTICS ----------")

print(f"Total Tests : {total_tests}")
print(f"PASS        : {pass_count}")
print(f"FAIL        : {fail_count}")
print(f"Pass Rate   : {pass_rate:.2f}%")


# ============================================================
# FAILURE DIAGNOSIS
# ============================================================

print()
print("---------- FAILURE DIAGNOSIS ----------")


failure_exists = False


for result in results:

    diagnosis = diagnose_failure(
        result["target_frequency"],
        result["target_duty"],
        result["measured_frequency"],
        result["measured_duty"]
    )


    if diagnosis != "PASS":

        failure_exists = True


        path_name = EXPECTED_PATHS.get(
            result["path_id"],
            ("UNKNOWN PATH", 0, 0)
        )[0]


        print(
            f"Test {result['test_number']} | "
            f"{path_name} | "
            f"{result['target_frequency']} Hz | "
            f"{result['target_duty']:.0f}%"
        )


        print(
            f"  Measured Frequency : "
            f"{result['measured_frequency']:.2f} Hz"
        )


        print(
            f"  Measured Duty      : "
            f"{result['measured_duty']:.2f}%"
        )


        print(
            f"  High Time          : "
            f"{result['high_time']} us"
        )


        print(
            f"  Low Time           : "
            f"{result['low_time']} us"
        )


        print(
            f"  Diagnosis          : "
            f"{diagnosis}"
        )


# ============================================================
# FINAL RESULT
# ============================================================

print()
print("---------- FINAL RESULT -------------")


expected_tests = (
    len(EXPECTED_PATHS)
    * len(EXPECTED_FREQUENCIES)
    * len(EXPECTED_DUTIES)
    * EXPECTED_REPETITIONS
)


if total_tests != expected_tests:

    print("Overall Result : FAIL")

    print(
        f"Diagnosis : Expected {expected_tests} "
        f"tests but received {total_tests}."
    )


elif fail_count == 0:

    print("Overall Result : PASS")

    print(
        "Diagnosis : All PWM conditions "
        "passed the acceptance criteria."
    )


else:

    print("Overall Result : FAIL")

    print(
        "Diagnosis : One or more PWM conditions "
        "failed the acceptance criteria."
    )


print()