#include <Arduino.h>
#include <WiFi.h>
#include <ESP32Servo.h>

const char *ssid = "moong";
const char *password = "09876543";

// Server on port 80
WiFiServer server(80);

const int ledPin = 12;      
const int servoPin = 13;     

Servo myServo;
bool doorIsOpen = false;

void setup() {
  Serial.begin(115200);

  pinMode(ledPin, OUTPUT);

  myServo.attach(servoPin);
  myServo.write(0); 

  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected.");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  server.begin();
}

void loop() {
  WiFiClient client = server.available();

  if (client) {
    Serial.println("New Client.");
    String currentLine = "";

    while (client.connected()) {
      if (client.available()) {
        char c = client.read();
        Serial.write(c);
        currentLine += c;

        if (c == '\n') {
          if (currentLine.indexOf("GET /OPEN") >= 0) {
            if (!doorIsOpen) {
              digitalWrite(ledPin, 128);  // LED indicates "door open" state
              myServo.write(90);          // Rotate servo to 90 degrees (open position)
              doorIsOpen = true;
              Serial.println("Door opened.");
            }
          } else if (currentLine.indexOf("GET /CLOSE") >= 0) {
            if (doorIsOpen) {
              digitalWrite(ledPin, 0);    // LED off for "door closed" state
              myServo.write(0);           // Rotate servo back to 0 degrees (closed position)
              doorIsOpen = false;
              Serial.println("Door closed.");
            }
          }

          // Send minimal HTTP response and close connection
          client.println("HTTP/1.1 200 OK");
          client.println("Content-type:text/html");
          client.println("Connection: close");  
          client.println();  
          client.println("Command received");  
          client.stop();  
          Serial.println("Client disconnected.");
          break;  
        }
      }
    }
  }
}
