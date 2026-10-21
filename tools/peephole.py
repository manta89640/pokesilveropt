#!/usr/bin/env python3
"""
Shrink code with safe peephole rewrites of the assembly source.

Usage: tools/peephole.py [--revert file:line ...] files...

Rewrites, each of which only makes code smaller and never slower:
  - "jr/jp cc, Label" where Label is a plain "ret"   ->  "ret cc"
  - "jr/jp Label" where Label is a plain "ret"       ->  "ret"
  - "call Label" followed by an unlabeled "ret"      ->  "jp Label"
  - "jp [cc,] Label" to a label in the same section  ->  "jr [cc,] Label"

A "jr" that turns out to be out of range is reported by rgblink; pass
those locations back with --revert to turn them into "jp" again.
"""

import argparse
import os
import re
import sys

# Functions that read their return address from the stack
STACK_READERS = re.compile(r'AnonJumptable|JumpTable|DummyPredef2F')

LABEL = re.compile(r'^(\.?[A-Za-z_][\w.]*)(:{0,2})(?=\s|;|$)')
CODE = re.compile(r'^\s+(\w+)\b\s*(.*?)\s*$')
COND = r'(?:(nz|z|nc|c)\s*,\s*)?'
JUMP = re.compile(r'^(\s+)(jp|jr)(\s+)' + COND + r'(\.?[A-Za-z_][\w.]*)\s*(;.*)?$')
CALL = re.compile(r'^(\s+)call(\s+)(\.?[A-Za-z_][\w.]*)\s*(;.*)?$')
RET = re.compile(r'^\s+ret\s*(;.*)?$')


def split_comment(line):
	in_str = False
	for i, c in enumerate(line):
		if c == '"':
			in_str = not in_str
		elif c == ';' and not in_str:
			return line[:i], line[i:]
	return line, ''


class Source:
	def __init__(self, path):
		self.path = path
		self.lines = open(path, encoding='utf-8').read().split('\n')
		self.analyze()

	def analyze(self):
		"""Find labels, their sections, and which lines are inside macros."""
		self.labels = {}       # full label name -> line index
		self.line_label = {}   # line index -> list of labels on that line
		self.section_of = []   # line index -> section number
		self.scope_of = []     # line index -> current global label
		self.in_macro = []
		section = 0
		scope = None
		macro = False
		for i, line in enumerate(self.lines):
			code, _ = split_comment(line)
			low = code.strip().lower()
			if low.startswith('section'):
				section += 1
			if re.match(r'^macro\b', low):
				macro = True
			m = LABEL.match(code)
			if m and m.group(1) and not code[:1].isspace() and not low.startswith(('section', 'macro', 'endm', 'if', 'else', 'endc', 'include', 'incbin', 'def ', 'charmap', 'rept', 'endr')):
				name = m.group(1)
				if name.startswith('.'):
					name = f'{scope}{name}' if scope else name
				else:
					scope = name.split('.')[0]
				self.labels[name] = i
				self.line_label.setdefault(i, []).append(name)
			self.section_of.append(section)
			self.scope_of.append(scope)
			self.in_macro.append(macro)
			if re.match(r'^endm\b', low):
				macro = False

	def resolve(self, name, i):
		if name.startswith('.'):
			return f'{self.scope_of[i]}{name}'
		return name

	def first_instruction(self, i):
		"""Index of the first instruction at or after line i (skipping labels/comments)."""
		while i < len(self.lines):
			code, _ = split_comment(self.lines[i])
			m = LABEL.match(code)
			if m and m.group(1) and not code[:1].isspace():
				code = code[m.end():]
				if not code.strip():
					i += 1
					continue
			if code.strip():
				return i, code.strip()
			i += 1
		return None, None

	def labeled(self, i):
		return i in self.line_label

	def write(self):
		open(self.path, 'w', encoding='utf-8').write('\n'.join(self.lines))


def is_plain_ret(src, target_line):
	j, code = src.first_instruction(target_line)
	return j is not None and src.section_of[j] == src.section_of[target_line] \
		and re.fullmatch(r'ret', code) is not None


def optimize(src, stats):
	lines = src.lines
	for i, line in enumerate(lines):
		if src.in_macro[i]:
			continue
		m = JUMP.match(line)
		if m:
			indent, op, sp, cond, target, comment = m.groups()
			full = src.resolve(target, i)
			t = src.labels.get(full)
			if t is not None and src.section_of[t] == src.section_of[i] and is_plain_ret(src, t):
				lines[i] = f'{indent}ret{" " + cond if cond else ""}{" " + comment if comment else ""}'
				stats['ret'] += 1
				continue
		m = CALL.match(line)
		if m and not STACK_READERS.search(m.group(3)):
			j = i + 1
			while j < len(lines) and (not lines[j].strip() or lines[j].lstrip().startswith(';')):
				j += 1
			if j < len(lines) and RET.match(lines[j]) and not src.labeled(j) and not src.in_macro[j]:
				indent, sp, target, comment = m.groups()
				lines[i] = f'{indent}jp{sp}{target}{" " + comment if comment else ""}'
				del lines[j]
				stats['tail'] += 1
				src.analyze()
				return True
	return False


def jp_to_jr(src, stats):
	lines = src.lines
	for i, line in enumerate(lines):
		if src.in_macro[i]:
			continue
		m = JUMP.match(line)
		if not m or m.group(2) != 'jp':
			continue
		indent, op, sp, cond, target, comment = m.groups()
		full = src.resolve(target, i)
		t = src.labels.get(full)
		if t is None or src.section_of[t] != src.section_of[i]:
			continue
		# Leave tables of jumps alone, since their entries must stay 3 bytes
		if not cond:
			prev = next((lines[k] for k in range(i - 1, -1, -1) if split_comment(lines[k])[0].strip()), '')
			nxt = next((lines[k] for k in range(i + 1, len(lines)) if split_comment(lines[k])[0].strip()), '')
			if re.match(r'^\s+jp\s+[^,]+$', split_comment(prev)[0]) or re.match(r'^\s+jp\s+[^,]+$', split_comment(nxt)[0]):
				continue
		lines[i] = line.replace('jp', 'jr', 1)
		stats['jr'] += 1


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('--revert', action='append', default=[], help='file:line of a jr to turn back into jp')
	ap.add_argument('--no-jr', action='store_true')
	ap.add_argument('files', nargs='*')
	args = ap.parse_args()

	if args.revert:
		by_file = {}
		for loc in args.revert:
			path, line = loc.rsplit(':', 1)
			by_file.setdefault(path, []).append(int(line) - 1)
		for path, idxs in by_file.items():
			lines = open(path, encoding='utf-8').read().split('\n')
			for i in idxs:
				lines[i] = re.sub(r'^(\s+)jr\b', r'\1jp', lines[i])
			open(path, 'w', encoding='utf-8').write('\n'.join(lines))
		return

	stats = {'ret': 0, 'tail': 0, 'jr': 0}
	for path in args.files:
		src = Source(path)
		while optimize(src, stats):
			pass
		if not args.no_jr:
			jp_to_jr(src, stats)
		src.write()
	print(stats, file=sys.stderr)


if __name__ == '__main__':
	main()
