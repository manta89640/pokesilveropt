#!/usr/bin/env python3
"""
Check that every song, sound effect and cry plays the same notes and commands
as in a reference ROM.

Usage: tools/tests/verify_music.py reference.gbc modified.gbc

For each entry of the Music, SFX and Cries tables, this follows each
channel's data the way the sound engine does (sound_call, sound_ret,
sound_loop and sound_jump), and compares everything else it reads: the notes
and the other commands with their parameters, in order. It stops after STEPS
of them, or where the channel ends. The reference ROM's engine can only call
one level deep; the modified one can call two. Both ROMs need their .sym
files.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STEPS = 20000
FIRST_MUSIC_CMD = 0xd0
CHAN4 = 3

# Number of parameter bytes of each command, or None if the checker doesn't
# know the command (which music doesn't use)
PARAMS = {0xd9: 1, 0xda: 2, 0xdb: 1, 0xdc: 1, 0xdd: 1, 0xde: 1, 0xdf: 0, 0xe0: 2, 0xe1: 2,
	0xe4: 1, 0xe5: 1, 0xe6: 2, 0xec: 0, 0xed: 0, 0xef: 1, 0xfa: 1}
for cmd in range(0xd0, 0xd8):
	PARAMS[cmd] = 0
for cmd in range(0xf1, 0xf9):
	PARAMS[cmd] = 0
TOGGLE_NOISE, SFX_TOGGLE_NOISE = 0xe3, 0xf0
TOGGLE_SFX = 0xdf
NOTE_TYPE = 0xd8
JUMP_IF, JUMP, LOOP, CALL, RET = 0xfb, 0xfc, 0xfd, 0xfe, 0xff


class Rom:
	def __init__(self, path):
		self.data = open(path, 'rb').read()
		self.syms = {}
		for line in open(os.path.splitext(path)[0] + '.sym'):
			m = re.match(r'([0-9a-f]+):([0-9a-f]+) (\S+)', line)
			if m:
				self.syms[m.group(3)] = (int(m.group(1), 16), int(m.group(2), 16))

	def byte(self, bank, addr):
		return self.data[addr if addr < 0x4000 else bank * 0x4000 + addr - 0x4000]

	def word(self, bank, addr):
		return self.byte(bank, addr) | self.byte(bank, addr + 1) << 8


def play_channel(rom, bank, addr, channel, depth, sfx):
	"""Returns the list of notes and commands that a channel plays. Sound effects
	and cries start with notes that have a volume envelope and frequency."""
	out = []
	stack = []
	looping = False
	loop_count = 0
	condition = 0
	noise = False
	while len(out) < STEPS:
		cmd = rom.byte(bank, addr)
		addr += 1
		if cmd < FIRST_MUSIC_CMD:
			if sfx:
				n = 2 if channel & 3 == CHAN4 else 3
				out.append((cmd,) + tuple(rom.byte(bank, addr + i) for i in range(n)))
				addr += n
			else:
				out.append((cmd,))
		elif cmd == RET:
			if not stack:
				out.append(('end',))
				break
			addr = stack.pop()
		elif cmd == CALL:
			if len(stack) == depth:
				out.append(('call too deep',))
				break
			stack.append(addr + 2)
			addr = rom.word(bank, addr)
		elif cmd == JUMP:
			addr = rom.word(bank, addr)
		elif cmd == JUMP_IF:
			if rom.byte(bank, addr) == condition:
				addr = rom.word(bank, addr + 1)
			else:
				addr += 3
		elif cmd == LOOP:
			count = rom.byte(bank, addr)
			if not looping and count:
				looping = True
				loop_count = count - 1
			if looping and loop_count == 0:
				looping = False
				addr += 3
			else:
				if looping:
					loop_count -= 1
				addr = rom.word(bank, addr + 1)
		else:
			if cmd == NOTE_TYPE:
				n = 1 if channel & 3 == CHAN4 else 2
			elif cmd in (TOGGLE_NOISE, SFX_TOGGLE_NOISE):
				n = 0 if noise else 1
				noise = not noise
			elif cmd == TOGGLE_SFX:
				n = 0
				sfx = not sfx
			elif PARAMS.get(cmd) is None:
				out.append(('unknown command', cmd))
				break
			else:
				n = PARAMS[cmd]
			params = tuple(rom.byte(bank, addr + i) for i in range(n))
			if cmd == 0xfa:
				condition = params[0]
			addr += n
			out.append((cmd,) + params)
	return out


def play_song(rom, table, song, depth):
	table_bank, table = rom.syms[table]
	entry = table + song * 3
	bank = rom.byte(table_bank, entry)
	header = rom.word(table_bank, entry + 1)
	count = (rom.byte(bank, header) >> 6) + 1
	channels = []
	for i in range(count):
		channel = rom.byte(bank, header + i * 3) & 0xf
		addr = rom.word(bank, header + i * 3 + 1)
		channels.append((channel, play_channel(rom, bank, addr, channel, depth,
			table != rom.syms['Music'][1])))
	return channels


def main():
	ref, new = Rom(sys.argv[1]), Rom(sys.argv[2])
	bad = 0
	for table, path in (('Music', 'music_pointers'), ('SFX', 'sfx_pointers'),
			('Cries', 'cry_pointers')):
		count = sum(1 for line in open(os.path.join(ROOT, f'audio/{path}.asm'))
			if re.match(r'\s+dba\b', line))
		differ = 0
		for i in range(count):
			a = play_song(ref, table, i, 1)
			b = play_song(new, table, i, 2)
			problems = [x for channel in a + b for x in channel[1] if x[0] in
				('call too deep', 'unknown command')]
			if a != b or problems:
				differ += 1
				print(f'{table} {i} differs', problems[:1])
		print(f'{table}: {count} checked, {differ} differ')
		bad += differ
	sys.exit(1 if bad else 0)


if __name__ == '__main__':
	main()
