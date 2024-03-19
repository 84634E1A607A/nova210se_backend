import pydenticon
import random
import colorsys
import hashlib
import base64


def generate_random_avatar(seed: str) -> str:
    """
    Generate base64 encoded avatar image from a seed string.
    """

    # Generate a random foreground color
    hue = random.random()
    saturation = random.random() * 0.5 + 0.3
    brightness = random.random() * 0.4 + 0.5
    foreground = colorsys.hsv_to_rgb(hue, saturation, brightness)
    foreground = '#%02x%02x%02x' % (int(foreground[0] * 255), int(foreground[1] * 255), int(foreground[2] * 255))

    # Generate a random background color
    hue = hue + 0.5 + random.random() * 0.1
    if hue > 1:
        hue -= 1
    saturation = random.random() * 0.15
    brightness = 1
    background = colorsys.hsv_to_rgb(hue, saturation, brightness)
    background = '#%02x%02x%02x' % (int(background[0] * 255), int(background[1] * 255), int(background[2] * 255))

    # Generate the identicon
    identicon = pydenticon.Generator(8, 8, foreground=[foreground], background=background, digest=hashlib.sha512) \
        .generate(seed, 256, 256)

    return f"data:image/png;base64,{base64.b64encode(identicon).decode("latin-1")}"
