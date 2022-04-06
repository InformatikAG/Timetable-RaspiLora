from asyncio import create_task, sleep, run, Event
from datetime import datetime, timedelta

from PIL import Image
from webuntis import Session

from draw import draw_timetable
from lora import Lora
from utils import noblock
from config import *


async def room_info(room_name: str) -> dict:

    # we always create a new session for each room info request
    # because for some reason we're logged out after some time
    # with results in an error if we use the same session for all requests
    session = Session(
        server=SERVER,
        username=USERNAME,
        password=PASSWORD,
        school=SCHOOL,
        useragent="ePaper Server"
    )

    await noblock(session.login)

    # get the room object
    room = [room for room in await noblock(session.rooms) if room.name == room_name][0]

    now = datetime.now()

    timetable = await noblock(session.timetable, start=now, end=now, room=room.id)

    # TODO: property access (e.g. period.subjects) can also cause a network request
    #       consider wrapping them in noblock() or use an async websuntis lib

    # info dict, maps to the parameters of the draw_timetable function
    info = {
        "room": room.name,
        "current": None,
        "next": None,
    }

    def info_from_period(period):
        short_name = period.subjects[0].name
        long_name = period.subjects[0].long_name

        return {
            "subject": long_name if len(long_name) < 15 else short_name,
            # special permissions needed to access teacher names
            # "teacher": period.teachers[0].name,
            "teacher": "[REDACTED]",
            "from": period.start,
            "to": period.end,
        }

    # find the current lesson
    for period in timetable:
        if period.start <= now < period.end:
            info["current"] = info_from_period(period)
            break

    # find the next lesson
    for period in timetable:
        # no current lesson, choose next lesson after now
        if not info["current"] and period.start > now:
            info["next"] = info_from_period(period)
            break
        # there is a current lesson, choose next lesson after current lesson
        elif info["current"] and period.start >= info["current"]["to"]:
            info["next"] = info_from_period(period)
            break

    await noblock(session.logout)

    return info


def calculate_hibernate_until(info: dict):
    if info["current"]:
        return info["current"]["to"] - timedelta(seconds=HIBERNATION_DELAY)
    elif info["next"]:
        return info["next"]["from"] - timedelta(seconds=HIBERNATION_DELAY)
    else:
        next_day = datetime.now() + timedelta(days=1)
        # next day after midnight
        return datetime(next_day.year, next_day.month, next_day.day, 0, 1)


async def update_and_hibernate(
    buffer: Image, device_id: int, hibernate_until: datetime, lora: Lora
) -> None:
    print("[INFO] Updating screen")
    await lora.send_image(buffer, device_id)
    await sleep(HIBERNATION_DELAY)
    print("[INFO] Hibernating until", hibernate_until)
    await lora.send_hibernation_request(hibernate_until, device_id)


async def update_loop(room_name: str, lora: Lora) -> None:

    # first update should instantly update the screen
    sleep_until = None

    while True:
        # wait seconds (until after hibernation is over)
        if sleep_until:
            # plus 10 to allow the device to boot up
            seconds_to_sleep = (sleep_until -
                                datetime.now()).total_seconds() + HIBERNATION_DELAY
            await sleep(seconds_to_sleep)

        # get new room info
        info = await room_info(room_name)

        # calculate new hibernation duration
        sleep_until = calculate_hibernate_until(info)

        # update the screen and go back to sleep
        await update_and_hibernate(
            draw_timetable(**info), ROOMS[room_name], sleep_until, lora
        )


async def main() -> None:
    # lora setup
    lora = Lora("/dev/ttyUSB0", 115200)
    await lora.init()

    # initial framebuffer update
    for room in ROOMS:
        create_task(update_loop(room, lora))

    # wait forever
    await Event().wait()


if __name__ == "__main__":
    run(main())
