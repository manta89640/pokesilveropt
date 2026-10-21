#!/usr/bin/env python3
"""
Play a scenario on two ROMs and compare the results.

Usage: tools/tests/compare.py original.gbc new.gbc scenario.txt [save.ram] [--out DIR]

Reports which checkpoints differ, and writes DIR/<scenario>_diff.png with the
differing screenshots side by side (original left, new right). Changed code
can shift timing by a frame, so a few differences in partly printed text,
blinking cursors or wandering NPCs are expected; look at the sheet.

A crash can leave the emulator spinning without finishing a frame, so a run
that takes longer than --timeout seconds is stopped and reported.
"""

import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# Log lines from play.py that describe the game state rather than a screenshot
STATE_LINES = ('state ', 'pos ', 'battle=')


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument('original')
	ap.add_argument('new')
	ap.add_argument('scenario')
	ap.add_argument('save', nargs='?')
	ap.add_argument('--out', default='test_output')
	ap.add_argument('--timeout', type=float, default=1800)
	args = ap.parse_args()

	name = os.path.splitext(os.path.basename(args.scenario))[0]
	dirs = [os.path.join(args.out, name, side) for side in ('original', 'new')]
	procs = []
	for rom, d in zip((args.original, args.new), dirs):
		cmd = [sys.executable, os.path.join(HERE, 'play.py'), rom, d, args.scenario]
		if args.save:
			cmd.append(args.save)
		procs.append(subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True))
	logs = []
	for p, rom in zip(procs, (args.original, args.new)):
		try:
			logs.append(p.communicate(timeout=args.timeout)[0].splitlines())
		except subprocess.TimeoutExpired:
			for q in procs:
				q.kill()
			sys.exit(f'{name}: {rom} did not finish in {args.timeout:.0f} seconds (crashed?)')

	differing = []
	state_diffs = []
	for a, b in zip(*logs):
		if a == b:
			continue
		if a.startswith(STATE_LINES):
			state_diffs.append((a, b))
		else:
			differing.append(a.split()[0])
	shots = sum(1 for line in logs[0] if not line.startswith(STATE_LINES))
	print(f'{name}: {len(differing)}/{shots} screenshots and {len(state_diffs)} states differ')
	for a, b in state_diffs[:5]:
		print(f'  original: {a}\n  new:      {b}')

	if differing:
		from PIL import Image
		shown = differing[:30]
		sheet = Image.new('RGB', (340 * 3, 154 * ((len(shown) + 2) // 3)), 'white')
		for i, shot in enumerate(shown):
			for side, d in enumerate(dirs):
				image = Image.open(os.path.join(d, shot + '.png')).convert('RGB')
				sheet.paste(image, ((i % 3) * 340 + side * 165, (i // 3) * 154))
		path = os.path.join(args.out, f'{name}_diff.png')
		sheet.save(path)
		print(f'  differences: {path}')


if __name__ == '__main__':
	main()
