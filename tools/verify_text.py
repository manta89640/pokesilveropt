#!/usr/bin/env python3
"""
Check that every text in a modified ROM prints the same as in a reference ROM.

Usage: tools/verify_text.py reference.gbc modified.gbc [source_dir]

Both ROMs need .sym files next to them. Text labels are found by scanning the
source for labels followed by text macros, Pokédex entries, move/item
descriptions, and the item, move and trainer class name lists. Each text is
decoded (following text_far and expanding
dictionary codes) and the results are compared.
"""

import os
import re
import sys

BANK_SIZE = 0x4000

TX_START, TX_RAM, TX_BCD, TX_MOVE, TX_BOX, TX_LOW, TX_PROMPT_BUTTON, TX_SCROLL, \
	TX_START_ASM, TX_DECIMAL, TX_PAUSE, TX_SOUND_DEX_FANFARE_50_79, TX_DOTS, \
	TX_WAIT_BUTTON, TX_SOUND_DEX_FANFARE_20_49, TX_SOUND_ITEM, TX_SOUND_CAUGHT_MON, \
	TX_SOUND_DEX_FANFARE_80_109, TX_SOUND_FANFARE, TX_SOUND_SLOT_MACHINE_START, \
	TX_STRINGBUFFER, TX_DAY, TX_FAR = range(0x17)
TX_END = 0x50

ARG_SIZES = {
	TX_RAM: 2, TX_BCD: 3, TX_MOVE: 2, TX_BOX: 4, TX_DECIMAL: 3, TX_DOTS: 1,
	TX_STRINGBUFFER: 1,
}

CHAR_END = 0x50
CHAR_DONE = 0x57
CHAR_PROMPT = 0x58
FIRST_REGULAR_TEXT_CHAR = 0x60
GROUP_SIZE = 16
CODES_PER_PREFIX = 0xa0

# Codes handled by PlaceString itself rather than as dictionary entries
CONTROL_CODES = {0x00, 0x1f, 0x22, 0x24, 0x25, 0x38, 0x39, 0x3f, 0x49, 0x4a, 0x4b,
	0x4c, 0x4e, 0x4f} | set(range(0x50, 0x60))


class Rom:
	def __init__(self, path, num_prefixes=None):
		self.data = open(path, 'rb').read()
		self.syms = {}
		for line in open(os.path.splitext(path)[0] + '.sym'):
			m = re.match(r'([0-9a-f]+):([0-9a-f]+) (\S+)', line, re.I)
			if m:
				self.syms[m.group(3)] = (int(m.group(1), 16), int(m.group(2), 16))
		self.num_prefixes = num_prefixes
		self.dict = self.syms.get('TextDictGroups') if num_prefixes is not None else None

	def offset(self, bank, addr):
		if addr < 0x4000:
			return addr
		return bank * BANK_SIZE + addr - 0x4000

	def byte(self, bank, addr):
		return self.data[self.offset(bank, addr)]

	def word(self, bank, addr):
		return self.byte(bank, addr) | self.byte(bank, addr + 1) << 8

	def dict_entry(self, slot):
		bank, table = self.dict
		addr = self.word(bank, table + 2 * (slot // GROUP_SIZE))
		for _ in range(slot % GROUP_SIZE):
			while self.byte(bank, addr) != CHAR_END:
				addr += 1
			addr += 1
		return bank, addr

	def string(self, bank, addr, out, depth=0):
		"""Decode a PlaceString string; returns (address after terminator, ended_text)."""
		while True:
			c = self.byte(bank, addr)
			addr += 1
			if c == CHAR_END:
				return addr, False
			if c in (CHAR_DONE, CHAR_PROMPT):
				out.append(c)
				return addr, True
			if self.dict and c < FIRST_REGULAR_TEXT_CHAR and c not in CONTROL_CODES:
				if c <= self.num_prefixes:
					slot = (c - 1) * CODES_PER_PREFIX + self.byte(bank, addr)
					addr += 1
				else:
					slot = c
				if depth > 8:
					raise ValueError('dictionary recursion too deep')
				dbank, daddr = self.dict_entry(slot)
				_, ended = self.string(dbank, daddr, out, depth + 1)
				if ended:
					raise ValueError('dictionary entry ends text')
				continue
			out.append(c)
			if len(out) > 5000:
				raise ValueError('runaway string')

	def text(self, bank, addr, out, depth=0):
		"""Decode a text command stream starting at bank:addr."""
		while True:
			cmd = self.byte(bank, addr)
			addr += 1
			if cmd == TX_END:
				out.append(('end',))
				return
			if cmd == TX_START:
				s = []
				addr, ended = self.string(bank, addr, s)
				out.append(('str', bytes(s)))
				if ended:
					return
			elif cmd == TX_FAR:
				target = self.word(bank, addr)
				tbank = self.byte(bank, addr + 2)
				addr += 3
				if depth > 4:
					raise ValueError('text_far recursion')
				self.text(tbank, target, out, depth + 1)
			elif cmd == TX_START_ASM:
				out.append(('asm',))
				return
			elif cmd < TX_FAR:
				n = ARG_SIZES.get(cmd, 0)
				args = bytes(self.byte(bank, addr + i) for i in range(n))
				addr += n
				out.append(('cmd', cmd, args))
			else:
				raise ValueError(f'bad text command ${cmd:02x}')


LABEL_RE = re.compile(r'^(\.?[A-Za-z_][\w.]*)(:{0,2})(?=\s|$)')
TEXT_START_RE = re.compile(r'^\s*(text|text_start|text_far|text_ram|text_decimal|text_promptbutton|'
	r'text_asm|text_end|text_buffer|text_today|text_bcd|text_low|text_scroll|text_pause|text_dots|'
	r'text_waitbutton|text_move|text_box|sound_\w+)\b')


def find_text_labels(src):
	"""Returns {label: kind} for labels that point at text."""
	labels = {}
	for root, dirs, files in os.walk(src):
		rel = os.path.relpath(root, src)
		if rel.startswith(('tools', '.git')):
			dirs[:] = []
			continue
		for name in files:
			if not name.endswith('.asm'):
				continue
			path = os.path.join(root, name)
			relpath = os.path.relpath(path, src).replace(os.sep, '/')
			scope = None
			pending = []
			for line in open(path, encoding='utf-8'):
				code = line.split(';', 1)[0].rstrip()
				if not code.strip():
					continue
				m = LABEL_RE.match(code)
				if m and not code.startswith((' ', '\t')):
					label = m.group(1)
					if label.startswith('.'):
						if scope is None:
							continue
						label = scope + label
					else:
						scope = label.split('.')[0]
					pending.append(label)
					rest = code[m.end():].strip()
					if not rest:
						continue
					code = '\t' + rest
				if pending:
					kind = None
					if TEXT_START_RE.match(code):
						kind = 'text'
					elif re.match(r'data/pokemon/dex_entries_(gold|silver)\.asm$', relpath):
						kind = 'dex'
					elif relpath in ('data/moves/descriptions.asm', 'data/items/descriptions.asm') \
							and re.match(r'^\s*db\s+"', code):
						kind = 'desc'
					if kind:
						for label in pending:
							labels[label] = kind
					pending = []
	# Name lists: one label, then a "li" per name
	for relpath in NAME_LISTS:
		label = None
		for line in open(os.path.join(src, relpath), encoding='utf-8'):
			m = re.match(r'^(\w+)::', line)
			if m:
				label = m.group(1)
			elif label and re.match(r'^\s*li\s+"', line):
				kind = labels.get(label, ('list', 0))
				labels[label] = ('list', kind[1] + 1)
	return labels


NAME_LISTS = ('data/items/names.asm', 'data/moves/names.asm', 'data/trainers/class_names.asm')


def decode(rom, label, kind):
	bank, addr = rom.syms[label]
	out = []
	if kind == 'text':
		rom.text(bank, addr, out)
	elif kind == 'desc':
		s = []
		rom.string(bank, addr, s)
		out.append(bytes(s))
	elif kind[0] == 'list':
		for _ in range(kind[1]):
			s = []
			addr, _ = rom.string(bank, addr, s)
			out.append(bytes(s))
	elif kind == 'dex':
		s = []
		addr, _ = rom.string(bank, addr, s)
		out.append(bytes(s))
		out.append(bytes(rom.byte(bank, addr + i) for i in range(4)))
		addr += 4
		for _ in range(2):
			s = []
			addr, _ = rom.string(bank, addr, s)
			out.append(bytes(s))
	return out


def main():
	ref_path, new_path = sys.argv[1:3]
	src = sys.argv[3] if len(sys.argv) > 3 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	num_prefixes = None
	charmap_path = os.path.join(src, 'constants/text_dict_charmap.asm')
	if os.path.exists(charmap_path):
		m = re.search(r'NUM_DICT_PREFIXES EQU (\d+)', open(charmap_path).read())
		num_prefixes = int(m.group(1))
	ref = Rom(ref_path)
	new = Rom(new_path, num_prefixes)
	if num_prefixes is not None and new.dict is None:
		new.num_prefixes = None
	labels = find_text_labels(src)
	checked = mismatched = skipped = 0
	for label, kind in sorted(labels.items(), key=lambda item: item[0]):
		if label not in ref.syms or label not in new.syms:
			skipped += 1
			continue
		try:
			a = decode(ref, label, kind)
		except (ValueError, IndexError):
			skipped += 1
			continue
		try:
			b = decode(new, label, kind)
		except (ValueError, IndexError) as e:
			b = [f'error: {e}']
		checked += 1
		if a != b:
			mismatched += 1
			if mismatched <= 20:
				print(f'MISMATCH {label} ({kind})')
				print('  ref:', a)
				print('  new:', b)
	print(f'{checked} texts checked, {mismatched} mismatched, {skipped} skipped')
	sys.exit(1 if mismatched else 0)


if __name__ == '__main__':
	main()
