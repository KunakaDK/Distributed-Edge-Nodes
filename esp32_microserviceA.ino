#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <time.h>

// ================= WIFI =================
const char* ssid = "Redmi Note 11 Pro";
const char* password = "1234567890";

// ================= MICROSERVICE B =================
const char* serverURL = "http://10.17.146.189:8001/traiter";

// ================= NTP =================
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 0;
const int daylightOffset_sec = 0;

// ================= TIMING =================
unsigned long lastSend = 0;
// La documentation demande une mesure par seconde (1000 ms)
const unsigned long interval = 1000; 

// ================= DATA STRUCT =================
struct SensorData {
  float temperature;
  float humidity;
  float pressure;

  float ax, ay, az;
  float gx, gy, gz;

  float voltage;
  float current;

  double lat;
  double lon;
};

SensorData prevData;

// ================= UTILS =================
float randFloat(float min, float max) {
  return min + ((float)random(0, 10000) / 10000.0f) * (max - min);
}

float clamp(float v, float min, float max) {
  if (v < min) return min;
  if (v > max) return max;
  return v;
}

float smooth(float previous, float current) {
  return previous * 0.7f + current * 0.3f;
}

// ================= DATA GENERATION =================

void generateData(SensorData &d) {
  d.temperature = randFloat(20.0, 40.0);
  d.humidity = randFloat(30.0, 90.0);
  d.pressure = randFloat(980.0, 1030.0);

  d.ax = randFloat(-10.0, 10.0);
  d.ay = randFloat(-10.0, 10.0);
  d.az = randFloat(-10.0, 10.0);

  d.gx = randFloat(-0.1, 0.1);
  d.gy = randFloat(-0.1, 0.1);
  d.gz = randFloat(-0.1, 0.1);

  d.voltage = randFloat(3.0, 5.0);
  d.current = randFloat(0.1, 2.0);

  d.lat = 35.5765 + randFloat(-0.001, 0.001);
  d.lon = -5.3682 + randFloat(-0.001, 0.001);
}

// ================= DATA CLEANING =================
void cleanData(SensorData &d) {
  d.temperature = clamp(d.temperature, 20, 40);
  d.humidity = clamp(d.humidity, 30, 90);
  d.pressure = clamp(d.pressure, 980, 1030);

  d.temperature = smooth(prevData.temperature, d.temperature);
  d.humidity = smooth(prevData.humidity, d.humidity);
  d.pressure = smooth(prevData.pressure, d.pressure);

  prevData = d;
}

// ================= UTC TIMESTAMP =================

String getTimestamp() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    return "1970-01-01T00:00:00.000Z";
  }

  char timeString[30];
  strftime(timeString, sizeof(timeString),
           "%Y-%m-%dT%H:%M:%S.000Z",
           &timeinfo);

  return String(timeString);
}

// ================= JSON CREATION =================

String createJSON(SensorData &d) {
  StaticJsonDocument<512> doc;

 
  doc["device_id"] = "edge-node-01"; 
  doc["timestamp"] = getTimestamp();

  doc["temperature"] = d.temperature;
  doc["humidity"] = d.humidity;
  doc["pressure"] = d.pressure;

  JsonObject acceleration = doc.createNestedObject("acceleration");
  acceleration["x"] = d.ax;
  acceleration["y"] = d.ay;
  acceleration["z"] = d.az;

  JsonObject gyroscope = doc.createNestedObject("gyroscope");
  gyroscope["x"] = d.gx;
  gyroscope["y"] = d.gy;
  gyroscope["z"] = d.gz;

  doc["voltage"] = d.voltage;
  doc["current"] = d.current;

  JsonObject gps = doc.createNestedObject("gps");
  gps["lat"] = d.lat;
  gps["lon"] = d.lon;

  String payload;
  serializeJson(doc, payload);

  return payload;
}

// ================= HTTP POST =================
void sendData(String payload) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected");
    return;
  }

  HTTPClient http;
  http.begin(serverURL);
  http.addHeader("Content-Type", "application/json");

  int httpResponseCode = http.POST(payload);
  
  Serial.print("HTTP Response: ");
  Serial.println(httpResponseCode);
  
  // Afficher la réponse du serveur pour le débogage 
  if(httpResponseCode > 0) {
    String response = http.getString();
    Serial.println("Server reply: " + response);
  }

  http.end();
}

// ================= SETUP =================
void setup() {
  Serial.begin(115200);
  randomSeed(esp_random());

  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected");

  // Initialisation du temps pour les Timestamps ISO 8601 UTC
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  Serial.println("NTP initialized");
}

// ================= LOOP =================
void loop() {
  if (millis() - lastSend >= interval) {
    lastSend = millis();
    SensorData data;

    generateData(data); // Génère selon les contraintes
    cleanData(data);
    String jsonPayload = createJSON(data);

    // SERIAL OUTPUT
    Serial.println(jsonPayload);

    // HTTP POST TO MICROSERVICE B
    sendData(jsonPayload);
  }
}