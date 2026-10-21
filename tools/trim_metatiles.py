#!/usr/bin/env python3
"""
Remove the blocks of each tileset that no map can show.

Usage: tools/trim_metatiles.py [--apply]

A block can be shown if a map using the tileset has it in its blocks or as
its border block, or if a map connected to such a map has it (the strips of
connected maps are drawn with the current map's tileset). Scripts can place
blocks with changeblock (or the Goldenrod Underground ugdoor_def doors), Cut
and Whirlpool replace blocks from data/collision/field_move_blocks.asm, and
the player's room shows decorations as blocks (data/decorations/attributes.asm,
where a carpet also uses the next two blocks). Block 0 is always kept, since
a decoration of 0 means none.

Tilesets of maps without connections are renumbered without the blocks that
can't be shown: their metatiles and collision, and every reference to their
blocks listed above, are rewritten. Other tilesets only lose the blocks after
the last one that can be shown. Without --apply, only reports what it would
remove.
"""

import argparse
import collections
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METATILE_SIZE = 16
COLLISION_SIZE = 4
CARPET_BLOCKS = 3
CHANGEBLOCK = re.compile(r'^(\s*changeblock\s+[^,]+,[^,]+,\s*)\$([0-9a-fA-F]+)(.*)$')
UGDOOR = re.compile(r'^(\s*ugdoor_def\s+)([^;]*)(.*)$')
BORDER = re.compile(r'^(\tmap_attributes (\w+), \w+, )\$([0-9a-fA-F]+)(.*)$')
FIELD_MOVE = re.compile(r'^(\tdb )\$([0-9a-fA-F]+), \$([0-9a-fA-F]+)(.*)$')
DECORATION = re.compile(r'^(\tdecoration (DECO_\w+),.*,\s*)\$([0-9a-fA-F]+)(\s*)$')


def path(name):
	return os.path.join(ROOT, name)


def read(name):
	return open(path(name)).read()


def lines(name):
	return read(name).split('\n')


def write_lines(name, new):
	open(path(name), 'w').write('\n'.join(new))


def field_move_tileset(label):
	return 'TILESET_' + label.upper()


class Maps:
	def __init__(self):
		self.tileset_of = dict(re.findall(r'^\tmap (\w+), (TILESET_\w+)',
			read('data/maps/maps.asm'), re.M))
		self.blk = {}
		labels = []
		for line in lines('data/maps/blocks.asm'):
			m = re.match(r'(\w+)_Blocks:', line)
			if m:
				labels.append(m.group(1))
			m = re.search(r'INCBIN "(maps/\w+\.blk)', line)
			if m:
				for label in labels:
					self.blk[label] = m.group(1)
				labels = []
		self.shown = collections.defaultdict(set)  # map -> blocks it can show
		self.connections = collections.defaultdict(list)
		current = None
		for line in lines('data/maps/attributes.asm'):
			m = BORDER.match(line)
			if m:
				current = m.group(2)
				self.shown[current].add(int(m.group(3), 16))
			m = re.match(r'\tconnection \w+, (\w+),', line)
			if m:
				self.connections[current].append(m.group(1))
		for name in self.tileset_of:
			self.shown[name] |= set(open(path(self.blk[name]), 'rb').read())
			for line in lines(f'maps/{name}.asm'):
				code = line.split(';')[0]
				m = CHANGEBLOCK.match(code)
				if m:
					self.shown[name].add(int(m.group(2), 16))
				elif re.match(r'\s*ugdoor_def\b', code):
					self.shown[name] |= set(ugdoor_blocks(code))
				elif 'changeblock' in code:
					assert 'UGDOOR_' in code, f'maps/{name}.asm: {line}'

		self.used = collections.defaultdict(set)  # tileset -> blocks
		self.connected = set()  # tilesets of maps with connections
		for name, tileset in self.tileset_of.items():
			self.used[tileset] |= self.shown[name]
			for other in self.connections[name]:
				self.used[tileset] |= self.shown[other]
				self.connected.add(tileset)
		tileset = None
		for line in lines('data/collision/field_move_blocks.asm'):
			m = re.match(r'\.(\w+):', line)
			if m:
				tileset = field_move_tileset(m.group(1))
			m = FIELD_MOVE.match(line)
			if m and tileset:
				self.used[tileset] |= {int(m.group(2), 16), int(m.group(3), 16)}
		for line in lines('data/decorations/attributes.asm'):
			m = DECORATION.match(line)
			if m:
				block = int(m.group(3), 16)
				count = CARPET_BLOCKS if m.group(2) == 'DECO_CARPET' else 1
				self.used['TILESET_PLAYERS_ROOM'] |= set(range(block, block + count))

		# Tilesets that share metatiles and collision
		constants = ['TILESET_0'] + re.findall(r'^\tconst (TILESET_\w+)',
			read('constants/tileset_constants.asm'), re.M)
		names = re.findall(r'^\ttileset (\w+)', read('data/tilesets.asm'), re.M)
		files = {}
		pending = []
		for line in lines('gfx/tilesets.asm'):
			m = re.match(r'(\w+)(Meta|Coll)::', line)
			if m:
				pending.append(m.group(1))
				continue
			m = re.match(r'(INCBIN|INCLUDE) "(data/tilesets/\w+_(metatiles\.bin|collision\.asm))"',
				line)
			if m:
				for name in pending:
					files.setdefault(name, []).append(m.group(2))
				pending = []
		self.groups = collections.defaultdict(set)  # (metatiles, collision) -> tilesets
		for constant, name in zip(constants, names):
			meta, coll = files[name]
			assert meta.endswith('.bin') and coll.endswith('.asm')
			self.groups[(meta, coll)].add(constant)


def ugdoor_blocks(code):
	values = [v.strip() for v in code.split(None, 1)[1].split(',')]
	return [int(v[1:], 16) for i, v in enumerate(values) if i % 4 >= 2]


def plan(maps):
	"""Returns {(metatiles, collision): (tilesets, blocks to keep, block count)}."""
	plans = {}
	for (meta, coll), tilesets in sorted(maps.groups.items()):
		count = os.path.getsize(path(meta)) // METATILE_SIZE
		blocks = set().union(*(maps.used[t] for t in tilesets))
		if 'TILESET_0' in tilesets or not blocks:
			continue
		if tilesets & maps.connected:
			keep = list(range(max(blocks) + 1))
		else:
			keep = sorted(blocks | {0})
		if len(keep) < count:
			plans[(meta, coll)] = (tilesets, keep, count)
	return plans


def apply(maps, plans):
	remap = {}  # tileset -> {old block: new block}
	for (meta, coll), (tilesets, keep, count) in plans.items():
		new = {old: i for i, old in enumerate(keep)}
		for tileset in tilesets:
			remap[tileset] = new
		data = open(path(meta), 'rb').read()
		open(path(meta), 'wb').write(b''.join(
			data[i * METATILE_SIZE:(i + 1) * METATILE_SIZE] for i in keep))
		old = [line for line in lines(coll) if line.strip().startswith('tilecoll')]
		assert len(old) == count
		write_lines(coll, [re.sub(r'; [0-9a-f]{2}$', f'; {i:02x}', old[block])
			for i, block in enumerate(keep)] + [
			'; blocks that no map can show were removed (tools/trim_metatiles.py)', ''])

	def block(tileset, value):
		return f'${remap[tileset][int(value, 16)]:02x}'

	done = set()
	for name, tileset in maps.tileset_of.items():
		if tileset not in remap:
			continue
		if maps.blk[name] not in done:
			done.add(maps.blk[name])
			data = open(path(maps.blk[name]), 'rb').read()
			open(path(maps.blk[name]), 'wb').write(bytes(remap[tileset][b] for b in data))
		script = f'maps/{name}.asm'
		new = []
		for line in lines(script):
			m = CHANGEBLOCK.match(line)
			if m:
				line = m.group(1) + block(tileset, m.group(2)) + m.group(3)
			m = UGDOOR.match(line)
			if m:
				values = m.group(2).split(',')
				values = [re.sub(r'\$([0-9a-fA-F]+)', lambda v: block(tileset, v.group(1)), v)
					if i % 4 >= 2 else v for i, v in enumerate(values)]
				line = m.group(1) + ','.join(values) + m.group(3)
			new.append(line)
		write_lines(script, new)

	new = []
	for line in lines('data/maps/attributes.asm'):
		m = BORDER.match(line)
		if m and maps.tileset_of[m.group(2)] in remap:
			line = m.group(1) + block(maps.tileset_of[m.group(2)], m.group(3)) + m.group(4)
		new.append(line)
	write_lines('data/maps/attributes.asm', new)

	new = []
	tileset = None
	for line in lines('data/collision/field_move_blocks.asm'):
		m = re.match(r'\.(\w+):', line)
		if m:
			tileset = field_move_tileset(m.group(1))
		m = FIELD_MOVE.match(line)
		if m and tileset in remap:
			line = (m.group(1) + block(tileset, m.group(2)) + ', ' + block(tileset, m.group(3)) +
				m.group(4))
		new.append(line)
	write_lines('data/collision/field_move_blocks.asm', new)

	if 'TILESET_PLAYERS_ROOM' in remap:
		new = []
		for line in lines('data/decorations/attributes.asm'):
			m = DECORATION.match(line)
			if m and int(m.group(3), 16):
				line = m.group(1) + block('TILESET_PLAYERS_ROOM', m.group(3)) + m.group(4)
			new.append(line)
		write_lines('data/decorations/attributes.asm', new)


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('--apply', action='store_true')
	args = ap.parse_args()
	maps = Maps()
	plans = plan(maps)
	total = 0
	for (meta, coll), (tilesets, keep, count) in plans.items():
		saved = (count - len(keep)) * (METATILE_SIZE + COLLISION_SIZE)
		total += saved
		print(f'{meta}: {count - len(keep)} of {count} blocks unused ({saved} bytes)')
	print(f'{total} bytes')
	if args.apply:
		apply(maps, plans)


if __name__ == '__main__':
	main()
