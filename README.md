# Pokémon Gold and Silver, size-optimized

This is a fork of [pret/pokegold](https://github.com/pret/pokegold), the disassembly of Pokémon Gold and Pokémon Silver. It builds the same games in a **1 MB ROM** instead of the original 2 MB, without removing any features.

| | Original | This fork |
|-|-|-|
| ROM file | 2,097,152 bytes (128 banks) | **1,048,576 bytes (64 banks)** |
| Content | 1,155,066 bytes | 981,391 bytes |
| Free space | 942,086 bytes | 67,185 bytes |

The figures are for Silver; Gold is within a few hundred bytes. The debug ROMs keep uncompressed text (their menus are in Japanese) and still build at 2 MB.

To set up the repository, see [INSTALL.md](INSTALL.md). `make` builds `pokegold.gbc` and `pokesilver.gbc`, and fails if either does not fit in 1 MB. `make compare` checks that the build reproduces the ROMs listed in `roms.sha1`, which are this fork's, not the originals.


## What changed

**Text compression** (`tools/textdict.py`, `home/text.asm`). Text is encoded with a dictionary of about 2,500 frequent substrings, from two-letter pairs like `"e "` up to whole phrases like `"#MON CENTER"`. The `text`, `line`, `para`, `cont`, `next` and `page` macros, Pokédex entries, and move and item descriptions use a `dict` charmap, so rgbasm picks dictionary entries itself and the source text stays readable. One-byte codes reuse character values below `$60` that English text never prints (Japanese kana with dakuten). Codes 1–16 are prefixes for two-byte codes whose second byte is `$60`–`$ff`, so no byte of a code looks like a control character to code that scans text for `"@"` or `"<NEXT>"`. `PlaceString` prints an entry by switching to the dictionary bank and printing it recursively. This shrinks the text from 243 KB to 127 KB, dictionary included.

**1 MB layout** (`layout.link`). Sections that lived in banks `$40`–`$7f` now float, and rgblink packs them into free space in banks `$01`–`$3f`. Each map's scripts are their own section so they can fill small gaps. `tools/section_xref.py` reads the object files and reports code that uses another section's addresses without asking for its bank. It found which sections must share a bank: three pairs of maps, glued with `SECTION FRAGMENT`. The Pokédex entries stay in four consecutive banks because their bank is computed from the species. The Stadium 2 checksums move to the end of the 1 MB ROM, and `tools/stadium` handles any ROM size.

**Optimal LZ compression.** Graphics are compressed with `tools/lzcompress`'s optimal mode instead of byte-for-byte matching settings.

**Compressed map blocks** (`home/map.asm`). Map block data is LZ-compressed like graphics. When a map loads, its blocks and those of each connected map are decompressed in turn to the SRAM scratch buffer, and copied from there.

**Compressed overworld sprites** (`engine/overworld/overworld.asm`). Overworld sprite tiles are LZ-compressed, except the player, rival, Mom and Poké Ball, whose tiles other code loads directly. `GetSprite` decompresses them to a 384-byte SRAM buffer placed in space the save layout leaves free.

**Pokédex footprints** (`gfx/footprints.asm`). Each distinct footprint is stored once, with a table mapping species to footprints; 61 of 251 were duplicates.

**Dead code and data** (`tools/find_dead_code.py`). Code and data that nothing can reach are removed: beta map blocks, unused graphics and text, the debug color picker, Safari Zone leftovers, and so on. The tool follows references and fallthrough from code and scripts.

**Peephole optimizations** (`tools/peephole.py`). Tail calls become jumps, jumps to `ret` become `ret cc`, near `jp`s become `jr`, and pairs of constant loads become `lb`. Every rewrite is smaller and no slower; serial, link, printer and infrared code is left alone.

Savings by step (Silver, bytes): text dictionary 117,494; dead code 17,742; overworld sprites 12,311; LZ 11,456; map blocks 10,684; footprints 1,864; peephole 1,854.


## What is unchanged

- RAM, SRAM and link data layouts, so saves are compatible with the original games, and trades and battles with them still work. (The sprite buffer uses SRAM that the save layout leaves free.)
- All text, as printed on screen. `tools/verify_text.py` decodes every text in a build and compares it with the original ROM.
- Gameplay timing. Text prints at the same speed; some code runs slightly faster.


## Verification

- `tools/verify_text.py original.gbc pokesilver.gbc` checks all 5,000+ texts, Pokédex entries, and move and item descriptions.
- `tools/tests/maps.py` loads all 368 maps and checks that their blocks, with the strips of connected maps, match the original ROM.
- The changes were also played in an emulator (PyBoy) next to the original ROMs with the scenarios in `tools/tests`: the intro and new game, Elm's lab, menus, every Pokédex entry, the Pack, the Pokégear phone and radio, a Pokémon Center, a Mart, and wild battles. Apart from timing, the screens match. See [tools/tests/README.md](tools/tests/README.md).


## See also

- [**pret/pokegold**](https://github.com/pret/pokegold), the original disassembly
- [**Symbols**][symbols]
- [**Tools**][tools]

[symbols]: https://github.com/pret/pokegold/tree/symbols
[tools]: https://github.com/pret/gb-asm-tools
