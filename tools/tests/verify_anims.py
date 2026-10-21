#!/usr/bin/env python3
"""
Check that every battle animation runs the same commands as in a reference ROM.

Usage: tools/tests/verify_anims.py reference.gbc modified.gbc

For each entry of the BattleAnimations table and each value of the
animation's parameter (wBattleAnimParam), this follows the script the way the
battle animation engine does (anim_call, anim_ret, anim_jump, anim_loop and
the conditional jumps), and compares everything else it reads: the waits and
the other commands with their parameters, in order. Scripts that check how a
Poké Ball wobbles are followed for each result. It stops after STEPS commands,
or where the script ends. Both ROMs need their .sym files.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STEPS = 2000
FIRST_COMMAND = 0xd0
WOBBLE_RESULTS = range(4)

# Number of parameter bytes of each command that doesn't change the flow
PARAMS = {0xd0: 4, 0xd1: 1, 0xd2: 2, 0xd3: 3, 0xd4: 4, 0xd5: 5, 0xd6: 1, 0xd7: 2, 0xd8: 1,
	0xe0: 2, 0xe1: 1, 0xf0: 4, 0xf1: 1, 0xf2: 1, 0xf3: 1, 0xf9: 1}
for cmd in (0xd9, 0xda, 0xdb, 0xdc, 0xdd, 0xde, 0xdf, 0xe2, 0xe3, 0xe4, 0xe5, 0xe6, 0xe7, 0xe8,
		0xe9, 0xea, 0xeb, 0xec, 0xed, 0xf4, 0xf5, 0xf6, 0xf7, 0xfa):
	PARAMS[cmd] = 0
CHECKPOKEBALL, IF_PARAM_AND, JUMPUNTIL, IF_PARAM_EQUAL = 0xdb, 0xee, 0xef, 0xf8
SETVAR, INCVAR, IF_VAR_EQUAL, JUMP, LOOP, CALL, RET = 0xf9, 0xfa, 0xfb, 0xfc, 0xfd, 0xfe, 0xff


class Rom:
	def __init__(self, path):
		self.data = open(path, 'rb').read()
		self.syms = {}
		for line in open(os.path.splitext(path)[0] + '.sym'):
			m = re.match(r'([0-9a-f]+):([0-9a-f]+) (\S+)', line)
			if m:
				self.syms[m.group(3)] = (int(m.group(1), 16), int(m.group(2), 16))
		self.bank = self.syms['BattleAnimations'][0]

	def byte(self, addr):
		return self.data[self.bank * 0x4000 + addr - 0x4000]

	def word(self, addr):
		return self.byte(addr) | self.byte(addr + 1) << 8


def run(rom, addr, param, wobble, uses):
	"""Returns what the script runs, and adds to uses whether it read the
	parameter or the wobble."""
	out = []
	parent = None
	looping = False
	loops = 0
	var = 0
	while len(out) < STEPS:
		cmd = rom.byte(addr)
		addr += 1
		if cmd < FIRST_COMMAND:
			out.append(('wait', cmd))
		elif cmd == RET:
			if parent is None:
				out.append(('end',))
				break
			addr, parent = parent, None
		elif cmd == CALL:
			if parent is not None:
				out.append(('call too deep',))
				break
			parent = addr + 2
			addr = rom.word(addr)
		elif cmd == JUMP:
			addr = rom.word(addr)
		elif cmd == LOOP:
			count = rom.byte(addr)
			if not looping and count:
				looping = True
				loops = count - 1
			if looping and loops == 0:
				looping = False
				addr += 3
			else:
				if looping:
					loops -= 1
				addr = rom.word(addr + 1)
		elif cmd in (IF_PARAM_EQUAL, IF_VAR_EQUAL, IF_PARAM_AND):
			value = rom.byte(addr)
			uses.add('param' if cmd != IF_VAR_EQUAL else 'var')
			if cmd == IF_PARAM_EQUAL:
				taken = value == param
			elif cmd == IF_VAR_EQUAL:
				taken = value == var
			else:
				taken = value & param
			addr = rom.word(addr + 1) if taken else addr + 3
		elif cmd == JUMPUNTIL:
			uses.add('param')
			if param:
				param -= 1
				addr = rom.word(addr)
			else:
				addr += 2
		elif cmd in PARAMS:
			params = tuple(rom.byte(addr + i) for i in range(PARAMS[cmd]))
			addr += PARAMS[cmd]
			out.append((cmd,) + params)
			if cmd == SETVAR:
				var = params[0]
			elif cmd == INCVAR:
				var = (var + 1) & 0xff
			elif cmd == CHECKPOKEBALL:
				var = wobble
				uses.add('wobble')
		else:
			out.append(('unknown command', cmd))
			break
	return out


def main():
	ref, new = Rom(sys.argv[1]), Rom(sys.argv[2])
	count = sum(1 for line in open(os.path.join(ROOT, 'data/moves/animations.asm'))
		if re.match(r'\tdw BattleAnim_', line))
	bad = 0
	for i in range(count):
		scripts = [rom.word(rom.syms['BattleAnimations'][1] + i * 2) for rom in (ref, new)]
		differ = False
		uses = set()
		for param in range(0x100):
			for wobble in WOBBLE_RESULTS:
				a = run(ref, scripts[0], param, wobble, uses)
				b = run(new, scripts[1], param, wobble, uses)
				if a != b or any(x[0] in ('call too deep', 'unknown command') for x in a + b):
					differ = True
				if differ or 'wobble' not in uses:
					break
			# Other parameters only matter to scripts that read it
			if differ or 'param' not in uses:
				break
		if differ:
			bad += 1
			print(f'animation {i} differs (parameter {param})')
	print(f'{count} animations checked, {bad} differ')
	sys.exit(1 if bad else 0)


if __name__ == '__main__':
	main()
