from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap
import imageio
import random
import os

GIF_SIZE = (480, 270)
FONT_PATH = "NotoEmoji.ttf"
FONT_SIZE = 40
FRAME_DURATION = 30
BACKGROUNDS_DIR = "backgrounds"

def _choose_background():
    if os.path.isdir(BACKGROUNDS_DIR):
        files = [f for f in os.listdir(BACKGROUNDS_DIR) if f.lower().endswith((".jpg",".jpeg",".png"))]
        if files:
            return os.path.join(BACKGROUNDS_DIR, random.choice(files))
    return None

def _measure_text(draw, text, font):
    try:
        bbox = draw.textbbox((0,0), text, font=font)
        return bbox[2]-bbox[0], bbox[3]-bbox[1]
    except AttributeError:
        return draw.textsize(text, font=font)

def get_wrapped_lines(draw, text, font, width=20):
    wrapped = textwrap.fill(text, width=width)
    lines = wrapped.split("\n")
    sizes = [_measure_text(draw, line, font) for line in lines]
    total_width = max(w for w,h in sizes)
    total_height = sum(h for w,h in sizes) + (len(lines)-1)*5
    return lines, total_width, total_height

def choose_word_position(prev_x, prev_w, word_w, gif_w, max_shift=40):
    if prev_x is None:
        return (gif_w - word_w)//2
    shift = random.randint(10, max_shift)
    direction = random.choice([-1,1])
    x = prev_x + direction * (prev_w + shift)
    if x < 10:
        x = prev_x + prev_w + shift
        if x > gif_w - word_w - 10:
            x = gif_w - word_w - 10
    elif x + word_w > gif_w - 10:
        x = prev_x - word_w - shift
        if x < 10:
            x = 10
    return x

def compute_display_frames(word, font, draw, base_frames=10, time_per_pixel=0.15):
    w, _ = _measure_text(draw, word, font)
    return base_frames + int(w * time_per_pixel)

def draw_text_with_shadow(draw, x, y, lines, font, color, shadow_color=(0,0,0,200), shadow_offset=2):
    for line_idx, line in enumerate(lines):
        line_y = y + line_idx * (font.size + 5)
        draw.text((x + shadow_offset, line_y + shadow_offset), line, font=font, fill=shadow_color)
        draw.text((x, line_y), line, font=font, fill=color)

def create_frames_for_word(bg, font, author_font, author, shown_words, word_lines, x, y, colors):
    frames = []
    W,H = bg.size
    word_color = random.choice(colors)
    shown_words.append((word_lines, x, y, word_color))
    frame_img = bg.copy()
    draw = ImageDraw.Draw(frame_img)
    for lines, lx, ly, lcolor in shown_words:
        draw_text_with_shadow(draw, lx, ly, lines, font, lcolor)
    aw, ah = _measure_text(draw, f"- {author}", author_font)
    draw.text((W-aw-20, H-ah-20), f"- {author}", font=author_font, fill=(220,220,220,230))
    num_frames = compute_display_frames(word_lines[0], font, draw)
    for _ in range(num_frames):
        frames.append(frame_img)
    return frames

def create_dynamic_gif(author, text):
    words = text.split()
    bg_path = _choose_background()
    if bg_path:
        bg = Image.open(bg_path).convert("RGBA")
        bg = bg.resize(GIF_SIZE, Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=1.3))
    else:
        bg = Image.new("RGBA", GIF_SIZE, (30,30,60,255))
    W,H = GIF_SIZE
    frames = []
    colors = [(255,255,255),(255,200,200),(200,255,200),(200,200,255),(255,255,100),(255,150,0)]
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    author_font = ImageFont.truetype(FONT_PATH, int(FONT_SIZE*0.5))
    i = 0
    while i < len(words):
        current_line = []
        line_width = 0
        max_width = int(W*0.8)
        temp_img = Image.new("RGBA",(1,1))
        draw_temp = ImageDraw.Draw(temp_img)
        while i < len(words):
            lines, w_w, w_h = get_wrapped_lines(draw_temp, words[i], font)
            if line_width + w_w + 7 <= max_width or len(current_line)==0:
                current_line.append(words[i])
                line_width += w_w + 7
                i += 1
            else:
                break
        line_sizes = [get_wrapped_lines(draw_temp, w, font) for w in current_line]
        group_height = sum(h for lines, w, h in line_sizes) + (len(current_line)-1)*5
        start_y = (H - group_height)//2
        shown_words = []
        prev_x, prev_w = None, 0
        y_offset = 0
        for idx, word in enumerate(current_line):
            lines, word_w, word_h = get_wrapped_lines(draw_temp, word, font)
            y = start_y + y_offset + random.randint(-5,5)
            x = choose_word_position(prev_x, prev_w, word_w, W)
            frames += create_frames_for_word(bg, font, author_font, author, shown_words, lines, x, y, colors)
            prev_x = x
            prev_w = word_w
            y_offset += word_h + 5
    bio = BytesIO()
    frames_for_imageio = [f.convert("RGBA") for f in frames]
    imageio.mimsave(bio, frames_for_imageio, format="GIF", duration=FRAME_DURATION, loop=0)
    bio.seek(0)
    return bio