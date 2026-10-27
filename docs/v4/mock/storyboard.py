"""python3 docs/v4/mock/storyboard.py : one contact sheet of the mock frames (frame area only, captions cropped).
Reads docs/v4/mock/out/*.png (made by render.js), writes docs/v4/mock/out/storyboard.png."""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
FRAME_H = {'B': 923, 'A': 903}          # stills B/A after the crop in mock.html (978-1-54, 935-0-32)
CELLS = [
    ('B-1-none', 'B', '1  UI none: the pure frame'),
    ('B-2-rest', 'B', '2  UI minimal, at rest: four corner chips'),
    ('B-3-hover', 'B', '3  hover: snap ring, dim, one-line tooltip'),
    ('B-4-card-nodetype', 'B', '4  dwell: ontology-aware NodeType card'),
    ('B-5-placement-map', 'B', '5  why that corner: density, halo, chips'),
    ('A-4-card-finding', 'A', '6  dwell on still A: a measured Finding'),
]
CW = 720
GAP = 14
LAB = 34
TITLE = 58
BG = (11, 10, 13)
GOLD = (233, 207, 138)
INK3 = (138, 132, 120)

def font(name, size):
    for p in ('/usr/share/fonts/truetype/dejavu/%s.ttf' % name, '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

fb, fs, fm = font('DejaVuSans-Bold', 20), font('DejaVuSans', 15), font('DejaVuSansMono', 13)
tiles = []
for name, still, label in CELLS:
    im = Image.open(os.path.join(OUT, name + '.png')).convert('RGB')
    im = im.crop((0, 0, im.width, FRAME_H[still]))
    tiles.append((im.resize((CW, round(im.height * CW / im.width)), Image.LANCZOS), label))

cols, rows = 3, 2
ch = max(t[0].height for t in tiles) + LAB
W = cols * CW + (cols + 1) * GAP
H = TITLE + rows * ch + (rows + 1) * GAP
sheet = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(sheet)
title = 'GOBBLER v4  hover + UI storyboard'
d.text((GAP + 4, 14), title, font=fb, fill=GOLD)
d.text((GAP + 4 + d.textlength(title, font=fb) + 24, 18), 'MOCK on your two stills: layout illustrative, all card text real data', font=fs, fill=INK3)
for i, (im, label) in enumerate(tiles):
    r, c = divmod(i, cols)
    x = GAP + c * (CW + GAP)
    y = TITLE + GAP + r * (ch + GAP)
    sheet.paste(im, (x, y))
    d.rectangle((x - 1, y - 1, x + CW, y + im.height), outline=(60, 54, 44))
    d.text((x + 2, y + im.height + 9), label, font=fm, fill=(207, 199, 184))
p = os.path.join(OUT, 'storyboard.png')
sheet.save(p, optimize=True)
print(p, sheet.size, round(os.path.getsize(p) / 1024), 'KB')
