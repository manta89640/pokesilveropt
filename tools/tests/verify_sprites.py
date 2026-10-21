#!/usr/bin/env python3
"""
Check that every overworld sprite loads the same tiles as in a reference ROM.

Usage: tools/tests/verify_sprites.py reference.gbc modified.gbc

GetSprite loads twice a sprite's length in tiles (once to vTiles0 and once
to vTiles1), except for still sprites. Some sprites are shorter than that, so
the original games load the start of the next sprites too. For each entry of
OverworldSprites, this decompresses the sprite (with tools/lzcompress) if it
is compressed, and compares the tiles that GetSprite loads. Both ROMs need
their .sym files.
"""

import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TILE = 16
STILL_SPRITE = 3
SPRITE_GFX_COMPRESSED = 1
ENTRY_SIZE = 6  # dw address; db length, bank, type, palette


class Rom:
	def __init__(self, path):
		self.data = open(path, 'rb').read()
		self.syms = {}
		for line in open(os.path.splitext(path)[0] + '.sym'):
			m = re.match(r'([0-9a-f]+):([0-9a-f]+) (\S+)', line)
			if m:
				self.syms[m.group(3)] = (int(m.group(1), 16), int(m.group(2), 16))

	def offset(self, bank, addr):
		return addr if addr < 0x4000 else bank * 0x4000 + addr - 0x4000

	def read(self, bank, addr, n):
		start = self.offset(bank, addr)
		return self.data[start:start + n]


def decompress(rom, bank, addr):
	with tempfile.TemporaryDirectory() as tmp:
		src = os.path.join(tmp, 'in.lz')
		dst = os.path.join(tmp, 'out.bin')
		with open(src, 'wb') as f:
			f.write(rom.read(bank, addr, 0x1000))
		subprocess.run([os.path.join(ROOT, 'tools/lzcompress'), '-u', src, dst], check=True,
			stdout=subprocess.DEVNULL)
		return open(dst, 'rb').read()


def main():
	ref, new = Rom(sys.argv[1]), Rom(sys.argv[2])
	count = sum(1 for line in open(os.path.join(ROOT, 'data/sprites/sprites.asm'))
		if re.match(r'\s+overworld_sprite\b', line))
	bad = 0
	for i in range(count):
		entries = []
		for rom in (ref, new):
			bank, addr = rom.syms['OverworldSprites']
			entries.append(rom.read(bank, addr + i * ENTRY_SIZE, ENTRY_SIZE))
		(ra, rl, rb, rt, rp), (na, nl, nb, nt, np) = [
			(e[0] | e[1] << 8, e[2], e[3], e[4], e[5]) for e in entries]
		tiles = (rl // TILE) * (1 if rt == STILL_SPRITE else 2)
		expected = ref.read(rb, ra, tiles * TILE)
		if nl & SPRITE_GFX_COMPRESSED:
			got = decompress(new, nb, na)[:tiles * TILE]
		else:
			got = new.read(nb, na, tiles * TILE)
		if (nl & ~SPRITE_GFX_COMPRESSED, nt, np) != (rl, rt, rp) or got != expected:
			bad += 1
			print(f'sprite ${i + 1:02x} differs')
	print(f'{count} sprites checked, {bad} differ')
	sys.exit(1 if bad else 0)


if __name__ == '__main__':
	main()
