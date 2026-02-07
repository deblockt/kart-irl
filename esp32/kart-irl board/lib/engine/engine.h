#pragma once

#include <Arduino.h>

class Motor {
public:
  Motor(int pwmPin, int in1Pin, int in2Pin, int channel);
  void setup();
  // speed: -255 (full reverse) to 255 (full forward)
  void setSpeed(int speed);
  void stop();

private:
  int _pwmPin;
  int _in1Pin;
  int _in2Pin;
  int _channel;
};

void engineSetup(Motor &motor);

// speed: -255 (full reverse) to 255 (full forward)
void engineSetSpeed(int speed);

void engineStop();
