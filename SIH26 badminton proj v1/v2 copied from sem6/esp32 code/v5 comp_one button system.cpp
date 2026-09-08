// updated on 3/5/26 ,, time: 11.35 am ,, 
//working but not checked !


#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <MPU6050.h>
#include <math.h>

MPU6050 mpu;

// ---------------- WiFi ----------------
const char* ssid = "ESP32_Swing";
const char* password = "12345678";
WebServer server(80);

// ---------------- LED ----------------
#define BLUE_LED 19
#define GREEN_LED 18

// ---------------- BUTTON ----------------
#define BUTTON_PIN 22

// ---------------- STATES ----------------
enum State {
  WAITING,
  CALIBRATING,
  IDLE,
  GAME,
  PAUSED
};

State currentState = WAITING;

// ---------------- BUTTON LOGIC ----------------
bool lastButtonState = HIGH;
unsigned long pressStart = 0;
bool longPressTriggered = false;

// ---------------- SWING VARIABLES (UNCHANGED) ----------------
float START_THRESHOLD = 17.0;
float END_THRESHOLD   = 8.5;
float MIN_DURATION = 0.25;
unsigned long COOLDOWN = 350;

float axO = 0, ayO = 0, azO = 0;
float gxO = 0, gyO = 0, gzO = 0;

bool swing = false;
unsigned long swingStart = 0;
unsigned long lastSwingEnd = 0;

float peakSpeed = 0;
float maxImpact = 0;

float gravity = 0;
float alpha = 0.95;

float live_speed = 0;
float live_impact = 0;
float live_duration = 0;
unsigned long live_time = 0;
int swingCount = 0;

// ---------------- CSV ----------------
String csvData =
"timestamp,ax,ay,az,gx,gy,gz,speed,impact,duration\n";

// ---------------- LED TIMING ----------------
unsigned long lastBlink = 0;
bool blinkState = false;
unsigned long breathTimer = 0;
int breathVal = 10;
int breathDir = 1;

// =====================================================
// WEB PAGE
// =====================================================
const char htmlPage[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<body style="background:black;color:white;text-align:center;">
<h1>🏸 Smart Racket</h1>
<p id="mode">Mode: --</p>
<p id="speed">Speed: --</p>

<script>
setInterval(async ()=>{
 let r=await fetch('/data');
 let d=await r.json();
 document.getElementById("mode").innerText="Mode: "+d.mode;
 document.getElementById("speed").innerText="Speed: "+d.speed;
},200);
</script>
</body>
</html>
)rawliteral";

// =====================================================
// WEB HANDLER
// =====================================================
String getModeName() {
  switch(currentState) {
    case WAITING: return "WAITING";
    case CALIBRATING: return "CALIBRATION";
    case IDLE: return "IDLE";
    case GAME: return "GAME";
    case PAUSED: return "PAUSED";
  }
  return "";
}

void handleData() {
  String json = "{";
  json += "\"mode\":\"" + getModeName() + "\",";
  json += "\"speed\":" + String(live_speed);
  json += "}";
  server.send(200, "application/json", json);
}

// =====================================================
// BUTTON HANDLER
// =====================================================
void handleButton() {
  bool reading = digitalRead(BUTTON_PIN);

  if (lastButtonState == HIGH && reading == LOW) {
    pressStart = millis();
    longPressTriggered = false;
  }

  if (reading == LOW && !longPressTriggered) {
    if (millis() - pressStart > 2000) {
      longPressTriggered = true;

      if (currentState == GAME) currentState = PAUSED;
      else if (currentState == PAUSED) currentState = GAME;
    }
  }

  if (lastButtonState == LOW && reading == HIGH) {
    if (!longPressTriggered) {
      // short press
      switch(currentState) {
        case WAITING: currentState = CALIBRATING; break;
        case CALIBRATING: currentState = IDLE; break;
        case IDLE: currentState = GAME; break;
        case GAME: currentState = IDLE; break;
        default: break;
      }
    }
  }

  lastButtonState = reading;
}

// =====================================================
// LED ENGINE
// =====================================================
void runLED() {

  switch(currentState) {

    case WAITING:
      // triple strobe
      if (millis() - lastBlink > 100) {
        digitalWrite(BLUE_LED, !digitalRead(BLUE_LED));
        lastBlink = millis();
      }
      break;

    case CALIBRATING:
      analogWrite(BLUE_LED, 3);
      break;

    case IDLE:
      if (millis() - breathTimer > 20) {
        breathVal += breathDir;
        if (breathVal > 120 || breathVal < 10) breathDir *= -1;
        analogWrite(BLUE_LED, breathVal);
        breathTimer = millis();
      }
      break;

    case GAME:
      analogWrite(BLUE_LED, 3);
      break;

    case PAUSED:
      if (millis() - lastBlink > 800) {
        blinkState = !blinkState;
        digitalWrite(BLUE_LED, blinkState);
        lastBlink = millis();
      }
      break;
  }
}

// =====================================================
// SETUP
// =====================================================
void setup() {
  Serial.begin(115200);
  Wire.begin(26, 25);

  pinMode(BLUE_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  mpu.initialize();
  mpu.setFullScaleGyroRange(MPU6050_GYRO_FS_2000);

  // calibration (UNCHANGED)
  long ax=0,ay=0,az=0,gx=0,gy=0,gz=0;
  int n=0;
  unsigned long t=millis();

  while (millis()-t<3000){
    int16_t a,b,c,d,e,f;
    mpu.getMotion6(&a,&b,&c,&d,&e,&f);
    ax+=a; ay+=b; az+=c;
    gx+=d; gy+=e; gz+=f;
    n++; delay(2);
  }

  axO=ax/(float)n; ayO=ay/(float)n; azO=az/(float)n;
  gxO=gx/(float)n; gyO=gy/(float)n; gzO=gz/(float)n;

  WiFi.softAP(ssid,password);
  server.on("/", [](){ server.send(200,"text/html",htmlPage); });
  server.on("/data", handleData);
  server.begin();
}

// =====================================================
// LOOP
// =====================================================
void loop() {

  server.handleClient();
  handleButton();
  runLED();

  // --------- KEEP YOUR MPU LOGIC EXACTLY SAME ----------
  int16_t ax, ay, az, gx, gy, gz;
  mpu.getMotion6(&ax,&ay,&az,&gx,&gy,&gz);

  float Ax=(ax-axO)/16384.0;
  float Ay=(ay-ayO)/16384.0;
  float Az=(az-azO)/16384.0;

  float Gx=(gx-gxO)/16.4;
  float Gy=(gy-gyO)/16.4;
  float Gz=(gz-gzO)/16.4;

  gravity=alpha*gravity+(1-alpha)*Az;

  float linAccX=Ax*9.81;
  float linAccY=Ay*9.81;
  float linAccZ=(Az-gravity)*9.81;

  float totalAcc=sqrt(linAccX*linAccX+linAccY*linAccY+linAccZ*linAccZ);
  float angularVelocity=sqrt(Gx*Gx+Gy*Gy+Gz*Gz);
  float instantSpeed=angularVelocity*0.03;

  unsigned long now=millis();

  if ((currentState == GAME || currentState == CALIBRATING) &&
      !swing &&
      totalAcc > START_THRESHOLD &&
      angularVelocity > 120 &&
      (now - lastSwingEnd > COOLDOWN)) {

    swing = true;
    swingStart = now;
    peakSpeed = 0;
    maxImpact = totalAcc;
    digitalWrite(GREEN_LED, HIGH);
  }

  if (swing) {

    if (instantSpeed > peakSpeed) peakSpeed = instantSpeed;
    if (totalAcc > maxImpact) maxImpact = totalAcc;

    float duration = (now - swingStart) / 1000.0;

    if (duration > 1.2) {
      swing = false;
      lastSwingEnd = now;
      digitalWrite(GREEN_LED, LOW);
    }

    if ((totalAcc < END_THRESHOLD && angularVelocity < 60) && duration > 0.25) {

      swingCount++;
      live_time = now;
      live_speed = peakSpeed;
      live_impact = maxImpact;
      live_duration = duration;

      digitalWrite(GREEN_LED, LOW);

      swing = false;
      lastSwingEnd = now;
    }
  }

  delay(5);
}