import random

# =========================
# SIM CLOCK
# =========================
class SimClock:
    def __init__(self):
        self.t = 0

    def tick(self, dt=1):
        self.t += dt
        return self.t

clock = SimClock()

# =========================
# STATES
# =========================
IDLE = "IDLE"
ALARM = "ALARM"
CHALLENGE = "CHALLENGE"
VERIFICATION = "VERIFICATION"
STABILIZATION = "STABILIZATION"

state = IDLE
state_start = 0

# =========================
# EVENT QUEUE (like interrupts)
# =========================
events = []

def emit(event_type, data=None):
    events.append((clock.t, event_type, data))

# =========================
# SENSOR MODELS (REALISTIC WAVES)
# =========================

def pir_signal(t, phase):
    """
    NOT random per loop.
    Instead behaves like real human activity pattern.
    """
    if phase == "ALARM":
        return random.random() < 0.1

    elif phase == "CHALLENGE":
        return random.random() < 0.5

    elif phase == "VERIFICATION":
        # bursts + silence pattern
        return (t % 5 < 2)

    elif phase == "STABILIZATION":
        return random.random() < 0.2

    return False

# =========================
# CHALLENGE ENGINE
# =========================
pattern = []
user_index = 0

def generate_pattern():
    return [random.randint(1, 3) for _ in range(6)]

# =========================
# STATE MACHINE
# =========================

def change(new_state):
    global state, state_start, user_index
    state = new_state
    state_start = clock.t
    user_index = 0

    emit("STATE_CHANGE", state)
    print(f"\n🔄 STATE → {state} @ t={clock.t}")

# =========================
# USER MODEL (sleepy brain simulator)
# =========================

def user_response():
    """Simulates human behavior realistically"""
    if random.random() < 0.7:
        return pattern  # sometimes correct
    else:
        return [random.randint(1, 3) for _ in pattern]

# =========================
# INIT
# =========================
change(ALARM)
pattern = generate_pattern()

# =========================
# MAIN LOOP (digital twin engine)
# =========================
while clock.t < 200:   # simulated time

    t = clock.tick(1)
    motion = pir_signal(t, state)

    # =====================
    # ALARM
    # =====================
    if state == ALARM:
        if motion:
            emit("PIR", True)
            change(CHALLENGE)
            pattern = generate_pattern()
            print("🎯 Pattern:", pattern)

    # =====================
    # CHALLENGE
    # =====================
    elif state == CHALLENGE:
        user = user_response()
        emit("USER_INPUT", user)

        if user == pattern:
            print("✅ Challenge PASS")
            change(VERIFICATION)

        elif t - state_start > 20:
            print("❌ Challenge TIMEOUT")
            change(ALARM)

    # =====================
    # VERIFICATION
    # =====================
    elif state == VERIFICATION:
        if motion:
            emit("PIR", True)

        if t - state_start > 30:
            if random.random() > 0.3:
                print("✅ Verification PASS")
                change(STABILIZATION)
            else:
                print("❌ Verification FAIL")
                change(CHALLENGE)

    # =====================
    # STABILIZATION
    # =====================
    elif state == STABILIZATION:
        if motion:
            emit("PIR", True)

        if t - state_start > 40:
            print("\n🎉 SESSION COMPLETE")
            change(IDLE)
            break

# =========================
# EVENT LOG OUTPUT
# =========================
print("\n📊 EVENT TRACE (like oscilloscope):")
for e in events[:20]:
    print(e)