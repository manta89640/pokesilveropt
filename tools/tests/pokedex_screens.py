#!/usr/bin/env python3
"""
Go through the Pokédex's screens and print a hash of each.

Usage: tools/tests/pokedex_screens.py rom.gbc save.ram > screens.txt

Starting from a save (with Unown mode unlocked and every Unown caught), this
opens the Pokédex and goes through the list in each mode (new, old, A to Z)
one step at a time, the option screen, the search screen and its results, a
Pokédex entry and Unown mode. After each step it waits for the screen to
settle and hashes the tilemap (without the blinking arrow cursor), the
attribute map and the sprites, so the
drawing code can be compared with the original ROM's. Run it on two ROMs and
diff the output.
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

STATUSFLAGS_UNOWN_DEX_F = 1
NUM_UNOWN = 26
SCREEN_AREA = 20 * 18
OAM_SIZE = 40 * 4
ARROW = 0xed  # '▶'
SPACE = 0x7f  # ' '


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

	def press(button, wait=90):
		pb.button_press(button)
		tick(4)
		pb.button_release(button)
		tick(wait)

	def dump(name):
		# The arrow cursor blinks, so it's left out
		tilemap = bytes(SPACE if t == ARROW else t for t in (mem[sym['wTilemap'] + i] for i in range(SCREEN_AREA)))
		data = tilemap + b''.join(bytes(mem[sym[label] + i] for i in range(n))
			for label, n in (('wAttrmap', SCREEN_AREA), ('wShadowOAM', OAM_SIZE)))
		print(f'{name} {hashlib.md5(data).hexdigest()[:12]}', flush=True)
		if os.environ.get('DEX_SHOTS'):
			# With DEX_SHOTS set to a directory, also save a screenshot of each step
			pb.tick(1, True)
			FRAMES[0] += 1
			pb.screen.image.save(os.path.join(os.environ['DEX_SHOTS'], name.replace(' ', '_') + '.png'))

	# Continue from the save
	tick(400)
	press('start', 60)
	press('a', 120)
	press('a', 200)
	press('a', 200)
	tick(100)
	# Unlock Unown mode with every Unown caught, in order
	mem[sym['wStatusFlags']] |= 1 << STATUSFLAGS_UNOWN_DEX_F
	for i in range(NUM_UNOWN):
		mem[sym['wUnownDex'] + i] = i + 1
	mem[sym['wFirstUnownSeen']] = 1

	# Open the Pokédex
	press('start', 60)
	press('a', 200)

	def walk_list(mode):
		dump(f'{mode} list')
		for i in range(10):
			press('down', 60)
			dump(f'{mode} down {i}')
		press('right', 60)
		dump(f'{mode} page down')
		press('left', 60)
		dump(f'{mode} page up')
		for i in range(12):
			press('up', 60)
			dump(f'{mode} up {i}')

	def option(index):
		# open the option screen, pick a mode, and go back to the list
		press('select', 120)
		dump(f'option {index}')
		for _ in range(4):
			press('up', 40)
		for _ in range(index):
			press('down', 40)
		dump(f'option {index} cursor')
		press('a', 400)

	walk_list('start')
	for index, mode in enumerate(('new', 'old', 'abc')):
		option(index)
		walk_list(mode)

	# Search: type 1 next three times, type 2 once, then search
	press('start', 120)
	dump('search')
	for i in range(3):
		press('right', 60)
		dump(f'search type1 {i}')
	press('down', 60)
	press('right', 60)
	dump('search type2')
	press('up', 60)
	press('left', 60)
	press('left', 60)
	press('down', 60)
	press('left', 60)
	dump('search types')
	press('down', 60)
	press('a', 600)
	dump('search results')
	for i in range(5):
		press('down', 60)
		dump(f'search results down {i}')
	press('a', 200)
	dump('search results entry')
	press('b', 200)
	dump('back to search results')
	press('b', 200)
	dump('back to search')
	press('b', 200)
	dump('after search')

	# A Pokémon's entry and its second page
	press('a', 200)
	dump('entry')
	press('a', 120)
	dump('entry page 2')
	press('down', 200)
	dump('entry next')
	press('b', 200)
	dump('list after entry')

	# Unown mode
	option(3)
	dump('unown mode')
	for i in range(NUM_UNOWN + 1):
		press('right', 40)
		dump(f'unown right {i}')
	for i in range(3):
		press('left', 40)
		dump(f'unown left {i}')
	press('b', 300)
	dump('after unown mode')

	pb.stop(save=False)
	shutil.rmtree(tmp)


if __name__ == '__main__':
	main()
