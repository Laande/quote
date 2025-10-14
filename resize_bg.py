from PIL import Image
import os

INPUT_DIR = "backgrounds"
TARGET_SIZE = (480, 270)

for filename in os.listdir(INPUT_DIR):
    if filename.lower().endswith((".jpg", ".jpeg", ".png")):
        input_path = os.path.join(INPUT_DIR, filename)
        output_path = os.path.join(INPUT_DIR, filename)

        with Image.open(input_path) as img:
            img = img.resize(TARGET_SIZE, Image.LANCZOS)
            img.save(output_path, optimize=True)