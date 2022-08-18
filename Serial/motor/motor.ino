#define dirPin 2
#define stepPin 3
#define dirPin2 4
#define stepPin2 5
#define stepsPerRevolution 200
#define enablePin 6
#define enablePin2 7
#define emagPin 21

#define SQUARE_FULL LOW
#define SQUARE_EMPTY HIGH
#define SQUARE_INVALID 2
#define DEBOUNCE 200

typedef struct sensorVal {
  int val;
  int diff = 0;
}sensorVal;

//static const int mux7_pin = 38
static const int mux0_pin = 30;
static const int select_pin2 = 53;
static const int select_pin1 = 52;
static const int select_pin0 = 51;
sensorVal sensors[8][12];

//using this struct as a debouncer
//we have to see a different value than what's in the array DEBOUNCE number of times
//before we swap it, we use diff to keep track of the number of times we've seen a new number

void set_chess_start() {
  //set initial board positions to 1
  for(int i =2; i<11; i++){
    sensors[0][i].val = SQUARE_FULL; 
    sensors[1][i].val = SQUARE_FULL; 
    sensors[6][i].val = SQUARE_FULL; 
    sensors[7][i].val = SQUARE_FULL; 
  }
}

void invalidate_sensors() {
  for(auto& row  : sensors) {
    for(auto& sensor : row) {
      sensor.val = SQUARE_INVALID;
      sensor.diff = 0;
    }
  }
}

void setSelectPins(int rowNum) {
  //set the selector to choose row 0-7
    digitalWrite(select_pin0, rowNum & 0x1);
    digitalWrite(select_pin1, rowNum & 0x2);
    digitalWrite(select_pin2, rowNum & 0x4);
}

void update_sensors() {
  for (int row = 0; row < 8; ++row) {
    setSelectPins(row);
    for(int col = 0; col < 12; ++col) {
      const int pin = mux0_pin + col;
      const int value = digitalRead(pin);
      sensorVal& sensor = sensors[row][col];
      if(sensor.val == value){
        sensor.diff = 0;
      }
      else {
        if(sensor.diff < DEBOUNCE) {
          sensor.diff += 1;
        }
        else {
          sensor.val = value;
          char diff_char = value == SQUARE_FULL ? '+' : '-';
          Serial.print(diff_char);
          Serial.print(row, 16);
          Serial.println(col, 16);
        }
      }
    }
  }
}

void save_sensor_state() {
  for(auto& row : sensors) {
    for(auto& sensor : row) {
      sensor.diff = 0;
    }
  }
}

bool electro = false;

void setup() {
  Serial.begin(115200);
  pinMode(stepPin, OUTPUT);
  pinMode(dirPin, OUTPUT);
  pinMode(stepPin2, OUTPUT);
  pinMode(dirPin2, OUTPUT);
  pinMode(enablePin, OUTPUT);
  pinMode(emagPin, OUTPUT);
  digitalWrite(stepPin, LOW);
  digitalWrite(stepPin2, LOW);
  digitalWrite(enablePin, HIGH);
  digitalWrite(enablePin2, HIGH);
  digitalWrite(emagPin, LOW);

  invalidate_sensors();
  pinMode(select_pin0, OUTPUT);
  pinMode(select_pin1, OUTPUT);
  pinMode(select_pin2, OUTPUT);
  
  for(int col = 0; col < 12; col++) {
    const int pin = mux0_pin + col;
    pinMode(pin, INPUT_PULLUP);
  }
}


char next_cmd_char() {
  while(!Serial.available()) {
    // do nothing
  }
  return Serial.read();
}

enum D {
  LEFT, RIGHT, UP, DOWN, UP_LEFT, UP_RIGHT, DOWN_LEFT, DOWN_RIGHT
};


void move(int drection, int steps) {
    digitalWrite(enablePin, LOW);
    digitalWrite(enablePin2, LOW);
    bool doSteps1 = HIGH;
    bool doSteps2 = HIGH;
    switch(drection) {
    case DOWN:
      //Double check these my dude
      digitalWrite(dirPin, HIGH);
      digitalWrite(dirPin2, LOW);
      // Serial.write("d");
      break;
    case UP:
      digitalWrite(dirPin, LOW);
      digitalWrite(dirPin2, HIGH);
      // Serial.write("u");
      break;
    case LEFT:
      digitalWrite(dirPin, LOW);
      digitalWrite(dirPin2, LOW);
      // Serial.write("l");
      break;
    case RIGHT:
      digitalWrite(dirPin, HIGH);
      digitalWrite(dirPin2, HIGH);
      // Serial.write("r");
      break;
    case UP_LEFT:
      digitalWrite(dirPin, LOW);
      doSteps2 = LOW;
      steps *= 2;
      break;
    case UP_RIGHT:
      digitalWrite(dirPin2, HIGH);
      doSteps1 = LOW;
      steps *= 2;
      break;
    case DOWN_LEFT:
      digitalWrite(dirPin2, LOW);
      doSteps1 = LOW;
      steps *= 2;
      break;
    case DOWN_RIGHT:
      digitalWrite(dirPin, HIGH);
      doSteps2 = LOW;
      steps *= 2;
      break;
  }
  for (int i = 0; i < steps; i++) {
    // These four lines result in 1 step:
    digitalWrite(stepPin, doSteps1);
    digitalWrite(stepPin2, doSteps2);
    delayMicroseconds(2000);
    digitalWrite(stepPin, LOW);
    digitalWrite(stepPin2, LOW);
  }
  digitalWrite(enablePin, HIGH);
  digitalWrite(enablePin2, HIGH);
  //time for a step is 2000 microseconds according to the tutorial

}

void set_electro(bool state) {
  if (state == false){
    electro = false;
    digitalWrite(emagPin, LOW);
    // Serial.write("Electo Off");
  }
  else {
    electro = true;
    digitalWrite(emagPin, HIGH);
    // Serial.write("Electo On");
  }
}

template<int N>
int next_n_digit() {
  char buf[N];
  for(int i = 0; i < N; ++i) buf[i] = next_cmd_char();
  return atoi(buf); 
}

bool calibrate;
    
// execute command sequence until newline
void execute_cmds() {
  char c;
  int steps;
  do {
    c = next_cmd_char();
    int dir;
    if(c == 'X') {
      calibrate = true;
      continue;
    }
    if(c == 'P') {
      int pin = next_n_digit<2>();
      Serial.println(digitalRead(pin));
    }
    // move
    switch(c) {
      case 'r':
        dir = RIGHT;
        break;
      case 'l':
        dir = LEFT;
        break;
      case 'u': 
        dir = UP;
        break;
      case 'd':
        dir = DOWN;
        break;
      case 'U':
        c = next_cmd_char();
        dir = c == 'r' ? UP_RIGHT : UP_LEFT;
        break;
      case 'D':
        c = next_cmd_char();
        dir = c == 'r' ? DOWN_RIGHT : DOWN_LEFT;
        break;
      case 'e':
        set_electro(false);
        continue;
      case 'E':
        set_electro(true);
        continue;
      default:
        continue;
    }
    if(calibrate) {
      steps = next_n_digit<4>();
    }
    else {
      steps = next_n_digit<2>();
      steps *= 112.5;
    }
    move(dir, steps);
    calibrate = false;
  } while(c != '\n');
}

void loop() {
  //Serial.println("starting new loop");
  // read command if any
  if(Serial.available()) {
    save_sensor_state();
    execute_cmds();
  }
  update_sensors();
}
