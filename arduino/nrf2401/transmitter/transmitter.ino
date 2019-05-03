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
  radio.openWritingPipe(address);
  radio.setPALevel(RF24_PA_MIN);
  radio.stopListening();
  Serial.print("Payloadsize: ");
  Serial.println(radio.getPayloadSize());
  Serial.print("Channel: ");
  Serial.println(radio.getChannel());
  radio.printDetails();
}

const char msg1[] = "Hello world!";
const char msg2[] = "Goodbye world!";
const char msg3[] = "Muhahahahahahaaaaa...";
  
const char* select_message(int nr) {
  Serial.print("Selecting msg ");
  Serial.println(nr);
  switch (nr) {
    case 0: return msg1;
    break;
    case 1: return msg2;
    break;
    default: return msg3;
  }
}

void loop() {
  int selector = random(3);
  const char* msg = select_message(selector);
//  const char msg[]  ="Hello world!"; 
  bool sent = radio.write(msg, strlen(msg));
  Serial.print("Msg sent[");
  Serial.print(sent);
  Serial.print("]: "); 
  Serial.println(msg);
  delay(1000);
}
