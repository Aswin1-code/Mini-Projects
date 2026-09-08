"""
============================================================
 MINI ATE - CORE ENGINE
============================================================

This module is the validated "ATE engine": serial connection
handling, per-peripheral result parsers, validators, and
statistics calculators.

It intentionally contains NO Streamlit code and NO console
printing. It is a refactor of the original terminal
mini_ate_controller.py into pure, reusable functions so a GUI
(or any other frontend) can call it without duplicating the
test logic, parsing logic, validation logic, or acceptance
limits.

Architecture:

    UI (Streamlit)
         v
    ATE Controller (this module: open_dut / MODULES / run loop
                     driven from the UI, since the UI owns the
                     live display while reading the serial
                     stream)
         v
    Serial Interface (pyserial)
         v
    ESP32 DUT
         v
    Result Parser (parse_*_result)
         v
    Validator (validate_*_result)
         v
    Result Storage (caller-owned lists, e.g. Streamlit
                     session_state)
         v
    Statistics / Report (compute_*_stats, compute_final_report)

Nothing about acceptance limits, parsing, or validation was
changed from the original terminal controller - only the
printing was replaced with structured return values, and the
blocking waits were made non-exiting (return status instead of
sys.exit()) so a GUI can recover gracefully.

Adding a future peripheral (ADC, I2C, SPI, ...) means adding:
  - a parse_xxx_result() function
  - a validate_xxx_result() function
  - a compute_xxx_stats() function
  - one more entry in MODULES / MODULE_ORDER
No existing module needs to change.
============================================================
"""

import time
import statistics
import serial


# ============================================================
# SERIAL CONNECTION HELPERS
# ============================================================

def open_dut(port, baudrate, serial_timeout=0.5):
    """
    Opens the serial connection to the DUT.
    Raises serial.SerialException (or OSError) on failure -
    the caller (GUI) is responsible for catching it and
    displaying a friendly message.
    """
    dut = serial.Serial(port, baudrate, timeout=serial_timeout)
    time.sleep(2)  # allow ESP32 to reboot after DTR toggle
    dut.reset_input_buffer()
    return dut


def close_dut(dut):
    try:
        if dut is not None and dut.is_open:
            dut.close()
    except Exception:
        pass


def wait_for_dut_ready(dut, timeout=5):
    """
    Waits for the "DUT_READY" line.
    Returns (ready: bool, boot_lines: list[str])
    boot_lines contains every line seen while waiting (e.g. ESP32
    boot/reset banners) so the caller can log them without
    treating them as test failures.
    """
    boot_lines = []
    ready = False
    start = time.time()

    while time.time() - start < timeout:
        line = dut.readline().decode(errors="ignore").strip()

        if not line:
            continue

        boot_lines.append(line)

        if line == "DUT_READY":
            ready = True
            break

    return ready, boot_lines


# ============================================================
# GPIO MODULE
# ============================================================

GPIO_EXPECTED_TRANSACTIONS = 36
GPIO_TEST_TIMEOUT = 30


def parse_gpio_result(line):
    fields = line.split(",")

    # GPIO_RESULT,TEST_ID,OUTPUT,INPUT,EXPECTED,ACTUAL,REPETITION,TIME_US
    if len(fields) != 8:
        return None

    try:
        return {
            "test_id": int(fields[1]),
            "output": int(fields[2]),
            "input": int(fields[3]),
            "expected": fields[4],
            "actual": fields[5],
            "repetition": int(fields[6]),
            "time": int(fields[7]),
        }
    except ValueError:
        return None


def validate_gpio_result(r):
    r["result"] = "PASS" if r["actual"] == r["expected"] else "FAIL"
    return r


def compute_gpio_stats(results):
    total = len(results)
    passed = sum(1 for r in results if r["result"] == "PASS")
    failed = total - passed
    pass_rate = (passed / total * 100) if total else 0.0

    times = [r["time"] for r in results]
    timing = {
        "min": min(times) if times else 0,
        "max": max(times) if times else 0,
        "avg": (sum(times) / len(times)) if times else 0,
    }

    paths = {}
    for r in results:
        key = (r["output"], r["input"])
        entry = paths.setdefault(key, {"total": 0, "pass": 0, "fail": 0})
        entry["total"] += 1
        entry["pass" if r["result"] == "PASS" else "fail"] += 1

    path_stats = [
        {
            "path": f"GPIO{out} -> GPIO{inp}",
            "total": d["total"],
            "pass": d["pass"],
            "fail": d["fail"],
        }
        for (out, inp), d in paths.items()
    ]

    complete = total == GPIO_EXPECTED_TRANSACTIONS
    module_pass = complete and failed == 0

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "timing": timing,
        "paths": path_stats,
        "complete": complete,
        "expected": GPIO_EXPECTED_TRANSACTIONS,
        "module_pass": module_pass,
    }


# ============================================================
# UART MODULE
# ============================================================

UART_EXPECTED_TRANSACTIONS = 24
UART_TEST_TIMEOUT = 180


def parse_uart_result(line):
    fields = line.split(",")

    # RESULT,UART,TEST_ID,TX,RX,PATTERN,REP,EXP_LEN,RECV_LEN,TIME,EXP_HEX,ACT_HEX
    if len(fields) != 12:
        return None

    try:
        return {
            "uart": int(fields[1]),
            "test_id": int(fields[2]),
            "tx": int(fields[3]),
            "rx": int(fields[4]),
            "pattern": fields[5],
            "repetition": int(fields[6]),
            "expected_length": int(fields[7]),
            "received_length": int(fields[8]),
            "time_us": int(fields[9]),
            "expected": fields[10],
            "actual": fields[11],
        }
    except ValueError:
        return None


def validate_uart_result(r):
    if r["received_length"] == 0:
        result, reason = "FAIL", "RX TIMEOUT"
    elif r["received_length"] != r["expected_length"]:
        result, reason = "FAIL", "INCOMPLETE DATA"
    elif r["actual"].upper() != r["expected"].upper():
        result, reason = "FAIL", "DATA CORRUPTION / MISMATCH"
    else:
        result, reason = "PASS", "DATA MATCH"

    r["result"] = result
    r["reason"] = reason
    return r


def compute_uart_stats(results):
    total = len(results)
    passed = sum(1 for r in results if r["result"] == "PASS")
    failed = total - passed
    pass_rate = (passed / total * 100) if total else 0.0

    times = [r["time_us"] for r in results]
    timing = {
        "min": min(times) if times else 0,
        "max": max(times) if times else 0,
        "avg": (sum(times) / len(times)) if times else 0,
    }

    reasons = {
        "RX TIMEOUT": sum(1 for r in results if r["reason"] == "RX TIMEOUT"),
        "INCOMPLETE DATA": sum(1 for r in results if r["reason"] == "INCOMPLETE DATA"),
        "DATA CORRUPTION / MISMATCH": sum(1 for r in results if r["reason"] == "DATA CORRUPTION / MISMATCH"),
        "DATA MATCH": sum(1 for r in results if r["reason"] == "DATA MATCH"),
    }

    def summarize(data):
        p = sum(1 for r in data if r["result"] == "PASS")
        return {"total": len(data), "pass": p, "fail": len(data) - p}

    uart_summary = [
        {"uart": 1, **summarize([r for r in results if r["uart"] == 1])},
        {"uart": 2, **summarize([r for r in results if r["uart"] == 2])},
    ]

    directions = {}
    for r in results:
        key = (r["tx"], r["rx"])
        directions.setdefault(key, []).append(r)

    direction_summary = [
        {
            "direction": f"GPIO{tx} TX -> GPIO{rx} RX",
            **summarize(data),
        }
        for (tx, rx), data in directions.items()
    ]

    complete = total == UART_EXPECTED_TRANSACTIONS
    module_pass = complete and failed == 0

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "timing": timing,
        "reasons": reasons,
        "uart_summary": uart_summary,
        "direction_summary": direction_summary,
        "complete": complete,
        "expected": UART_EXPECTED_TRANSACTIONS,
        "module_pass": module_pass,
    }


# ============================================================
# PWM MODULE
# ============================================================

FREQUENCY_TOLERANCE_PERCENT = 5.0
DUTY_TOLERANCE_PERCENT = 2.0

PWM_EXPECTED_FREQUENCIES = [500, 1000, 2000, 5000]
PWM_EXPECTED_DUTIES = [10, 50, 90]
PWM_EXPECTED_REPETITIONS = 3

# Result lines only carry a path_id, not raw pin numbers, so the
# pin mapping (fixed by the firmware) is kept here for display.
PWM_EXPECTED_PATHS = {
    1: ("GPIO18 OUT -> GPIO19 IN", 18, 19),
    2: ("GPIO4 OUT -> GPIO5 IN", 4, 5),
}

PWM_EXPECTED_TESTS = (
    len(PWM_EXPECTED_PATHS)
    * len(PWM_EXPECTED_FREQUENCIES)
    * len(PWM_EXPECTED_DUTIES)
    * PWM_EXPECTED_REPETITIONS
)

PWM_TEST_TIMEOUT = 120


def frequency_limits(target):
    tol = target * (FREQUENCY_TOLERANCE_PERCENT / 100.0)
    return target - tol, target + tol


def duty_limits(target):
    return target - DUTY_TOLERANCE_PERCENT, target + DUTY_TOLERANCE_PERCENT


def check_frequency(target, measured):
    lo, hi = frequency_limits(target)
    return lo <= measured <= hi


def check_duty(target, measured):
    lo, hi = duty_limits(target)
    return lo <= measured <= hi


def diagnose_pwm_failure(target_frequency, target_duty, measured_frequency, measured_duty):
    """
    Returns "PASS" or a description of which acceptance limit(s)
    were exceeded. This is a TEST-RESULT indication (an
    acceptance-limit breach), not a confirmed root-cause
    determination that the DUT hardware is defective.
    """
    freq_ok = check_frequency(target_frequency, measured_frequency)
    duty_ok = check_duty(target_duty, measured_duty)

    if freq_ok and duty_ok:
        return "PASS"

    problems = []

    if not freq_ok:
        lo, hi = frequency_limits(target_frequency)
        problems.append(
            f"Frequency outside acceptance limit (allowed {lo:.2f}-{hi:.2f} Hz) "
            f"- possible indication: PWM frequency generation/configuration issue"
        )

    if not duty_ok:
        lo, hi = duty_limits(target_duty)
        problems.append(
            f"Duty cycle outside acceptance limit (allowed {lo:.2f}-{hi:.2f}%) "
            f"- possible indication: PWM duty cycle generation issue"
        )

    return " + ".join(problems)


def parse_pwm_result(line):
    fields = line.split(",")

    if len(fields) != 10:
        return None
    if fields[0] != "PWM_RESULT":
        return None

    try:
        return {
            "test_number": int(fields[1]),
            "path_id": int(fields[2]),
            "target_frequency": int(fields[3]),
            "target_duty": float(fields[4]),
            "repetition": int(fields[5]),
            "high_time": int(fields[6]),
            "low_time": int(fields[7]),
            "measured_frequency": float(fields[8]),
            "measured_duty": float(fields[9]),
        }
    except ValueError:
        return None


def validate_pwm_result(r):
    diagnosis = diagnose_pwm_failure(
        r["target_frequency"], r["target_duty"],
        r["measured_frequency"], r["measured_duty"]
    )
    r["result"] = "PASS" if diagnosis == "PASS" else "FAIL"
    r["diagnosis"] = diagnosis
    return r


def compute_pwm_stats(results):
    total = len(results)
    passed = sum(1 for r in results if r["result"] == "PASS")
    failed = total - passed
    pass_rate = (passed / total * 100) if total else 0.0

    path_stats = []
    for path_id, (name, _out, _in) in PWM_EXPECTED_PATHS.items():
        data = [r for r in results if r["path_id"] == path_id]
        p = sum(1 for r in data if r["result"] == "PASS")
        path_stats.append({
            "path_id": path_id,
            "name": name,
            "total": len(data),
            "pass": p,
            "fail": len(data) - p,
        })

    frequency_stats = []
    seen_freqs = sorted(set(r["target_frequency"] for r in results)) or PWM_EXPECTED_FREQUENCIES
    for freq in seen_freqs:
        vals = [r["measured_frequency"] for r in results if r["target_frequency"] == freq]
        if vals:
            frequency_stats.append({
                "frequency": freq,
                "min": min(vals),
                "max": max(vals),
                "avg": statistics.mean(vals),
            })

    duty_stats = []
    seen_duties = sorted(set(r["target_duty"] for r in results)) or PWM_EXPECTED_DUTIES
    for duty in seen_duties:
        vals = [r["measured_duty"] for r in results if r["target_duty"] == duty]
        if vals:
            duty_stats.append({
                "duty": duty,
                "min": min(vals),
                "max": max(vals),
                "avg": statistics.mean(vals),
            })

    complete = total == PWM_EXPECTED_TESTS
    module_pass = complete and failed == 0

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "path_stats": path_stats,
        "frequency_stats": frequency_stats,
        "duty_stats": duty_stats,
        "complete": complete,
        "expected": PWM_EXPECTED_TESTS,
        "module_pass": module_pass,
    }


# ============================================================
# MODULE-DRIVEN CONFIGURATION
#
# Everything the UI needs to run a peripheral test generically.
# Adding ADC/I2C/SPI later = one more entry here.
# ============================================================

MODULES = {
    "GPIO": {
        "command": b"RUN_GPIO\n",
        "result_prefix": "GPIO_RESULT,",
        "complete_marker": "GPIO_TEST_COMPLETE",
        "timeout": GPIO_TEST_TIMEOUT,
        "expected": GPIO_EXPECTED_TRANSACTIONS,
        "parse": parse_gpio_result,
        "validate": validate_gpio_result,
        "compute_stats": compute_gpio_stats,
    },
    "UART": {
        "command": b"RUN_UART\n",
        "result_prefix": "RESULT,",
        "complete_marker": "UART_TEST_COMPLETE",
        "timeout": UART_TEST_TIMEOUT,
        "expected": UART_EXPECTED_TRANSACTIONS,
        "parse": parse_uart_result,
        "validate": validate_uart_result,
        "compute_stats": compute_uart_stats,
    },
    "PWM": {
        "command": b"RUN_PWM\n",
        "result_prefix": "PWM_RESULT,",
        "complete_marker": "PWM_TEST_COMPLETE",
        "timeout": PWM_TEST_TIMEOUT,
        "expected": PWM_EXPECTED_TESTS,
        "parse": parse_pwm_result,
        "validate": validate_pwm_result,
        "compute_stats": compute_pwm_stats,
    },
}

# Must match the order the ESP32 firmware executes under RUN_ALL.
MODULE_ORDER = ["GPIO", "UART", "PWM"]


# ============================================================
# FINAL COMBINED ATE REPORT
# ============================================================

def compute_final_report(results_by_module):
    """
    results_by_module: dict like
        {"GPIO": [...], "UART": [...], "PWM": [...]}
    (missing/empty keys are treated as "not run yet")

    Returns a structured report dict - same semantics as the
    original print_final_ate_report(), just returned instead
    of printed.
    """
    module_stats = {}

    total_tests = 0
    total_passed = 0
    total_failed = 0

    for m in MODULE_ORDER:
        results = results_by_module.get(m, [])
        cfg = MODULES[m]

        if not results:
            module_stats[m] = {
                "ran": False,
                "status": "NOT RUN",
                "total": 0,
                "passed": 0,
                "failed": 0,
            }
            continue

        stats = cfg["compute_stats"](results)
        status = "PASS" if stats["module_pass"] else "FAIL"

        module_stats[m] = {
            "ran": True,
            "status": status,
            "total": stats["total"],
            "passed": stats["passed"],
            "failed": stats["failed"],
        }

        total_tests += stats["total"]
        total_passed += stats["passed"]
        total_failed += stats["failed"]

    pass_rate = (total_passed / total_tests * 100) if total_tests else 0.0

    all_ran = all(module_stats[m]["ran"] for m in MODULE_ORDER)
    overall_pass = all_ran and all(module_stats[m]["status"] == "PASS" for m in MODULE_ORDER)

    failing_modules = [
        m for m in MODULE_ORDER
        if not module_stats[m]["ran"] or module_stats[m]["status"] != "PASS"
    ]

    return {
        "modules": module_stats,
        "total_tests": total_tests,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "pass_rate": pass_rate,
        "overall_result": "PASS" if overall_pass else "FAIL",
        "failing_modules": failing_modules if not overall_pass else [],
        "note": (
            "This indicates a test-limit failure in the listed module(s), "
            "not a confirmed root-cause defect in the DUT."
        ),
    }
