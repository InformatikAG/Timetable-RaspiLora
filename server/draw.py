from typing import Optional
from PIL import Image, ImageDraw, ImageFont


def draw_timetable(room: str, current: Optional[dict], next: Optional[dict]) -> Image:
    img = Image.new("1", (400, 300), "white")
    draw = ImageDraw.Draw(img)

    font_big = ImageFont.truetype("./assets/Iosevka Medium Nerd Font Complete.ttf", 48)
    font_small = ImageFont.truetype("./assets/Iosevka Nerd Font Complete.ttf", 30)
    font_xsmall = ImageFont.truetype("./assets/Iosevka Nerd Font Complete.ttf", 20)

    box_margin = 5

    draw.rectangle(
        (box_margin, box_margin * 2 + 48, 400 - box_margin, 160),
        width=2,
        fill=None,
        outline="black"
    )

    draw.text(
        ((400 - draw.textsize(room, font=font_big)[0]) // 2, 0),
        room,
        fill="black",
        font=font_big
    )

    if current:

        draw.text(
            ((400 - draw.textsize(current["subject"], font=font_small)[0]) // 2, 60),
            current["subject"],
            fill="black",
            font=font_small
        )

        draw.text(
            ((400 - draw.textsize(current["teacher"], font=font_small)[0]) // 2, 90),
            current["teacher"],
            fill="black",
            font=font_small
        )

        from_to = f"{current['from'].strftime('%H:%M')} - {current['to'].strftime('%H:%M')}"
        draw.text(
            ((400 - draw.textsize(from_to, font=font_small)[0]) // 2, 120),
            from_to,
            fill="black",
            font=font_small
        )

    else:
        draw.text(
            ((400 - draw.textsize("Kein Unterricht", font=font_small)[0]) // 2, 90),
            "Kein Unterricht",
            fill="black",
            font=font_small
        )

    # draw rectangle for next lesson

    draw.rectangle(
        (400 / 2 + box_margin, 160 + box_margin, 400 - box_margin, 300 - box_margin),
        width=2,
        fill=None,
        outline="black"
    )

    if next:

        draw.text(
            (
                (200 - draw.textsize(next["subject"], font=font_xsmall)[0]) // 2 + 200,
                160 + 35
            ),
            next["subject"],
            fill="black",
            font=font_xsmall
        )

        draw.text(
            (
                (200 - draw.textsize(next["teacher"], font=font_xsmall)[0]) // 2 + 200,
                160 + 60
            ),
            next["teacher"],
            fill="black",
            font=font_xsmall
        )

        next_from_to = f"{next['from'].strftime('%H:%M')} - {next['to'].strftime('%H:%M')}"
        draw.text(
            (
                (200 - draw.textsize(next_from_to, font=font_xsmall)[0]) // 2 + 200,
                160 + 85
            ),
            next_from_to,
            fill="black",
            font=font_xsmall
        )

    else:
        draw.text(
            (
                (200 - draw.textsize("Kein Unterricht", font=font_xsmall)[0]) // 2 + 200,
                160 + 60
            ),
            "Kein Unterricht",
            fill="black",
            font=font_xsmall
        )

    tbz_img = Image.open("./assets/tbz-logo.png")
    tbz_img = tbz_img.convert("1")
    tbz_img = tbz_img.resize((
        400 // 2 - 4 * box_margin,
        300 // 2 - 4 * box_margin,
    ))

    img.paste(tbz_img, (box_margin, 160 + 5))

    return img
