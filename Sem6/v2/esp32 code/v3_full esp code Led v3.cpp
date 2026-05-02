//updated with FINAL LED UX

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

// ================= PWM =================
#define CH_GREEN 0
#define CH_BLUE  1

// ================= Modes =================
enum Mode { IDLE, CALIBRATION, GAME };
Mode currentMode = IDLE;

// ================= Detection =================
float START_THRESHOLD = 15.0;
float END_THRESHOLD   = 7.0;
float MIN_DURATION = 0.20;
unsigned long COOLDOWN = 400;

// ================= Offsets =================
float axO=0, ayO=0, azO=0;
float gxO=0, gyO=0, gzO=0;

// ================= Swing =================
bool swing = false;
unsigned long swingStart = 0;
unsigned long lastSwingEnd = 0;

float peakSpeed = 0;
float maxImpact = 0;

// ================= Gravity =================
float gravity = 0;
float alpha = 0.95;

// ================= Live =================
float live_speed=0, live_impact=0;
int swingCount = 0;

// ================= CSV =================
String csvData = "timestamp,speed,impact\n";

// ================= Flags =================
bool triggerDownload = false;

// ================= Buttons =================
bool lastCalibState = HIGH;
bool lastGameState = HIGH;

// ================= HTML =================
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
async function update(){
 let r = await fetch('/data');
 let d = await r.json();

 document.getElementById("mode").innerText="Mode: "+d.mode;
 document.getElementById("speed").innerText="Speed: "+d.speed;
 document.getElementById("impact").innerText="Impact: "+d.impact;
 document.getElementById("count").innerText="Swings: "+d.count;

 if(d.download){
   window.location.href="/download";
 }
}
setInterval(update,200);
</script>
</body>
</html>
)rawliteral";

// ================= LED CORE =================
void setGreen(int b){ ledcWrite(CH_GREEN, b); }
void setBlue(int b){ ledcWrite(CH_BLUE, b); }

// 🔵 Idle breathing (max 80)
void idleBreathing(){
  static int b = 0, dir = 2;
  b += dir;
  if(b >= 80 || b <= 0) dir = -dir;
  setBlue(b);
}

// 🎬 Calibration ENTRY
void calibEntry(){
  setBlue(20);
  for(int i=0;i<2;i++){
    setGreen(120); delay(120);
    setGreen(0);   delay(120);
  }
}

// 🎬 Calibration EXIT
void calibExit(){
  setGreen(150);
  delay(300);
  setGreen(0);
}

// 🎬 Game ENTRY
void gameEntry(){
  setBlue(0);
  for(int i=0;i<3;i++){
    setGreen(120); delay(100);
    setGreen(0);   delay(100);
  }
  setBlue(10);
}

// 🎬 Game EXIT
void gameExit(){
  for(int i=0;i<2;i++){
    setBlue(80); setGreen(80);
    delay(120);
    setBlue(0); setGreen(0);
    delay(120);
  }
}

// 🎯 Swing feedback (smooth)
void swingLED(float speed){
  int b = map(speed, 0, 80, 40, 150);
  setGreen(b);
  delay(80);
  setGreen(0);
}

// ================= Deep Sleep =================
void goToSleep(){
  setGreen(0); setBlue(0);
  esp_sleep_enable_ext0_wakeup((gpio_num_t)BTN_GAME, 0);
  delay(100);
  esp_deep_sleep_start();
}

// ================= Web =================
void handleRoot(){ server.send(200,"text/html",htmlPage); }

void handleData(){
  String modeStr = (currentMode==CALIBRATION)?"CALIBRATION":
                   (currentMode==GAME)?"GAME":"IDLE";

  String json="{";
  json += "\"mode\":\""+modeStr+"\",";
  json += "\"speed\":"+String(live_speed)+",";
  json += "\"impact\":"+String(live_impact)+",";
  json += "\"count\":"+String(swingCount)+",";
  json += "\"download\":"+(triggerDownload?"true":"false");
  json += "}";

  server.send(200,"application/json",json);
}

void handleDownload(){
  server.sendHeader("Content-Disposition","attachment; filename=data.csv");
  server.send(200,"text/csv",csvData);

  csvData = "timestamp,speed,impact\n";
  swingCount = 0;
  triggerDownload = false;

  delay(2000);
  goToSleep();
}

// ================= Calibration =================
void calibrateMPU(){
  long ax=0, ay=0, az=0, gx=0, gy=0, gz=0;
  int n=0;

  for(int i=0;i<300;i++){
    int16_t a,b,c,d,e,f;
    mpu.getMotion6(&a,&b,&c,&d,&e,&f);

    ax+=a; ay+=b; az+=c;
    gx+=d; gy+=e; gz+=f;

    setBlue(10);
    delay(5);
    n++;
  }

  axO=ax/(float)n;
  ayO=ay/(float)n;
  azO=az/(float)n;

  gxO=gx/(float)n;
  gyO=gy/(float)n;
  gzO=gz/(float)n;
}

// ================= Setup =================
void setup(){
  Serial.begin(115200);
  Wire.begin();

  pinMode(BTN_CALIB, INPUT_PULLUP);
  pinMode(BTN_GAME, INPUT_PULLUP);

  ledcSetup(CH_GREEN,5000,8);
  ledcAttachPin(GREEN_LED,CH_GREEN);

  ledcSetup(CH_BLUE,5000,8);
  ledcAttachPin(BLUE_LED,CH_BLUE);

  mpu.initialize();

  WiFi.softAP(ssid,password);

  server.on("/",handleRoot);
  server.on("/data",handleData);
  server.on("/download",handleDownload);
  server.begin();
}

// ================= Loop =================
void loop(){
  server.handleClient();

  // 🔵 Idle breathing
  if(currentMode==IDLE){
    idleBreathing();
  }

  // ===== Buttons =====
  bool c = digitalRead(BTN_CALIB);
  bool g = digitalRead(BTN_GAME);

  // CALIB BUTTON
  if(lastCalibState==HIGH && c==LOW){
    if(currentMode!=CALIBRATION){
      currentMode=CALIBRATION;
      calibEntry();
      calibrateMPU();
    } else {
      calibExit();
      currentMode=IDLE;
      triggerDownload=true;
    }
    delay(300);
  }

  // GAME BUTTON
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

  // ===== Mode steady LEDs =====
  if(currentMode==CALIBRATION){
    setBlue(10);
  }
  else if(currentMode==GAME){
    setBlue(10);
  }

  // ===== Sensor =====
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
  float angVel = sqrt(Gx*Gx+Gy*Gy+Gz*Gz);
  float speed = angVel * 0.18;

  unsigned long now=millis();

  if(currentMode==CALIBRATION || currentMode==GAME){

    if(!swing && totalAcc>START_THRESHOLD &&
       (now-lastSwingEnd>COOLDOWN)){

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