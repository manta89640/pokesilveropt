#!/usr/bin/env python3
"""
Load every picture and print a hash of it.

Usage: tools/tests/pics.py rom.gbc save.ram > pics.txt

Starting from a save, the front and back pictures of every Pokémon (and every
Unown letter), the egg, every trainer class and the player's back are loaded
by calling the game's own GetMonFrontpic, GetMonBackpic, GetTrainerPic and
DecompressGet2bpp from DelayFrame. Each picture is hashed when it is copied
from SRAM to VRAM (Get2bpp), so front pictures are hashed padded to 7x7 tiles
and back pictures with the box alignment applied. Intro_GetMonFrontpic, which
decompresses a picture as is, is checked too. Run it on two ROMs and diff the
output.
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

NUM_POKEMON = 251
EGG = 253
UNOWN = 201
NUM_UNOWN = 26
NUM_TRAINER_CLASSES = 66
PIC_BYTES = 7 * 7 * 16


def main():
	rom, save = sys.argv[1:3]
	sym = {}
	banks = {}
	for line in open(os.path.splitext(rom)[0] + '.sym'):
		m = re.match(r'([0-9a-f]+):([0-9a-f]+) (\S+)', line)
		if m:
			sym[m.group(3)] = int(m.group(2), 16)
			banks[m.group(3)] = int(m.group(1), 16)
	data = open(rom, 'rb').read()

	def predef_id(name):
		table = banks['PredefPointers'] * 0x4000 + sym['PredefPointers'] - 0x4000
		for i in range(256):
			lo, hi, bank = data[table + i * 3:table + i * 3 + 3]  # dab
			if (bank, lo | hi << 8) == (banks[name], sym[name]):
				return i
		raise KeyError(name)

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

	def tick(n=1):
		for _ in range(n):
			pb.tick(1, False)
			FRAMES[0] += 1

	def press(button, wait):
		pb.button_press(button)
		tick(4)
		pb.button_release(button)
		tick(wait)

	# Continue from the save
	tick(400)
	press('start', 60)
	press('a', 120)
	press('a', 200)
	press('a', 300)

	# Hash what Get2bpp copies from SRAM
	copied = []
	timing = os.environ.get('PIC_TIMING')
	frames_to_copy = []

	def get_2bpp(_):
		r = pb.register_file
		source = r.D << 8 | r.E
		if 0xa000 <= source < 0xc000:
			if not copied:
				frames_to_copy.append(FRAMES[0])
			copied.append(bytes(mem[source + i] for i in range(r.C * 16)))

	pb.hook_register(0, sym['Get2bpp'], get_2bpp, None)

	# Call a function from DelayFrame, as if DelayFrame called it
	calls = []

	def delay_frame(_):
		if not calls:
			return
		pc, regs = calls.pop()
		r = pb.register_file
		sp = r.SP - 2
		mem[sp] = r.PC & 0xff
		mem[sp + 1] = r.PC >> 8
		r.SP = sp
		for reg, value in regs.items():
			setattr(r, reg, value)
		r.PC = pc

	pb.hook_register(0, sym['DelayFrame'], delay_frame, None)

	def call(pc, frames=40, **regs):
		copied.clear()
		frames_to_copy.clear()
		calls.append((pc, regs))
		start = FRAMES[0]
		tick(frames)
		if calls:
			print('call did not happen')
		h = hashlib.md5(b''.join(copied)).hexdigest()[:12] if copied else 'none'
		if timing and frames_to_copy:
			# With PIC_TIMING set, also print how many frames it took to get to the copy
			h += f' {frames_to_copy[0] - start}'
		return h

	def predef(name, **regs):
		return call(sym['Predef'], A=predef_id(name), **regs)

	pics = []
	for species in list(range(1, NUM_POKEMON + 1)) + [EGG]:
		for letter in range(1, NUM_UNOWN + 1) if species == UNOWN else [1]:
			mem[sym['wCurPartySpecies']] = species
			mem[sym['wUnownLetter']] = letter
			name = f'{species}' + (f'.{letter}' if species == UNOWN else '')
			pics.append((f'front {name}', predef('GetMonFrontpic', D=0x80, E=0x00)))
			if species != EGG:
				pics.append((f'back {name}', predef('GetMonBackpic', D=0x80, E=0x00)))
			if species <= NUM_POKEMON and species != UNOWN:
				# Intro_GetMonFrontpic decompresses into de as is (Unown has its own
				# table, so its entry in PokemonPicPointers is empty)
				buffer = sym['wOverworldMapBlocks']
				for i in range(PIC_BYTES):
					mem[buffer + i] = 0
				call(sym['FarCall_hl'], A=banks['Intro_GetMonFrontpic'], HL=sym['Intro_GetMonFrontpic'],
					C=species, D=buffer >> 8, E=buffer & 0xff)
				raw = bytes(mem[buffer + i] for i in range(PIC_BYTES))
				pics.append((f'intro {species}', hashlib.md5(raw).hexdigest()[:12]))
	for trainer_class in range(1, NUM_TRAINER_CLASSES + 1):
		mem[sym['wTrainerClass']] = trainer_class
		pics.append((f'trainer {trainer_class}', predef('GetTrainerPic', D=0x80, E=0x00)))
	for name, tiles in (('ChrisBackpic', 7 * 7), ('DudeBackpic', 7 * 7), ('Shrink1Pic', 7 * 7), ('Shrink2Pic', 7 * 7)):
		pics.append((name, predef('DecompressGet2bpp', B=banks[name], C=tiles, HL=sym[name], D=0x80, E=0x00)))
	for name, h in pics:
		print(name, h)
	pb.stop(save=False)
	shutil.rmtree(tmp)


if __name__ == '__main__':
	main()
