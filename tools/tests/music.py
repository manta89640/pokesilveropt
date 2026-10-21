#!/usr/bin/env python3
"""
Play every song, sound effect and cry in PyBoy and print a hash of the sound
engine's state.

Usage: tools/tests/music.py rom.gbc save.ram [FRAMES]

Continues from the save, and while the player stands in the overworld, has
the sound engine fade to each song in turn, then hashes the state of the
music channels each time _UpdateSound runs, FRAMES times (default 3600) from
when the song starts. Then it plays each sound effect, and each Pokémon's
cry, by calling PlaySFX or PlayCry from DelayFrame, and hashes the state of
the sound effect channels until they stop. The addresses in the sound data
and the subroutine flag are left out, so the output of two ROMs whose sound
data is laid out differently can be compared. Needs `pip install pyboy`, and
the ROM's .sym file for RAM addresses.
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
NUM_POKEMON = 251
CHANNEL_STRUCT_LENGTH = 0x32
CHANNEL_FLAGS1 = 3
ADDRESSES = range(6, 12)  # CHANNEL_MUSIC_ADDRESS to CHANNEL_LAST_MUSIC_ADDRESS_2
SOUND_CHANNEL_ON = 1 << 0
SOUND_SUBROUTINE = 1 << 1
MAX_SFX_UPDATES = 3600


def count_entries(path):
	return sum(1 for line in open(os.path.join(ROOT, path)) if re.match(r'\s+dba\b', line))


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

	def state(first):
		start = sym['wChannel1'] + first * CHANNEL_STRUCT_LENGTH
		data = bytearray(mem[start:start + CHANNEL_STRUCT_LENGTH * NUM_MUSIC_CHANS])
		for c in range(NUM_MUSIC_CHANS):
			base = c * CHANNEL_STRUCT_LENGTH
			for i in ADDRESSES:
				data[base + i] = 0
			data[base + CHANNEL_FLAGS1] &= ~SOUND_SUBROUTINE
		return data

	def sfx_playing():
		return any(mem[sym['wChannel5Flags1'] + c * CHANNEL_STRUCT_LENGTH] & SOUND_CHANNEL_ON
			for c in range(NUM_MUSIC_CHANS))

	# recording: [hash, updates so far, what starts it, what ends it, first channel, done]
	recording = []

	def update_sound(_):
		# _UpdateSound does nothing while a sound is being set up
		if not recording or recording[5] or not mem[sym['wMusicPlaying']]:
			return
		h, updates, start, stop, first, _ = recording
		if not updates and not start():
			return
		if updates and stop():
			recording[5] = True
			return
		h.update(state(first))
		recording[1] += 1

	pb.hook_register(banks['_UpdateSound'], sym['_UpdateSound'], update_sound, None)

	# Calls PlaySFX or PlayCry with de from DelayFrame, as if DelayFrame called it
	calls = []

	def delay_frame(_):
		if not calls:
			return
		function, de = calls.pop()
		r = pb.register_file
		sp = r.SP - 2
		mem[sp] = r.PC & 0xff
		mem[sp + 1] = r.PC >> 8
		r.SP = sp
		r.D = de >> 8
		r.E = de & 0xff
		r.PC = function

	pb.hook_register(0, sym['DelayFrame'], delay_frame, None)

	for song in range(1, count_entries('audio/music_pointers.asm')):
		mem[sym['wMusicFadeID']] = song
		mem[sym['wMusicFadeID'] + 1] = 0
		mem[sym['wMusicFade']] = 1
		recording[:] = [hashlib.md5(), 0,
			lambda: mem[sym['wMusicID']] == song and not mem[sym['wMusicFade']],
			lambda: recording[1] >= frames, 0, False]
		for _ in range(frames + 600):
			tick()
			if recording[5]:
				break
		else:
			print(f'song {song} did not start')
		print(f'song {song} {recording[0].hexdigest()[:12]}')
		recording.clear()

	sounds = [('sfx', i, 'PlaySFX') for i in range(count_entries('audio/sfx_pointers.asm'))]
	sounds += [('cry', i, 'PlayCry') for i in range(NUM_POKEMON)]
	for kind, i, function in sounds:
		while sfx_playing():
			tick()
		calls.append((sym[function], i))
		recording[:] = [hashlib.md5(), 0, lambda: not calls and sfx_playing(),
			lambda: recording[1] >= MAX_SFX_UPDATES or not sfx_playing(), NUM_MUSIC_CHANS, False]
		for _ in range(MAX_SFX_UPDATES + 600):
			tick()
			if recording[5]:
				break
		print(f'{kind} {i} {recording[0].hexdigest()[:12]} {recording[1]}')
		recording.clear()
	pb.stop(save=False)
	shutil.rmtree(tmp)


if __name__ == '__main__':
	main()
