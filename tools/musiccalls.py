#!/usr/bin/env python3
"""
Move repeated phrases of music into subroutines.

Usage: tools/musiccalls.py [--apply]

Within each song section of audio.asm, this looks for runs of notes and
commands that appear more than once, and replaces them with a sound_call to
one copy of the run, which it adds at the end of a song file with a
sound_ret. It picks the run that saves the most bytes, and repeats until no
run saves any. A run doesn't include labels or sound_call, sound_ret,
sound_loop or sound_jump. The sound engine can call a subroutine from a
subroutine but no deeper, so it follows each channel to find where its data
is played, and doesn't add calls where they would be too deep. Without
--apply, only reports how much it would save.

tools/tests/verify_music.py checks the result against the original ROMs.
"""

import argparse
import collections
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_DEPTH = 2  # how deep a channel can be in subroutines
MAX_RUN = 100  # longest run to look for, in commands
CALL_SIZE = 3
RET_SIZE = 1

SIZES = {'note': 1, 'rest': 1, 'drum_note': 1, 'octave': 1, 'transpose': 2, 'tempo': 3,
	'duty_cycle': 2, 'volume_envelope': 2, 'pitch_sweep': 2, 'duty_cycle_pattern': 2,
	'toggle_sfx': 1, 'pitch_slide': 3, 'vibrato': 3, 'force_stereo_panning': 2, 'volume': 2,
	'pitch_offset': 3, 'tempo_relative': 2, 'sfx_priority_on': 1, 'sfx_priority_off': 1,
	'stereo_panning': 2, 'set_condition': 2, 'sound_jump_if': 4, 'sound_jump': 3,
	'sound_loop': 4, 'sound_call': 3, 'sound_ret': 1}
FLOW = ('sound_jump_if', 'sound_jump', 'sound_loop', 'sound_call', 'sound_ret')


def command_size(op, args):
	if op in ('note_type', 'drum_speed'):
		return 2 if len(args) == 1 else 3
	if op == 'toggle_noise':
		return 2 if args else 1
	return SIZES[op]


def song_sections():
	"""Returns {section: [song files]}."""
	sections = {}
	section = None
	for line in open(os.path.join(ROOT, 'audio.asm')):
		m = re.match(r'SECTION "(.*)"', line)
		if m:
			section = m.group(1)
		m = re.match(r'INCLUDE "(audio/music/.*)"', line)
		if m:
			sections.setdefault(section, []).append(m.group(1))
	return sections


class Item:
	def __init__(self, path, line, kind, name=None, op=None, args=(), code=None):
		self.path, self.line, self.kind = path, line, kind
		self.name, self.op, self.args, self.code = name, op, args, code
		self.size = command_size(op, args) if kind == 'command' else 0


def parse(path):
	items = []
	scope = None
	for i, raw in enumerate(open(os.path.join(ROOT, path)).read().split('\n')):
		code = raw.split(';')[0].rstrip()
		if not code.strip():
			continue
		if not code[0].isspace():
			name = code.strip().rstrip(':')
			if name.startswith('.'):
				name = scope + name
			else:
				scope = name
			items.append(Item(path, i, 'label', name=name))
			continue
		op, _, rest = code.strip().partition(' ')
		args = [a.strip() for a in rest.split(',')] if rest.strip() else []
		if op in ('channel_count', 'channel', 'db'):
			items.append(Item(path, i, 'header', op=op, args=args))
			continue
		args = [scope + a if a.startswith('.') else a for a in args]
		items.append(Item(path, i, 'command', op=op, args=args, code=code.strip()))
	return items


def depths(items):
	"""Returns {item index: set of subroutine depths it is played at}."""
	labels = {item.name: i for i, item in enumerate(items) if item.kind == 'label'}
	played = collections.defaultdict(set)
	todo = [(labels[item.args[1]], 0) for item in items if item.op == 'channel']
	seen = set()
	while todo:
		i, depth = todo.pop()
		while i < len(items) and (i, depth) not in seen:
			seen.add((i, depth))
			item = items[i]
			i += 1
			if item.kind != 'command':
				continue
			played[i - 1].add(depth)
			if item.op == 'sound_ret':
				break
			if item.op == 'sound_call':
				todo.append((labels[item.args[0]], depth + 1))
			elif item.op == 'sound_jump':
				i = labels[item.args[0]]
			elif item.op in ('sound_loop', 'sound_jump_if'):
				todo.append((labels[item.args[1]], depth))
				if item.op == 'sound_loop' and item.args[0] == '0':
					break
	return played


class Run:
	"""A run of commands that can hold calls: a list of elements, which are item
	indices or Sub objects (calls), with a string of one character each to
	search."""
	def __init__(self, elements, chars, depth, path):
		self.elements, self.chars, self.depth, self.path = elements, chars, depth, path


class Sub:
	def __init__(self, run, char):
		self.run, self.char = run, char
		self.label = None


def factor(items, runs, char_of, sizes):
	"""Greedily moves repeated phrases of the runs into new Subs."""
	subs = []
	next_char = 0xf0000
	while True:
		counts = collections.Counter()
		for run in runs:
			if run.depth >= MAX_DEPTH:
				continue
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
			if (count - 1) * size - CALL_SIZE * count - RET_SIZE <= (best[0] if best else 0):
				continue
			hosts = [run for run in runs if run.depth < MAX_DEPTH and phrase in run.chars]
			n = sum(run.chars.count(phrase) for run in hosts)
			saved = (n - 1) * size - CALL_SIZE * n - RET_SIZE
			if saved > (best[0] if best else 0):
				best = (saved, phrase, hosts)
		if not best:
			return subs
		saved, phrase, hosts = best
		sub_char = chr(next_char)
		next_char += 1
		first = hosts[0]
		start = first.chars.index(phrase)
		body = Run(first.elements[start:start + len(phrase)], phrase,
			max(run.depth for run in hosts) + 1, first.path)
		sub = Sub(body, sub_char)
		sizes[sub_char] = CALL_SIZE
		for run in hosts:
			elements = []
			i = 0
			while True:
				j = run.chars.find(phrase, i)
				if j < 0:
					break
				elements += run.elements[i:j] + [sub]
				i = j + len(phrase)
			run.elements = elements + run.elements[i:]
			run.chars = run.chars.replace(phrase, sub_char)
		runs.append(body)
		subs.append(sub)


def plan_section(files):
	items = [item for path in files for item in parse(path)]
	played = depths(items)
	runs = []
	current = None
	char_of = {}
	sizes = {}
	for i, item in enumerate(items):
		depth = max(played[i]) if i in played else None
		if item.kind != 'command' or item.op in FLOW or depth is None or depth >= MAX_DEPTH:
			current = None
			continue
		if not current or current.depth != depth:
			current = Run([], '', depth, item.path)
			runs.append(current)
		if item.code not in char_of:
			char_of[item.code] = chr(0x100 + len(char_of))
			sizes[char_of[item.code]] = item.size
		current.elements.append(i)
		current.chars += char_of[item.code]
	original = [list(run.elements) for run in runs]
	subs = factor(items, runs, char_of, sizes)
	saved = sum(sizes[c] for run in original for i in run for c in [char_of[items[i].code]])
	saved -= sum(sizes[c] for run in runs for c in run.chars)
	saved -= RET_SIZE * len(subs)
	return items, runs[:len(original)], original, subs, saved


def apply(items, runs, original, subs):
	files = collections.defaultdict(list)
	for item in items:
		if item.kind == 'label' and '.' not in item.name:
			files[item.path].append(item.name)
	counters = collections.Counter()
	for sub in subs:
		song = files[sub.run.path][0]
		existing = ' '.join(files[sub.run.path])
		while True:
			counters[song] += 1
			label = f'{song}_Shared{counters[song]}'
			if label not in existing:
				break
		sub.label = label

	def lines_of(elements):
		return [f'\tsound_call {e.label}' if isinstance(e, Sub) else f'\t{items[e].code}'
			for e in elements]

	edits = collections.defaultdict(list)  # path -> [(first line, last line, new lines)]
	for before, run in zip(original, runs):
		if [e for e in run.elements if not isinstance(e, Sub)] == before and \
				len(run.elements) == len(before):
			continue
		path = items[before[0]].path
		edits[path].append((items[before[0]].line, items[before[-1]].line,
			lines_of(run.elements)))
	appends = collections.defaultdict(list)
	for sub in subs:
		appends[sub.run.path] += ['', f'{sub.label}: ; (tools/musiccalls.py)']
		appends[sub.run.path] += lines_of(sub.run.elements) + ['\tsound_ret']
	for path in set(edits) | set(appends):
		full = os.path.join(ROOT, path)
		lines = open(full).read().split('\n')
		for first, last, new in sorted(edits[path], reverse=True):
			lines[first:last + 1] = new
		while lines and not lines[-1]:
			lines.pop()
		lines += appends[path] + ['']
		open(full, 'w').write('\n'.join(lines))


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('--apply', action='store_true')
	args = ap.parse_args()
	total = 0
	for section, files in song_sections().items():
		items, runs, original, subs, saved = plan_section(files)
		print(f'{section}: {len(subs)} subroutines, {saved} bytes')
		total += saved
		if args.apply:
			apply(items, runs, original, subs)
	print(f'{total} bytes')


if __name__ == '__main__':
	main()
