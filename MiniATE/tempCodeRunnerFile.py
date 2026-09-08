import serial
import time
import sys


# ==================================================
# MINI ATE CONFIGURATION
# ==================================================

PORT = "COM5"          # CHANGE THIS
BAUDRATE = 115200

DUT_READY_TIMEOUT = 5
TEST_TIMEOUT = 3

EXPECTED_TEST_1 = "MINIATE_UART_A"
EXPECTED_TEST_2 = "MINIATE_UART_B"


# ==================================================
# CONNECT TO DUT
# ==================================================

try:

    dut = serial.Serial(
        port=PORT,
        baudrate=BAUDRATE,
        timeout=0.2
    )

except serial.SerialException:
    print("FAIL")
    sys.exit()


# ESP32 may reset when serial port is opened
time.sleep(2)

# Remove old serial data
dut.reset_input_buffer()


# ==================================================
# WAIT FOR DUT_READY
# ==================================================

ready = False

start_time = time.time()

while time.time() - start_time < DUT_READY_TIMEOUT:

    line = dut.readline().decode(
        errors="ignore"
    ).strip()

    if line == "DUT_READY":
        ready = True
        break


# DUT didn't respond
if not ready:

    print("FAIL")

    dut.close()

    sys.exit()


# ==================================================
# SEND UART TEST COMMAND
# ==================================================

dut.write(b"RUN_UART_TEST\n")

dut.flush()


# ==================================================
# RECEIVE TEST RESULTS
# ==================================================

result1 = None
result2 = None
test_complete = False

start_time = time.time()

while time.time() - start_time < TEST_TIMEOUT:

    line = dut.readline().decode(
        errors="ignore"
    ).strip()

    if not line:
        continue


    # -------------------------------
    # TEST 1 RESULT
    # -------------------------------

    if line.startswith("UART_TEST_1:"):

        result1 = line[
            len("UART_TEST_1:")
        ]


    # -------------------------------
    # TEST 2 RESULT
    # -------------------------------

    elif line.startswith("UART_TEST_2:"):

        result2 = line[
            len("UART_TEST_2:")
        ]


    # -------------------------------
    # TEST COMPLETE
    # -------------------------------

    elif line == "UART_TEST_COMPLETE":

        test_complete = True
        break


# ==================================================
# PYTHON ATE DECISION
# ==================================================

test1_pass = (
    result1 == EXPECTED_TEST_1
)

test2_pass = (
    result2 == EXPECTED_TEST_2
)


# Both directions must pass
if test1_pass and test2_pass:
    print("PASS")
else:
    print("FAIL")


# ==================================================
# CLOSE DUT CONNECTION
# ==================================================

dut.close()