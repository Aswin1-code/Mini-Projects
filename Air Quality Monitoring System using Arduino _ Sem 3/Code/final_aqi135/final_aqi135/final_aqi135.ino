#include <Wire.h> 
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27,16,2);  // set the LCD address to 0x27 for a 16 chars and 2 line display
int i=0;
int n=100;
int good135=350;  //350
int bad135=700;   //700
int lpg_leak=300;  //900
void setup()
{
  lcd.init();                      // initialize the lcd 
  lcd.init();
  // Print a message to the LCD.
  lcd.backlight();
  pinMode(8,OUTPUT);
  pinMode(10,OUTPUT);
  pinMode(9,OUTPUT);
  pinMode(11,OUTPUT);
  

      

  // Initialize the LCD
  lcd.begin(16, 2);
  for(int pin=11;pin<=8;pin--)
   {
     digitalWrite(pin,HIGH);
     delay(200);
     digitalWrite(pin,LOW);
     delay(50);
   }
    for(int pin=8;pin<=11;pin++)
   {
     digitalWrite(pin,HIGH);
     delay(200);
     digitalWrite(pin,LOW);
     delay(50);
   }
  lcd.setCursor(0,0);
  lcd.print("     Welcome!  ");
  delay(500); 
  lcd.clear(); 
  lcd.setCursor(0,0);
  lcd.print("   *SensAir*  ");
  delay(500);
  lcd.clear();// Set up the LCD's number of columns and rows
  lcd.print("  Air Quality"); 
  lcd.setCursor(0,1);
  lcd.print("    Monitor ");
  delay(500); 


        // Display for 2 seconds
  lcd.clear();

  Serial.begin(9600); // Initialize serial communication for debugging
}
void loop()
{    
    
     int gs135=analogRead(A0);
     int gs5=analogRead(A1);
     lcd.clear();
     

     lcd.setCursor(0, 0); // Set cursor to first line
     lcd.print("Air Quality:");
     delay(100);
      Serial.print("  mq 5 : ");
     Serial.print(gs5);
     delay(1000);
    Serial.println(" ");
     Serial.print("  mq 135 : ");
     Serial.print(gs135);
     delay(1000);
     if(gs5<=lpg_leak)
     {

     
     if(gs135<good135&&gs135>0)
     {
      
      lcd.setCursor(0,1);
      lcd.print(" Good ");
      delay(100);
      digitalWrite(9,LOW);
      delay(800);
      digitalWrite(8,LOW);
      delay(800);
     
      analogWrite(10,120);
      delay(800);

     }
     else if(gs135>=good135&&gs135<bad135)
     {
      lcd.setCursor(0,1);
      lcd.print(" Moderate ");
     
       delay(100);
      digitalWrite(10,HIGH);
      delay(800);
     
      analogWrite(9,75);
      delay(800);

      digitalWrite(8,LOW);
      delay(800);
      

     }
     else if(gs135>=bad135) 
     {
     lcd.setCursor(0,1);
      lcd.print(" Bad");
      delay(100);
      digitalWrite(10,HIGH);
      delay(800);
     
      digitalWrite(9,HIGH);
      delay(800);
      digitalWrite(8,HIGH);
      delay(800);
      
       digitalWrite(11,HIGH);
      delay(800);
      
     }
  }
  
  else if(gs5>lpg_leak)
  {
      lcd.setCursor(0,1);
      lcd.println("Gas Leak");
      delay(1000);
  
  
     for(int pin=8;pin<=11;pin++)
   {
     digitalWrite(pin,HIGH);
     delay(200);
     digitalWrite(pin,LOW);
     delay(50);
     
   }
    for(int pin=11;pin<=8;pin--)
   {
     digitalWrite(pin,HIGH);
     delay(200);
     digitalWrite(pin,LOW);
     delay(50);
   }
  }
} 

    