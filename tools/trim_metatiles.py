#!/usr/bin/env python3
"""
Find the blocks at the end of each tileset that no map can show.

Usage: tools/trim_metatiles.py [--apply]

A block can be shown if a map using the tileset has it in its blocks or as
its border block, or if a map connected to such a map has it (the strips of
connected maps are drawn with the current map's tileset). Scripts can place
blocks with changeblock (or the Goldenrod Underground ugdoor_def doors), Cut
and Whirlpool replace blocks from data/collision/field_move_blocks.asm, and
the player's room shows decorations as blocks (data/decorations/attributes.asm,
where a carpet also uses the next two blocks). With --apply, it removes the
metatiles and collision of the blocks after the last one that can be shown.
"""

import argparse
import collections
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METATILE_SIZE = 16
CARPET_BLOCKS = 3


def read(path):
	return open(os.path.join(ROOT, path)).read()


def hex_values(text):
	return [int(x, 16) for x in re.findall(r'\$([0-9a-fA-F]+)\b', text)]


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('--apply', action='store_true')
	args = ap.parse_args()

	tileset_of = dict(re.findall(r'^\tmap (\w+), (TILESET_\w+)', read('data/maps/maps.asm'), re.M))

	blk = {}
	labels = []
	for line in read('data/maps/blocks.asm').split('\n'):
		m = re.match(r'(\w+)_Blocks:', line)
		if m:
			labels.append(m.group(1))
		m = re.search(r'INCBIN "(maps/\w+\.blk)', line)
		if m:
			for label in labels:
				blk[label] = m.group(1)
			labels = []

	shown = collections.defaultdict(set)  # map -> blocks it can show
	connections = collections.defaultdict(list)
	current = None
	for line in read('data/maps/attributes.asm').split('\n'):
		m = re.match(r'\tmap_attributes (\w+), \w+, \$([0-9a-fA-F]+)', line)
		if m:
			current = m.group(1)
			shown[current].add(int(m.group(2), 16))
		m = re.match(r'\tconnection \w+, (\w+),', line)
		if m:
			connections[current].append(m.group(1))
	for name in tileset_of:
		shown[name] |= set(open(os.path.join(ROOT, blk[name]), 'rb').read())
		script = read(f'maps/{name}.asm')
		for line in script.split('\n'):
			code = line.split(';')[0]
			if re.match(r'\s*changeblock\b', code):
				shown[name] |= set(hex_values(code.split(',')[-1]))
			elif re.match(r'\s*ugdoor_def\b', code):
				values = [v.strip() for v in code.split(None, 1)[1].split(',')]
				shown[name] |= {int(v[1:], 16) for i, v in enumerate(values) if i % 4 >= 2}
			elif 'changeblock' in code:
				assert 'UGDOOR_' in code, f'maps/{name}.asm: {line}'

	used = collections.defaultdict(set)  # tileset -> blocks
	for name, tileset in tileset_of.items():
		used[tileset] |= shown[name]
		for other in connections[name]:
			used[tileset] |= shown[other]

	tileset = None
	for line in read('data/collision/field_move_blocks.asm').split('\n'):
		m = re.match(r'\tdbw (TILESET_\w+), \.(\w+)', line)
		if m:
			continue
		m = re.match(r'\.(\w+):', line)
		if m:
			tileset = 'TILESET_' + re.sub(r'(?<!^)(?=[A-Z])', '_', m.group(1)).upper()
			continue
		m = re.match(r'\tdb \$([0-9a-fA-F]+), \$([0-9a-fA-F]+)', line)
		if m and tileset:
			used[tileset] |= {int(m.group(1), 16), int(m.group(2), 16)}
	for line in read('data/decorations/attributes.asm').split('\n'):
		m = re.match(r'\tdecoration (DECO_\w+),.*,\s*\$([0-9a-fA-F]+)\s*$', line)
		if m:
			block = int(m.group(2), 16)
			count = CARPET_BLOCKS if m.group(1) == 'DECO_CARPET' else 1
			used['TILESET_PLAYERS_ROOM'] |= set(range(block, block + count))

	# Tilesets that share metatiles and collision
	constants = ['TILESET_0'] + re.findall(r'^\tconst (TILESET_\w+)',
		read('constants/tileset_constants.asm'), re.M)
	names = re.findall(r'^\ttileset (\w+)', read('data/tilesets.asm'), re.M)
	files = {}
	pending = []
	for line in read('gfx/tilesets.asm').split('\n'):
		m = re.match(r'(\w+)(Meta|Coll)::', line)
		if m:
			pending.append(m.group(1))
			continue
		m = re.match(r'(INCBIN|INCLUDE) "(data/tilesets/\w+_(metatiles\.bin|collision\.asm))"', line)
		if m:
			for name in pending:
				files.setdefault(name, []).append(m.group(2))
			pending = []
	groups = collections.defaultdict(set)
	for constant, name in zip(constants, names):
		meta, coll = files[name]
		groups[(meta, coll)] |= used[constant] if constant != 'TILESET_0' else set()

	total = 0
	for (meta, coll), blocks in sorted(groups.items()):
		count = os.path.getsize(os.path.join(ROOT, meta)) // METATILE_SIZE
		keep = max(blocks) + 1 if blocks else count
		if keep >= count:
			continue
		saved = (count - keep) * (METATILE_SIZE + 4)
		total += saved
		print(f'{meta}: blocks ${keep:02x}-${count - 1:02x} unused ({saved} bytes)')
		if args.apply:
			path = os.path.join(ROOT, meta)
			data = open(path, 'rb').read()
			open(path, 'wb').write(data[:keep * METATILE_SIZE])
			path = os.path.join(ROOT, coll)
			lines = open(path).read().split('\n')
			tilecoll = [i for i, line in enumerate(lines) if line.strip().startswith('tilecoll')]
			assert len(tilecoll) == count
			lines = lines[:tilecoll[keep - 1] + 1] + [
				f'; blocks ${keep:02x}-${count - 1:02x} were unused (tools/trim_metatiles.py)', '']
			open(path, 'w').write('\n'.join(lines))
	print(f'{total} bytes')


if __name__ == '__main__':
	main()
