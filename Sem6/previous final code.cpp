#include <Wire.h>
#include <WiFi.h>
#include <WebServer.h>
#include <MPU6050.h>
#include <math.h>

MPU6050 mpu;

// ======== Wi-Fi AP ========
const char* ssid = "ESP32_Swing";
const char* password = "12345678";
WebServer server(80);

// ======== Swing Variables ========
float axOffset=0, ayOffset=0, azOffset=0;
float gxOffset=0, gyOffset=0, gzOffset=0;

bool swingStarted = false;
float velocity = 0, impactShock = 0, peakAngularVelocity = 0, swingAngle = 0;
unsigned long swingStartTime = 0, lastTime = 0;

float maxSpeed = 0, maxImpact = 0;
int swingCount = 0;

// ======== Gravity Filter ========
float gravity = 0;
float alpha = 0.95;

// ======== LED Pins ========
int ledGreen = 27;
int ledOrange = 32;
int ledRed = 33;

// ======== Kalman Filter Class ========
class Kalman {
  float Q,R,P,X;
public:
  Kalman(float q,float r,float x0){ Q=q; R=r; P=1; X=x0; }
  float update(float measurement){
    P=P+Q;
    float K=P/(P+R);
    X=X+K*(measurement-X);
    P=(1-K)*P;
    return X;
  }
};

// ======== Kalman Filters ========
Kalman kAx(0.001,0.1,0), kAy(0.001,0.1,0), kAz(0.001,0.1,0);
Kalman kGx(0.001,0.1,0), kGy(0.001,0.1,0), kGz(0.001,0.1,0);

// ======== Store all swings for CSV ========
struct SwingRecord {
  float speed;
  float impact;
  float angle;
  String type;
};
#define MAX_SWINGS 1000
SwingRecord swingData[MAX_SWINGS];
int swingIndex = 0;

// ======== HTML Dashboard ========
const char htmlPage[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <title>Badminton Swing Analyzer</title>
  <meta charset="UTF-8">
  <style>
    body { font-family:'Segoe UI'; background:#101820; color:#FEE715; text-align:center; }
    h1 { font-size:28px; margin-top:20px; }
    .dashboard { display:flex; flex-wrap:wrap; justify-content:center; }
    .card { margin:15px; padding:20px; background:#1c1c1c; border-radius:15px; width:220px; box-shadow:0 0 20px #FEE715; }
    .card p { font-size:18px; margin:5px; }
    .progress { width:100%; background:#333; border-radius:10px; height:10px; margin-top:5px; }
    .bar { height:10px; border-radius:10px; background:#FEE715; width:0%; transition:0.3s; }
    button { margin-top:15px; padding:10px 20px; font-size:16px; border:none; border-radius:10px; cursor:pointer; background:#FEE715; color:#101820; }
  </style>
</head>
<body>
  <h1>🏸 ESP32 Swing Dashboard</h1>
  <div class="dashboard">
    <div class="card">
      <h2>Speed</h2>
      <p id="speed">-- km/h</p>
      <div class="progress"><div id="speed-bar" class="bar"></div></div>
    </div>
    <div class="card">
      <h2>Impact</h2>
      <p id="impact">-- m/s²</p>
      <div class="progress"><div id="impact-bar" class="bar"></div></div>
    </div>
    <div class="card">
      <h2>Angle</h2>
      <p id="angle">-- °</p>
    </div>
    <div class="card">
      <h2>Swing Type</h2>
      <p id="type">--</p>
    </div>
    <div class="card">
      <h2>Session Stats</h2>
      <p id="maxSpeed">Max Speed: -- km/h</p>
      <p id="maxImpact">Max Impact: -- m/s²</p>
      <p id="swingCount">Swings: --</p>
      <button onclick="downloadCSV()">Download CSV</button>
    </div>
  </div>
  <script>
    async function updateData(){
      const res = await fetch('/data');
      const data = await res.json();
      document.getElementById("speed").innerText = data.speed.toFixed(2);
      document.getElementById("impact").innerText = data.impact.toFixed(2);
      document.getElementById("angle").innerText = data.angle.toFixed(1);
      document.getElementById("type").innerText = data.type;
      document.getElementById("maxSpeed").innerText = "Max Speed: "+data.maxSpeed.toFixed(2);
      document.getElementById("maxImpact").innerText = "Max Impact: "+data.maxImpact.toFixed(2);
      document.getElementById("swingCount").innerText = "Swings: "+data.swingCount;
      document.getElementById("speed-bar").style.width = Math.min(data.speed,50)+"%";
      document.getElementById("impact-bar").style.width = Math.min(data.impact,50)+"%";
    }
    setInterval(updateData, 5);

    function downloadCSV(){
      window.location.href = "/download";
    }
  </script>
</body>
</html>
)rawliteral";

// ======== Latest Swing Data ========
struct SwingData {
  float speed;
  float impact;
  float angle;
  String type;
  float maxSpeed;
  float maxImpact;
  int swingCount;
};
SwingData currentData = {0,0,0,"--",0,0,0};

// ======== Web Handlers ========
void handleRoot(){ server.send(200,"text/html",htmlPage); }

void handleData(){
  String json = "{";
  json += "\"speed\":"+String(currentData.speed)+",";
  json += "\"impact\":"+String(currentData.impact)+",";
  json += "\"angle\":"+String(currentData.angle)+",";
  json += "\"type\":\""+currentData.type+"\",";
  json += "\"maxSpeed\":"+String(currentData.maxSpeed)+",";
  json += "\"maxImpact\":"+String(currentData.maxImpact)+",";
  json += "\"swingCount\":"+String(currentData.swingCount)+"}";
  server.send(200,"application/json",json);
}

void handleDownload(){
  String csv = "Speed(km/h),Impact(m/s^2),Angle(°),Type\n";
  for(int i=0;i<swingIndex;i++){
    csv += String(swingData[i].speed)+","+String(swingData[i].impact)+","+String(swingData[i].angle)+","+swingData[i].type+"\n";
  }
  server.sendHeader("Content-Type","text/csv");
  server.sendHeader("Content-Disposition","attachment; filename=swing_data.csv");
  server.send(200,"text/csv",csv);
}

// ======== Setup ========
void setup() {
  Serial.begin(115200);
  Wire.begin(26,25);

  pinMode(ledGreen, OUTPUT);
  pinMode(ledOrange, OUTPUT);
  pinMode(ledRed, OUTPUT);

  Serial.println("Initializing MPU6050...");
  mpu.initialize();
  if(!mpu.testConnection()){ Serial.println("MPU6050 failed!"); while(1); }

  // ======= Calibration =======
  Serial.println("Keep racket still for 3 seconds...");
  int calTime = 3000;
  unsigned long start = millis();
  long axSum=0, aySum=0, azSum=0, gxSum=0, gySum=0, gzSum=0;
  int samples = 0;
  while(millis()-start<calTime){
    int16_t ax,ay,az,gx,gy,gz;
    mpu.getMotion6(&ax,&ay,&az,&gx,&gy,&gz);
    axSum+=ax; aySum+=ay; azSum+=az;
    gxSum+=gx; gySum+=gy; gzSum+=gz;
    samples++;
    delay(1);
  }
  axOffset=axSum/(float)samples; ayOffset=aySum/(float)samples; azOffset=azSum/(float)samples;
  gxOffset=gxSum/(float)samples; gyOffset=gySum/(float)samples; gzOffset=gzSum/(float)samples;
  Serial.println("Calibration done!");

  // ======= Start Wi-Fi AP =======
  WiFi.softAP(ssid,password);
  Serial.print("AP started: "); Serial.println(ssid);
  Serial.print("Connect to: "); Serial.println(WiFi.softAPIP());

  server.on("/", handleRoot);
  server.on("/data", handleData);
  server.on("/download", handleDownload);
  server.begin();

  lastTime = millis();
}

// ======== Main Loop ========
void loop() {
  server.handleClient();

  int16_t ax,ay,az,gx,gy,gz;
  mpu.getMotion6(&ax,&ay,&az,&gx,&gy,&gz);

  float Ax = (ax-axOffset)/16384.0;
  float Ay = (ay-ayOffset)/16384.0;
  float Az = (az-azOffset)/16384.0;
  float Gx = (gx-gxOffset)/131.0;
  float Gy = (gy-gyOffset)/131.0;
  float Gz = (gz-gzOffset)/131.0;

  unsigned long currentTime = millis();
  float dt = (currentTime - lastTime)/1000.0;
  lastTime = currentTime;

  // Kalman filter
  float Ax_f = kAx.update(Ax); float Ay_f = kAy.update(Ay); float Az_f = kAz.update(Az);
  float Gx_f = kGx.update(Gx); float Gy_f = kGy.update(Gy); float Gz_f = kGz.update(Gz);

  // Gravity filter
  gravity = alpha*gravity + (1-alpha)*Az_f;
  float linAccZ = (Az_f - gravity)*9.81;
  float linAccTotal = sqrt((Ax_f*9.81)*(Ax_f*9.81)+(Ay_f*9.81)*(Ay_f*9.81)+linAccZ*linAccZ);
  float angularVelocity = sqrt(Gx_f*Gx_f + Gy_f*Gy_f + Gz_f*Gz_f);

  // Detect swing start
  if(!swingStarted && linAccTotal>15){
    swingStarted=true; velocity=0; impactShock=linAccTotal; peakAngularVelocity=angularVelocity; swingAngle=0; swingStartTime=millis();
    currentData.type="Forehand";
  }
  Serial.println(linAccTotal);
  if(swingStarted){
    velocity += linAccZ*dt;
    if(linAccTotal>impactShock) impactShock=linAccTotal;
    if(angularVelocity>peakAngularVelocity) peakAngularVelocity=angularVelocity;
    swingAngle += Gy_f*dt;

    if(linAccTotal<10){    ////////////////
      float speed_kmh = fabs(velocity)*3.6;
      currentData.speed = speed_kmh; currentData.impact=impactShock; currentData.angle=fabs(swingAngle); 
      currentData.type=currentData.type;
      currentData.maxSpeed=max(maxSpeed,speed_kmh); maxSpeed=currentData.maxSpeed;
      currentData.maxImpact=max(maxImpact,impactShock); maxImpact=currentData.maxImpact;
      swingCount++; currentData.swingCount=swingCount;
    
      // Store for CSV
      if(swingIndex<MAX_SWINGS){
        swingData[swingIndex].speed=speed_kmh;
        swingData[swingIndex].impact=impactShock;
        swingData[swingIndex].angle=fabs(swingAngle);
        swingData[swingIndex].type=currentData.type;
        swingIndex++;}
      //////////////////////////

      // LED alerts
      digitalWrite(ledGreen,speed_kmh<20);
      digitalWrite(ledOrange,(speed_kmh>=20 && speed_kmh<35));
      digitalWrite(ledRed,speed_kmh>=35);

      swingStarted=false;
      Serial.printf("Speed: %.2f km/h | Impact: %.2f m/s² | Angle: %.2f° | Type: %s\n",
                    speed_kmh, impactShock, swingAngle, currentData.type.c_str());
    
    }
  }
  

  delay(10);
}
