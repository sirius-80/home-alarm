#include <SPI.h>
#include <nRF24L01.h>
#include <RF24.h>

RF24 radio(7, 8); //CNS, CE
const byte address[6] = "00001";
const char* device_id = "6c89f539";

static FILE uartout = {0};

// create a output function
// This works because Serial.write, although of
// type virtual, already exists.
static int uart_putchar (char c, FILE *stream)
{
  Serial.write(c) ;
  return 0 ;
}


void setup() {
  // Enable radio.printDetails to print to serial out
  Serial.begin(115200);
  fdev_setup_stream (&uartout, uart_putchar, NULL, _FDEV_SETUP_WRITE);
  stdout = &uartout;

  Serial.println("Setting up radio...");
  bool ok = radio.begin();
  if (!ok) {
    Serial.println("FAILED TO SETUP RADIO!");
  } else {
    Serial.println("Radio is setup");
  }
  radio.setDataRate(RF24_250KBPS);
  radio.openWritingPipe(address);
  radio.setPALevel(RF24_PA_MIN);
  radio.stopListening();
  radio.printDetails();
}

int read_temperature() {
  // TODO: Replace with actual measurement
  return random(15,35);
}

int read_smoke_ppm() {
  // TODO: Replace with actual measurement
  return random(2, 50);
}

int read_co_ppm() {
  // TODO: Replace with actual measurement
  return random(10, 150);
}

const char* generate_message() {
  static char buffer[32];
  snprintf(buffer, sizeof(buffer), "%s,%d,%d,%d", device_id, read_temperature(), read_smoke_ppm(), read_co_ppm());
  return buffer;
}

void loop() {
  int selector = random(3);
  const char* msg = generate_message();
  bool sent = radio.write(msg, strlen(msg));
  Serial.print("Msg sent[");
  Serial.print(sent);
  Serial.print("]: "); 
  Serial.println(msg);
  delay(1000);
}
