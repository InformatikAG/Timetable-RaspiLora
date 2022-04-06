#include <GxEPD.h>
#include <GxGDEW042T2/GxGDEW042T2.h>
#include <GxIO/GxIO_SPI/GxIO_SPI.h>
#include <LoRa.h>
#include <SPI.h>
#include <driver/adc.h>
#include <esp_bt.h>
#include <esp_sleep.h>
#include <esp_wifi.h>

extern "C" {
#include "puff.h"
}

#define DEVICE_ID 1

// general spi stuff
#define SCK 5 // CLK
// not used by the epd, we use a different pin for BUSY
#define MISO 19
#define MOSI 27 // DIN

// lora
#define LORA_SS 18
#define LORA_RST 14
#define LORA_DIO0 26
#define LORA_BAND 866E6

// e paper display
#define EPD_RST 16
#define EPD_SS 2 // CS
#define EPD_DC 17
#define EPD_BUSY 23

#define FRAMEBUFFER_SIZE (400 * 300 / 8) // 15k
#define MAX_PACKET_SIZE 255

GxIO_Class io(SPI, EPD_SS, EPD_DC, EPD_RST);
GxEPD_Class display(io, EPD_RST, EPD_BUSY);

uint8_t frameBuffer[FRAMEBUFFER_SIZE];
uint8_t compressedFrameBuffer[FRAMEBUFFER_SIZE];
size_t compressedFramebufferOffset = 0;
uint8_t packetBuffer[MAX_PACKET_SIZE];
size_t currentTransmissionSize = 0;
bool isReceiving = false;

void swapBuffers() {
    display.init(115200);
    display.drawBitmap(frameBuffer, FRAMEBUFFER_SIZE, 0);
}

void hibernate(uint32_t time_s) {
    esp_sleep_enable_timer_wakeup(time_s * 1000000);

    Serial.printf("Hibernating for %d seconds\n", time_s);
    Serial.flush();

    esp_deep_sleep_start();
}

void setup() {
    Serial.begin(115200);
    delay(100);

    SPI.begin(SCK, MISO, MOSI, 0);

    LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);
    if (!LoRa.begin(LORA_BAND)) {
        Serial.println("LoRa init error");
        for (;;) {}
    }
    Serial.println("LoRa init success");

    adc_power_off();
    esp_wifi_stop();
    esp_bt_controller_disable();

    setCpuFrequencyMhz(80);
}

void loop() {
    size_t packetSize = LoRa.parsePacket();
    if (!packetSize) {
        return;
    }

    LoRa.readBytes(packetBuffer, packetSize);
    Serial.printf("Received LoRa packet of size %d\n", packetSize);

    if (packetBuffer[0] != DEVICE_ID) {
        Serial.println("Packet not destined for this device");
        return;
    }

    // skip device id
    uint8_t* packet = packetBuffer + 1;
    packetSize = packetSize - 1;

    // we are currently in a transmission, append to the buffer
    if (isReceiving) {
        if (packetSize + compressedFramebufferOffset > FRAMEBUFFER_SIZE) {
            Serial.println("Compressed framebuffer too large");
            isReceiving = false;
            compressedFramebufferOffset = 0;
        } else {
            memcpy(compressedFrameBuffer + compressedFramebufferOffset, packet,
                   packetSize);
            compressedFramebufferOffset += packetSize;
        }
    }

    // first packet in a transmission
    else {

        // handle hibernation request
        if (*(uint32_t*)(packet) == 0x1fae9fb3) {
            hibernate(*(uint32_t*)(packet + 4));
        }

        // is data

        isReceiving = true;
        currentTransmissionSize = *(uint16_t*)packet;

        Serial.printf("Begin of transmission of framebuffer (%d bytes)\n",
                      currentTransmissionSize);

        memcpy(compressedFrameBuffer, packet + 2, packetSize - 2);
        compressedFramebufferOffset = packetSize - 2;
    }

    // got all data, decompress and draw
    if (compressedFramebufferOffset >= currentTransmissionSize) {
        isReceiving = false;
        compressedFramebufferOffset = 0;

        Serial.println("End of transmission of framebuffer");

        unsigned long destSize = FRAMEBUFFER_SIZE;
        unsigned long srcSize = currentTransmissionSize;
        int ret = puff(frameBuffer, &destSize, compressedFrameBuffer, &srcSize);
        if (ret != 0) {
            Serial.printf("puff error: %d\n", ret);
            return;
        }

        Serial.printf("Decompressed framebuffer (%d bytes)\n", destSize);

        swapBuffers();
    }
}
