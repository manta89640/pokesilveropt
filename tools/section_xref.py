#!/usr/bin/env python3
"""
Find ROMX sections that must share a bank.

Usage: tools/section_xref.py file.o...

Reads rgbasm object files and reports every patch in one ROMX section that
uses the address of a symbol in another ROMX section, when the first section
never asks for the bank of that symbol (or its section). Such references only
work if both sections end up in the same bank.
"""

import collections
import struct
import sys

SECT_TYPES = ['WRAM0', 'VRAM', 'ROMX', 'ROM0', 'HRAM', 'WRAMX', 'SRAM', 'OAM']


class Reader:
	def __init__(self, data):
		self.data = data
		self.pos = 0

	def long(self):
		v = struct.unpack_from('<i', self.data, self.pos)[0]
		self.pos += 4
		return v

	def byte(self):
		v = self.data[self.pos]
		self.pos += 1
		return v

	def string(self):
		end = self.data.index(0, self.pos)
		s = self.data[self.pos:end].decode('utf-8')
		self.pos = end + 1
		return s

	def bytes(self, n):
		v = self.data[self.pos:self.pos + n]
		self.pos += n
		return v


def parse_rpn(rpn):
	"""Yields (kind, value) for symbol/section references in an RPN expression."""
	r = Reader(rpn)
	while r.pos < len(rpn):
		op = r.byte()
		if op == 0x80:
			r.long()
		elif op == 0x81:
			yield 'sym', r.long()
		elif op == 0x50:
			yield 'banksym', r.long()
		elif op in (0x51, 0x53, 0x54):
			yield ('banksect' if op == 0x51 else 'sectref'), r.string()
		elif op in (0x55, 0x56):
			r.byte()
		elif op == 0x62:
			r.byte()


def parse_object(path):
	r = Reader(open(path, 'rb').read())
	assert r.bytes(4) == b'RGB9'
	r.long()
	nsyms = r.long()
	nsects = r.long()
	nnodes = r.long()
	for _ in range(nnodes):
		r.long()
		r.long()
		t = r.byte() & 0x7f
		if t != 0:
			r.string()
		else:
			depth = r.long()
			for _ in range(depth):
				r.long()
	syms = []
	for _ in range(nsyms):
		name = r.string()
		t = r.byte()
		if t != 1:
			r.long()
			r.long()
			sect = r.long()
			value = r.long()
			syms.append((name, t, sect, value))
		else:
			syms.append((name, t, None, None))
	sects = []
	for _ in range(nsects):
		name = r.string()
		r.long()
		r.long()
		size = r.long()
		stype = r.byte()
		r.long()  # address
		r.long()  # bank
		r.byte()  # alignment
		r.long()  # align offset
		patches = []
		if stype & 7 in (2, 3):
			r.bytes(size)
			npatches = r.long()
			for _ in range(npatches):
				r.long()
				line = r.long()
				offset = r.long()
				r.long()
				r.long()
				ptype = r.byte()
				rpn = r.bytes(r.long())
				patches.append((offset, ptype, rpn, line))
		sects.append((name, SECT_TYPES[stype & 7], size, patches))
	return syms, sects


def main():
	objects = [parse_object(p) for p in sys.argv[1:]]
	# Map every defined symbol to its section name
	sym_section = {}
	section_type = {}
	for syms, sects in objects:
		for name, stype, size, _ in sects:
			section_type[name] = stype
		for name, t, sect, value in syms:
			if t != 1 and sect is not None and sect >= 0:
				sym_section.setdefault(name, sects[sect][0])

	near = collections.defaultdict(lambda: collections.defaultdict(int))
	banked = collections.defaultdict(set)
	for syms, sects in objects:
		for sname, stype, size, patches in sects:
			if stype != 'ROMX':
				continue
			for offset, ptype, rpn, line in patches:
				refs = list(parse_rpn(rpn))
				# The difference of two symbols in one section doesn't depend on its bank
				sym_targets = [sym_section.get(syms[v][0]) for kind, v in refs if kind == 'sym']
				if len(sym_targets) >= 2 and len(set(sym_targets)) == 1:
					continue
				for kind, v in refs:
					if kind == 'sym':
						target = sym_section.get(syms[v][0])
						if target and target != sname and section_type.get(target) == 'ROMX':
							near[sname][(target, syms[v][0])] += 1
					elif kind == 'banksym':
						target = sym_section.get(syms[v][0])
						if target:
							banked[sname].add(target)
					elif kind == 'banksect':
						banked[sname].add(v)

	pairs = collections.defaultdict(set)
	for sname, refs in near.items():
		for (target, symbol), count in refs.items():
			if target not in banked[sname]:
				pairs[(sname, target)].add(symbol)
	for (a, b), symbols in sorted(pairs.items()):
		print(f'{a!r} -> {b!r}: {", ".join(sorted(symbols)[:6])}{" ..." if len(symbols) > 6 else ""}')


if __name__ == '__main__':
	main()
