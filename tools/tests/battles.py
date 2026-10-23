#!/usr/bin/env python3
"""
Play battles with the random numbers pinned, and log what happens.

Usage: tools/tests/battles.py rom.gbc save.ram [options] > log.txt

Starting from a save, this starts battles one after another with a small
script (loadwildmon or loadtrainer, startbattle, reloadmapafterbattle) and
plays them with a simple bot. While a battle is on, every call to Random
(which BattleRandom uses outside link battles) returns the next number of a
sequence seeded by the battle's number, so two ROMs whose battle code works
the same play the same battles, whatever their timing. The bot's choices
depend only on the battle's number, the turn and the game's state. Before
each battle the party is put back as it was in the save, and each battle can
give the player's and the wild Pokémon's moves from a list, to go through
every move.

It prints every text box (by its label in the .sym file), every battle
animation, a dump of the battle's state each time the battle menu opens, and
the result. Run it on two ROMs and diff the output: the first difference
shows where they part.

Options:
  --wild N        play N wild battles (default 64), going through every move
  --trainers      also fight every trainer of every class
  --classes A-B   only fight trainer classes A to B
  --external      make half of the wild battles take turns the way the
                  second player of a link battle does (hSerialConnectionStatus
                  set to USING_EXTERNAL_CLOCK)
  --no-anims      turn battle animations off (faster)
"""

import argparse
import hashlib
import os
import random
import re
import shutil
import sys
import tempfile
import time

FRAMES = [0]
time.time = lambda: 1700000000.0  # the clock stands still

from pyboy import PyBoy  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

NUM_MOVES = 251
STRUGGLE = 0xa5
DRAGON_RAGE = 0x52
USING_EXTERNAL_CLOCK = 0x01
OPT_BATTLE_SHIFT_F = 6  # set: "set" style, no switch prompt
OPT_BATTLE_SCENE_F = 7  # set: animations off
SCRIPT_ADDR = 0xc1e0  # unused WRAM0
LOADWILDMON, LOADTRAINER, STARTBATTLE, RELOADMAPAFTERBATTLE, END = 0x5c, 0x5d, 0x5e, 0x5f, 0x90
MAX_BATTLE_FRAMES = 60 * 60 * 20
# CAL2's party is the one Mystery Gift saved, and the battle waits for a link
SKIP_TRAINERS = {(12, 2)}
BATTLEMON_LENGTH = 0x20
PARTYMON_LENGTH = 0x30
MON_NAME_LENGTH = 11
# Moves that end a wild battle or make it drag on are left out of the
# player's moves when the bot picks them, but the list still has them all.


def parse_sym(path):
	syms = {}
	by_bank = {}
	for line in open(path):
		m = re.match(r'([0-9a-f]+):([0-9a-f]+) (\S+)', line)
		if m:
			bank, addr, name = int(m.group(1), 16), int(m.group(2), 16), m.group(3)
			syms[name] = (bank, addr)
			by_bank.setdefault(bank if addr >= 0x4000 and addr < 0x8000 else -1 if addr < 0x4000 else 'ram', []).append((addr, name))
	for v in by_bank.values():
		v.sort()
	return syms, by_bank


def trainer_counts():
	"""Number of trainers of each class, from constants/trainer_constants.asm."""
	counts = []
	for line in open(os.path.join(ROOT, 'constants', 'trainer_constants.asm')):
		if re.match(r'\s*trainerclass\s', line):
			counts.append(0)
		elif re.match(r'\s*const\s', line) and counts:
			counts[-1] += 1
	return counts


class Battles:
	def __init__(self, rom, save, args):
		self.args = args
		self.syms, self.by_bank = parse_sym(os.path.splitext(rom)[0] + '.sym')
		self.tmp = tempfile.mkdtemp()
		copy = os.path.join(self.tmp, 'rom.gbc')
		shutil.copy(rom, copy)
		self.rom = open(rom, 'rb').read()
		shutil.copy(save, copy + '.ram')
		rtc = os.path.splitext(save)[0] + '.rtc'
		if os.path.exists(rtc):
			shutil.copy(rtc, copy + '.rtc')
		self.pb = PyBoy(copy, window='null', sound_emulated=False)
		self.pb.set_emulation_speed(0)
		self.mem = self.pb.memory
		self.queue = []
		self.battle = None
		self.out = []

	def addr(self, name):
		return self.syms[name][1]

	def hook(self, name, func):
		bank, addr = self.syms[name]
		self.pb.hook_register(bank if addr >= 0x4000 else 0, addr, func, None)

	def label(self, addr):
		"""The label at or before addr, in the current ROM bank."""
		if addr < 0x4000:
			lst = self.by_bank.get(-1, [])
		elif addr < 0x8000:
			lst = self.by_bank.get(self.mem[self.addr('hROMBank')], [])
		else:
			lst = self.by_bank.get('ram', [])
		best = None
		lo, hi = 0, len(lst)
		while lo < hi:
			mid = (lo + hi) // 2
			if lst[mid][0] <= addr:
				lo = mid + 1
			else:
				hi = mid
		if lo:
			a, name = lst[lo - 1]
			best = name if a == addr else f'{name}+{addr - a}'
		return best or hex(addr)

	def log(self, text):
		print(text, flush=True)

	def read(self, name, n, offset=0):
		a = self.addr(name) + offset
		return bytes(self.mem[a + i] for i in range(n))

	def write(self, name, data, offset=0):
		a = self.addr(name) + offset
		for i, b in enumerate(data):
			self.mem[a + i] = b

	def ret(self):
		r = self.pb.register_file
		sp = r.SP
		r.PC = self.mem[sp] | self.mem[sp + 1] << 8
		r.SP = sp + 2

	# Hooks

	def on_random(self, _):
		if not self.battle or not self.mem[self.addr('wBattleMode')]:
			return
		b = self.battle
		v = b['rng'].getrandbits(16)
		add, sub = v & 0xff, v >> 8
		self.mem[self.addr('hRandomAdd')] = add
		self.mem[self.addr('hRandomSub')] = sub
		r = self.pb.register_file
		r.A = sub
		r.F = 0x80 if sub == 0 else 0
		b['randoms'] += 1
		self.ret()

	def on_text(self, _):
		if not self.battle:
			return
		r = self.pb.register_file
		label = self.label(r.HL)
		if label == 'BattleText_MonCantBeRecalled':
			self.battle['trapped'] = True
		self.log(f"  text {label}")

	def on_anim(self, _):
		if not self.battle:
			return
		fx = self.read('wFXAnimID', 2)
		self.log(f"  anim {fx[0] | fx[1] << 8:#05x} param {self.mem[self.addr('wBattleAnimParam')]} turn {self.mem[self.addr('hBattleTurn')]}")

	def snapshot(self, what):
		b = self.battle
		regions = [
			('wBattle', self.addr('wBattleEnd') - self.addr('wBattle')),
			('wEnemyMon', BATTLEMON_LENGTH),
			('wPartyCount', 8),
			('wPartyMons', 6 * PARTYMON_LENGTH),
			('wOTPartyCount', 8),
			('wOTPartyMons', 6 * PARTYMON_LENGTH),
		]
		self.log(f"  {what} randoms {b['randoms']}")
		for name, n in regions:
			self.log(f"    {name} {self.read(name, n).hex()}")

	def on_battle_menu(self, _):
		b = self.battle
		if not b:
			return
		b['menus'] += 1
		if b['menus'] == 1 and b.get('enemy_moves'):
			moves = b['enemy_moves']
			self.write('wEnemyMonMoves', moves)
			self.write('wEnemyMonPP', [10 if m else 0 for m in moves])
		if b.get('external'):
			self.mem[self.addr('hSerialConnectionStatus')] = USING_EXTERNAL_CLOCK
		self.snapshot(f"menu {b['menus']}")
		bot = random.Random(b['seed'] * 1000 + b['menus'])
		roll = bot.random()
		action = 1  # FIGHT
		if roll < 0.10 and self.switch_targets():
			action = 2  # PKMN
		elif roll < 0.15 and not b['trainer']:
			action = 4  # RUN
		if b['menus'] > 40:
			# Too long: end it
			if b['trainer']:
				self.write('wBattleMonMoves', [DRAGON_RAGE])
				self.write('wBattleMonPP', [10])
				self.write('wEnemyMonHP', [0, 1])
				action = 1
			else:
				action = 4
		b['bot'] = bot
		self.mem[self.addr('wBattleMenuCursorPosition')] = action
		self.log(f"  choose {['', 'fight', 'pkmn', 'pack', 'run'][action]}")

	def switch_targets(self):
		count = self.mem[self.addr('wPartyCount')]
		cur = self.mem[self.addr('wCurBattleMon')]
		hp = self.addr('wPartyMon1HP')
		return [i for i in range(count) if i != cur and (self.mem[hp + i * PARTYMON_LENGTH] or self.mem[hp + i * PARTYMON_LENGTH + 1])]

	def on_move_menu(self, _):
		b = self.battle
		if not b:
			return
		moves = self.read('wBattleMonMoves', 4)
		pp = self.read('wBattleMonPP', 4)
		disabled = self.mem[self.addr('wDisabledMove')]
		ok = [i for i in range(4) if moves[i] and pp[i] & 0x3f and moves[i] != disabled]
		bot = b.get('bot') or random.Random(b['seed'])
		if b['menus'] > 40 and b['trainer'] and 0 in ok:
			ok = [0]
		if ok:
			slot = bot.choice(ok)
			self.mem[self.addr('wCurMoveNum')] = slot
			self.log(f"  move slot {slot}")

	def on_party_menu(self, _):
		b = self.battle
		if not b:
			return
		targets = self.switch_targets()
		bot = b.get('bot') or random.Random(b['seed'])
		if b.pop('trapped', False):
			# The switch didn't happen: cancel
			self.mem[self.addr('wMenuCursorY')] = self.mem[self.addr('wPartyCount')] + 1
			self.log('  party cancel')
		elif targets:
			i = bot.choice(targets)
			self.mem[self.addr('wMenuCursorY')] = i + 1
			self.log(f"  party {i}")

	def on_forget_move(self, _):
		if self.battle:
			self.battle['forget'] = 0

	def on_forget_hm(self, _):
		if self.battle:
			self.battle['forget'] = self.battle.get('forget', 0) + 1

	def on_forget_menu(self, _):
		# The cursor starts on the first move; after an HM, try the next one
		if self.battle and self.battle.get('forget'):
			self.mem[self.addr('wMenuCursorY')] = self.battle['forget'] + 1

	def find_call(self, func, target, length=200):
		"""The address of the first call to target in func."""
		bank, addr = self.syms[func]
		rom = self.rom
		base = bank * 0x4000 + addr - (0x4000 if addr >= 0x4000 else 0)
		t = self.syms[target][1]
		for i in range(length):
			if rom[base + i] == 0xcd and rom[base + i + 1] == t & 0xff and rom[base + i + 2] == t >> 8:
				return bank, addr + i
		raise ValueError(f'no call to {target} in {func}')

	def on_battle_end(self, _):
		b = self.battle
		if not b:
			return
		self.snapshot('end')
		self.log(f"  result {self.mem[self.addr('wBattleResult')]:#04x}")
		b['done'] = True

	def on_mem_script(self, _):
		"""The overworld is idle: start the next battle."""
		if self.battle and not self.battle.get('done'):
			return
		if not self.queue:
			self.battle = None
			return
		self.start(self.queue.pop(0))

	def start(self, b):
		b.update(rng=random.Random(b['seed']), randoms=0, menus=0, frames=0)
		self.battle = b
		desc = f"trainer {b['trainer']} {b['id']}" if b['trainer'] else f"wild {b['species']} level {b['level']}"
		self.log(f"battle {b['seed']}: {desc}" + (' external' if b.get('external') else ''))
		# Put the party back as it was
		self.write('wPartyCount', self.party)
		self.write('wOptions', [self.options])
		if b.get('moves'):
			self.write('wPartyMon1Moves', b['moves'])
			self.write('wPartyMon1PP', [10 if m else 0 for m in b['moves']])
		self.mem[self.addr('wBattleType')] = 0
		if b['trainer']:
			script = [LOADTRAINER, b['trainer'], b['id']]
		else:
			script = [LOADWILDMON, b['species'], b['level']]
		script += [STARTBATTLE, RELOADMAPAFTERBATTLE, END]
		for i, x in enumerate(script):
			self.mem[SCRIPT_ADDR + i] = x
		self.mem[self.addr('wMapReentryScriptQueueFlag')] = 1
		self.mem[self.addr('wMapReentryScriptBank')] = 1
		self.mem[self.addr('wMapReentryScriptAddress')] = SCRIPT_ADDR & 0xff
		self.mem[self.addr('wMapReentryScriptAddress') + 1] = SCRIPT_ADDR >> 8

	def run(self):
		pb = self.pb
		args = self.args
		for _ in range(400):
			pb.tick(1, False)
		for button, wait in (('start', 60), ('a', 120), ('a', 200), ('a', 200)):
			pb.button_press(button)
			for _ in range(4):
				pb.tick(1, False)
			pb.button_release(button)
			for _ in range(wait):
				pb.tick(1, False)
		for _ in range(100):
			pb.tick(1, False)
		party_len = self.addr('wPartyMonNicknamesEnd') - self.addr('wPartyCount')
		self.party = self.read('wPartyCount', party_len)
		options = self.mem[self.addr('wOptions')]
		options = (options & ~0x07) | 1  # fast text
		options |= 1 << OPT_BATTLE_SHIFT_F
		if args.no_anims:
			options |= 1 << OPT_BATTLE_SCENE_F
		else:
			options &= ~(1 << OPT_BATTLE_SCENE_F)
		self.options = options

		# The battles to play
		moves = list(range(1, NUM_MOVES + 1))
		for i in range(args.wild):
			player = [moves[(4 * i + j) % NUM_MOVES] for j in range(4)]
			enemy = [moves[(4 * i + 2 + 97 * j) % NUM_MOVES] for j in range(4)]
			self.queue.append(dict(seed=len(self.queue), trainer=0, species=(i * 37) % 251 + 1,
				level=5 + (i * 13) % 60, moves=player, enemy_moves=enemy,
				external=args.external and i % 2 == 1))
		if args.trainers:
			counts = trainer_counts()
			lo, hi = args.classes or (1, len(counts) - 1)
			for cls in range(lo, hi + 1):
				for tid in range(1, counts[cls] + 1):
					if (cls, tid) in SKIP_TRAINERS:
						continue
					self.queue.append(dict(seed=len(self.queue), trainer=cls, id=tid))

		self.hook('Random', self.on_random)
		self.hook('PrintText', self.on_text)
		self.hook('PlayBattleAnim', self.on_anim)
		self.hook('LoadBattleMenu', self.on_battle_menu)
		self.hook('MoveSelectionScreen', self.on_move_menu)
		self.hook('PartyMenuSelect', self.on_party_menu)
		self.hook('Script_reloadmapafterbattle', self.on_battle_end)
		self.hook('RunMemScript', self.on_mem_script)
		# Don't get stuck picking an HM to forget
		self.hook('ForgetMove', self.on_forget_move)
		self.hook('ForgetMove.hmmove', self.on_forget_hm)
		bank, addr = self.find_call('ForgetMove', 'StaticMenuJoypad')
		pb.hook_register(bank, addr, self.on_forget_menu, None)

		frame = 0
		last = None
		while self.queue or (self.battle and not self.battle.get('done')):
			# Press A for 2 frames out of 6
			if frame % 6 == 0:
				pb.button_press('a')
			elif frame % 6 == 2:
				pb.button_release('a')
			pb.tick(1, False)
			frame += 1
			b = self.battle
			if b is not last:
				last, start = b, frame
			if b and not b.get('done') and frame - start > MAX_BATTLE_FRAMES:
				self.log('  TIMEOUT')
				if os.environ.get('BATTLE_SHOT'):
					pb.tick(1, True)
					pb.screen.image.save(os.environ['BATTLE_SHOT'])
					self.log(f'  PC {pb.register_file.PC:#06x} bank {self.mem[self.addr("hROMBank")]:#04x}')
				break
		pb.stop(save=False)
		shutil.rmtree(self.tmp)


def main():
	p = argparse.ArgumentParser()
	p.add_argument('rom')
	p.add_argument('save')
	p.add_argument('--wild', type=int, default=64)
	p.add_argument('--trainers', action='store_true')
	p.add_argument('--classes', type=lambda s: tuple(int(x) for x in s.split('-')))
	p.add_argument('--external', action='store_true')
	p.add_argument('--no-anims', action='store_true')
	args = p.parse_args()
	Battles(args.rom, args.save, args).run()


if __name__ == '__main__':
	main()
