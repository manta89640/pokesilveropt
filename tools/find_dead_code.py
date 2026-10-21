#!/usr/bin/env python3
"""
List code and data blocks that are unreachable in retail (non-debug) builds.

Usage: tools/find_dead_code.py [pokesilver.sym] [--version gold|silver]

The source is split into blocks, one per global label. A block is live if a
live block references its label, or if a live block can fall through into
it. Code before the first label of a file or section is a root, as are
labels whose names are built by macros (map attributes, std scripts, etc.).
This is a heuristic: review its output before removing anything.
"""

import argparse
import bisect
import collections
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ROM_OBJECTS = [
	'home.asm', 'main.asm', 'audio.asm', 'data/text/common.asm', 'data/maps/map_data.asm',
	'data/pokemon/egg_moves.asm', 'data/pokemon/evos_attacks.asm', 'engine/movie/credits.asm',
	'engine/overworld/events.asm', 'gfx/misc.asm', 'gfx/sprites.asm', 'gfx/tilesets.asm',
	'data/pokemon/dex_entries_{v}.asm', 'gfx/pics_{v}.asm',
]

# Labels whose names macros construct; treat them as roots
CONSTRUCTED_SUFFIXES = ('Predef', 'StdScript', 'Special', '_MapAttributes', '_Blocks',
	'_MapScripts', '_MapEvents', '_MapSetupCmd', '_TradeCmd')
TILESET_SUFFIXES = ('GFX', 'Meta', 'Coll', 'Anim', 'PalMap')

TERMINATORS = re.compile(r'^\s*(ret|reti|jp|jr|farjp|predef_jump|jumpstd|end|endcallback|'
	r'sjump|endtext|text_end|done|prompt|step_end|endall|db|dw|dba|dbw|dwb|dn|dt|dd|ds|'
	r'INCBIN|incbin|dab|bigdw|dc|dr|sound_ret|anim_ret|anim_jump|sound_loop|'
	r'anim_end|oamend|endanim|step_loop|dex_end|movement_end|jump|loopchannel|endchannel)\b(.*)$')

# Directives that emit nothing, so they don't end a block
NON_EMITTING = re.compile(r'^(const|const_def|const_skip|const_next|shift_const|rb_skip|def|redef|'
	r'assert|static_assert|charmap|newcharmap|setcharmap|pushc|popc|pusho|popo|opt|export|purge|'
	r'println|print|warn|fail|table_width|assert_table_length|list_start|assert_list_length|'
	r'_redef_current_label|maskbits|rsreset|rsset|vc_hook|vc_assert|vc_patch|vc_patch_end|'
	r'align|endr|rept|for|endl|load|endu|union|nextu)\b', re.I)

IDENT = re.compile(r'[A-Za-z_][\w]*(?:\.[\w]+)?')


def strip(line):
	"""Removes a comment from a line."""
	in_str = False
	i = 0
	while i < len(line):
		c = line[i]
		if in_str:
			if c == '\\':
				i += 1
			elif c == '"':
				in_str = False
		elif c == '"':
			in_str = True
		elif c == ';':
			return line[:i]
		i += 1
	return line


STRING = re.compile(r'"(?:[^"\\]|\\.)*"')


class Block:
	def __init__(self, label, path, lineno):
		self.label = label
		self.path = path
		self.lineno = lineno
		self.refs = set()
		self.last = ''
		self.next = None
		self.root = label is None


def eval_cond(cond, defines):
	cond = cond.strip()
	m = re.fullmatch(r'(!?)\s*DEF\((\w+)\)', cond)
	if m:
		val = m.group(2) in defines
		return (not val) if m.group(1) else val
	m = re.fullmatch(r'DEF\((\w+)\)\s*\|\|\s*DEF\((\w+)\)', cond)
	if m:
		return m.group(1) in defines or m.group(2) in defines
	return None  # unknown


def parse(defines):
	blocks = []
	labels = {}
	seen_files = set()

	def parse_file(rel, parent_block):
		path = os.path.join(ROOT, rel)
		lines = open(path, encoding='utf-8').read().split('\n')
		cur = parent_block
		stack = []  # conditional states: (active, known)
		macro_depth = 0
		for lineno, raw in enumerate(lines, 1):
			line = strip(raw)
			s = line.strip()
			if not s:
				continue
			low = s.lower()
			first = low.split()[0] if low.split() else ''
			if first in ('if',):
				val = eval_cond(s[2:], defines)
				active = all(a for a, _ in stack)
				stack.append((val is not False, val))
				continue
			if first == 'elif':
				continue
			if first == 'else':
				a, val = stack.pop()
				stack.append((val is not True, val))
				continue
			if first == 'endc':
				stack.pop()
				continue
			if not all(a for a, _ in stack):
				continue
			if first == 'macro':
				macro_depth += 1
				continue
			if first == 'endm':
				macro_depth -= 1
				continue
			if macro_depth:
				continue
			if first == 'section':
				cur = Block(None, rel, lineno)
				blocks.append(cur)
				continue
			m = re.match(r'^([A-Za-z_][\w]*)(:{1,2})(.*)$', line)
			if m and not line[0].isspace():
				new = Block(m.group(1), rel, lineno)
				if cur is not None:
					cur.next = new
				cur = new
				blocks.append(cur)
				labels[m.group(1)] = cur
				line = ' ' + m.group(3)
				s = line.strip()
				if not s:
					continue
			m = re.match(r'^(\.[\w]+):*(.*)$', s)
			if m:
				s = m.group(2).strip()
				line = ' ' + s
				if not s:
					continue
			mi = re.match(r'^\s*include\s+"([^"]+)"', line, re.I)
			if mi:
				inc = mi.group(1)
				if inc.endswith('.asm') and os.path.exists(os.path.join(ROOT, inc)):
					if inc not in seen_files:
						seen_files.add(inc)
					# Included code continues the current block stream
					cur = parse_file(inc, cur)
				continue
			if re.match(r'^\s*incbin\b', line, re.I):
				cur.last = 'db'
				continue
			if cur is None:
				cur = Block(None, rel, lineno)
				blocks.append(cur)
			for tok in IDENT.findall(STRING.sub('', line)):
				cur.refs.add(tok)
			if not NON_EMITTING.match(s) and not re.match(r'^\w+\s+(EQUS?|=|SET)\b', s, re.I):
				cur.last = s
		return cur

	for obj in ROM_OBJECTS:
		parse_file(obj.format(v=defines['_VERSION']), None)
	return blocks, labels


SM83 = set("""ld ldh ldi ldd add adc sub sbc and or xor cp inc dec push pop call rst rlca rla rrca rra
	rlc rl rrc rr sla sra srl swap bit set res nop halt stop di ei daa cpl scf ccf jp jr ret reti""".split())
CODE_MACROS = set("""farcall callfar homecall predef lda_predef predef_jump hlcoord bccoord decoord coord
	ldcoord_a lda_coord lb ln jumptable hlbgcoord bcbgcoord debgcoord bgcoord hlpixel bcpixel depixel
	ldpixel calc_sine_wave""".split())


def script_macros():
	names = set()
	for name in os.listdir(os.path.join(ROOT, 'macros/scripts')):
		for line in open(os.path.join(ROOT, 'macros/scripts', name), encoding='utf-8'):
			m = re.match(r'^MACRO\s+(\w+)', line)
			if m:
				names.add(m.group(1))
	return names


SCRIPT_MACROS = script_macros()


def falls_through(block):
	"""Whether execution can continue past the end of a block."""
	last = block.last
	if not last:
		return True
	op = last.split()[0].lower()
	m = TERMINATORS.match(last)
	if m:
		rest = m.group(2).strip()
		if op in ('jp', 'jr'):
			# conditional jumps fall through
			return bool(re.match(r'^(nz|z|nc|c)\s*,', rest))
		if op == 'ret':
			return bool(rest)
		return False
	# Data can't fall through; code and scripts can
	return op in SM83 or op in CODE_MACROS or last.split()[0] in SCRIPT_MACROS


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('sym', nargs='?', default=os.path.join(ROOT, 'pokesilver.sym'))
	ap.add_argument('--version', default='silver')
	ap.add_argument('--debug', action='store_true')
	args = ap.parse_args()
	defines = {'_' + args.version.upper(): 1, '_VERSION': args.version}
	if args.debug:
		defines['_DEBUG'] = 1
	blocks, labels = parse(defines)

	live = set()
	queue = collections.deque()

	def mark(b):
		if id(b) not in live:
			live.add(id(b))
			queue.append(b)

	for b in blocks:
		if b.root:
			mark(b)
	while queue:
		b = queue.popleft()
		for tok in b.refs:
			base = tok.split('.')[0]
			target = labels.get(base)
			if target is not None:
				mark(target)
			# Labels whose names macros build from this token
			for suffix in CONSTRUCTED_SUFFIXES + TILESET_SUFFIXES:
				target = labels.get(base + suffix)
				if target is not None:
					mark(target)
		if b.next is not None and falls_through(b):
			mark(b.next)

	syms = {}
	by_bank = collections.defaultdict(list)
	for line in open(args.sym):
		m = re.match(r'([0-9a-f]+):([0-9a-f]+) (\S+)', line)
		if m:
			bank, addr, name = int(m.group(1), 16), int(m.group(2), 16), m.group(3)
			syms[name] = (bank, addr)
			if '.' not in name:
				by_bank[bank].append(addr)
	for bank in by_bank:
		by_bank[bank].sort()

	# A dead data block right after live data may be reached by offset
	prev_of = {}
	for b in blocks:
		if b.next is not None:
			prev_of[id(b.next)] = b

	def is_data(b):
		if not b.last or b.last == 'include':
			return False
		op = b.last.split()[0]
		return op.lower() not in SM83 and op not in CODE_MACROS and op not in SCRIPT_MACROS

	total = 0
	dead = []
	suspects = set()
	for b in blocks:
		if b.label is None or id(b) in live or b.label not in syms:
			continue
		prev = prev_of.get(id(b))
		suspect = prev is not None and is_data(prev) and is_data(b) and prev.path == b.path \
			and (id(prev) in live or id(prev) in suspects)
		if suspect:
			suspects.add(id(b))
		bank, addr = syms[b.label]
		if bank == 0 and addr >= 0x8000:
			continue
		lst = by_bank[bank]
		i = bisect.bisect_right(lst, addr)
		size = (lst[i] if i < len(lst) else addr) - addr
		total += size
		dead.append((b.path, b.lineno, b.label, size, suspect))
	for path, lineno, label, size, suspect in sorted(dead):
		print(f'{path}:{lineno}: {label} ({size} bytes){" SUSPECT" if suspect else ""}')
	print(f'total: {total} bytes in {len(dead)} blocks')


if __name__ == '__main__':
	main()
