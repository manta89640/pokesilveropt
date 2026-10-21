#!/usr/bin/env python3
"""
Merge identical code blocks that end in the same section.

Usage: tools/tailmerge.py pokesilver.map [--suffix] [--apply]

A block runs from a label to the first unconditional ret, reti, jp or jr,
with no other label in between. When two or more blocks are identical and
the linker put them in the same section, all but the first (by address) are
replaced with a jump to the first, which does exactly the same. With
--suffix, a block that ends with the same instructions as an earlier block
in the same section jumps to a label added before them in that block
instead (cross-jumping). Blocks whose operands use local labels, or that
contain data, are left alone, as are the audio, serial, link, printer and
debug code. Without --apply, only lists what it would merge. The new jumps
are jp; turn them into jr where they are in range.
"""

import argparse
import bisect
import collections
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = ('tools', '.git', 'gfx', 'maps', 'data', 'audio', 'engine/link', 'engine/printer',
	'engine/debug')
SKIP_FILES = ('home/serial.asm',)
DIRECTIVES = ('section', 'if', 'else', 'elif', 'endc', 'macro', 'endm', 'def', 'for', 'endr', 'rept',
	'charmap', 'assert', 'include', 'incbin', 'union', 'nextu', 'endu', 'load', 'endl', 'pushc',
	'popc', 'setcharmap', 'newcharmap', 'opt', 'pusho', 'popo', 'redef')
LABEL = re.compile(r'^(\.?[A-Za-z_][\w.]*)(:{0,2})(?=\s|;|$)')
LOCAL_OPERAND = re.compile(r'(^|[ ,(\[+-])\.[A-Za-z_]')
DATA = ('db', 'dw', 'dba', 'dbw', 'dn', 'ds', 'dl', 'text', 'text_far', 'li')


def read_map(path):
	"""Returns {symbol: (section, address)} and sorted addresses per section."""
	symbols = {}
	addresses = collections.defaultdict(set)
	section = None
	for line in open(path):
		m = re.match(r'\s+SECTION: \$[0-9a-f]+-\$[0-9a-f]+ \(\$[0-9a-f]+ bytes?\) \["(.*)"\]', line)
		if m:
			section = m.group(1)
			continue
		m = re.match(r'\s+\$([0-9a-f]+) = (\S+)', line)
		if m and section:
			address = int(m.group(1), 16)
			symbols[m.group(2)] = (section, address)
			addresses[section].add(address)
	return symbols, {s: sorted(a) for s, a in addresses.items()}


def find_blocks():
	blocks = collections.defaultdict(list)
	for root, dirs, files in os.walk(ROOT):
		rel = os.path.relpath(root, ROOT)
		if rel.startswith(SKIP_DIRS):
			dirs[:] = []
			continue
		dirs.sort()
		for name in sorted(files):
			path = os.path.relpath(os.path.join(root, name), ROOT)
			if not name.endswith('.asm') or path in SKIP_FILES:
				continue
			lines = open(os.path.join(ROOT, path), encoding='utf-8').read().split('\n')
			scope = None
			in_macro = False
			for i, line in enumerate(lines):
				code = line.split(';')[0].rstrip()
				word = code.strip().lower().split()[0] if code.strip() else ''
				if word == 'macro' or re.match(r'^\s*macro\b', code, re.I):
					in_macro = True
				elif word == 'endm':
					in_macro = False
				if in_macro or not code or code[0].isspace():
					continue
				m = LABEL.match(code)
				if not m or word in DIRECTIVES or code[m.end():].strip():
					continue
				label = m.group(1)
				if label.startswith('.'):
					label = f'{scope}{label}' if scope else label
				else:
					scope = label.split('.')[0]
				body = []
				where = []
				end = None
				for j in range(i + 1, min(i + 80, len(lines))):
					raw = lines[j]
					c = raw.split(';')[0].strip()
					if not c:
						continue
					if not raw[0].isspace():
						break
					body.append(re.sub(r'\s+', ' ', c))
					where.append(j)
					if re.match(r'^(reti?|(jp|jr) [^,]+)$', c):
						end = j
						break
				if end is None:
					continue
				if any(LOCAL_OPERAND.search(x) or x.split()[0] in DATA for x in body):
					continue
				blocks[tuple(body)].append((label, path, i, end, where))
	return blocks


R8 = set('abcdehl')
INDIRECT = ('[hl]', '[hli]', '[hld]', '[bc]', '[de]')


def instruction_size(ins):
	"""Size in bytes of an instruction, or None if unsure."""
	op = ins.split()[0]
	a = [x.strip() for x in ins[len(op):].split(',')] if ins[len(op):].strip() else []
	if op in ('ret', 'reti', 'nop', 'di', 'ei', 'scf', 'ccf', 'cpl', 'daa', 'rla', 'rra', 'rlca',
			'rrca', 'push', 'pop', 'rst'):
		return 1
	if op in ('inc', 'dec'):
		return 1
	if op == 'jr':
		return 2
	if op == 'jp':
		return 1 if a == ['hl'] else 3
	if op == 'call':
		return 3
	if op in ('rl', 'rr', 'rlc', 'rrc', 'sla', 'sra', 'srl', 'swap', 'bit', 'res', 'set'):
		return 2
	if op == 'ldh':
		return 1 if '[c]' in a else 2
	if op == 'ld':
		d, s = a
		if (d in R8 and (s in R8 or s in INDIRECT)) or (d in INDIRECT and s in R8):
			return 1
		if d == 'sp' and s == 'hl':
			return 1
		if d in ('bc', 'de', 'hl', 'sp') or s.startswith('[') or d.startswith('['):
			return 3
		return 2
	if op in ('add', 'adc', 'sub', 'sbc', 'and', 'or', 'xor', 'cp'):
		if a[0] == 'hl':
			return 1
		return 1 if a[-1] in R8 or a[-1] == '[hl]' else 2
	if op in ('lb', 'hlcoord', 'decoord', 'bccoord'):
		return 3
	if op in ('farcall', 'callfar', 'predef'):
		return 6
	return None


def plan_suffixes(blocks, symbols, min_size):
	"""Returns [(source member, k, target label, target member, suffix size)]."""
	by_section = collections.defaultdict(list)
	for body, members in blocks.items():
		for member in members:
			if member[0] in symbols:
				by_section[symbols[member[0]][0]].append((body, member))
	plans = []
	for section, items in by_section.items():
		items.sort(key=lambda item: symbols[item[1][0]][1])
		suffixes = {}
		for body, member in items:
			found = None
			for k in range(len(body) - 1, 1, -1):
				target = suffixes.get(body[-k:])
				if not target:
					continue
				sizes = [instruction_size(x) for x in body[-k:]]
				if None in sizes or sum(sizes) < min_size:
					continue
				found = (member, k, target, sum(sizes))
				break
			if found:
				plans.append(found)
				continue
			for k in range(2, len(body) + 1):
				suffixes.setdefault(body[-k:], (member, k))
	return plans


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('map')
	ap.add_argument('--suffix', action='store_true')
	ap.add_argument('--apply', action='store_true')
	args = ap.parse_args()
	symbols, addresses = read_map(args.map)
	if args.suffix:
		return main_suffix(args, symbols)

	def size(label):
		section, address = symbols[label]
		lst = addresses[section]
		i = bisect.bisect_right(lst, address)
		return lst[i] - address if i < len(lst) else 0

	edits = collections.defaultdict(list)  # path -> [(first line, last line, target)]
	total = 0
	for body, members in find_blocks().items():
		by_section = collections.defaultdict(list)
		for member in members:
			if member[0] in symbols:
				by_section[symbols[member[0]][0]].append(member)
		for section, group in by_section.items():
			if len(group) < 2:
				continue
			group.sort(key=lambda m: symbols[m[0]][1])
			first = group[0]
			if size(first[0]) <= 3:
				continue
			for label, path, start, end, _ in group[1:]:
				edits[path].append((start + 1, end, first[0]))
				total += size(first[0]) - 3
				print(f'{path}:{start + 1}: {label} -> {first[0]}')
	print(f'about {total} bytes')
	if not args.apply:
		return
	for path, changes in edits.items():
		full = os.path.join(ROOT, path)
		lines = open(full, encoding='utf-8').read().split('\n')
		for start, end, target in sorted(changes, reverse=True):
			lines[start:end + 1] = [f'\tjp {target} ; same as there (tools/tailmerge.py)']
		open(full, 'w', encoding='utf-8').write('\n'.join(lines))


def main_suffix(args, symbols):
	plans = plan_suffixes(find_blocks(), symbols, 5)
	replace = collections.defaultdict(list)  # path -> [(first line, last line, jump target)]
	insert = collections.defaultdict(dict)   # path -> {line: label}
	total = 0
	for (label, path, start, end, where), k, (tmember, tk), size in plans:
		tlabel, tpath, tstart, tend, twhere = tmember
		if k == len(twhere):
			target = tlabel
		else:
			line = twhere[-k]
			name = insert[tpath].get(line)
			if not name:
				name = f'.tailmerge_{line + 1}'
				insert[tpath][line] = name
			target = tlabel.split('.')[0] + name
		replace[path].append((where[-k], end, target))
		total += size - 3
		print(f'{path}:{where[-k] + 1}: {label} -> {target} ({size} bytes)')
	print(f'about {total} bytes')
	if not args.apply:
		return
	for path in set(replace) | set(insert):
		full = os.path.join(ROOT, path)
		lines = open(full, encoding='utf-8').read().split('\n')
		changes = [(start, 0, end, target) for start, end, target in replace[path]]
		changes += [(line, 1, None, name) for line, name in insert[path].items()]
		for start, kind, end, target in sorted(changes, reverse=True):
			if kind:
				lines.insert(start, f'{target}: ; (tools/tailmerge.py)')
			else:
				lines[start:end + 1] = [f'\tjp {target} ; same as there (tools/tailmerge.py)']
		open(full, 'w', encoding='utf-8').write('\n'.join(lines))


if __name__ == '__main__':
	main()
