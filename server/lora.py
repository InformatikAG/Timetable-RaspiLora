from asyncio import StreamReader, StreamWriter, Task, Event, get_event_loop, sleep, create_task, Lock
from zlib import compress
from PIL import Image
from datetime import datetime
import struct

from serial_asyncio import open_serial_connection

MAX_PACKET_SIZE = 255 - 1  # -1 for device id


class Lora:
    port: str
    baudrate: int

    serial_writer: StreamWriter
    serial_reader: StreamReader

    _serial_lock: Lock
    _serial_task: Task
    _control_events: dict[str, Event]

    def __init__(self, port: str, baudrate: int):
        self.port = port
        self.baudrate = baudrate

        self._serial_lock = Lock()

        # way too much stuff going on only to wait for ACK,
        # but we may need more control events later
        # such as messages from the screen, e.g. when the battery is running low
        self._control_events = {
            "ACK": Event(),
        }

    async def init(self):
        self.serial_reader, self.serial_writer = await open_serial_connection(
            url=self.port, baudrate=self.baudrate
        )
        self._serial_task = create_task(self._serial_task_func())

    async def _serial_task_func(self):
        while True:
            line = (await self.serial_reader.readline()).decode("utf-8")
            print("[SERIAL]", line.removesuffix("\n"))
            if line.startswith("CONTROL:"):
                msg = line.split(":")[1].strip()
                if msg in self._control_events:
                    self._control_events[msg].set()
                    get_event_loop().call_later(0.1, self._control_events[msg].clear)
                else:
                    print("[WARNING] Got unknown control message:", msg)

    async def _wait_for_control(self, msg: str):
        if msg not in self._control_events:
            raise NotImplementedError(f"Unknown control message: {msg}")

        await self._control_events[msg].wait()

    async def send_packet(self, packet: bytes, device_id: int):
        if len(packet) > MAX_PACKET_SIZE:
            raise ValueError(f"Packet too large. Max size: {MAX_PACKET_SIZE}")

        packet = bytes([len(packet) + 1, device_id]) + packet
        self.serial_writer.write(packet)
        await self.serial_writer.drain()

        await self._wait_for_control("ACK")

    async def send_data(self, data: bytes, device_id: int):

        data = bytearray(data)

        # add header (size of data)
        size = len(data)
        data.insert(0, (size >> 8) & 0xFF)
        data.insert(0, size & 0xFF)

        async with self._serial_lock:

            # fits in one packet
            if len(data) < MAX_PACKET_SIZE:
                print(f"[INFO] Sending data in one packet ({len(data)} bytes)")
                await self.send_packet(data, device_id)

            # send in chunks
            else:
                offset = 0
                while offset < len(data):
                    chunk = None
                    if offset + MAX_PACKET_SIZE < len(data):
                        chunk = data[offset:offset + MAX_PACKET_SIZE]
                        offset += MAX_PACKET_SIZE
                        print(f"[INFO] Sending chunk {offset}/{len(data)}")
                    else:
                        chunk = data[offset:]
                        offset = len(data)
                        print(f"[INFO] Sending chunk {offset}/{len(data)}")
                        print("[INFO] Transmission finished")

                    await self.send_packet(chunk, device_id)
                    await sleep(0.1)

    async def send_image(self, img: Image, device_id: int):
        img = img.convert("1")
        img = img.resize((400, 300))

        # compress and remove header (puff expects raw deflate data)
        compressed_bytes = compress(img.tobytes(), level=9)[2:]

        await self.send_data(compressed_bytes, device_id)

    async def send_hibernation_request(self, until: datetime, device_id: int):
        seconds_until_wakeup = int((until - datetime.now()).total_seconds())

        # 32 bit unsigned int
        data = bytearray(struct.pack("<I", seconds_until_wakeup))

        # magic number: 0x1fae9fb3
        data.insert(0, 0x1f)
        data.insert(0, 0xae)
        data.insert(0, 0x9f)
        data.insert(0, 0xb3)

        await self.send_packet(data, device_id)
