#!/usr/bin/env python3
"""
Move runs of instructions that a section repeats into subroutines.

Usage: tools/outline.py pokesilver.map [--apply]

Within each section, this looks for runs of plain instructions (loads,
arithmetic, bit operations, far calls; no jumps, calls, returns, rst, push or
pop) that appear more than once, and replaces each copy with a call to one copy that
ends with ret. If a copy is followed by a ret already, it stays where it is,
with a label for the others to call. It picks the run that saves the most
bytes, and repeats until no run saves any. Then a call followed by a ret
becomes a jump, or the subroutine moves to right after it. A call does
the same as the instructions it replaces (calls and returns leave the
flags alone), but takes 10 more cycles. (A far call in a run is all right:
FarCall_hl and Predef stand between the function and the run, so a function
can't return past them.)

Only runs of at least MIN_SIZE bytes are moved, and each call has a comment
with the instructions it stands for. Left alone are runs with labels or
local labels in them, home code (whose timing matters more, and whose bank
is ROM0), the audio, link, printer, debug, tile animation and movie code,
the code that runs every frame for every object or sprite, and every
function that moves the stack pointer, jumps to hl, reads rLY or rSTAT, or
refers to VRAM or loads code into RAM. Without --apply, only reports how
much it would save.
"""

import argparse
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tailmerge  # noqa: E402

ROOT = tailmerge.ROOT
SKIP_DIRS = ('tools', '.git', 'gfx', 'maps', 'data', 'audio', 'home', 'engine/link',
	'engine/printer', 'engine/debug', 'engine/tilesets', 'engine/movie', 'engine/sprite_anims',
	'engine/battle_anims')
# Code that runs every frame, for every object or sprite
SKIP_FILES = ('engine/overworld/map_objects.asm', 'engine/overworld/player_step.asm',
	'engine/overworld/events.asm', 'engine/overworld/player_object.asm', 'engine/gfx/sprites.asm')
MAX_RUN = 24
MIN_SIZE = 5  # bytes of a run worth a call
CALL_SIZE = 3
RET_SIZE = 1
# A run is made of instructions that don't change the flow or the stack
FLOW = re.compile(r'^(jr|jp|call|ret|reti|rst|push|pop|di|ei|halt|stop)\b')
# A function with any of these is left alone
UNSAFE = re.compile(r'\b(sp\s*[+-]|ld sp|add sp|jp hl|_hl_|rLY|rLYC|rSTAT|vTiles\d|vBGMap\d|'
	r'vWindow|load|endl|di|ei|halt|stop|reti)\b', re.I)


class Run:
	"""Instructions that can hold calls: a list of elements, which are line
	numbers or Subs (calls) or Jumps, with a string of one character each to
	search. A run may be followed by a ret (ret_after), or by the body of a
	Sub (tail)."""
	def __init__(self, path, scope):
		self.path, self.scope = path, scope
		self.elements, self.chars = [], ''
		self.ret_after = False
		self.ret_line = None
		self.tail = None
		self.conditional = False
		self.spans = []  # [Sub, first line, last line, kind] of the copies replaced
		self.in_file = True  # in a source file, not a Sub written at the end of one


class Sub:
	def __init__(self, run, char):
		self.run, self.char = run, char
		self.inplace = False
		self.label = None


class Jump:
	def __init__(self, sub):
		self.sub = sub


def farcall_targets():
	return {m.group(1) for m in re.finditer(r'^\tfarcall_target (\w+)',
		open(os.path.join(ROOT, 'data/farcall_targets.asm')).read(), re.M)}


def instruction_size(ins, indexed):
	"""farcall, callfar and predef are shorter than tools/tailmerge.py thinks,
	since they use rst FarCallIndexed or rst PredefIndexed."""
	op, _, arg = ins.partition(' ')
	if op in ('farcall', 'callfar'):
		return 2 if arg.strip() in indexed else 6
	if op == 'predef':
		return 2
	return tailmerge.instruction_size(ins)


def read_runs(symbols):
	"""Returns {section: [runs]} and {path: lines}."""
	sections = collections.defaultdict(list)
	files = {}
	indexed = farcall_targets()
	for root, dirs, names in os.walk(ROOT):
		rel = os.path.relpath(root, ROOT)
		if rel.startswith(SKIP_DIRS):
			dirs[:] = []
			continue
		dirs.sort()
		for name in sorted(names):
			path = os.path.relpath(os.path.join(root, name), ROOT)
			if not name.endswith('.asm') or path in SKIP_FILES:
				continue
			lines = open(os.path.join(ROOT, path), encoding='utf-8').read().split('\n')
			files[path] = lines
			# Subroutines go at the end of a file, which must be in the same section
			if any(re.match(r'\s*SECTION\b', line, re.I) for line in lines):
				continue
			# Functions to leave alone
			scope = None
			unsafe = set()
			for line in lines:
				code = line.split(';')[0].rstrip()
				m = tailmerge.LABEL.match(code)
				if m and code and not code[0].isspace() and not m.group(1).startswith('.'):
					scope = m.group(1)
				elif scope and UNSAFE.search(code):
					unsafe.add(scope)
			scope = None
			run = None
			in_macro = False
			conditional = 0
			for i, line in enumerate(lines):
				code = line.split(';')[0].rstrip()
				if not code.strip():
					continue
				word = code.strip().lower().split()[0]
				if word == 'macro' or re.match(r'^\s*macro\b', code, re.I):
					in_macro = True
				elif word == 'endm':
					in_macro = False
					continue
				if in_macro:
					continue
				if word == 'if':
					conditional += 1
				elif word == 'endc':
					conditional -= 1
				if not code[0].isspace():
					m = tailmerge.LABEL.match(code)
					if m and not m.group(1).startswith('.'):
						scope = m.group(1)
					run = None
					continue
				ins = re.sub(r'\s+', ' ', code.strip())
				if run and ins == 'ret':
					run.ret_after = True
					run.ret_line = i
				size = instruction_size(ins, indexed)
				if (scope not in symbols or scope in unsafe or word in tailmerge.DIRECTIVES or
						word in tailmerge.DATA or FLOW.match(ins) or '@' in ins or
						tailmerge.LOCAL_OPERAND.search(ins) or size is None):
					run = None
					continue
				if not run:
					run = Run(path, scope)
					run.conditional = conditional > 0
					sections[symbols[scope][0]].append(run)
				run.elements.append((i, ins, size))
				run.conditional |= conditional > 0
	return sections, files


def factor(runs, sizes):
	"""Greedily moves repeated instructions of the runs into new Subs. A
	repeat at the end of a run that returns can stay there, with a label for
	the other copies to call."""
	subs = []
	next_char = 0xf0000
	while True:
		counts = collections.Counter()
		for run in runs:
			for piece in re.split('[\U000f0000-\U000fffff]', run.chars):
				n = len(piece)
				for length in range(2, min(MAX_RUN, n) + 1):
					for start in range(n - length + 1):
						counts[piece[start:start + length]] += 1
		best = None
		for phrase, count in counts.items():
			if count < 2:
				continue
			size = sum(sizes[c] for c in phrase)
			if size < MIN_SIZE or (count - 1) * (size - CALL_SIZE) <= (best[0] if best else 0):
				continue
			hosts = [run for run in runs if phrase in run.chars]
			n = sum(run.chars.count(phrase) for run in hosts)
			saved = (n - 1) * size - CALL_SIZE * n - RET_SIZE
			if saved > (best[0] if best else 0):
				best = (saved, phrase, hosts, None)
			for run in hosts:
				if run.ret_after and not run.conditional and run.chars.endswith(phrase):
					head = run.chars[:-len(phrase)]
					n = 1 + head.count(phrase) + sum(other.chars.count(phrase)
						for other in hosts if other is not run)
					saved = (n - 1) * (size - CALL_SIZE)
					if saved > (best[0] if best else 0):
						best = (saved, phrase, hosts, run)
		if not best:
			return subs
		saved, phrase, hosts, place = best
		sub_char = chr(next_char)
		next_char += 1
		sizes[sub_char] = CALL_SIZE
		if place:
			k = len(place.chars) - len(phrase)
			body = Run(place.path, place.scope)
			body.elements, body.chars = place.elements[k:], phrase
			body.ret_after, body.ret_line = True, place.ret_line
			body.in_file = place.in_file
			body.first_line = body.elements[0][0]
			place.elements, place.chars = place.elements[:k], place.chars[:k]
			place.ret_after, place.ret_line = False, None
			place.tail = sub = Sub(body, sub_char)
			sub.inplace = True
		else:
			first = hosts[0]
			start = first.chars.index(phrase)
			body = Run(first.path, first.scope)
			body.elements, body.chars = first.elements[start:start + len(phrase)], phrase
			body.ret_after = True
			body.in_file = False
			sub = Sub(body, sub_char)
		for run in hosts:
			if phrase not in run.chars:
				continue
			elements = []
			i = 0
			while True:
				j = run.chars.find(phrase, i)
				if j < 0:
					break
				copy = run.elements[j:j + len(phrase)]
				run.spans.append([sub, copy[0][0], copy[-1][0], 'call'])
				elements += run.elements[i:j] + [sub]
				i = j + len(phrase)
			run.elements = elements + run.elements[i:]
			run.chars = run.chars.replace(phrase, sub_char)
		runs.append(body)
		subs.append(sub)


def tail_calls(runs):
	"""A run that ends with a call and returns jumps instead, or goes on into the
	Sub's body if that can be placed after it."""
	saved = 0
	for run in runs:
		if not run.ret_after or not run.elements or not isinstance(run.elements[-1], Sub):
			continue
		sub = run.elements[-1]
		span = max(run.spans, key=lambda span: span[2]) if run.spans else None
		if not sub.inplace and not run.conditional and not sub.run.in_file:
			sub.inplace = True
			run.elements = run.elements[:-1]
			run.chars = run.chars[:-1]
			run.tail = sub
			if span:
				span[3] = 'tail'
			saved += CALL_SIZE + RET_SIZE
		else:
			run.elements[-1] = Jump(sub)
			if span:
				span[3] = 'jump'
			saved += RET_SIZE
			run.ret_after = False
			continue
		run.ret_after = False
	return saved


TOOL_COMMENT = '(tools/outline.py)'
OUTLINED = r'\S*(_Shared\d*|\.shared\d+)'


def expanded(files, paths):
	"""Returns the instructions of each of paths, with every call to a
	subroutine made here replaced by the instructions it runs, and the
	subroutines at the ends of files left out."""
	def norm(line):
		code = line.split(';')[0].rstrip()
		return re.sub(r'\s+', ' ', code.strip()), code

	bodies = {}
	for lines in files.values():
		scope = None
		for i, line in enumerate(lines):
			ins, code = norm(line)
			m = re.match(r'(\.?[A-Za-z_][\w.]*):', code)
			if not m or code[0].isspace():
				continue
			name = m.group(1)
			if not name.startswith('.'):
				scope = name
			if TOOL_COMMENT in line:
				body = []
				for following in lines[i + 1:]:
					ins, code = norm(following)
					if ins and code[0].isspace():
						body.append(ins)
						if ins == 'ret' or re.match(rf'(jp|jr) {OUTLINED}$', ins):
							break
				bodies[scope + name if name.startswith('.') else name] = body

	def expand(ins):
		m = re.match(rf'(call|jp|jr) ({OUTLINED})$', ins)
		if not m:
			return [ins]
		out = []
		for b in bodies[m.group(2)]:
			if b == 'ret':
				return out + (['ret'] if m.group(1) != 'call' else [])
			if re.match(rf'(jp|jr) {OUTLINED}$', b):
				tail = expand(b)
				return out + (tail[:-1] if m.group(1) == 'call' else tail)
			out += expand(b)
		return out

	streams = {}
	for path in paths:
		stream = []
		lines = files[path]
		i = 0
		while i < len(lines):
			ins, code = norm(lines[i])
			if TOOL_COMMENT in lines[i] and not code.startswith('.'):
				# A subroutine at the end of the file
				while i < len(lines) and not re.match(r'(ret|jp|jr)\b', norm(lines[i])[0]):
					i += 1
			elif ins and TOOL_COMMENT not in lines[i]:
				stream += expand(ins)
			i += 1
		streams[path] = stream
	return streams


def check(old_files, paths):
	"""Checks that the changed files run the same instructions as before."""
	new_files = dict(old_files)
	for path in paths:
		new_files[path] = open(os.path.join(ROOT, path), encoding='utf-8').read().split('\n')
	before, after = expanded(old_files, paths), expanded(new_files, paths)
	for path in paths:
		if before[path] != after[path]:
			sys.exit(f'{path}: the instructions changed; this is a bug in tools/outline.py')


def main():
	global MIN_SIZE  # noqa: PLW0603
	ap = argparse.ArgumentParser()
	ap.add_argument('map')
	ap.add_argument('--apply', action='store_true')
	ap.add_argument('--min-size', type=int, default=MIN_SIZE)
	args = ap.parse_args()
	MIN_SIZE = args.min_size
	symbols, _ = tailmerge.read_map(args.map)
	sections, files = read_runs(symbols)
	edits = collections.defaultdict(list)  # path -> [(first line, last line, new lines)]
	appends = collections.defaultdict(list)
	counters = collections.Counter()
	total = 0
	for section, runs in sorted(sections.items()):
		char_of = {}
		sizes = {}
		for run in runs:
			for _, ins, size in run.elements:
				if ins not in char_of:
					char_of[ins] = chr(0x100 + len(char_of))
					sizes[char_of[ins]] = size
			run.chars = ''.join(char_of[ins] for _, ins, _ in run.elements)
		source = list(runs)
		before = sum(sizes[c] for run in runs for c in run.chars)
		subs = factor(runs, sizes)
		saved = before - sum(sizes[c] for run in runs for c in run.chars)
		saved -= RET_SIZE * sum(1 for sub in subs if not sub.inplace)
		saved += tail_calls(runs)
		total += saved
		if not subs:
			continue
		print(f'{section}: {len(subs)} subroutines, {saved} bytes')

		def name(scope):
			counters[scope] += 1
			return f'{scope}_Shared{counters[scope]}' if counters[scope] > 1 else f'{scope}_Shared'

		for sub in subs:
			if not sub.inplace:
				sub.label = name(sub.run.scope)
		roots = [(run, run.scope) for run in source]
		roots += [(sub.run, sub.label) for sub in subs if not sub.inplace]
		for root, scope in roots:
			run = root
			while run.tail:
				sub = run.tail
				counters[scope] += 1
				sub.local = f'.shared{counters[scope]}'
				sub.label = scope + sub.local
				run = sub.run

		def instructions(run):
			out = []
			for e in run.elements:
				if isinstance(e, tuple):
					out.append(e[1])
				else:
					out += instructions((e.sub if isinstance(e, Jump) else e).run)
			return out + (instructions(run.tail.run) if run.tail else [])

		def summary(sub):
			"""What a call does, for a comment."""
			ins = instructions(sub.run)
			return ' / '.join(ins[:3]) + (' / ...' if len(ins) > 3 else '')

		def render(run):
			"""Lines of a Sub written out anew, at the end of a file or in place of a call."""
			out = []
			for e in run.elements:
				if isinstance(e, Sub):
					out.append(f'\tcall {e.label} ; {summary(e)}')
				elif isinstance(e, Jump):
					out.append(f'\tjp {e.sub.label} ; {summary(e.sub)}')
				else:
					out.append(files[run.path][e[0]])
			if run.tail:
				out.append(f'{run.tail.local}: ; (tools/outline.py)')
				out += render(run.tail.run)
			return out

		# Runs in the source files change in place: each copy is replaced by a
		# call (or a jump, or the body of the Sub it calls), and a label goes
		# before a copy that the others call
		for run in runs:
			if not run.in_file:
				continue
			for sub, first, last, kind in run.spans:
				if kind == 'jump':
					new = [f'\tjp {sub.label} ; {summary(sub)}']
				elif kind == 'tail':
					new = [f'{sub.local}: ; (tools/outline.py)'] + render(sub.run)
				else:
					new = [f'\tcall {sub.label} ; {summary(sub)}']
				edits[run.path].append((first, last, new))
			for sub, first, last, kind in run.spans:
				end = sub.run
				while end.tail:
					end = end.tail.run
				if kind == 'tail' and end.elements and isinstance(end.elements[-1], Jump) and \
						run.ret_line is not None:
					edits[run.path].append((run.ret_line, run.ret_line, []))
			if hasattr(run, 'first_line'):
				label = [sub for sub in subs if sub.run is run][0]
				edits[run.path].append((run.first_line, run.first_line - 1,
					[f'{label.local}: ; (tools/outline.py)']))
			if isinstance(run.elements[-1] if run.elements else None, Jump) and \
					run.ret_line is not None:
				edits[run.path].append((run.ret_line, run.ret_line, []))
		for sub in subs:
			if not sub.inplace:
				appends[sub.run.path] += ['', f'{sub.label}: ; (tools/outline.py)']
				appends[sub.run.path] += render(sub.run)
				run = sub.run
				while run.tail:
					run = run.tail.run
				if not (run.elements and isinstance(run.elements[-1], Jump)):
					appends[sub.run.path].append('\tret')
	print(f'about {total} bytes')
	if not args.apply:
		return
	old_files = {path: list(lines) for path, lines in files.items()}
	for path in set(edits) | set(appends):
		lines = files[path]
		for first, last, new in sorted(edits[path], key=lambda e: (e[0], e[1]), reverse=True):
			lines[first:last + 1] = new
		while lines and not lines[-1]:
			lines.pop()
		lines += appends[path] + ['']
		open(os.path.join(ROOT, path), 'w', encoding='utf-8').write('\n'.join(lines))
	check(old_files, set(edits) | set(appends))


if __name__ == '__main__':
	main()
