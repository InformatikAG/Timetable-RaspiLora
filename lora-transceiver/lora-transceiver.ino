#include <LoRa.h>
#include <SPI.h>

#define SCK 5
#define MISO 19
#define MOSI 27
#define SS 18
#define RST 14
#define DIO0 26
#define BAND 866E6
#define LORA_MAX_PACKET_SIZE 255

void setup() {
    Serial.begin(115200);

    SPI.begin(SCK, MISO, MOSI, SS);
    LoRa.setPins(SS, RST, DIO0);
    if (!LoRa.begin(BAND)) {
        Serial.println("LoRa init error");
        for (;;) {}
    }
    Serial.println("LoRa init success");
}

// holds data to be sent via lora
uint8_t packetBuffer[LORA_MAX_PACKET_SIZE];

// current offset into the packetBuffer
size_t packetBufferOffset = 0;

// length of the lora packet we are currently receiving via serial
size_t currentLoraPacketLen = 0;

// whether we are currently receiving a lora packet via serial
// if yes, data is copied to packetBuffer + packetBufferOffset
bool serialReceiving = false;

// temporary buffer for receiving data via serial
// data is then copied into packetBuffer
uint8_t tempPacketBuffer[LORA_MAX_PACKET_SIZE];

void loop() {
    while (Serial.available()) {
        size_t serialPacketLen = Serial.read(tempPacketBuffer, LORA_MAX_PACKET_SIZE);
        Serial.printf("Received serial packet of size %d\n", serialPacketLen);

        if (serialReceiving) {
            if (packetBufferOffset + serialPacketLen > LORA_MAX_PACKET_SIZE) {
                Serial.println("Packet to large, dropping");
                serialReceiving = false;
                packetBufferOffset = 0;
            } else {
                memcpy(packetBuffer + packetBufferOffset, tempPacketBuffer,
                       serialPacketLen);
                packetBufferOffset += serialPacketLen;
            }
        } else {
            serialReceiving = true;
            currentLoraPacketLen = tempPacketBuffer[0];

            Serial.printf("Begin of transmission of LoRa packet (%d bytes)\n",
                          currentLoraPacketLen);

            // copy data to packet buffer without the length byte
            memcpy(packetBuffer, tempPacketBuffer + 1, serialPacketLen - 1);
            packetBufferOffset = serialPacketLen - 1;
        }

        // if received the full packet, send it
        if (packetBufferOffset == currentLoraPacketLen) {
            Serial.printf("Sending LoRa packet of size %d\n", packetBufferOffset);
            LoRa.beginPacket();
            LoRa.write(packetBuffer, packetBufferOffset);
            LoRa.endPacket();
            Serial.println("CONTROL:ACK");
            packetBufferOffset = 0;
            serialReceiving = false;
        }
    }
}
