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

// ================= Swing =================
bool swing = false;
unsigned long swingStart = 0;
float peakSpeed = 0;
float maxImpact = 0;

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
<head>
<meta charset="UTF-8">
</head>
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

// ================= LED FUNCTIONS =================
void setGreen(int b){ ledcWrite(CH_GREEN, b); }
void setBlue(int b){ ledcWrite(CH_BLUE, b); }

void blinkGreen(int t){
  for(int i=0;i<t;i++){
    setGreen(255); delay(100);
    setGreen(0); delay(100);
  }
}

void blinkBlue(int t){
  for(int i=0;i<t;i++){
    setBlue(255); delay(100);
    setBlue(0); delay(100);
  }
}

// ================= Web =================
void handleRoot(){
  server.send(200,"text/html",htmlPage);
}

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

  // reset
  csvData = "timestamp,speed,impact\n";
  swingCount = 0;
  triggerDownload = false;

  delay(2000);

}

// ================= Setup =================
void setup(){
  Serial.begin(115200);
  Wire.begin();

  pinMode(BTN_CALIB, INPUT_PULLUP);
  pinMode(BTN_GAME, INPUT_PULLUP);

  // PWM setup
  ledcSetup(CH_GREEN, 5000, 8);
  ledcAttachPin(GREEN_LED, CH_GREEN);

  ledcSetup(CH_BLUE, 5000, 8);
  ledcAttachPin(BLUE_LED, CH_BLUE);

  mpu.initialize();

  if(!mpu.testConnection()){
    while(1){
      blinkBlue(1);
      setGreen(255);
      delay(100);
    }
  }

  WiFi.softAP(ssid,password);

  server.on("/",handleRoot);
  server.on("/data",handleData);
  server.on("/download",handleDownload);
  server.begin();
}

// ================= Loop =================
void loop(){
  server.handleClient();

  // ========= IDLE MODE =========
  if(currentMode==IDLE){
    static int b=0, dir=5;
    b+=dir;
    if(b>=255||b<=0) dir=-dir;
    setBlue(b);
    delay(10);
  }

  // ========= BUTTONS =========
  bool c = digitalRead(BTN_CALIB);
  bool g = digitalRead(BTN_GAME);

  // CALIB BUTTON
  if(lastCalibState==HIGH && c==LOW){
    if(currentMode!=CALIBRATION){
      currentMode=CALIBRATION;
      blinkBlue(2);
    } else {
      currentMode=IDLE;
      triggerDownload=true;
      setGreen(255); delay(500);
      setGreen(0);
    }
    delay(300);
  }

  // GAME BUTTON
  if(lastGameState==HIGH && g==LOW){
    if(currentMode!=GAME){
      currentMode=GAME;
      blinkGreen(3);
    } else {
      currentMode=IDLE;
      triggerDownload=true;
      for(int i=0;i<3;i++){
        setGreen(255); setBlue(255); delay(100);
        setGreen(0); setBlue(0); delay(100);
      }
    }
    delay(300);
  }

  lastCalibState=c;
  lastGameState=g;

  // ========= SENSOR =========
  int16_t ax,ay,az,gx,gy,gz;
  mpu.getMotion6(&ax,&ay,&az,&gx,&gy,&gz);

  float totalAcc = sqrt(ax*ax+ay*ay+az*az)/16384.0*9.81;
  float angVel = sqrt(gx*gx+gy*gy+gz*gz)/131.0;
  float speed = angVel*0.12;

  unsigned long now=millis();

  if(currentMode==CALIBRATION || currentMode==GAME){

    if(!swing && totalAcc>START_THRESHOLD){
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

        // intensity LED
        int bright = map(peakSpeed,0,50,50,255);
        setGreen(bright);
        delay(80);
        setGreen(0);

        csvData += String(now)+","+String(peakSpeed)+","+String(maxImpact)+"\n";

        swing=false;
      }
    }
  }

  delay(10);
}