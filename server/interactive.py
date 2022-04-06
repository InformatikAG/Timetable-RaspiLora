from asyncio import get_event_loop, run

import pygame
from PIL import Image

from lora import Lora


def interactive() -> Image:
    pygame.init()
    screen = pygame.display.set_mode((400, 300))
    pygame.display.set_caption("interactive epaper demo")
    clock = pygame.time.Clock()

    is_drawing = False

    screen.fill((255, 255, 255))

    while True:
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                is_drawing = True
            elif event.type == pygame.MOUSEBUTTONUP:
                is_drawing = False
            elif event.type == pygame.MOUSEMOTION and is_drawing:
                pos = pygame.mouse.get_pos()
                pygame.draw.circle(screen, (0, 0, 0), pos, 8)

            elif event.type == pygame.QUIT:

                img_str = pygame.image.tostring(screen, "RGB")
                img = Image.frombytes("RGB", (400, 300), img_str)

                pygame.quit()

                return img

        pygame.display.flip()
        clock.tick(60)


async def main():
    lora = Lora("/dev/ttyUSB0", 115200)
    await lora.init()
    while True:
        img = await get_event_loop().run_in_executor(None, interactive)
        await lora.send_image(img, 1)


if __name__ == "__main__":
    run(main())
