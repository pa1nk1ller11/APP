/*
  Arduino Mega firmware for the Wind Tunnel Control Windows app.

  PC commands over Serial:
    ON       enable the fan at the current speed
    OFF      disable the fan and set speed to 0
    0-100    set fan speed percent

  Telemetry to PC:
    static_pressure dynamic_pressure temperature

  Set FAN_ENABLE_PIN and FAN_PWM_PIN for your actual motor controller before
  running the tunnel. Startup always drives the fan off.
*/

const unsigned long PC_BAUD = 9600;
const unsigned long SENSOR_BAUD = 115200;

const byte FAN_ENABLE_PIN = 7;
const byte FAN_PWM_PIN = 9;
const bool FAN_ENABLE_ACTIVE_HIGH = true;

bool fanEnabled = false;
float fanSpeedPercent = 0.0;

String pcCommandBuffer = "";
String sensorBuffer = "";

void setup() {
  pinMode(FAN_ENABLE_PIN, OUTPUT);
  pinMode(FAN_PWM_PIN, OUTPUT);
  applyFanOutput();

  Serial.begin(PC_BAUD);
  Serial1.begin(SENSOR_BAUD);

  Serial.println("UPDATE: Wind tunnel controller ready");
}

void loop() {
  readPcCommands();
  forwardSensorTelemetry();
}

void readPcCommands() {
  while (Serial.available() > 0) {
    char incoming = char(Serial.read());

    if (incoming == '\r') {
      continue;
    }

    if (incoming == '\n') {
      pcCommandBuffer.trim();
      if (pcCommandBuffer.length() > 0) {
        handlePcCommand(pcCommandBuffer);
      }
      pcCommandBuffer = "";
    } else if (pcCommandBuffer.length() < 32) {
      pcCommandBuffer += incoming;
    } else {
      pcCommandBuffer = "";
      Serial.println("ERROR: Command too long");
    }
  }
}

void handlePcCommand(String command) {
  command.trim();
  command.toUpperCase();

  if (command == "ON") {
    fanEnabled = true;
    applyFanOutput();
    Serial.println("UPDATE: Fan on");
    return;
  }

  if (command == "OFF") {
    fanEnabled = false;
    fanSpeedPercent = 0.0;
    applyFanOutput();
    Serial.println("UPDATE: Fan off");
    return;
  }

  if (isNumericCommand(command)) {
    float requestedSpeed = command.toFloat();
    if (requestedSpeed < 0.0 || requestedSpeed > 100.0) {
      Serial.println("ERROR: Speed input out of bounds");
      return;
    }

    fanSpeedPercent = requestedSpeed;
    fanEnabled = fanSpeedPercent > 0.0;
    applyFanOutput();

    Serial.print("UPDATE: Speed ");
    Serial.print(fanSpeedPercent, 1);
    Serial.println("%");
    return;
  }

  Serial.print("ERROR: Unknown command ");
  Serial.println(command);
}

bool isNumericCommand(String command) {
  if (command.length() == 0) {
    return false;
  }

  bool sawDigit = false;
  bool sawDecimal = false;

  for (unsigned int i = 0; i < command.length(); i++) {
    char c = command.charAt(i);

    if (isDigit(c)) {
      sawDigit = true;
      continue;
    }

    if (c == '.' && !sawDecimal) {
      sawDecimal = true;
      continue;
    }

    return false;
  }

  return sawDigit;
}

void applyFanOutput() {
  bool enableLevel = FAN_ENABLE_ACTIVE_HIGH ? fanEnabled : !fanEnabled;
  digitalWrite(FAN_ENABLE_PIN, enableLevel ? HIGH : LOW);

  int pwmValue = fanEnabled ? round((fanSpeedPercent / 100.0) * 255.0) : 0;
  analogWrite(FAN_PWM_PIN, constrain(pwmValue, 0, 255));
}

void forwardSensorTelemetry() {
  while (Serial1.available() > 0) {
    char incoming = char(Serial1.read());

    if (incoming == '\r') {
      continue;
    }

    if (incoming == '\n') {
      sensorBuffer.trim();
      if (sensorBuffer.length() > 0) {
        Serial.println(sensorBuffer);
      }
      sensorBuffer = "";
    } else if (sensorBuffer.length() < 80) {
      sensorBuffer += incoming;
    } else {
      sensorBuffer = "";
      Serial.println("ERROR: Sensor line too long");
    }
  }
}
