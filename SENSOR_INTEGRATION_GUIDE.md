# Fuel Monitoring Sensor Integration Guide

## Overview
This guide provides comprehensive instructions for connecting fuel monitoring sensors to the School Management System's transport module. The system uses MQTT protocol for real-time telemetry data transmission.

## Hardware Requirements

### 1. Fuel Level Sensor
- **Recommended**: Ultrasonic fuel level sensor (e.g., FLS-D series)
- **Alternative**: Resistive fuel level sensor
- **Specifications**:
  - Operating voltage: 12V DC
  - Output: 4-20mA or 0-5V
  - Accuracy: ±1% full scale
  - Temperature range: -40°C to +85°C

### 2. GPS Module
- **Recommended**: u-blox NEO-8M GPS module
- **Specifications**:
  - UART communication
  - Update rate: 1-10 Hz
  - Accuracy: 2.5m CEP

### 3. Microcontroller/Gateway
- **Recommended**: ESP32 DevKit
- **Features needed**:
  - WiFi connectivity
  - Multiple analog inputs
  - UART for GPS
  - 3.3V and 5V power rails

### 4. Additional Sensors (Optional)
- Speed sensor (Hall effect or Reed switch)
- Engine ON/OFF detection (relay or voltage divider)
- Temperature sensor (DS18B20)

## Software Setup

### 1. MQTT Broker Configuration
The system uses HiveMQ public broker by default. For production:

```bash
# Set environment variables
export MQTT_BROKER_URL=your-mqtt-broker.com
export MQTT_BROKER_PORT=1883
export MQTT_USERNAME=your-username
export MQTT_PASSWORD=your-password
```

### 2. Device Topic Structure
Each bus publishes to: `quantafons/{school_id}/buses/{bus_id}/telemetry`

Example: `quantafons/1/buses/3/telemetry`

## Hardware Wiring

### ESP32 Connections
```
Fuel Sensor (4-20mA):
- Sensor+ -> 12V Power Supply
- Sensor- -> 250Ω Resistor -> GND
- Signal -> ESP32 ADC Pin (GPIO36)

GPS Module:
- VCC -> 3.3V
- GND -> GND  
- TX -> ESP32 RX (GPIO16)
- RX -> ESP32 TX (GPIO17)

Engine Detection:
- Ignition Wire -> Voltage Divider -> ESP32 ADC Pin (GPIO39)

Speed Sensor:
- Signal -> ESP32 Interrupt Pin (GPIO2)
- VCC -> 5V
- GND -> GND
```

### Fuel Level Calculation
For 4-20mA sensor with 250Ω load resistor:
```
Voltage = ADC_Reading * (3.3V / 4095)
Current = Voltage / 250Ω
Fuel_Percentage = (Current - 0.004) / 0.016 * 100
Fuel_Liters = Fuel_Percentage * Tank_Capacity / 100
```

## Arduino Code Example

```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <SoftwareSerial.h>

// WiFi credentials
const char* ssid = "your-wifi-ssid";
const char* password = "your-wifi-password";

// MQTT settings
const char* mqtt_broker = "broker.hivemq.com";
const int mqtt_port = 1883;
const char* mqtt_topic = "quantafons/1/buses/3/telemetry";

// Pin definitions
#define FUEL_SENSOR_PIN 36
#define ENGINE_DETECT_PIN 39
#define SPEED_SENSOR_PIN 2

// GPS Serial
SoftwareSerial gpsSerial(16, 17);

// Variables
float fuelTankCapacity = 80.0; // Liters
volatile int speedPulseCount = 0;
unsigned long lastSpeedTime = 0;

WiFiClient espClient;
PubSubClient client(espClient);

void setup() {
  Serial.begin(115200);
  gpsSerial.begin(9600);
  
  // Setup pins
  pinMode(FUEL_SENSOR_PIN, INPUT);
  pinMode(ENGINE_DETECT_PIN, INPUT);
  pinMode(SPEED_SENSOR_PIN, INPUT_PULLUP);
  
  // Speed sensor interrupt
  attachInterrupt(digitalPinToInterrupt(SPEED_SENSOR_PIN), speedPulseISR, FALLING);
  
  // Connect to WiFi
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  
  // Connect to MQTT
  client.setServer(mqtt_broker, mqtt_port);
  
  Serial.println("System initialized");
}

void loop() {
  if (!client.connected()) {
    reconnectMQTT();
  }
  client.loop();
  
  // Read sensors every 30 seconds
  static unsigned long lastReading = 0;
  if (millis() - lastReading > 30000) {
    sendTelemetry();
    lastReading = millis();
  }
  
  delay(100);
}

void sendTelemetry() {
  // Read fuel level
  int fuelRaw = analogRead(FUEL_SENSOR_PIN);
  float fuelVoltage = fuelRaw * (3.3 / 4095.0);
  float fuelCurrent = fuelVoltage / 250.0; // 250Ω load resistor
  float fuelPercentage = (fuelCurrent - 0.004) / 0.016 * 100;
  float fuelLiters = fuelPercentage * fuelTankCapacity / 100;
  
  // Read engine status
  int engineRaw = analogRead(ENGINE_DETECT_PIN);
  bool engineOn = engineRaw > 2048; // Threshold for 12V detection
  
  // Calculate speed
  float speed = calculateSpeed();
  
  // Get GPS data
  float latitude, longitude;
  bool gpsValid = readGPS(&latitude, &longitude);
  
  // Create JSON payload
  StaticJsonDocument<512> doc;
  doc["timestamp"] = millis();
  doc["fuel_level_liters"] = fuelLiters;
  doc["speed_kmh"] = speed;
  doc["engine_on"] = engineOn;
  
  if (gpsValid) {
    doc["latitude"] = latitude;
    doc["longitude"] = longitude;
  }
  
  // Optional: Add more sensor data
  doc["fuel_flow_lph"] = 0; // Calculate if flow sensor available
  doc["odometer_km"] = 0;   // Calculate from speed integration
  doc["heading"] = 0;       // From GPS or compass
  doc["altitude"] = 0;      // From GPS
  
  String payload;
  serializeJson(doc, payload);
  
  // Publish to MQTT
  if (client.publish(mqtt_topic, payload.c_str())) {
    Serial.println("Telemetry sent: " + payload);
  } else {
    Serial.println("Failed to send telemetry");
  }
}

float calculateSpeed() {
  unsigned long currentTime = millis();
  unsigned long timeDiff = currentTime - lastSpeedTime;
  
  if (timeDiff >= 1000) { // Calculate every second
    // Assume 1 pulse per wheel rotation, wheel circumference = 2m
    float rpm = (speedPulseCount * 60000.0) / timeDiff;
    float speed = rpm * 2.0 * 60.0 / 1000.0; // Convert to km/h
    
    speedPulseCount = 0;
    lastSpeedTime = currentTime;
    
    return speed;
  }
  
  return 0;
}

void speedPulseISR() {
  speedPulseCount++;
}

bool readGPS(float* latitude, float* longitude) {
  // Simplified GPS parsing - use proper NMEA library in production
  if (gpsSerial.available()) {
    String gpsData = gpsSerial.readStringUntil('\n');
    
    // Parse NMEA sentence (implement full parsing)
    if (gpsData.startsWith("$GPGGA")) {
      // Extract latitude and longitude
      // This is a simplified example
      *latitude = 40.7128;  // Example coordinates
      *longitude = -74.0060;
      return true;
    }
  }
  return false;
}

void reconnectMQTT() {
  while (!client.connected()) {
    if (client.connect("ESP32_Bus_3")) {
      Serial.println("Connected to MQTT broker");
    } else {
      delay(5000);
    }
  }
}
```

## Calibration Procedure

### 1. Fuel Sensor Calibration
1. **Empty Tank Calibration**:
   - Drain fuel tank completely
   - Record ADC reading (should correspond to 4mA)
   - Set as 0% fuel level

2. **Full Tank Calibration**:
   - Fill tank completely
   - Record ADC reading (should correspond to 20mA)  
   - Set as 100% fuel level

3. **Linear Interpolation**:
   ```
   Fuel_Percentage = (Current_Reading - Empty_Reading) / (Full_Reading - Empty_Reading) * 100
   ```

### 2. Speed Sensor Calibration
1. Measure wheel circumference accurately
2. Count pulses per wheel rotation
3. Drive a known distance and verify accuracy
4. Adjust calculation formula if needed

## Testing Procedures

### 1. Sensor Validation
```bash
# Test fuel sensor readings
# Connect multimeter to sensor output
# Verify 4-20mA range across full tank

# Test GPS accuracy
# Compare GPS coordinates with known location
# Ensure accuracy within 5 meters
```

### 2. MQTT Communication Test
```bash
# Subscribe to telemetry topic
mosquitto_sub -h broker.hivemq.com -t "quantafons/1/buses/3/telemetry"

# Verify JSON format
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "speed_kmh": 45.2,
  "fuel_level_liters": 65.4,
  "engine_on": true,
  "timestamp": 1635789123456
}
```

### 3. System Integration Test
1. Start the School Management System
2. Check MQTT client connection logs
3. Verify telemetry data appears in dashboard
4. Test fuel anomaly detection
5. Confirm real-time map updates

## Deployment Checklist

- [ ] Hardware properly installed and wired
- [ ] Fuel sensor calibrated
- [ ] GPS receiving satellite signals
- [ ] WiFi connection stable
- [ ] MQTT broker accessible
- [ ] Device publishing to correct topic
- [ ] School Management System receiving data
- [ ] Dashboard displaying real-time updates
- [ ] Alerts triggering correctly
- [ ] Data logging functioning

## Troubleshooting

### Common Issues

1. **No MQTT Connection**:
   - Check WiFi credentials
   - Verify MQTT broker URL and port
   - Test network connectivity

2. **Inaccurate Fuel Readings**:
   - Recalibrate sensor
   - Check wiring connections
   - Verify power supply voltage

3. **GPS Not Working**:
   - Check antenna connection
   - Verify outdoor location for satellite reception
   - Confirm baud rate (9600)

4. **Speed Readings Incorrect**:
   - Verify wheel circumference measurement
   - Check pulse sensor mounting
   - Confirm interrupt pin configuration

### Logs and Monitoring
Monitor these files for troubleshooting:
- Application logs: Check for MQTT connection issues
- Database logs: Verify telemetry data storage
- Network logs: Confirm data transmission

## Production Recommendations

1. **Security**: Use SSL/TLS for MQTT communication
2. **Reliability**: Implement local data buffering
3. **Monitoring**: Set up sensor health checks
4. **Maintenance**: Schedule regular calibration
5. **Backup**: Multiple communication paths (cellular backup)

## Support and Maintenance

For technical support:
1. Check system logs first
2. Verify sensor connections
3. Test MQTT communication
4. Contact support with detailed error information

Regular maintenance schedule:
- Weekly: Check data transmission
- Monthly: Verify sensor accuracy
- Quarterly: Full system calibration
- Annually: Hardware inspection and replacement