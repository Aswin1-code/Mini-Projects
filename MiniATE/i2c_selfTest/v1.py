import serial
import time
import sys


# =====================================================
# CONFIGURATION
# =====================================================

PORT = "COM5"
BAUDRATE = 115200

DUT_READY_TIMEOUT = 5
TEST_TIMEOUT = 5


# =====================================================
# OPEN DUT
# =====================================================

print("Opening DUT...")

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

print("Waiting for ESP32...")

ready = False

start = time.time()


while time.time() - start < DUT_READY_TIMEOUT:

    line = dut.readline().decode(
        errors="ignore"
    ).strip()

    if line:
        print(
            f"ESP32 -> '{line}'"
        )

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

print("Starting I2C self-test...")

dut.write(
    b"RUN_I2C_SELF_TEST\n"
)

dut.flush()


# =====================================================
# RECEIVE RESULT
# =====================================================

result = None

start = time.time()


while time.time() - start < TEST_TIMEOUT:

    line = dut.readline().decode(
        errors="ignore"
    ).strip()


    if not line:
        continue


    print(
        f"ESP32 -> '{line}'"
    )


    # -----------------------------------------------
    # RESULT
    # -----------------------------------------------

    if line.startswith(
        "I2C_SELF_RESULT,"
    ):

        fields = line.split(",")


        # Expected:
        #
        # I2C_SELF_RESULT,
        # controller,
        # SDA,
        # SCL,
        # frequency,
        # time
        #
        # Total = 6 fields

        if len(fields) != 6:

            print(
                "Invalid I2C result format"
            )

            continue


        try:

            controller_ok = int(
                fields[1]
            )

            sda_ok = int(
                fields[2]
            )

            scl_ok = int(
                fields[3]
            )

            frequency_ok = int(
                fields[4]
            )

            elapsed_us = int(
                fields[5]
            )

        except ValueError:

            print(
                "Invalid numeric result"
            )

            continue


        result = {

            "controller_ok":
                controller_ok,

            "sda_ok":
                sda_ok,

            "scl_ok":
                scl_ok,

            "frequency_ok":
                frequency_ok,

            "elapsed_us":
                elapsed_us
        }


    elif line == "I2C_SELF_TEST_COMPLETE":

        break


# =====================================================
# MINI ATE SUMMARY
# =====================================================

print()

print(
    "========== MINI ATE I2C V1 =========="
)


# =====================================================
# NO RESULT
# =====================================================

if result is None:

    print(
        "Overall Result : FAIL"
    )

    print(
        "Diagnosis : "
        "No valid I2C self-test result received"
    )

    dut.close()
    sys.exit()


# =====================================================
# INDIVIDUAL EVALUATION
# =====================================================

controller_status = (
    "PASS"
    if result["controller_ok"] == 1
    else "FAIL"
)


sda_status = (
    "PASS"
    if result["sda_ok"] == 1
    else "FAIL"
)


scl_status = (
    "PASS"
    if result["scl_ok"] == 1
    else "FAIL"
)


frequency_status = (
    "PASS"
    if result["frequency_ok"] == 1
    else "FAIL"
)


# =====================================================
# DISPLAY
# =====================================================

print(
    f"I2C Controller Init : "
    f"{controller_status}"
)

print(
    f"SDA Idle HIGH      : "
    f"{sda_status}"
)

print(
    f"SCL Idle HIGH      : "
    f"{scl_status}"
)

print(
    f"I2C Clock Config   : "
    f"{frequency_status}"
)

print(
    f"Test Execution Time: "
    f"{result['elapsed_us']} us"
)


# =====================================================
# FINAL DECISION
# =====================================================

if (
    controller_status == "PASS"
    and
    sda_status == "PASS"
    and
    scl_status == "PASS"
    and
    frequency_status == "PASS"
):

    overall = "PASS"

else:

    overall = "FAIL"


# =====================================================
# FINAL RESULT
# =====================================================

print()

print(
    "---------- FINAL RESULT -------------"
)

print(
    f"Overall Result : {overall}"
)


# =====================================================
# DIAGNOSIS
# =====================================================

if overall == "PASS":

    print(
        "Diagnosis : "
        "I2C controller initialized and "
        "SDA/SCL bus is in expected idle state"
    )

else:

    if controller_status == "FAIL":

        print(
            "Diagnosis : "
            "I2C controller initialization failed"
        )

    elif sda_status == "FAIL":

        print(
            "Diagnosis : "
            "SDA is not in expected idle HIGH state"
        )

    elif scl_status == "FAIL":

        print(
            "Diagnosis : "
            "SCL is not in expected idle HIGH state"
        )

    elif frequency_status == "FAIL":

        print(
            "Diagnosis : "
            "I2C clock configuration failed"
        )


# =====================================================
# CLOSE DUT
# =====================================================

dut.close()