#!/usr/bin/env python3
"""
Move repeated runs of music and battle animation scripts into subroutines.

Usage: tools/scriptcalls.py [--apply]

Within each section of songs, sound effects or cries in audio.asm, and in
the battle animations, this looks for runs of commands that appear more than
once, and replaces them with a call (sound_call or anim_call) to one copy of
the run, which it adds at the end of a file with a return. If a copy is
followed by a return already, it stays where it is instead, with a label for
the others to call. It picks the run that saves the most bytes, and repeats
until no run saves any. A run doesn't include labels, or commands that jump,
loop, call or return. Then a call followed by a return becomes a jump, or
the subroutine moves to right after it. The sound engine can call a
subroutine from a subroutine but no deeper, and the battle animation engine
can't at all, so it follows each script from its entry points to find how
deep its commands run, and doesn't add calls where they would be too deep.
Without --apply, only reports how much it would save.

tools/tests/verify_music.py and tools/tests/verify_anims.py check the result
against the original ROMs.
"""

import argparse
import collections
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_RUN = 100  # longest run to look for, in commands
CALL_SIZE = 3
RET_SIZE = 1


class Music:
	call, ret, jump = 'sound_call', 'sound_ret', 'sound_jump'
	# command: index of the argument it can jump to
	branches = {'sound_loop': 1, 'sound_jump_if': 1}
	loop = 'sound_loop'
	headers = ('channel_count', 'channel', 'db', 'assert')
	max_depth = 2  # how deep a channel can be in subroutines
	sizes = {'note': 1, 'rest': 1, 'drum_note': 1, 'octave': 1, 'transpose': 2, 'tempo': 3,
		'duty_cycle': 2, 'volume_envelope': 2, 'pitch_sweep': 2, 'duty_cycle_pattern': 2,
		'toggle_sfx': 1, 'pitch_slide': 3, 'vibrato': 3, 'force_stereo_panning': 2, 'volume': 2,
		'pitch_offset': 3, 'tempo_relative': 2, 'sfx_priority_on': 1, 'sfx_priority_off': 1,
		'stereo_panning': 2, 'set_condition': 2, 'sound_jump_if': 4, 'sound_jump': 3,
		'sound_loop': 4, 'sound_call': 3, 'sound_ret': 1, 'square_note': 4, 'noise_note': 3}

	@classmethod
	def size(cls, op, args):
		if op in ('note_type', 'drum_speed'):
			return 2 if len(args) == 1 else 3
		if op in ('toggle_noise', 'sfx_toggle_noise'):
			return 2 if args else 1
		return cls.sizes[op]

	@staticmethod
	def entry(op, args):
		return args[1] if op == 'channel' else None

	@staticmethod
	def sections():
		"""Returns {section: [files of songs, sound effects or cries]}."""
		sections = {}
		section = None
		for line in open(os.path.join(ROOT, 'audio.asm')):
			m = re.match(r'SECTION "(.*)"', line)
			if m:
				section = m.group(1)
			m = re.match(r'INCLUDE "(audio/(music/.*|sfx.asm|cries.asm))"', line)
			if m:
				sections.setdefault(section, []).append(m.group(1))
		return sections

	@staticmethod
	def prefix(path, label):
		# Name new labels after the song, or Sfx_ or Cry_ for the sound effects
		# and cries, which are all in one file
		return label if '/music/' in path else label.split('_')[0]


class BattleAnims:
	call, ret, jump = 'anim_call', 'anim_ret', 'anim_jump'
	branches = {'anim_loop': 1, 'anim_if_param_equal': 1, 'anim_if_var_equal': 1,
		'anim_if_param_and': 1, 'anim_jumpuntil': 0}
	loop = 'anim_loop'
	headers = ('table_width', 'dw', 'assert_table_length')
	max_depth = 1
	sizes = {'anim_obj': 5, 'anim_1gfx': 2, 'anim_2gfx': 3, 'anim_3gfx': 4, 'anim_4gfx': 5,
		'anim_5gfx': 6, 'anim_incobj': 2, 'anim_setobj': 3, 'anim_incbgeffect': 2, 'anim_sound': 3,
		'anim_cry': 2, 'anim_if_param_and': 4, 'anim_jumpuntil': 3, 'anim_bgeffect': 5,
		'anim_bgp': 2, 'anim_obp0': 2, 'anim_obp1': 2, 'anim_if_param_equal': 4, 'anim_setvar': 2,
		'anim_if_var_equal': 4, 'anim_jump': 3, 'anim_loop': 4, 'anim_call': 3}

	@classmethod
	def size(cls, op, args):
		# anim_wait and the commands without parameters are one byte
		return cls.sizes.get(op, 1)

	@staticmethod
	def entry(op, args):
		return args[0] if op == 'dw' else None

	@staticmethod
	def sections():
		return {'Battle animations': ['data/moves/animations.asm']}

	@staticmethod
	def prefix(path, label):
		return 'BattleAnim'


class Item:
	def __init__(self, path, line, kind, name=None, op=None, args=(), code=None, size=0):
		self.path, self.line, self.kind = path, line, kind
		self.name, self.op, self.args, self.code, self.size = name, op, args, code, size


def parse(lang, path):
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
		if op in lang.headers:
			items.append(Item(path, i, 'header', op=op, args=args))
			continue
		args = [scope + a if a.startswith('.') else a for a in args]
		items.append(Item(path, i, 'command', op=op, args=args, code=code.strip(),
			size=lang.size(op, args)))
	return items


def depths(lang, items):
	"""Returns {item index: set of subroutine depths it runs at}."""
	labels = {item.name: i for i, item in enumerate(items) if item.kind == 'label'}
	played = collections.defaultdict(set)
	todo = [(labels[lang.entry(item.op, item.args)], 0) for item in items
		if item.kind == 'header' and lang.entry(item.op, item.args)]
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
			if item.op == lang.ret:
				break
			if item.op == lang.call:
				todo.append((labels[item.args[0]], depth + 1))
			elif item.op == lang.jump:
				i = labels[item.args[0]]
			elif item.op in lang.branches:
				todo.append((labels[item.args[lang.branches[item.op]]], depth))
				if item.op == lang.loop and item.args[0] == '0':
					break
	return played


class Run:
	"""Commands that can hold calls: a list of elements, which are item indices,
	Subs (calls) or Jumps, with a string of one character each to search. A run
	may be followed by a return (ret_after), or by the body of a Sub (tail)."""
	def __init__(self, elements, chars, depth, path, scope, ret_after):
		self.elements, self.chars, self.depth = elements, chars, depth
		self.path, self.scope, self.ret_after = path, scope, ret_after
		self.tail = None
		self.lines = None  # (first line, last line, return line) for runs of the source


class Sub:
	"""A subroutine: a run, and whether it is placed after another run instead of
	at the end of a file."""
	def __init__(self, run, char):
		self.run, self.char = run, char
		self.inplace = False
		self.label = None


class Jump:
	def __init__(self, sub):
		self.sub = sub


def factor(runs, sizes, max_depth):
	"""Greedily moves repeated phrases of the runs into new Subs. A phrase at the
	end of a run that returns can stay there, with a label for the other copies
	to call."""
	subs = []
	next_char = 0xf0000
	while True:
		counts = collections.Counter()
		for run in runs:
			if run.depth >= max_depth:
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
			if (count - 1) * (size - CALL_SIZE) <= (best[0] if best else 0):
				continue
			hosts = [run for run in runs if run.depth < max_depth and phrase in run.chars]
			n = sum(run.chars.count(phrase) for run in hosts)
			saved = (n - 1) * size - CALL_SIZE * n - RET_SIZE
			if saved > (best[0] if best else 0):
				best = (saved, phrase, hosts, None)
			for run in runs:
				if run.ret_after and run.chars.endswith(phrase):
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
			body = Run(place.elements[k:], phrase, place.depth, place.path, place.scope, True)
			place.elements, place.chars = place.elements[:k], place.chars[:k]
			place.ret_after = False
			place.tail = sub = Sub(body, sub_char)
			sub.inplace = True
		else:
			first = hosts[0]
			start = first.chars.index(phrase)
			body = Run(first.elements[start:start + len(phrase)], phrase, 0, first.path, None,
				True)
			sub = Sub(body, sub_char)
		callers = [run for run in hosts if phrase in run.chars]
		if callers:
			body.depth = max([body.depth] + [run.depth + 1 for run in callers])
		for run in callers:
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


def tail_calls(runs):
	"""A run that ends with a call and returns jumps instead, or goes on into the
	Sub's body if that can be placed after it."""
	saved = 0
	for run in runs:
		if not run.ret_after or not run.elements or not isinstance(run.elements[-1], Sub):
			continue
		sub = run.elements[-1]
		if not sub.inplace:
			sub.inplace = True
			run.elements = run.elements[:-1]
			run.chars = run.chars[:-1]
			run.ret_after = False
			run.tail = sub
			saved += CALL_SIZE + RET_SIZE
		else:
			run.elements[-1] = Jump(sub)
			run.ret_after = False
			saved += RET_SIZE
	return saved


def plan_section(lang, files):
	items = [item for path in files for item in parse(lang, path)]
	played = depths(lang, items)
	runs = []
	current = None
	char_of = {}
	sizes = {}
	scope = None
	for i, item in enumerate(items):
		if item.kind == 'label' and '.' not in item.name:
			scope = item.name
		depth = max(played[i]) if i in played else None
		flow = item.op in (lang.call, lang.ret, lang.jump) or item.op in lang.branches
		if item.kind != 'command' or flow or depth is None or depth >= lang.max_depth:
			if current and item.op == lang.ret:
				current.ret_after = True
				current.lines = current.lines[:2] + (item.line,)
			current = None
			continue
		if not current or current.depth != depth:
			current = Run([], '', depth, item.path, scope, False)
			current.lines = (item.line, item.line, None)
			runs.append(current)
		if item.code not in char_of:
			char_of[item.code] = chr(0x100 + len(char_of))
			sizes[char_of[item.code]] = item.size
		current.elements.append(i)
		current.chars += char_of[item.code]
		current.lines = (current.lines[0], item.line, None)
	before = sum(sizes[c] for run in runs for c in run.chars)
	source = list(runs)
	for run in source:
		run.original = (list(run.elements), run.ret_after)
	subs = factor(runs, sizes, lang.max_depth)
	saved = before - sum(sizes[c] for run in runs for c in run.chars)
	saved -= RET_SIZE * sum(1 for sub in subs if not sub.inplace)
	saved += tail_calls(runs)
	return items, source, subs, saved


def apply(lang, items, source, subs):
	songs = {}
	for item in items:
		if item.kind == 'label':
			songs.setdefault(item.path, lang.prefix(item.path, item.name))
	counters = collections.Counter()

	def name(sub, path):
		counters[path] += 1
		return f'Shared{counters[path]}'

	# Subs at the end of a file get global labels. Subs placed after another
	# run get local ones, so they don't change the scope of the local labels
	# that follow.
	roots = [(run, run.scope, run.path) for run in source]
	for sub in subs:
		if not sub.inplace:
			sub.label = f'{songs[sub.run.path]}_{name(sub, sub.run.path)}'
			roots.append((sub.run, sub.label, sub.run.path))
	for run, scope, path in roots:
		while run.tail:
			sub = run.tail
			sub.local = '.' + name(sub, path).lower()
			sub.label = scope + sub.local
			run = sub.run

	def render(run):
		lines = []
		for e in run.elements:
			if isinstance(e, Sub):
				lines.append(f'\t{lang.call} {e.label}')
			elif isinstance(e, Jump):
				lines.append(f'\t{lang.jump} {e.sub.label}')
			else:
				lines.append(f'\t{items[e].code}')
		if run.tail:
			lines.append(f'{run.tail.local}: ; (tools/scriptcalls.py)')
			lines += render(run.tail.run)
		return lines

	def returns(run):
		while run.tail:
			run = run.tail.run
		return run.ret_after

	edits = collections.defaultdict(list)  # path -> [(first line, last line, ret line, new lines)]
	for run in source:
		if run.original == (run.elements, run.ret_after) and not run.tail:
			continue
		first, last, ret = run.lines
		edits[run.path].append((first, last, None if returns(run) else ret, render(run)))
	appends = collections.defaultdict(list)
	for sub in subs:
		if not sub.inplace:
			appends[sub.run.path] += ['', f'{sub.label}: ; (tools/scriptcalls.py)']
			appends[sub.run.path] += render(sub.run)
			if returns(sub.run):
				appends[sub.run.path].append(f'\t{lang.ret}')
	for path in set(edits) | set(appends):
		full = os.path.join(ROOT, path)
		lines = open(full).read().split('\n')
		for first, last, ret, new in sorted(edits[path], reverse=True):
			if ret is not None:
				del lines[ret]
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
	for lang in (Music, BattleAnims):
		for section, files in lang.sections().items():
			items, source, subs, saved = plan_section(lang, files)
			print(f'{section}: {len(subs)} subroutines, {saved} bytes')
			total += saved
			if args.apply:
				apply(lang, items, source, subs)
	print(f'{total} bytes')


if __name__ == '__main__':
	main()
