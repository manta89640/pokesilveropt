#!/usr/bin/env python3
"""
Load every map and print a hash of its blocks, including connections.

Usage: tools/tests/maps.py rom.gbc save.ram > maps.txt

Starting from a save, each map is entered like the warp script command does,
then wOverworldMapBlocks (the map's blocks plus the strips of connected
maps), the tilemap, the sprite tiles in VRAM (those of the player and every
NPC on the map), the graphics of the background tiles on the screen, the
map objects (without their script addresses) and the connections to other
maps (without the address of the strip of blocks) are hashed. Run it on two ROMs and diff the output.
"""

import hashlib
import os
import re
import shutil
import sys
import tempfile
import time

FRAMES = [0]
time.time = lambda: 1700000000.0 + FRAMES[0] / 59.7275

from pyboy import PyBoy  # noqa: E402

MAPSETUP_WARP = 0xf1
SPAWN_N_A = 0xff
MAPSTATUS_ENTER = 1
MAPSTATUS_HANDLE = 2
MAPOBJECT_LENGTH = 16
MAPOBJECT_SCRIPT_POINTER = 10
NUM_OBJECTS = 16
CONNECTION_LENGTH = 12  # map_connection_struct
CONNECTION_STRIP_POINTER = 2

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read_maps():
	maps = []
	group = 0
	number = 0
	for line in open(os.path.join(ROOT, 'constants/map_constants.asm')):
		if re.match(r'\s+newgroup\b', line):
			group += 1
			number = 0
		m = re.match(r'\s+map_const\s+(\w+),\s*(\d+),\s*(\d+)', line)
		if m:
			number += 1
			maps.append((m.group(1), group, number, int(m.group(2)), int(m.group(3))))
	return maps


def main():
	rom, save = sys.argv[1:3]
	sym = {}
	for line in open(os.path.splitext(rom)[0] + '.sym'):
		m = re.match(r'([0-9a-f]+):([0-9a-f]+) (\S+)', line)
		if m:
			sym[m.group(3)] = int(m.group(2), 16)
	tmp = tempfile.mkdtemp()
	copy = os.path.join(tmp, 'rom.gbc')
	shutil.copy(rom, copy)
	shutil.copy(save, copy + '.ram')
	rtc = os.path.splitext(save)[0] + '.rtc'
	if os.path.exists(rtc):
		shutil.copy(rtc, copy + '.rtc')

	pb = PyBoy(copy, window='null', sound_emulated=False)
	pb.set_emulation_speed(0)
	mem = pb.memory

	def tick(n):
		for _ in range(n):
			pb.tick(1, False)
			FRAMES[0] += 1

	def press(button, wait):
		pb.button_press(button)
		tick(4)
		pb.button_release(button)
		tick(wait)

	# Title screen, then CONTINUE
	tick(400)
	press('start', 60)
	press('a', 120)
	press('a', 200)
	press('a', 200)
	tick(100)

	blocks = sym['wOverworldMapBlocks']
	tilemap = sym['wTilemap']
	for name, group, number, width, height in read_maps():
		mem[sym['wMapGroup']] = group
		mem[sym['wMapNumber']] = number
		# Stand near the middle, so connections to every side are loaded
		mem[sym['wXCoord']] = width
		mem[sym['wYCoord']] = height
		mem[sym['wDefaultSpawnpoint']] = SPAWN_N_A
		mem[sym['hMapEntryMethod']] = MAPSETUP_WARP
		mem[sym['wMapStatus']] = MAPSTATUS_ENTER
		for _ in range(600):
			tick(1)
			if mem[sym['wMapStatus']] == MAPSTATUS_HANDLE:
				break
		data = bytes(mem[blocks + i] for i in range(1300))
		screen = bytes(mem[tilemap + i] for i in range(20 * 18))
		sprites = bytes(mem[0x8000 + i] for i in range(0x1000))  # vTiles0 and vTiles1
		# The map objects, without their script addresses
		objects = bytearray(mem[sym['wMapObjects'] + i] for i in range(MAPOBJECT_LENGTH * NUM_OBJECTS))
		for o in range(NUM_OBJECTS):
			objects[o * MAPOBJECT_LENGTH + MAPOBJECT_SCRIPT_POINTER] = 0
			objects[o * MAPOBJECT_LENGTH + MAPOBJECT_SCRIPT_POINTER + 1] = 0
		# The connections to other maps, without the address of the strip of
		# blocks next to this map (in ROM in the original games; this fork
		# decompresses the connected map's blocks to SRAM first). The blocks
		# column checks the strips.
		connections = bytearray(mem[sym['wNorthMapConnection'] + i] for i in range(CONNECTION_LENGTH * 4))
		for c in range(4):
			connections[c * CONNECTION_LENGTH + CONNECTION_STRIP_POINTER] = 0
			connections[c * CONNECTION_LENGTH + CONNECTION_STRIP_POINTER + 1] = 0
		# The graphics of the background tiles on the screen
		bgtiles = b''.join(bytes(mem[(0x9000 + t * 16 if t < 0x80 else 0x8800 + (t - 0x80) * 16) + i]
			for i in range(16)) for t in sorted(set(screen)))
		if os.environ.get('DUMP_MAP') == name:
			pb.tick(1, True)
			pb.screen.image.save(os.environ['DUMP_PNG'])
		print(f'{name} {group}:{number} blocks={hashlib.md5(data).hexdigest()[:12]} '
			f'tilemap={hashlib.md5(screen).hexdigest()[:12]} '
			f'sprites={hashlib.md5(sprites).hexdigest()[:12]} '
			f'bgtiles={hashlib.md5(bgtiles).hexdigest()[:12]} '
			f'objects={hashlib.md5(objects).hexdigest()[:12]} '
			f'connections={hashlib.md5(connections).hexdigest()[:12]}', flush=True)
	pb.stop(save=False)
	shutil.rmtree(tmp)


if __name__ == '__main__':
	main()
