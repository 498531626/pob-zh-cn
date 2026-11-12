"""Build local Noto Sans SC Medium glyphs at the UI's actual pixel sizes."""
from pathlib import Path
import hashlib
import json
import math
import re
from PIL import Image, ImageDraw, ImageFont

FONT = Path('C:/Windows/Fonts/NotoSansSC-VF.ttf')
SIZES = (*range(10, 25), 32, 48)


def build_atlas(chars, out):
    # Use the installed font locally; do not bundle the system font file.
    font = ImageFont.truetype(str(FONT), 48)
    font.set_variation_by_axes([500])
    advances = {ch: font.getlength(ch) for ch in chars}
    bands = []
    height = 0
    for size in SIZES:
        cell = size + 4
        cols = 4096 // cell
        bands.append((size, cell, cols, height))
        height += math.ceil(len(chars) / cols) * cell
    image = Image.new('RGBA', (4096, height))
    strikes = []
    base = []
    for size, cell, cols, top in bands:
        # Area filtering before upload preserves thin strokes even when the
        # native image renderer samples a small glyph without mipmaps.
        face = ImageFont.truetype(str(FONT), size * 3)
        face.set_variation_by_axes([500])
        baseline = max(-face.getbbox(ch, anchor='ls')[1] for ch in chars)
        positions = []
        for i, ch in enumerate(chars):
            x, y = i % cols * cell, top + i // cols * cell
            mask = Image.new('L', (cell * 3, cell * 3))
            ImageDraw.Draw(mask).text((0, baseline), ch, font=face, fill=255, anchor='ls')
            mask = mask.resize((cell, cell), Image.Resampling.LANCZOS)
            tile = Image.new('RGBA', (cell, cell), 'white')
            tile.putalpha(mask)
            image.paste(tile, (x, y))
            key = json.dumps(ch, ensure_ascii=False)
            positions.append(f'[{key}]={{{x},{y}}},\n')
            if size == 48:
                base.append(f'\t[{key}] = {{{x}, {y}, {advances[ch]:.4f}}},\n')
        strikes.append(f'[{size}]={{cell={cell},chars={{\n' + ''.join(positions) + '}},\n')
    image.save(out / 'ChineseGlyphs.png')
    (out / 'Glyphs.lua').write_text(
        f'return {{size=48,cell=52,width=4096,height={height},chars={{\n'
        + ''.join(base) + '},strikes={\n' + ''.join(strikes) + '}}\n', 'utf8')
    return {'font': 'Noto Sans SC Medium (installed on local PC)',
            'font_weight': 500, 'font_sizes': list(SIZES),
            'font_sha256': hashlib.sha256(FONT.read_bytes()).hexdigest()}


if __name__ == '__main__':
    out = Path(__file__).resolve().parents[2] / 'src/Localization'
    # Refresh only the font, retaining the current translation inventory.
    source = (out / 'Glyphs.lua').read_text('utf8').split('strikes=')[0]
    chars = sorted(set(re.findall(r'\["(.)"\]\s*=', source)))
    assert chars, 'No existing glyph inventory'
    info = build_atlas(chars, out)
    report_path = out / 'build-info.json'
    report = json.loads(report_path.read_text('utf8'))
    report.update(info)
    report_path.write_text(json.dumps(report, indent=2) + '\n', 'utf8')
    print(json.dumps(info))
