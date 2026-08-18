from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

# Generate the LMS application icon (packaging/assets/app.ico).
#
# The icon is a rounded blue square with a white house silhouette and door,
# matching the application's primary color. Run standalone to regenerate:
# ``python scripts/create_icon.py``

SIZE = 256
PRIMARY = (47, 107, 255, 255)
WHITE = (255, 255, 255, 255)

OUT = Path(__file__).resolve().parent.parent / "packaging" / "assets" / "app.ico"


def build_icon() -> Path:
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((8, 8, SIZE - 8, SIZE - 8), radius=48, fill=PRIMARY)

    draw.polygon([(SIZE // 2, 40), (216, 150), (40, 150)], fill=WHITE)

    draw.rectangle((56, 128, 200, 216), fill=WHITE)

    draw.rounded_rectangle((104, 160, 152, 216), radius=14, fill=PRIMARY)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    return OUT


if __name__ == "__main__":
    path = build_icon()
    print(f"icon written to {path}")
    sys.exit(0)
