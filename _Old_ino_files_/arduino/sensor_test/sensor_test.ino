// classic STL alg, set target but retrieve its old value
template<class T, class Arg>
T exchange(T& target, Arg&& arg) {
  const T old_val = target;
  target = static_cast<Arg&&>(arg); // We don't have std::forward
  return old_val;
}

constexpr float kAnalogThresh  = 1.5;

float adc_ref() {
  return 5.0;  
}

float read_analog(const int pin) {
  static constexpr int resolution = 1024;
  return static_cast<float>(analogRead(pin)) / resolution * adc_ref();
}

constexpr int kGridHeight = 2;
constexpr int kGridWidth = 2;
constexpr int kGridArea = 4;

using state_t = char;
constexpr state_t kStateNorth = 'N';
constexpr state_t kStateSouth = 'S';
constexpr state_t kStateEmpty = ' ';


constexpr int kAnalogPinBase = A0;
constexpr int kAnalogPinMax = A15;
static_assert(kAnalogPinBase + kGridArea <= kAnalogPinMax);

using state_t = char; // avr-g++ is seeming to get confused
state_t get_board_state_at(const int row, const int col) {
  const int flat_index = row * kGridWidth + col;
  const float analog_val = read_analog(kAnalogPinBase + flat_index);
  // Serial.print("Pin ");
  // Serial.print(flat_index);
  // Serial.print(' ');
  // Serial.println(analog_val);

  if(analog_val >= kAnalogThresh) return kStateNorth;
  else if (analog_val <= -kAnalogThresh) return kStateSouth;
  else return kStateEmpty;
}

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
  for(int analog_pin = kAnalogPinBase; analog_pin <= kAnalogPinMax; ++analog_pin) {
    pinMode(analog_pin, INPUT);
  }
}

// draws board every time it changes
void draw_board_if_delta() {
  static state_t board_state[kGridHeight][kGridWidth];
  bool has_delta = false;
  for(int row = 0; row < kGridHeight; ++row) {
    for(int col = 0; col < kGridWidth; ++col) {
      const auto new_state = get_board_state_at(row, col);
      const auto old_state = exchange(board_state[row][col], new_state);
      if(new_state != old_state) has_delta = true;
    }
  }
  
  auto print_horiz_line = [] {
    Serial.println();
    for(int col = 0; col < 2*kGridWidth + 1; ++col) {
      Serial.print('-');
    }
    Serial.println();
  };

  if(has_delta) {
    // for nice extra space
    Serial.println();
    Serial.println();
    
    print_horiz_line();
    for(int row = 0; row < kGridHeight; ++row) {
      Serial.print('|');
      for(int col = 0; col < kGridWidth; ++col) {
        Serial.print(board_state[row][col]);
        Serial.print('|');
      }
      print_horiz_line();
    }
  }
}

void plot_vals() {
  for(int i = 0; i < kGridArea; ++i) {
    const int pin = i + kAnalogPinBase;
    Serial.print('A');
    Serial.print(pin);
    Serial.print('_');
    Serial.print(i/kGridWidth);
    Serial.print('_');
    Serial.print(i%kGridWidth);
    Serial.print(':');
    Serial.print(read_analog(pin));
    Serial.print('\t');
  }
  Serial.println();
}

void loop() {
  using fn_t = void (*)();
  constexpr static fn_t fns[2] = {draw_board_if_delta, plot_vals};
  static int fn_idx = 0;

  int peek = Serial.peek();
  if(peek == 't') {
    fn_idx = !fn_idx;
  }
  while(peek != -1) {
    peek = Serial.read();
  }
  // invoke function
  fns[fn_idx]();
}
