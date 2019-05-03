#include <SPI.h>
#include <nRF24L01.h>
#include <RF24.h>

RF24 radio(7, 8); //CNS, CE
const byte address[6] = "00001";


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
  radio.openReadingPipe(0, address);
  radio.setPALevel(RF24_PA_MIN);
  radio.startListening();
  radio.setRetries(15, 15);
  Serial.print("Channel: ");
  Serial.println(radio.getChannel());
  radio.printDetails();
}

void loop() {
  if (radio.available()) {
    char text[32] = {0};
    radio.read(&text, sizeof(text));
    Serial.print("Received message: ");
    Serial.println(text);
  } else {
    //    Serial.println("Radio not available...");
  }
}
