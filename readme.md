## timetable - epaper signs at every classroom displaying current and future occupation

-   **`epaper-controller`**: Receives framebuffer updates and hibernation requests and handles them accordingly.
-   **`lora-transceiver`**: Forwards LoRa packets received via serial to the `epaper-controller`. In the future, this connection will be bidirectional, thus _transceiver_.
-   **`server`**: Responsible for sending out the framebuffer updates and hibernation requests when needed.
