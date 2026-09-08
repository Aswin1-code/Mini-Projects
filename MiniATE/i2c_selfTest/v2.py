import serial
import time

# =====================================================
# CONFIGURATION
# =====================================================

PORT = "COM5"       # CHANGE THIS
BAUDRATE = 115200

COMMAND = "RUN_I2C_V2"

# =====================================================
# OPEN DUT
# =====================================================

print("Opening DUT...")

ser = serial.Serial(
    PORT,
    BAUDRATE,
    timeout=1
)

# Opening serial can reset ESP32
time.sleep(2)

print("Waiting for ESP32...")

# =====================================================
# WAIT FOR DUT_READY
# =====================================================

ready = False

start_wait = time.time()

while time.time() - start_wait < 5:

    line = ser.readline().decode(
        errors="ignore"
    ).strip()

    if line:

        print(f"ESP32 -> '{line}'")

        if line == "DUT_READY":
            ready = True
            break


if not ready:

    print("DUT_READY not received")

    ser.close()

    raise SystemExit


# =====================================================
# START TEST
# =====================================================

print("Starting I2C V2 self-test...")

ser.write((COMMAND + "\n").encode())

# =====================================================
# RECEIVE RESULT
# =====================================================

result = None

start_wait = time.time()

while time.time() - start_wait < 5:

    line = ser.readline().decode(
        errors="ignore"
    ).strip()

    if line:

        print(f"ESP32 -> '{line}'")

        if line.startswith("I2C_V2_RESULT"):

            result = line

        if line == "I2C_V2_TEST_COMPLETE":

            break


ser.close()


# =====================================================
# VALIDATE RESULT
# =====================================================

if result is None:

    print("\n========== MINI ATE I2C V2 ==========")

    print("Overall Result : FAIL")
    print("Diagnosis : No valid I2C V2 result received")

    raise SystemExit


# =====================================================
# PARSE RESULT
# =====================================================

try:

    parts = result.split(",")

    # Format:
    #
    # I2C_V2_RESULT,
    # controller,
    # SDA,
    # SCL,
    # transaction,
    # expectedNACK,
    # errorCode,
    # time

    controller_ok = int(parts[1])
    sda_ok = int(parts[2])
    scl_ok = int(parts[3])
    transaction_ok = int(parts[4])
    nack_ok = int(parts[5])
    error_code = int(parts[6])
    transaction_time = int(parts[7])

except (ValueError, IndexError):

    print("\n========== MINI ATE I2C V2 ==========")

    print("Overall Result : FAIL")
    print("Diagnosis : Invalid I2C result format")

    raise SystemExit


# =====================================================
# INDIVIDUAL TEST DECISIONS
# =====================================================

test_controller = controller_ok == 1

test_sda = sda_ok == 1

test_scl = scl_ok == 1

test_transaction = transaction_ok == 1

test_nack = nack_ok == 1


# =====================================================
# OVERALL DECISION
# =====================================================

overall_pass = (
    test_controller
    and test_sda
    and test_scl
    and test_transaction
    and test_nack
)


# =====================================================
# DIAGNOSIS
# =====================================================

if not test_controller:

    diagnosis = "I2C controller initialization failed"

elif not test_sda:

    diagnosis = "SDA line is not in expected idle HIGH state"

elif not test_scl:

    diagnosis = "SCL line is not in expected idle HIGH state"

elif not test_transaction:

    diagnosis = "I2C transaction was not executed"

elif not test_nack:

    diagnosis = (
        f"Unexpected I2C response; "
        f"error code = {error_code}"
    )

else:

    diagnosis = (
        "I2C controller generated transaction "
        "and expected NACK was detected with no slave connected"
    )


# =====================================================
# FINAL REPORT
# =====================================================

print()
print("========== MINI ATE I2C V2 ==========")

print(
    f"I2C Controller Init : "
    f"{'PASS' if test_controller else 'FAIL'}"
)

print(
    f"SDA Idle HIGH      : "
    f"{'PASS' if test_sda else 'FAIL'}"
)

print(
    f"SCL Idle HIGH      : "
    f"{'PASS' if test_scl else 'FAIL'}"
)

print(
    f"I2C Transaction    : "
    f"{'PASS' if test_transaction else 'FAIL'}"
)

print(
    f"Expected NACK      : "
    f"{'PASS' if test_nack else 'FAIL'}"
)

print(
    f"Error Code         : {error_code}"
)

print(
    f"Transaction Time   : {transaction_time} us"
)

print()
print("---------- FINAL RESULT -------------")

print(
    f"Overall Result : "
    f"{'PASS' if overall_pass else 'FAIL'}"
)

print(f"Diagnosis : {diagnosis}")