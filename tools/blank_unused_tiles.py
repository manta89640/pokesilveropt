#!/usr/bin/env python3
"""
Blank the tiles of tileset graphics that nothing shows.

Usage: tools/blank_unused_tiles.py [--apply]

A tile of gfx/tilesets/*.png is shown if a metatile of a tileset that uses
the graphics has it, or, for the train station, if the Magnet Train (which
draws with the station's tiles) uses it. Tileset animations only change
tiles in place, so they don't matter. The other tiles are made blank, which
compresses better; this is only done where the compressed graphics get
smaller. Run it after tools/trim_metatiles.py, and on a built tree (it
compares the compressed sizes with tools/lzcompress). Without --apply, only
reports how much it would save.
"""

import argparse
import os
import re
import subprocess
import tempfile

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TILE_SIZE = 8
TILE_BYTES = 16
WHITE = 255


def path(name):
	return os.path.join(ROOT, name)


def magnet_train_tiles():
	tiles = set()
	for name in ('gfx/overworld/magnet_train_fg.tilemap', 'gfx/overworld/magnet_train_bg.tilemap'):
		tiles |= set(open(path(name), 'rb').read())
	return tiles


def metatile_files():
	"""Returns {graphics: {metatiles}} from gfx/tilesets.asm."""
	text = open(path('gfx/tilesets.asm')).read()
	gfx, meta = {}, {}
	labels = []
	for line in text.split('\n'):
		m = re.match(r'(\w+?)(GFX|Meta|Coll)::', line)
		if m:
			labels.append((m.group(1), m.group(2)))
			continue
		m = re.match(r'(INCBIN|INCLUDE) "([^"]+)"', line)
		if m:
			for name, kind in labels:
				if kind == 'GFX':
					gfx[name] = m.group(2).replace('.2bpp.lz', '.png')
				elif kind == 'Meta':
					meta[name] = m.group(2)
			labels = []
	files = {}
	for name, png in gfx.items():
		if name in meta:
			files.setdefault(png, set()).add(meta[name])
	return files


def compressed_size(data):
	with tempfile.TemporaryDirectory() as tmp:
		src, dst = os.path.join(tmp, 'in.2bpp'), os.path.join(tmp, 'out.lz')
		open(src, 'wb').write(data)
		subprocess.run([path('tools/lzcompress'), src, dst], check=True, capture_output=True)
		return os.path.getsize(dst)


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('--apply', action='store_true')
	args = ap.parse_args()
	total = 0
	for png, metas in sorted(metatile_files().items()):
		used = magnet_train_tiles() if png == 'gfx/tilesets/train_station.png' else set()
		for meta in metas:
			used |= set(open(path(meta), 'rb').read())
		image = Image.open(path(png))
		columns = image.width // TILE_SIZE
		count = columns * (image.height // TILE_SIZE)
		unused = []
		for tile in range(count):
			if tile in used:
				continue
			box = ((tile % columns) * TILE_SIZE, (tile // columns) * TILE_SIZE)
			box += (box[0] + TILE_SIZE, box[1] + TILE_SIZE)
			if set(image.crop(box).getdata()) != {WHITE}:
				unused.append(box)
		if not unused:
			continue
		data = open(path(png.replace('.png', '.2bpp')), 'rb').read()
		blank = image.copy()
		for box in unused:
			blank.paste(WHITE, box)
		new = bytearray(data)
		for tile in range(count):
			box = ((tile % columns) * TILE_SIZE, (tile // columns) * TILE_SIZE)
			box += (box[0] + TILE_SIZE, box[1] + TILE_SIZE)
			if box in unused:
				new[tile * TILE_BYTES:(tile + 1) * TILE_BYTES] = bytes(TILE_BYTES)
		saved = compressed_size(data) - compressed_size(bytes(new))
		if saved <= 0:
			continue
		total += saved
		print(f'{png}: {len(unused)} tiles blanked ({saved} bytes)')
		if args.apply:
			blank.save(path(png))
	print(f'{total} bytes')


if __name__ == '__main__':
	main()
