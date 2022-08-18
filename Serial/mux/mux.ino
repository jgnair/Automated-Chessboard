// Code used to read all of the hall effect sensors data from the MUXs
// Library used for mux https://github.com/stechio/arduino-ad-mux-lib / https://www.arduino.cc/reference/en/libraries/analog-digital-multiplexers/
//
//8x12 signals that we need to read
//rows are selected by select bins 0b000 to 0b111 or 0-7
//columns are determined by the pin on the arduino

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

void setup() {
  Serial.begin(115200);
  invalidate_sensors();
  pinMode(select_pin0, OUTPUT);
  pinMode(select_pin1, OUTPUT);
  pinMode(select_pin2, OUTPUT);
  
  for(int col = 0; col < 12; col++) {
    const int pin = mux0_pin + col;
    pinMode(pin, INPUT_PULLUP);
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

void loop() {
  update_sensors();
  delayMicroseconds(5);
}


//  digitalWrite(select_pin, rowNum & 0x1);
//  for(int bitNum = 0; bitNum < 3; ++bitNum) {
//    digitalWrite(select_pin + bitNum, rowNum & 0x1)
//    rowNum >>= 1
//  }
