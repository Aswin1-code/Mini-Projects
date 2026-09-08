"""
============================================================
 MINI ATE - STREAMLIT DASHBOARD
============================================================

Operator-facing GUI for the Mini ATE. All test logic, parsing,
validation, acceptance limits, and statistics live in
ate_core.py (the validated ATE engine) - this file is only
responsible for:

  - the serial connection lifecycle (open once, reuse across
    Streamlit reruns via st.session_state)
  - driving a module's test and streaming its output into a
    live monitor panel while it runs
  - rendering results, progress, status cards, charts and the
    final consolidated report

Run with:
    streamlit run mini_ate_dashboard.py
============================================================
"""

import html
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from serial.tools import list_ports
except ImportError:
    list_ports = None

import ate_core


# ============================================================
# PAGE CONFIG + STYLING
# ============================================================

st.set_page_config(
    page_title="Mini ATE",
    page_icon="🧪",
    layout="wide",
)

st.markdown(
    """
    <style>
    .ate-monitor {
        background-color: #0b0f14;
        color: #d7e0e8;
        font-family: "Consolas", "Courier New", monospace;
        font-size: 0.82rem;
        line-height: 1.35rem;
        padding: 14px;
        border-radius: 8px;
        border: 1px solid #2a323c;
        height: 480px;
        overflow-y: auto;
        white-space: pre-wrap;
    }
    .ate-status-line {
        font-family: "Consolas", "Courier New", monospace;
        color: #9fb3c8;
        font-size: 0.85rem;
        margin-top: 6px;
    }
    .module-pass {
        background-color: #123d1f;
        border-radius: 6px;
        padding: 6px 10px;
    }
    .module-fail {
        background-color: #4a1414;
        border-radius: 6px;
        padding: 6px 10px;
    }
    .module-notrun {
        background-color: #2a2f36;
        border-radius: 6px;
        padding: 6px 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

def init_state():
    defaults = {
        "dut": None,
        "connected": False,
        "dut_ready": False,
        "port": "COM5",
        "baud": 115200,
        "running": False,
        "current_module": None,
        "live_log": [],
        "gpio_results": [],
        "uart_results": [],
        "pwm_results": [],
        "last_error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


# ============================================================
# LOGGING HELPERS
# ============================================================

MAX_LOG_LINES = 1000
VISIBLE_LOG_LINES = 400


def log(message):
    st.session_state.live_log.append(message)
    if len(st.session_state.live_log) > MAX_LOG_LINES:
        st.session_state.live_log = st.session_state.live_log[-MAX_LOG_LINES:]


def line_color(line):
    upper = line.upper()
    if "FAIL" in upper or "ERROR" in upper or "⚠" in line:
        return "#ff6b6b"
    if "PASS" in upper or "COMPLETE" in upper or "DUT_READY" in upper:
        return "#5fd97a"
    if line.startswith("ets ") or line.startswith("rst:") or line.startswith("boot:") \
            or line.startswith("configsip") or line.startswith("clk_drv") or line.startswith("mode:"):
        return "#e6b85c"  # ESP32 boot/reset banner - informational, not a failure
    return "#d7e0e8"


def render_monitor(placeholder):
    lines = st.session_state.live_log[-VISIBLE_LOG_LINES:]
    rows = []
    for line in lines:
        color = line_color(line)
        rows.append(f'<div style="color:{color}">{html.escape(line)}</div>')
    body = "".join(rows) if rows else '<div style="color:#5a6572">Waiting for activity...</div>'
    placeholder.markdown(f'<div class="ate-monitor">{body}</div>', unsafe_allow_html=True)


# ============================================================
# CONNECTION HANDLING
# ============================================================

def connect_dut(port, baud):
    st.session_state.last_error = None
    try:
        dut = ate_core.open_dut(port, baud)
    except Exception as e:
        st.session_state.last_error = str(e)
        log(f"⚠ DUT CONNECTION FAILED: {e}")
        return

    log(f"> Opened serial port {port} @ {baud} baud")

    ready, boot_lines = ate_core.wait_for_dut_ready(dut, timeout=5)

    for line in boot_lines:
        log(f"> {line}")

    if ready:
        st.session_state.dut = dut
        st.session_state.connected = True
        st.session_state.dut_ready = True
        st.session_state.port = port
        st.session_state.baud = baud
        log("🟢 DUT CONNECTED - DUT READY")
    else:
        st.session_state.last_error = "DUT_READY not received within timeout."
        log("⚠ DUT_READY timeout - closing port")
        ate_core.close_dut(dut)
        st.session_state.dut = None
        st.session_state.connected = False
        st.session_state.dut_ready = False


def disconnect_dut():
    ate_core.close_dut(st.session_state.dut)
    st.session_state.dut = None
    st.session_state.connected = False
    st.session_state.dut_ready = False
    log("> DUT disconnected by operator")


# ============================================================
# TEST EXECUTION (single module)
# ============================================================

def run_single_module(module_name, log_placeholder, progress_placeholder, status_placeholder):
    cfg = ate_core.MODULES[module_name]
    dut = st.session_state.dut

    st.session_state.running = True
    st.session_state.current_module = module_name

    status_placeholder.markdown(
        f'<div class="ate-status-line">Status: {module_name} TEST RUNNING</div>',
        unsafe_allow_html=True,
    )

    log(f"> Sending {cfg['command'].decode().strip()}")
    render_monitor(log_placeholder)

    try:
        dut.reset_input_buffer()
        dut.write(cfg["command"])
        dut.flush()
    except Exception as e:
        log(f"⚠ ERROR sending command to DUT: {e}")
        render_monitor(log_placeholder)
        st.session_state.running = False
        st.session_state.current_module = None
        return

    results = []
    start = time.time()

    while time.time() - start < cfg["timeout"]:
        try:
            raw = dut.readline()
        except Exception as e:
            log(f"⚠ DUT disconnected during {module_name} test: {e}")
            render_monitor(log_placeholder)
            st.session_state.connected = False
            st.session_state.dut_ready = False
            break

        if not raw:
            continue

        line = raw.decode(errors="ignore").strip()
        if not line:
            continue

        log(f"> {line}")
        render_monitor(log_placeholder)

        if line.startswith(cfg["result_prefix"]):
            parsed = cfg["parse"](line)
            if parsed is not None:
                results.append(cfg["validate"](parsed))
                progress = min(len(results) / cfg["expected"], 1.0)
                progress_placeholder.progress(
                    progress,
                    text=f"{module_name} TEST   {len(results)} / {cfg['expected']}",
                )
            else:
                log(f"⚠ Malformed result line ignored: {line}")

        elif line == cfg["complete_marker"]:
            break

    else:
        log(f"⚠ {module_name} test timed out before completion ({cfg['timeout']}s)")

    render_monitor(log_placeholder)

    key = f"{module_name.lower()}_results"
    st.session_state[key] = results

    status_placeholder.markdown(
        f'<div class="ate-status-line">Status: {module_name} TEST COMPLETE '
        f"({len(results)}/{cfg['expected']} results received)</div>",
        unsafe_allow_html=True,
    )

    st.session_state.running = False
    st.session_state.current_module = None


# ============================================================
# TEST EXECUTION (RUN ALL)
# ============================================================

def run_all_modules(log_placeholder, progress_placeholders, status_placeholder):
    dut = st.session_state.dut
    st.session_state.running = True

    log("> Sending RUN_ALL")
    render_monitor(log_placeholder)

    try:
        dut.reset_input_buffer()
        dut.write(b"RUN_ALL\n")
        dut.flush()
    except Exception as e:
        log(f"⚠ ERROR sending RUN_ALL to DUT: {e}")
        render_monitor(log_placeholder)
        st.session_state.running = False
        st.session_state.current_module = None
        return

    buffers = {m: [] for m in ate_core.MODULE_ORDER}
    idx = 0
    overall_timeout = sum(ate_core.MODULES[m]["timeout"] for m in ate_core.MODULE_ORDER) + 30
    start = time.time()

    while time.time() - start < overall_timeout and idx < len(ate_core.MODULE_ORDER):
        current = ate_core.MODULE_ORDER[idx]
        cfg = ate_core.MODULES[current]

        st.session_state.current_module = current
        status_placeholder.markdown(
            f'<div class="ate-status-line">Status: RUN ALL - {current} TEST RUNNING</div>',
            unsafe_allow_html=True,
        )

        try:
            raw = dut.readline()
        except Exception as e:
            log(f"⚠ DUT disconnected during RUN ALL ({current}): {e}")
            render_monitor(log_placeholder)
            st.session_state.connected = False
            st.session_state.dut_ready = False
            break

        if not raw:
            continue

        line = raw.decode(errors="ignore").strip()
        if not line:
            continue

        log(f"> {line}")
        render_monitor(log_placeholder)

        if line.startswith(cfg["result_prefix"]):
            parsed = cfg["parse"](line)
            if parsed is not None:
                buffers[current].append(cfg["validate"](parsed))
                progress = min(len(buffers[current]) / cfg["expected"], 1.0)
                progress_placeholders[current].progress(
                    progress,
                    text=f"{current}   {len(buffers[current])} / {cfg['expected']}",
                )
            else:
                log(f"⚠ Malformed result line ignored: {line}")

        elif line == cfg["complete_marker"]:
            idx += 1

        elif line == "ALL_TESTS_COMPLETE":
            break

    render_monitor(log_placeholder)

    st.session_state.gpio_results = buffers["GPIO"]
    st.session_state.uart_results = buffers["UART"]
    st.session_state.pwm_results = buffers["PWM"]

    status_placeholder.markdown(
        '<div class="ate-status-line">Status: RUN ALL COMPLETE</div>',
        unsafe_allow_html=True,
    )

    st.session_state.running = False
    st.session_state.current_module = None


# ============================================================
# RESULT TABLE STYLING
# ============================================================

def style_result_df(df):
    def highlight(row):
        color = "#123d1f" if row.get("Result") == "🟢 PASS" else "#4a1414"
        return [f"background-color:{color}"] * len(row)

    return df.style.apply(highlight, axis=1)


def pass_fail_badge(result):
    return "🟢 PASS" if result == "PASS" else "🔴 FAIL"


# ============================================================
# LEFT PANEL - CONTROL PANEL
# ============================================================

def render_control_panel():
    st.markdown("## 🧪 MINI ATE")
    st.caption("Automated Test Equipment - Operator Console")

    st.markdown("### DUT Connection")

    available_ports = []
    if list_ports is not None:
        try:
            available_ports = [p.device for p in list_ports.comports()]
        except Exception:
            available_ports = []

    port_options = available_ports + ["Custom..."] if available_ports else ["Custom..."]
    default_index = 0

    if available_ports:
        chosen = st.selectbox("COM Port", port_options, index=default_index, disabled=st.session_state.running)
        if chosen == "Custom...":
            port = st.text_input("Enter COM Port", value=st.session_state.port, disabled=st.session_state.running)
        else:
            port = chosen
    else:
        port = st.text_input("COM Port", value=st.session_state.port, disabled=st.session_state.running)

    baud = st.selectbox(
        "Baud Rate",
        options=[9600, 19200, 38400, 57600, 115200, 230400],
        index=[9600, 19200, 38400, 57600, 115200, 230400].index(st.session_state.baud)
        if st.session_state.baud in [9600, 19200, 38400, 57600, 115200, 230400] else 4,
        disabled=st.session_state.running,
    )

    col_c, col_d = st.columns(2)
    with col_c:
        connect_clicked = st.button(
            "🔌 Connect DUT", use_container_width=True,
            disabled=st.session_state.connected or st.session_state.running,
        )
    with col_d:
        disconnect_clicked = st.button(
            "❌ Disconnect DUT", use_container_width=True,
            disabled=not st.session_state.connected or st.session_state.running,
        )

    if connect_clicked:
        connect_dut(port, baud)
        st.rerun()

    if disconnect_clicked:
        disconnect_dut()
        st.rerun()

    if st.session_state.connected and st.session_state.dut_ready:
        st.success("🟢 DUT CONNECTED\nDUT READY")
    elif st.session_state.last_error:
        st.error(f"🔴 DUT CONNECTION FAILED\n{st.session_state.last_error}")
    else:
        st.info("⚪ DUT NOT CONNECTED")

    st.markdown("---")
    st.markdown("### Test Selection")

    controls_disabled = (not st.session_state.connected) or st.session_state.running

    gpio_clicked = st.button("▶ GPIO TEST", use_container_width=True, disabled=controls_disabled)
    uart_clicked = st.button("▶ UART TEST", use_container_width=True, disabled=controls_disabled)
    pwm_clicked = st.button("▶ PWM TEST", use_container_width=True, disabled=controls_disabled)
    run_all_clicked = st.button("⏩ RUN ALL", use_container_width=True, type="primary", disabled=controls_disabled)

    if st.session_state.running:
        st.warning(f"TEST IN PROGRESS ({st.session_state.current_module or '...'})")

    st.markdown("---")

    report_clicked = st.button(
        "📋 GENERATE COMPLETE ATE REPORT", use_container_width=True,
        disabled=st.session_state.running,
    )

    clear_clicked = st.button(
        "🗑 Clear Test Results", use_container_width=True,
        disabled=st.session_state.running,
    )

    if clear_clicked:
        st.session_state.gpio_results = []
        st.session_state.uart_results = []
        st.session_state.pwm_results = []
        log("> Test results cleared by operator")
        st.rerun()

    return {
        "gpio": gpio_clicked,
        "uart": uart_clicked,
        "pwm": pwm_clicked,
        "run_all": run_all_clicked,
        "report": report_clicked,
    }


# ============================================================
# TOP STATUS CARDS
# ============================================================

def render_status_cards():
    dut_status = "🟢 READY" if st.session_state.dut_ready else ("🔴 DISCONNECTED" if not st.session_state.connected else "🟡 CONNECTING")
    test_status = "🟡 RUNNING" if st.session_state.running else "⚪ IDLE"
    current_module = st.session_state.current_module or "-"

    all_results = st.session_state.gpio_results + st.session_state.uart_results + st.session_state.pwm_results
    total = len(all_results)
    passed = sum(1 for r in all_results if r["result"] == "PASS")
    failed = total - passed
    pass_rate = (passed / total * 100) if total else 0.0

    cols = st.columns(7)
    cols[0].metric("DUT", dut_status)
    cols[1].metric("TEST", test_status)
    cols[2].metric("MODULE", current_module)
    cols[3].metric("TOTAL", total)
    cols[4].metric("PASS", passed)
    cols[5].metric("FAIL", failed)
    cols[6].metric("PASS RATE", f"{pass_rate:.2f}%")


# ============================================================
# RIGHT PANEL - LIVE TEST MONITOR
# ============================================================

def render_live_monitor():
    st.markdown("### 📡 LIVE TEST MONITOR")
    log_placeholder = st.empty()
    render_monitor(log_placeholder)

    status_placeholder = st.empty()
    if not st.session_state.running:
        status_placeholder.markdown(
            '<div class="ate-status-line">Status: IDLE</div>', unsafe_allow_html=True
        )

    return log_placeholder, status_placeholder


# ============================================================
# GPIO RESULT VIEW
# ============================================================

def render_gpio_results():
    results = st.session_state.gpio_results
    if not results:
        st.info("No GPIO results yet. Run the GPIO test to populate this section.")
        return

    stats = ate_core.compute_gpio_stats(results)

    st.markdown("#### GPIO Tests")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", stats["total"])
    c2.metric("Passed", stats["passed"])
    c3.metric("Failed", stats["failed"])
    c4.metric("Pass Rate", f"{stats['pass_rate']:.2f}%")

    df = pd.DataFrame([
        {
            "Test": f"{r['test_id']:02d}",
            "Output": f"GPIO{r['output']}",
            "Input": f"GPIO{r['input']}",
            "Expected": r["expected"],
            "Actual": r["actual"],
            "Rep": r["repetition"],
            "Time (us)": r["time"],
            "Result": pass_fail_badge(r["result"]),
        }
        for r in results
    ])
    st.dataframe(style_result_df(df), use_container_width=True, height=280)

    with st.expander("Path Statistics"):
        path_df = pd.DataFrame(stats["paths"]).rename(
            columns={"path": "Path", "total": "Total", "pass": "Pass", "fail": "Fail"}
        )
        st.dataframe(path_df, use_container_width=True)

    with st.expander("Timing Statistics"):
        st.write(
            f"Minimum: {stats['timing']['min']} us | "
            f"Maximum: {stats['timing']['max']} us | "
            f"Average: {stats['timing']['avg']:.2f} us"
        )

    if not stats["complete"]:
        st.warning(f"Incomplete GPIO test execution: {stats['total']}/{stats['expected']} transactions received.")


# ============================================================
# UART RESULT VIEW
# ============================================================

def render_uart_results():
    results = st.session_state.uart_results
    if not results:
        st.info("No UART results yet. Run the UART test to populate this section.")
        return

    stats = ate_core.compute_uart_stats(results)

    st.markdown("#### UART Tests")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", stats["total"])
    c2.metric("Passed", stats["passed"])
    c3.metric("Failed", stats["failed"])
    c4.metric("Pass Rate", f"{stats['pass_rate']:.2f}%")

    df = pd.DataFrame([
        {
            "UART": r["uart"],
            "Test": f"{r['test_id']:03d}",
            "TX": f"GPIO{r['tx']}",
            "RX": f"GPIO{r['rx']}",
            "Pattern": r["pattern"],
            "Rep": r["repetition"],
            "Exp Len": r["expected_length"],
            "Recv Len": r["received_length"],
            "Time (us)": r["time_us"],
            "Result": pass_fail_badge(r["result"]),
        }
        for r in results
    ])
    st.dataframe(style_result_df(df), use_container_width=True, height=280)

    failures = [r for r in results if r["result"] == "FAIL"]
    if failures:
        with st.expander(f"Failure Details ({len(failures)})"):
            for r in failures:
                st.markdown(
                    f"**Test {r['test_id']:03d}** (UART{r['uart']}, "
                    f"GPIO{r['tx']} TX -> GPIO{r['rx']} RX)"
                )
                st.write(f"Expected : `{r['expected']}`")
                st.write(f"Actual   : `{r['actual']}`")
                st.write(f"Reason   : {r['reason']}")
                st.markdown("---")

    with st.expander("UART Summary"):
        for u in stats["uart_summary"]:
            st.write(f"UART{u['uart']}: {u['pass']}/{u['total']} PASS, {u['fail']} FAIL")

    with st.expander("Direction Summary"):
        for d in stats["direction_summary"]:
            st.write(f"{d['direction']}: {d['pass']}/{d['total']} PASS, {d['fail']} FAIL")

    with st.expander("Timing Statistics"):
        st.write(
            f"Minimum: {stats['timing']['min']:.0f} us | "
            f"Maximum: {stats['timing']['max']:.0f} us | "
            f"Average: {stats['timing']['avg']:.2f} us"
        )

    if not stats["complete"]:
        st.warning(f"Incomplete UART test execution: {stats['total']}/{stats['expected']} transactions received.")


# ============================================================
# PWM RESULT VIEW
# ============================================================

def render_pwm_results():
    results = st.session_state.pwm_results
    if not results:
        st.info("No PWM results yet. Run the PWM test to populate this section.")
        return

    stats = ate_core.compute_pwm_stats(results)

    st.markdown("#### PWM Tests")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", stats["total"])
    c2.metric("Passed", stats["passed"])
    c3.metric("Failed", stats["failed"])
    c4.metric("Pass Rate", f"{stats['pass_rate']:.2f}%")

    path_names = {pid: name for pid, (name, _o, _i) in ate_core.PWM_EXPECTED_PATHS.items()}

    df = pd.DataFrame([
        {
            "Test": f"{r['test_number']:02d}",
            "Path": path_names.get(r["path_id"], f"Path {r['path_id']}"),
            "Target Freq (Hz)": r["target_frequency"],
            "Measured Freq (Hz)": round(r["measured_frequency"], 2),
            "Target Duty (%)": r["target_duty"],
            "Measured Duty (%)": round(r["measured_duty"], 2),
            "Rep": r["repetition"],
            "Result": pass_fail_badge(r["result"]),
        }
        for r in results
    ])
    st.dataframe(style_result_df(df), use_container_width=True, height=280)

    failures = [r for r in results if r["result"] == "FAIL"]
    if failures:
        with st.expander(f"Failure Details ({len(failures)})"):
            st.caption(
                f"Frequency tolerance: ±{ate_core.FREQUENCY_TOLERANCE_PERCENT}%   |   "
                f"Duty tolerance: ±{ate_core.DUTY_TOLERANCE_PERCENT} percentage points"
            )
            for r in failures:
                path_name = path_names.get(r["path_id"], f"Path {r['path_id']}")
                st.markdown(f"**Test {r['test_number']:02d}** ({path_name})")
                st.write(f"Expected Frequency = {r['target_frequency']} Hz")
                st.write(f"Measured Frequency = {r['measured_frequency']:.2f} Hz")
                st.write(f"Expected Duty = {r['target_duty']:.0f}%")
                st.write(f"Measured Duty = {r['measured_duty']:.2f}%")
                st.write(f"Possible indication: {r['diagnosis']}")
                st.caption("This is a test-result indication, not a confirmed root-cause diagnosis.")
                st.markdown("---")

    with st.expander("Path Statistics"):
        for p in stats["path_stats"]:
            st.write(f"{p['name']}: {p['pass']}/{p['total']} PASS, {p['fail']} FAIL")

    with st.expander("Frequency Statistics"):
        freq_df = pd.DataFrame(stats["frequency_stats"]).rename(
            columns={"frequency": "Frequency (Hz)", "min": "Min", "max": "Max", "avg": "Average"}
        )
        st.dataframe(freq_df, use_container_width=True)

    with st.expander("Duty Statistics"):
        duty_df = pd.DataFrame(stats["duty_stats"]).rename(
            columns={"duty": "Duty (%)", "min": "Min", "max": "Max", "avg": "Average"}
        )
        st.dataframe(duty_df, use_container_width=True)

    if not stats["complete"]:
        st.warning(f"Incomplete PWM test execution: {stats['total']}/{stats['expected']} transactions received.")


# ============================================================
# VISUAL STATISTICS (charts)
# ============================================================

def render_visual_statistics():
    all_results = st.session_state.gpio_results + st.session_state.uart_results + st.session_state.pwm_results
    if not all_results:
        return

    st.markdown("### 📊 Visual Statistics")

    col1, col2 = st.columns([1, 2])

    with col1:
        passed = sum(1 for r in all_results if r["result"] == "PASS")
        failed = len(all_results) - passed
        fig = go.Figure(data=[go.Pie(
            labels=["PASS", "FAIL"],
            values=[passed, failed],
            hole=0.55,
            marker=dict(colors=["#2ecc71", "#e74c3c"]),
        )])
        fig.update_layout(
            title="Overall PASS / FAIL", margin=dict(t=40, b=0, l=0, r=0), height=300,
            paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#d7e0e8"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        module_data = []
        for name, results in [
            ("GPIO", st.session_state.gpio_results),
            ("UART", st.session_state.uart_results),
            ("PWM", st.session_state.pwm_results),
        ]:
            p = sum(1 for r in results if r["result"] == "PASS")
            module_data.append({"Module": name, "Total": len(results), "Passed": p, "Failed": len(results) - p})

        mod_df = pd.DataFrame(module_data)
        fig2 = go.Figure()
        fig2.add_bar(name="Passed", x=mod_df["Module"], y=mod_df["Passed"], marker_color="#2ecc71")
        fig2.add_bar(name="Failed", x=mod_df["Module"], y=mod_df["Failed"], marker_color="#e74c3c")
        fig2.update_layout(
            barmode="stack", title="Module Comparison", height=300,
            margin=dict(t=40, b=0, l=0, r=0),
            paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#d7e0e8"),
        )
        st.plotly_chart(fig2, use_container_width=True)


# ============================================================
# FINAL ATE REPORT
# ============================================================

def render_final_report():
    report = ate_core.compute_final_report({
        "GPIO": st.session_state.gpio_results,
        "UART": st.session_state.uart_results,
        "PWM": st.session_state.pwm_results,
    })

    st.markdown("## 📋 MINI ATE FINAL REPORT")

    cols = st.columns(3)
    for i, m in enumerate(ate_core.MODULE_ORDER):
        mstat = report["modules"][m]
        css_class = (
            "module-pass" if mstat["status"] == "PASS"
            else "module-fail" if mstat["status"] == "FAIL"
            else "module-notrun"
        )
        with cols[i]:
            st.markdown(
                f'<div class="{css_class}"><b>{m}</b><br>{mstat["status"]}<br>'
                f'{mstat["passed"]}/{mstat["total"]} passed</div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Tests", report["total_tests"])
    c2.metric("Total Passed", report["total_passed"])
    c3.metric("Total Failed", report["total_failed"])
    c4.metric("Overall Pass Rate", f"{report['pass_rate']:.2f}%")

    if report["overall_result"] == "PASS":
        st.success("Overall Result : PASS")
    else:
        st.error("Overall Result : FAIL")
        st.write(f"Failing module(s): {', '.join(report['failing_modules'])}")
        st.caption(report["note"])


# ============================================================
# MAIN LAYOUT
# ============================================================

def main():
    header_l, header_r = st.columns([3, 1])
    with header_l:
        st.title("MINI ATE")
    with header_r:
        if st.session_state.dut_ready:
            st.markdown("### DUT: 🟢 READY")
        elif st.session_state.connected:
            st.markdown("### DUT: 🟡 CONNECTING")
        else:
            st.markdown("### DUT: 🔴 DISCONNECTED")

    render_status_cards()
    st.markdown("---")

    left, right = st.columns([1, 2])

    with left:
        actions = render_control_panel()

    with right:
        log_placeholder, status_placeholder = render_live_monitor()

    # --------------------------------------------------------
    # Handle test-run actions (blocking within this script run
    # so the live monitor updates progressively as lines arrive)
    # --------------------------------------------------------

    if actions["gpio"] and st.session_state.connected:
        with right:
            progress_placeholder = st.empty()
        run_single_module("GPIO", log_placeholder, progress_placeholder, status_placeholder)
        st.rerun()

    if actions["uart"] and st.session_state.connected:
        with right:
            progress_placeholder = st.empty()
        run_single_module("UART", log_placeholder, progress_placeholder, status_placeholder)
        st.rerun()

    if actions["pwm"] and st.session_state.connected:
        with right:
            progress_placeholder = st.empty()
        run_single_module("PWM", log_placeholder, progress_placeholder, status_placeholder)
        st.rerun()

    if actions["run_all"] and st.session_state.connected:
        with right:
            st.markdown("**Overall ATE Progress**")
            progress_placeholders = {
                m: st.empty() for m in ate_core.MODULE_ORDER
            }
        run_all_modules(log_placeholder, progress_placeholders, status_placeholder)
        st.rerun()

    st.markdown("---")

    # --------------------------------------------------------
    # Result sections
    # --------------------------------------------------------

    tab_gpio, tab_uart, tab_pwm, tab_stats = st.tabs(
        ["GPIO Results", "UART Results", "PWM Results", "Statistics"]
    )

    with tab_gpio:
        render_gpio_results()

    with tab_uart:
        render_uart_results()

    with tab_pwm:
        render_pwm_results()

    with tab_stats:
        render_visual_statistics()

    if actions["report"]:
        st.markdown("---")
        render_final_report()


if __name__ == "__main__":
    main()
