"""python3 -I gobbler-v4/e2e/storyboard.py : one contact sheet of the live frames made by frames.js (e2e/out/frames/*.png -> storyboard.png).
Every frame is a real screenshot of the running page (software GL, ?glass=1); nothing on the sheet is drawn by hand except the captions."""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'frames')
CELLS = [
    ('1-none', '1  UI none: the pure frame, nothing added'),
    ('2-rest', '2  UI minimal, at rest: four corner chips'),
    ('3-tooltip', '3  hover 0.15 s: snap ring, dim, one-line tooltip'),
    ('4-card-shape', '4  dwell 1.2 s: NodeType card with the ontology block'),
    ('5-card-finding', '5  a measured Finding, camera flown to it'),
    ('6-sheet', '6  narrow screen: the card becomes a sheet'),
    ('7-tune', '7  press T: the tuning panel, the card keeps clear of it'),
]
CW, CH, GAP, LAB, TITLE = 720, 432, 14, 34, 58
BG, GOLD, INK3 = (11, 10, 13), (233, 207, 138), (138, 132, 120)


def font(name, size):
    for p in ('/usr/share/fonts/truetype/dejavu/%s.ttf' % name, '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


fb, fs = font('DejaVuSans-Bold', 20), font('DejaVuSans', 15)
cols, rows = 3, 3
W = cols * CW + (cols + 1) * GAP
H = TITLE + rows * (CH + LAB) + (rows + 1) * GAP
sheet = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(sheet)
title = 'GOBBLER v4  live hover + UI storyboard'
d.text((GAP + 4, 14), title, font=fb, fill=GOLD)
d.text((GAP + 4 + d.textlength(title, font=fb) + 24, 18), 'real frames from the running page; card text is read from the graph', font=fs, fill=INK3)
for i, (name, label) in enumerate(CELLS):
    im = Image.open(os.path.join(OUT, name + '.png')).convert('RGB')
    k = min(CW / im.width, CH / im.height)
    im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
    r, c = divmod(i, cols)
    x0, y0 = GAP + c * (CW + GAP), TITLE + GAP + r * (CH + LAB + GAP)
    sheet.paste(im, (x0 + (CW - im.width) // 2, y0))
    d.text((x0 + 2, y0 + CH + 8), label, font=fs, fill=INK3)
sheet.save(os.path.join(OUT, 'storyboard.png'), optimize=True)
print('wrote', os.path.join(OUT, 'storyboard.png'), sheet.size)
