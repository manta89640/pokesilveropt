#!/usr/bin/env python3
"""
Generate the text compression dictionary.

Usage: tools/textdict.py [--singles N] [--doubles N] [--groups-only]

Reads every compressible string in the source tree and picks a dictionary of
frequent substrings. Writes:
  constants/text_dict_charmap.asm - the "dict" charmap used by text macros
  data/text/dictionary.asm        - the dictionary entries themselves

Strings are encoded by rgbasm itself: the "dict" charmap maps each entry's
text to its code, and rgbasm's greedy longest-match picks the entries.
Single-byte codes reuse character values below FIRST_REGULAR_TEXT_CHAR that
PlaceString does not otherwise handle. Two-byte codes are a prefix byte
(1 to NUM_DICT_PREFIXES) followed by a byte from $60 to $ff, so neither byte
of any code can be mistaken for a control character.
"""

import argparse
import collections
import heapq
import itertools
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FIRST_REGULAR_TEXT_CHAR = 0x60
GROUP_SIZE = 16
SECOND_BYTE_MIN = 0x60
CODES_PER_PREFIX = 0x100 - SECOND_BYTE_MIN
MAX_ENTRY_LEN = 24

# Control characters that may appear inside a dictionary entry: they only
# print a fixed or RAM string, so they are safe to nest.
NESTABLE_CONTROLS = {
	'#', '<PLAYER>', '<RIVAL>', '<MOM>', '<RED>', '<GREEN>', '<ENEMY>',
	'<TARGET>', '<USER>', '<PC>', '<TM>', '<TRAINER>', '<ROCKET>',
	'<PKMN>', '<POKE>', '<……>',
}

# Character values that PlaceString handles specially (see home/text.asm),
# or that are otherwise reserved.
RESERVED_CODES = {
	0x00, # <NULL>
	0x1f, # <BSP>
	0x22, # <LF>
	0x24, # <POKE>
	0x25, # <WBR>
	0x38, # <RED>
	0x39, # <GREEN>
	0x3f, # <ENEMY>
	0x49, # <MOM>
	0x4a, # <PKMN>
	0x4b, # <_CONT>
	0x4c, # <SCROLL>
	0x4e, # <NEXT>
	0x4f, # <LINE>
} | set(range(0x50, 0x60)) # "@" and the remaining control characters

TEXT_MACROS = ('text', 'line', 'para', 'cont', 'next', 'page')

# Files whose `db` strings are compressed too (see their pushc/popc).
DB_TEXT_FILES = re.compile(r'^data/(pokemon/dex_entries/|moves/descriptions\.asm|items/descriptions\.asm|maps/landmarks\.asm|credits_strings\.asm|trainers/parties\.asm)')

# Name lists whose `li` strings are compressed (see their pushc/popc).
# Pokémon names are not: they are copied into nicknames.
LIST_TEXT_FILES = re.compile(r'^data/(items/names|moves/names|trainers/class_names)\.asm$')

SKIP_DIRS = ('tools', '.git', 'engine/debug')


def read_charmap():
	charmap = {}
	path = os.path.join(ROOT, 'constants/charmap.asm')
	for line in open(path, encoding='utf-8'):
		m = re.match(r'\s*charmap\s+"((?:[^"\\]|\\.)*)",\s*\$([0-9a-f]+)', line)
		if m:
			key = m.group(1).replace('\\"', '"')
			# The first definition of a key is the one in effect for English text
			charmap.setdefault(key, int(m.group(2), 16))
	return charmap


class Tokenizer:
	"""Greedy longest-match string encoding, like rgbasm's charmaps."""

	def __init__(self, keys):
		self.by_first = collections.defaultdict(list)
		for key in keys:
			self.by_first[key[0]].append(key)
		for lst in self.by_first.values():
			lst.sort(key=len, reverse=True)

	def split(self, s):
		units = []
		i = 0
		while i < len(s):
			for key in self.by_first.get(s[i], ()):
				if s.startswith(key, i):
					units.append(key)
					i += len(key)
					break
			else:
				raise ValueError(f'unmapped character {s[i]!r} in {s!r}')
		return units


def iter_asm_files():
	for root, dirs, files in os.walk(ROOT):
		rel = os.path.relpath(root, ROOT)
		if rel.startswith(SKIP_DIRS):
			dirs[:] = []
			continue
		dirs.sort()
		for name in sorted(files):
			if name.endswith('.asm'):
				path = os.path.join(root, name)
				yield os.path.relpath(path, ROOT).replace(os.sep, '/'), path


def strip_comment(line):
	in_string = False
	for i, c in enumerate(line):
		if c == '"' and (i == 0 or line[i - 1] != '\\'):
			in_string = not in_string
		elif c == ';' and not in_string:
			return line[:i]
	return line


STRING_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')
MACRO_RE = re.compile(r'^\s*(?:[\w.]+:+\s*)?(' + '|'.join(TEXT_MACROS) + r'|db|li)\b(.*)$')


def collect_strings():
	"""Yields (weight, string) for every compressible string literal."""
	for rel, path in iter_asm_files():
		db_file = DB_TEXT_FILES.match(rel) is not None
		list_file = LIST_TEXT_FILES.match(rel) is not None
		# Pokédex entries exist once per version; each ROM has only half of them
		weight = 0.5 if rel.startswith('data/pokemon/dex_entries/') else 1
		for line in open(path, encoding='utf-8'):
			m = MACRO_RE.match(strip_comment(line))
			if not m:
				continue
			macro, args = m.groups()
			if macro == 'db' and not db_file or macro == 'li' and not list_file:
				continue
			for s in STRING_RE.findall(args):
				if '{' in s:
					continue
				yield weight, s.replace('\\"', '"')


def build_runs(charmap):
	tok = Tokenizer(charmap.keys())
	runs = collections.Counter()
	total = 0
	for weight, s in collect_strings():
		units = tok.split(s)
		total += weight * len(units)
		cur = []
		for u in units:
			if charmap[u] >= FIRST_REGULAR_TEXT_CHAR or u in NESTABLE_CONTROLS:
				cur.append(u)
			else:
				if cur:
					runs[tuple(cur)] += weight
				cur = []
		if cur:
			runs[tuple(cur)] += weight
	return runs, total


def select_entries(runs, num_entries, num_singles, max_ngram=6):
	"""Byte-pair-encoding style selection of dictionary entries.

	Repeatedly picks the n-gram of units (or of previously picked entries)
	that saves the most bytes, and replaces it in the corpus.
	Returns a list of expansions (tuples of units)."""
	# Runs are numbered so that iteration order (and thus the result) does not
	# depend on Python's string hashing
	run_list = list(runs)
	weights = [runs[r] for r in run_list]
	seqs = [list(r) for r in run_list]
	expansions = []
	exp_len = []
	counts = collections.Counter()
	index = collections.defaultdict(set)

	def ngrams(s):
		n = len(s)
		for i in range(n - 1):
			for length in range(2, min(max_ngram, n - i) + 1):
				yield tuple(s[i:i + length])

	for k, r in enumerate(run_list):
		for g in ngrams(seqs[k]):
			counts[g] += weights[k]
		for u in r:
			index[u].add(k)

	def savings(g, code_cost):
		length = sum(exp_len[x] if isinstance(x, int) else 1 for x in g)
		if length > MAX_ENTRY_LEN:
			return 0
		return counts[g] * (len(g) - code_cost) - (len(g) + 1)

	tiebreak = itertools.count()

	def make_heap(code_cost):
		heap = []
		for g in counts:
			sav = savings(g, code_cost)
			if sav > 0:
				heap.append((-sav, next(tiebreak), g))
		heapq.heapify(heap)
		return heap

	code_cost = 1 if num_singles else 2
	heap = make_heap(code_cost)
	for it in range(num_entries):
		if it == num_singles and code_cost == 1:
			code_cost = 2
			heap = make_heap(code_cost)
		best = None
		while heap:
			neg, _, g = heapq.heappop(heap)
			sav = savings(g, code_cost)
			if sav <= 0:
				continue
			if sav < -neg:
				heapq.heappush(heap, (-sav, next(tiebreak), g))
				continue
			best, best_savings = g, sav
			break
		if best is None:
			break
		new_id = len(expansions)
		expansion = tuple(u for x in best for u in (expansions[x] if isinstance(x, int) else (x,)))
		expansions.append(expansion)
		exp_len.append(len(expansion))
		n = len(best)
		rarest = min(best, key=lambda x: (len(index[x]), str(x)))
		for k in sorted(index[rarest]):
			s = seqs[k]
			out = []
			i = 0
			changed = False
			while i < len(s):
				if s[i] == best[0] and tuple(s[i:i + n]) == best:
					out.append(new_id)
					i += n
					changed = True
				else:
					out.append(s[i])
					i += 1
			if not changed:
				continue
			weight = weights[k]
			for g in ngrams(s):
				counts[g] -= weight
			seqs[k] = out
			for g in ngrams(out):
				counts[g] += weight
				if new_id in g:
					sav = savings(g, code_cost)
					if sav > 0:
						heapq.heappush(heap, (-sav, next(tiebreak), g))
			index[new_id].add(k)
		if it % 50 == 0:
			print(f'  {it}: {"".join(expansion)!r} saves ~{best_savings:.0f}', file=sys.stderr)
	return expansions


class GreedyParser:
	"""Greedy longest-match over source strings using unit sequences as keys."""

	def __init__(self, entries):
		# entries: dict mapping tuple-of-units -> entry index
		self.entries = entries
		self.by_first = collections.defaultdict(list)
		for e in entries:
			self.by_first[e[0]].append(e)
		for lst in self.by_first.values():
			lst.sort(key=lambda e: len(''.join(e)), reverse=True)

	def parse(self, units):
		"""Yields entry indexes or single units.

		rgbasm matches characters, not units, but entries always begin and end
		on unit boundaries in practice; the final build is verified anyway."""
		i = 0
		n = len(units)
		out = []
		while i < n:
			for e in self.by_first.get(units[i], ()):
				if tuple(units[i:i + len(e)]) == e:
					out.append(self.entries[e])
					i += len(e)
					break
			else:
				out.append(units[i])
				i += 1
		return out


def assign_codes(num_prefixes):
	singles = [c for c in range(1 + num_prefixes, FIRST_REGULAR_TEXT_CHAR) if c not in RESERVED_CODES]
	# $ff is left out: GetTrainerName finds the next trainer by looking for it
	doubles = [(p, b) for p in range(1, 1 + num_prefixes) for b in range(SECOND_BYTE_MIN, 0xff)]
	return singles, doubles


def slot_of(code):
	if len(code) == 1:
		return code[0]
	p, b = code
	return (p - 1) * CODES_PER_PREFIX + b


def asm_string(units):
	return '"' + ''.join(units).replace('"', '\\"') + '"'


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('--entries', type=int, default=0,
		help='candidate entries to pick from (default: 15%% more than there are codes)')
	ap.add_argument('--prefixes', type=int, default=18)
	args = ap.parse_args()

	charmap = read_charmap()
	runs, total = build_runs(charmap)
	print(f'corpus: {total:.0f} characters, {len(runs)} unique runs', file=sys.stderr)

	singles, doubles = assign_codes(args.prefixes)
	num_entries = args.entries or (len(singles) + len(doubles)) * 115 // 100
	expansions = select_entries(runs, num_entries, len(singles))

	# Parse the corpus greedily (as rgbasm will) to count how often each entry
	# is used. Keep the entries that save the most, and parse again, since
	# dropping entries changes which ones the greedy parse picks.
	num_codes = len(singles) + len(doubles)
	kept = list(range(len(expansions)))
	for _ in range(4):
		parser = GreedyParser({expansions[i]: i for i in kept})
		uses = collections.Counter()
		for r, weight in runs.items():
			for x in parser.parse(r):
				if isinstance(x, int):
					uses[x] += weight
		def value(i, code_len):
			length = len(expansions[i])
			return uses[i] * (length - code_len) - (length + 1)
		# One-byte codes go where they gain the most over a two-byte code
		one = sorted(kept, key=lambda i: -(value(i, 1) - max(value(i, 2), 0)))[:len(singles)]
		rest = [i for i in kept if i not in set(one) and value(i, 2) > 0]
		two = sorted(rest, key=lambda i: -value(i, 2))[:len(doubles)]
		kept = one + two
	order = kept
	entry_index = {expansions[i]: i for i in kept}
	parser = GreedyParser(entry_index)
	codes = {}
	for rank, i in enumerate(order):
		if rank < len(singles):
			codes[i] = (singles[rank],)
		elif rank - len(singles) < len(doubles):
			codes[i] = doubles[rank - len(singles)]
	used = sorted(codes, key=lambda i: slot_of(codes[i]))

	# Encode each entry with entries strictly shorter than itself (no cycles)
	def encode_entry(i):
		exp = expansions[i]
		shorter = {expansions[j]: j for j in used if len(''.join(expansions[j])) < len(''.join(exp))}
		out = []
		for x in GreedyParser(shorter).parse(exp):
			if isinstance(x, int):
				out.extend(codes[x])
			else:
				out.append(charmap[x])
		return out

	encoded = {i: encode_entry(i) for i in used}

	# Estimate compressed size
	compressed = 0
	for r, weight in runs.items():
		for x in parser.parse(r):
			compressed += weight * (len(codes[x]) if isinstance(x, int) and x in codes else 1)
	printable = sum(len(r) * w for r, w in runs.items())
	num_slots = max(slot_of(codes[i]) for i in used) + 1
	num_groups = (num_slots + GROUP_SIZE - 1) // GROUP_SIZE
	storage = sum(len(e) + 1 for e in encoded.values()) + num_groups * 2 + (num_slots - len(used))
	print(f'dictable: {printable:.0f} -> {compressed:.0f}; dictionary {storage} bytes; '
		f'net savings {printable - compressed - storage:.0f}', file=sys.stderr)

	by_slot = {slot_of(codes[i]): i for i in used}

	with open(os.path.join(ROOT, 'constants/text_dict_charmap.asm'), 'w', encoding='utf-8') as f:
		f.write('; Generated by tools/textdict.py; do not edit.\n')
		f.write('; Text macros (see macros/scripts/text.asm) encode strings with this charmap.\n\n')
		f.write(f'DEF NUM_DICT_PREFIXES EQU {args.prefixes}\n\n')
		f.write('\tnewcharmap dict, main\n')
		for slot in sorted(by_slot):
			i = by_slot[slot]
			vals = ', '.join(f'${v:02x}' for v in codes[i])
			f.write(f'\tcharmap {asm_string(expansions[i])}, {vals}\n')
		f.write('\tsetcharmap main\n')

	with open(os.path.join(ROOT, 'data/text/dictionary.asm'), 'w', encoding='utf-8') as f:
		f.write('; Generated by tools/textdict.py; do not edit.\n')
		f.write('; Entries are grouped by 16 slots; see PlaceDictEntry in home/text.asm.\n\n')
		f.write('TextDictGroups::\n')
		for g in range(num_groups):
			f.write(f'\tdw .group{g}\n')
		for slot in range(num_groups * GROUP_SIZE):
			if slot % GROUP_SIZE == 0:
				f.write(f'.group{slot // GROUP_SIZE}\n')
			if slot >= num_slots:
				break
			if slot in by_slot:
				i = by_slot[slot]
				vals = ', '.join(f'${v:02x}' for v in encoded[i])
				f.write(f'\tdb {vals}, "@" ; {asm_string(expansions[i])}\n')
			else:
				f.write('\tdb "@"\n')


if __name__ == '__main__':
	main()
