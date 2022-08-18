
enum State {
  EMPTY, FULL
};

constexpr size_t kGridWidth = 2;
constexpr size_t kGridHeight = 2;
constexpr size_t kGridArea = kGridHeight*kGridWidth;

constexpr int kSensorPinMin = 22; // AVOID PIN 0/1. This wasted an hour of my time...
constexpr int kSensorPinMax = kSensorPinMin + kGridArea - 1; //(inclusive)


inline State read_sensor(int row, int col) {
  const int pin_idx = col + row*kGridWidth + kSensorPinMin;
  const int pin_val = digitalRead(pin_idx);
  return pin_val == HIGH ? FULL : EMPTY; 
}

void send_delta(int row, int col, State new_state) {
  if(new_state == EMPTY) Serial.print('-');
  else Serial.print('+');

  // pretend we are reading a7,b7,a6,b6
  Serial.print(1+row, HEX);
  Serial.print(2+col, HEX);
  Serial.println();
}

struct SensorState {
  State state;
  int debounce_count;
};

SensorState sensor_grid[kGridWidth][kGridHeight];

constexpr int kElectroPin = 2;
// range 0-24: 5 bits for each x/y
// motor pos encoded in pins 4-13 for now
constexpr int kMotorPosPinMin = kElectroPin + 2;
constexpr int kMotorPosPinMax = kMotorPosPinMin + 9;

#include <AccelStepper.h>

constexpr int kStepPin = 53, kDirPin = 52;

AccelStepper stepper(
  AccelStepper::MotorInterfaceType::DRIVER,
  kStepPin, kDirPin
);

void setup() {
  Serial.begin(115200);
  stepper.setMaxSpeed(100);
  stepper.setAcceleration(30);
  return;
  for(int sens_pin = kSensorPinMin; sens_pin <= kSensorPinMax; ++sens_pin) {
    pinMode(sens_pin, INPUT_PULLUP);
  }
  pinMode(kElectroPin, OUTPUT);
  for(int motor_pos_pin = kMotorPosPinMin; motor_pos_pin <= kMotorPosPinMax; ++motor_pos_pin) {
    pinMode(motor_pos_pin, OUTPUT);
  }
  for(auto& sensor_row : sensor_grid) {
    for(auto& sensor : sensor_row) {
      sensor.state = EMPTY;
      sensor.debounce_count = 0;
    }
  }
}

constexpr int kDebounceLen = 100;

char next_cmd_char() {
  while(!Serial.available()) {
    // do nothing
  }
  return Serial.read();
}

int hex_to_int(char str[]) {
  return strtol(str, 0, 16);
}

void set_motor_pos_pins(int row, int col) {
  for(int bit = 0; bit < 5; ++bit) {
    digitalWrite(kMotorPosPinMin + bit, row & 1);
    row >>= 1;
  }
  for(int bit = 5; bit < 10; ++bit) {
    digitalWrite(kMotorPosPinMin + bit, col & 1);
    col >>= 1;
  }
}

void move(int to_row, int to_col) {
  static int cur_row = 0;
  static int cur_col = 0;
  const int dy = to_row > cur_row ? 1 : -1;
  const int dx = to_col > cur_col ? 1 : -1;

  bool is_done = false;
  do {
    is_done = true;
    if(cur_row != to_row) {
      cur_row += dy;
      is_done = false;
    }
    if(cur_col != to_col) {
      cur_col += dx;
      is_done = false;
    }
    set_motor_pos_pins(cur_row, cur_col);
    delay(750);
  } while(!is_done);
}

void set_electro(bool state) {
  digitalWrite(kElectroPin, state);
  delay(1500);
}

// execute command sequence until newline
void execute_cmds() {
  char c;
  do {
    c = next_cmd_char();
    // move
    if(c == 'm') {
      char buf[3];
      buf[2] = 0;
      for(int i = 0; i < 2; ++i) buf[i] = next_cmd_char();
      const int to_row = hex_to_int(buf);
      for(int i = 0; i < 2; ++i) buf[i] = next_cmd_char();
      const int to_col = hex_to_int(buf);
      move(to_row, to_col);
    }
    // turn on electro
    else if(c == 'E') {
      set_electro(true);
    }
    // turn off electro
    else if(c == 'e') {
      set_electro(false);
    }
    // everything else is ignored (include trailing/leading '\r')
  } while(c != '\n');
}

void loop() {
  Serial.println("starting new loop");

  stepper.moveTo(600);
  stepper.runToPosition();

  delay(1000);

  stepper.moveTo(0);
  stepper.runToPosition();

  delay(1000);

  stepper.moveTo(-1000);
  stepper.runToPosition();
  
  delay(1000);
  return;


  // read command if any
  if(Serial.available()) {
    execute_cmds();
  }
  for(int row = 0; row < kGridWidth; ++row) {
    for(int col = 0; col < kGridHeight; ++col) {
      const State new_state = read_sensor(row, col);
      auto& old_state = sensor_grid[row][col];
      
      if(new_state != old_state.state) {
        if(old_state.debounce_count < kDebounceLen) {
          ++old_state.debounce_count;
          if(old_state.debounce_count == kDebounceLen) {
            old_state.state = new_state;
            send_delta(row, col, new_state);
          }
        }
      }
      else {
        old_state.debounce_count = 0;
      }
    }
  }
}
