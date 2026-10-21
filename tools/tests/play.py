#!/usr/bin/env python3
"""
Play a ROM with a scripted sequence of inputs in PyBoy, saving screenshots.

Usage: tools/tests/play.py rom.gbc outdir scenario.txt [save.ram]

Prints one line per checkpoint ("shot", "state", "pos", "grass"), so the
output of two ROMs can be compared. Needs `pip install pyboy`, and the
ROM's .sym file for RAM addresses.

Scenario commands:
  wait N                     run N frames
  press BUTTON [N]           press a button for 4 frames, then wait N (20) frames
  hold BUTTON N              hold a button for N frames
  mash BUTTON COUNT N        press a button COUNT times, N frames apart
  mashshot BUTTON COUNT N P  like mash, with a screenshot named P### after each press
  walk DIR N                 take N steps
  grass N [DIR1 DIR2]        pace back and forth up to N steps until a battle starts
  shot NAME                  save a screenshot
  pos                        log the map and coordinates
  state [NAME]               log a summary of the game state
  poke SYM[+N] BYTE...       write hex bytes to RAM at a symbol (plus an offset)
  pokeor SYM[+N] BYTE        OR a hex byte into RAM
  fill SYM[+N] COUNT BYTE    write COUNT copies of a hex byte
  copy SRC[+N] DST[+N] COUNT copy COUNT bytes of RAM
  savefile NAME              stop, and copy the save file (and clock) to outdir/NAME
"""

import hashlib
import os
import re
import shutil
import sys
import time

# Drive the cartridge clock from emulated time, so runs are repeatable
FRAMES = [0]
time.time = lambda: 1700000000.0 + FRAMES[0] / 59.7275

from pyboy import PyBoy  # noqa: E402


def read_syms(rom):
	syms = {}
	for line in open(os.path.splitext(rom)[0] + '.sym'):
		m = re.match(r'([0-9a-f]+):([0-9a-f]+) (\S+)', line)
		if m:
			syms[m.group(3)] = int(m.group(2), 16)
	return syms


def main():
	rom, outdir, scenario = sys.argv[1:4]
	save = sys.argv[4] if len(sys.argv) > 4 else None
	os.makedirs(outdir, exist_ok=True)
	sym = read_syms(rom)
	# Run a copy of the ROM, so its save file does not touch the original
	copy = os.path.join(outdir, 'rom.gbc')
	shutil.copy(rom, copy)
	for ext in ('.ram', '.rtc'):
		if os.path.exists(copy + ext):
			os.remove(copy + ext)
	if save:
		shutil.copy(save, copy + '.ram')
		rtc = os.path.splitext(save)[0] + '.rtc'
		if os.path.exists(rtc):
			shutil.copy(rtc, copy + '.rtc')

	pb = PyBoy(copy, window='null', sound_emulated=False)
	pb.set_emulation_speed(0)
	mem = pb.memory
	log = []

	def tick(n):
		for _ in range(n):
			pb.tick(1, False)
			FRAMES[0] += 1

	def press(button, wait):
		pb.button_press(button)
		tick(4)
		pb.button_release(button)
		tick(wait)

	def step(direction):
		pb.button_press(direction)
		tick(16)
		pb.button_release(direction)
		tick(2)

	def shot(name):
		pb.tick(1, True)
		FRAMES[0] += 1
		image = pb.screen.image
		image.save(os.path.join(outdir, name + '.png'))
		log.append(f'{name} {hashlib.md5(image.tobytes()).hexdigest()[:10]}')

	def read(name, n):
		addr = sym[name]
		return bytes(mem[addr + i] for i in range(n))

	def address(spec):
		name, _, offset = spec.partition('+')
		return sym[name] + (int(offset, 0) if offset else 0)

	def position():
		return (f"map={mem[sym['wMapGroup']]}:{mem[sym['wMapNumber']]} "
			f"x={mem[sym['wXCoord']]} y={mem[sym['wYCoord']]}")

	for line in open(scenario):
		args = line.split('#')[0].split()
		if not args:
			continue
		cmd = args[0]
		if cmd == 'wait':
			tick(int(args[1]))
		elif cmd == 'press':
			press(args[1], int(args[2]) if len(args) > 2 else 20)
		elif cmd == 'hold':
			pb.button_press(args[1])
			tick(int(args[2]))
			pb.button_release(args[1])
		elif cmd == 'mash':
			for _ in range(int(args[2])):
				press(args[1], int(args[3]))
		elif cmd == 'mashshot':
			for i in range(int(args[2])):
				press(args[1], int(args[3]))
				shot(f'{args[4]}{i:03d}')
		elif cmd == 'walk':
			for _ in range(int(args[2])):
				step(args[1])
		elif cmd == 'grass':
			directions = (args[2], args[3]) if len(args) > 3 else ('right', 'left')
			for k in range(int(args[1])):
				step(directions[k % 2])
				if mem[sym['wBattleMode']]:
					break
			tick(30)
			log.append(f"battle={mem[sym['wBattleMode']]}")
		elif cmd == 'pos':
			log.append('pos ' + position())
		elif cmd == 'state':
			digest = lambda data: hashlib.md5(data).hexdigest()[:8]
			log.append(f"state {args[1] if len(args) > 1 else ''} {position()} "
				f"party={read('wPartyCount', 7).hex()} mon1={digest(read('wPartyMon1', 48))} "
				f"money={read('wMoney', 3).hex()} events={digest(read('wEventFlags', 256))} "
				f"items={digest(read('wNumItems', 0x60))} dex={digest(read('wPokedexCaught', 64))}")
		elif cmd == 'shot':
			shot(args[1])
		elif cmd == 'poke':
			for i, byte in enumerate(args[2:]):
				mem[address(args[1]) + i] = int(byte, 16)
		elif cmd == 'pokeor':
			mem[address(args[1])] |= int(args[2], 16)
		elif cmd == 'fill':
			for i in range(int(args[2], 0)):
				mem[address(args[1]) + i] = int(args[3], 16)
		elif cmd == 'copy':
			src, dst = address(args[1]), address(args[2])
			data = [mem[src + i] for i in range(int(args[3], 0))]
			for i, byte in enumerate(data):
				mem[dst + i] = byte
		elif cmd == 'savefile':
			pb.stop(save=True)
			target = os.path.join(outdir, args[1])
			shutil.copy(copy + '.ram', target)
			if os.path.exists(copy + '.rtc'):
				shutil.copy(copy + '.rtc', os.path.splitext(target)[0] + '.rtc')
			print('\n'.join(log))
			return
		else:
			sys.exit(f'unknown command: {line.strip()}')

	pb.stop(save=False)
	print('\n'.join(log))


if __name__ == '__main__':
	main()
