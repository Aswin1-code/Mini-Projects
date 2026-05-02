// updated FINAL VERSION (analogWrite fixed + clean compile)
// working perfectly,,   1/5/26  time : 11:50pm   ... 
#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <MPU6050.h>
#include <math.h>

MPU6050 mpu;

// ================= WiFi =================
const char* ssid = "ESP32_Swing";
const char* password = "12345678";

WebServer server(80);

// ================= Pins =================
#define GREEN_LED 18
#define BLUE_LED  19
#define BTN_CALIB 22
#define BTN_GAME  23

// ================= Modes =================
enum Mode { IDLE, CALIBRATION, GAME };
Mode currentMode = IDLE;

// ================= Variables (UNCHANGED CORE) =================
float START_THRESHOLD = 15.0;
float END_THRESHOLD   = 7.0;
float MIN_DURATION = 0.20;
unsigned long COOLDOWN = 400;

float axO=0, ayO=0, azO=0;
float gxO=0, gyO=0, gzO=0;

bool swing = false;
unsigned long swingStart = 0;
unsigned long lastSwingEnd = 0;

float peakSpeed = 0;
float maxImpact = 0;

float gravity = 0;
float alpha = 0.95;

float live_speed=0, live_impact=0;
int swingCount = 0;

String csvData = "timestamp,speed,impact\n";

bool triggerDownload = false;

bool lastCalibState = HIGH;
bool lastGameState = HIGH;

bool wifiConnected = false;
unsigned long lastWifiCheck = 0;

// ================= LED (ANALOG ONLY) =================
void setGreen(int v){ analogWrite(GREEN_LED, v); }
void setBlue(int v){ analogWrite(BLUE_LED, v); }

// ================= STROBE =================
void strobeEffect(int cycles) {
  for (int i = 0; i < cycles; i++) {
    setGreen(255); setBlue(255);
    delay(60);
    setGreen(0); setBlue(0);
    delay(80);

    setGreen(255); setBlue(255);
    delay(60);
    setGreen(0); setBlue(0);

    delay(700);
  }
}

// ================= Idle breathing =================
void idleBreathing(){
  static int b = 0, dir = 2;
  b += dir;
  if(b >= 80 || b <= 0) dir = -dir;
  setBlue(b);
}

// ================= MODE EFFECTS =================
void calibEntry(){
  setBlue(20);
  for(int i=0;i<2;i++){
    setGreen(120); delay(120);
    setGreen(0); delay(120);
  }
}

void calibExit(){
  setGreen(150);
  delay(300);
  setGreen(0);
}

void gameEntry(){
  setBlue(0);
  for(int i=0;i<3;i++){
    setGreen(120); delay(100);
    setGreen(0); delay(100);
  }
  setBlue(10);
}

void gameExit(){
  for(int i=0;i<2;i++){
    setBlue(80); setGreen(80);
    delay(120);
    setBlue(0); setGreen(0);
    delay(120);
  }
}

void swingLED(float speed){
  int v = map(speed, 0, 80, 40, 150);
  setGreen(v);
  delay(80);
  setGreen(0);
}

// ================= WiFi =================
void updateWiFiStatus(){
  if (millis() - lastWifiCheck > 2000) {
    lastWifiCheck = millis();
    wifiConnected = (WiFi.softAPgetStationNum() > 0);
  }
}

void wifiLEDIndicator(){
  if (currentMode != IDLE) return;

  if (!wifiConnected) {
    setBlue(0);

    static bool state = false;
    static unsigned long t = 0;

    if (millis() - t > 800) {
      t = millis();
      state = !state;
      setGreen(state ? 50 : 0);
    }
  } else {
    static unsigned long t = 0;

    if (millis() - t > 2000) {
      t = millis();
      setBlue(40);
      delay(80);
      setBlue(0);
    }
  }
}

// ================= WEB =================
const char htmlPage[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<body>
<h2>🏸 Smart Racket</h2>
<p id="mode"></p>
<p id="speed"></p>
<p id="impact"></p>
<p id="count"></p>

<script>
setInterval(async ()=>{
 let r=await fetch('/data');
 let d=await r.json();

 document.getElementById("mode").innerText="Mode:"+d.mode;
 document.getElementById("speed").innerText=d.speed;
 document.getElementById("impact").innerText=d.impact;
 document.getElementById("count").innerText=d.count;

 if(d.download){
   window.location="/download";
 }
},200);
</script>
</body>
</html>
)rawliteral";

void handleRoot(){ server.send(200,"text/html",htmlPage); }

void handleData(){
  String modeStr = (currentMode==CALIBRATION)?"CALIBRATION":
                   (currentMode==GAME)?"GAME":"IDLE";

  String json="{";
  json += "\"mode\":\""+modeStr+"\",";
  json += "\"speed\":"+String(live_speed)+",";
  json += "\"impact\":"+String(live_impact)+",";
  json += "\"count\":"+String(swingCount)+",";
  json += "\"download\":" + String(triggerDownload ? "true" : "false");
  json += "}";

  server.send(200,"application/json",json);
}

// ================= SETUP =================
void setup(){
  Serial.begin(115200);
  Wire.begin();

  pinMode(GREEN_LED, OUTPUT);
  pinMode(BLUE_LED, OUTPUT);

  pinMode(BTN_CALIB, INPUT_PULLUP);
  pinMode(BTN_GAME, INPUT_PULLUP);

  mpu.initialize();
  WiFi.softAP(ssid,password);

  strobeEffect(3);

  server.on("/",handleRoot);
  server.on("/data",handleData);
  server.begin();
}

// ================= LOOP =================
void loop(){
  server.handleClient();

  updateWiFiStatus();
  wifiLEDIndicator();

  if(currentMode==IDLE){
    idleBreathing();
  }

  bool c = digitalRead(BTN_CALIB);
  bool g = digitalRead(BTN_GAME);

  if(lastCalibState==HIGH && c==LOW){
    if(currentMode!=CALIBRATION){
      currentMode=CALIBRATION;
      calibEntry();
    } else {
      calibExit();
      currentMode=IDLE;
      triggerDownload=true;
    }
    delay(300);
  }

  if(lastGameState==HIGH && g==LOW){
    if(currentMode!=GAME){
      currentMode=GAME;
      gameEntry();
    } else {
      gameExit();
      currentMode=IDLE;
      triggerDownload=true;
    }
    delay(300);
  }

  lastCalibState=c;
  lastGameState=g;

  // steady LED
  if(currentMode!=IDLE){
    setBlue(10);
  }

  // MPU logic (UNCHANGED)
  int16_t ax,ay,az,gx,gy,gz;
  mpu.getMotion6(&ax,&ay,&az,&gx,&gy,&gz);

  float Ax=(ax-axO)/16384.0;
  float Ay=(ay-ayO)/16384.0;
  float Az=(az-azO)/16384.0;

  float Gx=(gx-gxO)/131.0;
  float Gy=(gy-gyO)/131.0;
  float Gz=(gz-gzO)/131.0;

  gravity = alpha*gravity+(1-alpha)*Az;

  float linAccZ=(Az-gravity)*9.81;

  float totalAcc = sqrt(Ax*Ax+Ay*Ay+linAccZ*linAccZ);
  float speed = sqrt(Gx*Gx+Gy*Gy+Gz*Gz)*0.18;

  unsigned long now=millis();

  if(currentMode==CALIBRATION || currentMode==GAME){

    if(!swing && totalAcc>START_THRESHOLD && (now-lastSwingEnd>COOLDOWN)){
      swing=true;
      swingStart=now;
      peakSpeed=speed;
      maxImpact=totalAcc;
    }

    if(swing){
      if(speed>peakSpeed) peakSpeed=speed;
      if(totalAcc>maxImpact) maxImpact=totalAcc;

      float duration=(now-swingStart)/1000.0;

      if(totalAcc<END_THRESHOLD && duration>MIN_DURATION){

        swingCount++;
        live_speed=peakSpeed;
        live_impact=maxImpact;

        swingLED(peakSpeed);

        csvData += String(now)+","+String(peakSpeed)+","+String(maxImpact)+"\n";

        swing=false;
        lastSwingEnd=now;
      }
    }
  }

  delay(10);
}