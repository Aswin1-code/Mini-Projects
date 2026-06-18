import random
import time

# =========================
# CONFIG (TUNE THESE)
# =========================
CHALLENGE_TIMEOUT = 20     # seconds (fast sim)
VERIFICATION_TIME = 30
STABILIZATION_TIME = 40

SIM_SPEED = 0.2  # faster loop speed

# =========================
# STATES
# =========================
IDLE = "IDLE"
ALARM = "ALARM"
CHALLENGE = "CHALLENGE"
VERIFICATION = "VERIFICATION"
STABILIZATION = "STABILIZATION"

state = IDLE
state_start_time = time.time()

# =========================
# SESSION DATA
# =========================
session_log = {
    "challenge_attempts": 0,
    "verification_motion": 0,
    "stability_score": 0
}

# =========================
# FAKE SENSOR GENERATORS
# =========================

def fake_pir(state):
    """Simulate human motion patterns"""
    if state == ALARM:
        return random.random() < 0.15
    elif state == CHALLENGE:
        return random.random() < 0.6
    elif state == VERIFICATION:
        return random.random() < 0.3
    elif state == STABILIZATION:
        return random.random() < 0.2
    return False


def fake_button_sequence(correct_pattern):
    """
    Simulate user attempting sequence
    70% chance correct, 30% noise
    """
    if random.random() < 0.7:
        return correct_pattern
    else:
        return [random.randint(1, 3) for _ in correct_pattern]

# =========================
# CHALLENGE GENERATOR
# =========================

def generate_pattern():
    return [random.randint(1, 3) for _ in range(6)]

pattern = generate_pattern()
user_input_index = 0

# =========================
# STATE HANDLER
# =========================

def change_state(new_state):
    global state, state_start_time
    state = new_state
    state_start_time = time.time()
    print(f"\n🔄 STATE → {state}")

# =========================
# MAIN LOOP
# =========================

print("🧠 SMART WAKE SYSTEM SIMULATION STARTED\n")

change_state(ALARM)

while True:
    time.sleep(SIM_SPEED)

    now = time.time()
    elapsed = now - state_start_time

    pir = fake_pir(state)

    # =========================
    # ALARM STATE
    # =========================
    if state == ALARM:
        print("⏰ ALARM ACTIVE | waiting for wake trigger...")

        if pir:
            print("👀 Motion detected → moving to CHALLENGE")
            change_state(CHALLENGE)
            pattern = generate_pattern()
            print("🎯 Challenge Pattern:", pattern)

    # =========================
    # CHALLENGE STATE
    # =========================
    elif state == CHALLENGE:
        session_log["challenge_attempts"] += 1

        user_input = fake_button_sequence(pattern)

        print("🧩 Challenge running...")
        print("   Expected:", pattern)
        print("   User    :", user_input)

        if user_input == pattern:
            print("✅ Challenge PASS")
            change_state(VERIFICATION)

        elif elapsed > CHALLENGE_TIMEOUT:
            print("❌ Challenge TIMEOUT → BACK TO ALARM")
            change_state(ALARM)

    # =========================
    # VERIFICATION STATE
    # =========================
    elif state == VERIFICATION:
        if pir:
            session_log["verification_motion"] += 1
            print("👣 Motion detected in verification")

        if elapsed > VERIFICATION_TIME:
            if session_log["verification_motion"] > 3:
                print("✅ Verification PASS")
                change_state(STABILIZATION)
            else:
                print("❌ Verification FAIL → BACK TO CHALLENGE")
                change_state(CHALLENGE)

    # =========================
    # STABILIZATION STATE
    # =========================
    elif state == STABILIZATION:
        if pir:
            session_log["stability_score"] += 1
            print("📊 Stable movement detected")

        if elapsed > STABILIZATION_TIME:
            if session_log["stability_score"] > 2:
                print("\n🎉 SESSION COMPLETE → WAKE CONFIRMED")
                print("📦 SESSION LOG:", session_log)
                break
            else:
                print("⚠️ Relapse detected → BACK TO CHALLENGE")
                change_state(CHALLENGE)

# =========================
# END
# =========================

print("\n🏁 SIMULATION ENDED")