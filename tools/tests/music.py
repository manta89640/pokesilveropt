#!/usr/bin/env python3
"""
Play every song in PyBoy and print a hash of the sound engine's state.

Usage: tools/tests/music.py rom.gbc save.ram [FRAMES]

Continues from the save, and while the player stands in the overworld, has
the sound engine fade to each song in turn, then hashes the state of the
music channels each time _UpdateSound runs, FRAMES times (default 3600) from
when the song starts.
The addresses in the music data and the subroutine flag are left out, so the
output of two ROMs whose music data is laid out differently can be compared.
Needs `pip install pyboy`, and the ROM's .sym file for RAM addresses.
"""

import hashlib
import os
import re
import shutil
import sys
import tempfile
import time

# Drive the cartridge clock from emulated time, so runs are repeatable
FRAMES = [0]
time.time = lambda: 1700000000.0 + FRAMES[0] / 59.7275

from pyboy import PyBoy  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NUM_MUSIC_CHANS = 4
CHANNEL_STRUCT_LENGTH = 0x32
CHANNEL_FLAGS1 = 3
ADDRESSES = range(6, 12)  # CHANNEL_MUSIC_ADDRESS to CHANNEL_LAST_MUSIC_ADDRESS_2
SOUND_SUBROUTINE = 1 << 1


def main():
	rom, save = sys.argv[1:3]
	frames = int(sys.argv[3]) if len(sys.argv) > 3 else 3600
	sym = {}
	banks = {}
	for line in open(os.path.splitext(rom)[0] + '.sym'):
		m = re.match(r'([0-9a-f]+):([0-9a-f]+) (\S+)', line)
		if m:
			sym[m.group(3)] = int(m.group(2), 16)
			banks[m.group(3)] = int(m.group(1), 16)
	songs = sum(1 for line in open(os.path.join(ROOT, 'audio/music_pointers.asm'))
		if re.match(r'\s+dba\b', line))

	tmp = tempfile.mkdtemp()
	copy = os.path.join(tmp, 'rom.gbc')
	shutil.copy(rom, copy)
	shutil.copy(save, copy + '.ram')
	rtc = os.path.splitext(save)[0] + '.rtc'
	if os.path.exists(rtc):
		shutil.copy(rtc, copy + '.rtc')
	pb = PyBoy(copy, window='null', sound_emulated=False)
	pb.set_emulation_speed(0)
	mem = pb.memory

	def tick(n=1):
		for _ in range(n):
			pb.tick(1, False)
			FRAMES[0] += 1

	def press(button, wait):
		pb.button_press(button)
		tick(4)
		pb.button_release(button)
		tick(wait)

	# Continue from the save
	tick(400)
	press('start', 60)
	press('a', 120)
	press('a', 200)
	press('a', 300)

	channels = sym['wChannel1']
	recording = []

	def update_sound(_):
		# Start with the first update after the song starts
		if not recording or (not recording[1] and
				(mem[sym['wMusicID']] != recording[2] or mem[sym['wMusicFade']])):
			return
		state = bytearray(mem[channels:channels + CHANNEL_STRUCT_LENGTH * NUM_MUSIC_CHANS])
		for c in range(NUM_MUSIC_CHANS):
			base = c * CHANNEL_STRUCT_LENGTH
			for i in ADDRESSES:
				state[base + i] = 0
			state[base + CHANNEL_FLAGS1] &= ~SOUND_SUBROUTINE
		recording[0].update(state)
		recording[1] += 1

	pb.hook_register(banks['_UpdateSound'], sym['_UpdateSound'], update_sound, None)
	for song in range(1, songs):
		mem[sym['wMusicFadeID']] = song
		mem[sym['wMusicFadeID'] + 1] = 0
		mem[sym['wMusicFade']] = 1
		recording[:] = [hashlib.md5(), 0, song]
		for _ in range(frames + 600):
			tick()
			if recording[1] >= frames:
				break
		else:
			print(f'song {song} did not start')
			continue
		print(f'song {song} {recording[0].hexdigest()[:12]}')
		recording.clear()
	pb.stop(save=False)
	shutil.rmtree(tmp)


if __name__ == '__main__':
	main()
