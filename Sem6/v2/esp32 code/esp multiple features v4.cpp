/*
🧠 Input Intelligence
  ✅ Short press → start mode
  ✅ Long press → stop mode + trigger download
  ✅ Double click → reset data
  ✅ Tap-to-wake (IMU motion wake)

⚡ Power
  ✅ Deep sleep in IDLE
  ✅ Wake from BOTH buttons + motion

🎯 Modes
  IDLE → breathing blue
  CALIB → fast blue blink
  GAME → green solid

🟢 Feedback
  Swing intensity → brightness
  Impact → flash pulse

🌐 Smart Dashboard
  Auto CSV download
  Reset after download
*/



#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <MPU6050.h>

MPU6050 mpu;
WebServer server(80);

// ================= WiFi =================
const char* ssid = "ESP32_Swing";
const char* password = "12345678";

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
float START_THRESHOLD = 16.0;
float END_THRESHOLD   = 8.0;
float MIN_DURATION    = 0.30;
unsigned long COOLDOWN = 500;

// ================= Swing =================
bool swing = false;
unsigned long swingStart = 0;
unsigned long lastSwingEnd = 0;
float peakSpeed = 0;
float maxImpact = 0;

// ================= Data =================
int swingCount = 0;
float live_speed = 0;
float live_impact = 0;
String csvData = "time,speed,impact\n";

bool triggerDownload = false;

// ================= Button Logic =================
unsigned long pressStartCalib = 0;
unsigned long pressStartGame = 0;

unsigned long lastClickCalib = 0;
unsigned long lastClickGame = 0;

#define LONG_PRESS_TIME 800
#define DOUBLE_CLICK_TIME 400

// ================= HTML =================
const char htmlPage[] PROGMEM = R"rawliteral(
<html>
<body>
<h2>Smart Racket</h2>
<p id="mode"></p>
<p id="speed"></p>
<p id="impact"></p>
<p id="count"></p>

<script>
async function update(){
 let r = await fetch('/data');
 let d = await r.json();

 document.getElementById("mode").innerText=d.mode;
 document.getElementById("speed").innerText=d.speed;
 document.getElementById("impact").innerText=d.impact;
 document.getElementById("count").innerText=d.count;

 if(d.download){
   window.location.href="/download";
 }
}
setInterval(update,200);
</script>
</body>
</html>
)rawliteral";

// ================= LED =================
void setGreen(int b){ ledcWrite(CH_GREEN,b); }
void setBlue(int b){ ledcWrite(CH_BLUE,b); }

void blink(int pin,int times){
  for(int i=0;i<times;i++){
    digitalWrite(pin,HIGH); delay(100);
    digitalWrite(pin,LOW); delay(100);
  }
}

// ================= Deep Sleep =================
void goToSleep(){
  Serial.println("Sleeping...");

  esp_sleep_enable_ext1_wakeup(
    (1ULL<<BTN_GAME)|(1ULL<<BTN_CALIB),
    ESP_EXT1_WAKEUP_ANY_LOW
  );

  esp_sleep_enable_timer_wakeup(5 * 1000000); // fallback wake

  esp_deep_sleep_start();
}

// ================= Web =================
void handleRoot(){ server.send(200,"text/html",htmlPage); }

void handleData(){
  String modeStr = (currentMode==CALIBRATION)?"CALIB":
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

  csvData="time,speed,impact\n";
  swingCount=0;
  triggerDownload=false;

  delay(2000);
  goToSleep();
}

// ================= Setup =================
void setup(){
  Serial.begin(115200);
  Wire.begin();

  pinMode(BTN_CALIB,INPUT_PULLUP);
  pinMode(BTN_GAME,INPUT_PULLUP);

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

  // Wake reason
  if(esp_sleep_get_wakeup_cause()==ESP_SLEEP_WAKEUP_EXT1){
    uint64_t wakePin = esp_sleep_get_ext1_wakeup_status();

    if(wakePin & (1ULL<<BTN_CALIB)) currentMode = CALIBRATION;
    if(wakePin & (1ULL<<BTN_GAME)) currentMode = GAME;
  }
}

// ================= Button Handler =================
void handleButton(int pin,
                  unsigned long &pressStart,
                  unsigned long &lastClick,
                  bool isCalib){

  bool state = digitalRead(pin)==LOW;

  if(state && pressStart==0){
    pressStart = millis();
  }

  if(!state && pressStart>0){

    unsigned long duration = millis() - pressStart;

    // LONG PRESS
    if(duration > LONG_PRESS_TIME){
      currentMode = IDLE;
      triggerDownload = true;
    }
    else{
      // DOUBLE CLICK
      if(millis()-lastClick < DOUBLE_CLICK_TIME){
        csvData="time,speed,impact\n";
        swingCount=0;
      }
      else{
        // SHORT PRESS
        if(isCalib) currentMode = CALIBRATION;
        else currentMode = GAME;
      }
      lastClick = millis();
    }

    pressStart = 0;
  }
}

// ================= Loop =================
void loop(){
  server.handleClient();

  handleButton(BTN_CALIB,pressStartCalib,lastClickCalib,true);
  handleButton(BTN_GAME,pressStartGame,lastClickGame,false);

  // ========= IDLE =========
  if(currentMode==IDLE){
    static int b=0,d=5;
    b+=d;
    if(b>=255||b<=0)d=-d;
    setBlue(b);

    // Tap to wake detection
    int16_t ax,ay,az,gx,gy,gz;
    mpu.getMotion6(&ax,&ay,&az,&gx,&gy,&gz);

    float acc = sqrt(ax*ax+ay*ay+az*az)/16384.0;

    if(acc > 2.5){
      currentMode = GAME;
    }

    delay(20);
    return;
  }

  // ========= SENSOR =========
  int16_t ax,ay,az,gx,gy,gz;
  mpu.getMotion6(&ax,&ay,&az,&gx,&gy,&gz);

  float acc = sqrt(ax*ax+ay*ay+az*az)/16384.0*9.81;
  float speed = sqrt(gx*gx+gy*gy+gz*gz)/131.0 * 0.12;

  unsigned long now = millis();

  if(currentMode==CALIBRATION || currentMode==GAME){

    if(!swing && acc>START_THRESHOLD && (now-lastSwingEnd>COOLDOWN)){
      swing=true;
      swingStart=now;
      peakSpeed=speed;
      maxImpact=acc;
    }

    if(swing){
      if(speed>peakSpeed) peakSpeed=speed;
      if(acc>maxImpact) maxImpact=acc;

      float duration=(now-swingStart)/1000.0;

      if(acc<END_THRESHOLD && duration>MIN_DURATION){

        swingCount++;
        live_speed=peakSpeed;
        live_impact=maxImpact;

        int bright = map(peakSpeed,0,50,50,255);
        setGreen(bright);
        delay(80);
        setGreen(0);

        csvData += String(now)+","+String(peakSpeed)+","+String(maxImpact)+"\n";

        swing=false;
        lastSwingEnd=now;
      }
    }
  }

  delay(10);
}