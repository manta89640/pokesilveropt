# Pokémon Gold and Silver, size-optimized

This is a fork of [pret/pokegold](https://github.com/pret/pokegold), the disassembly of Pokémon Gold and Pokémon Silver. It builds the same games in a **1 MB ROM** instead of the original 2 MB, without removing any features.

| | Original | This fork |
|-|-|-|
| ROM file | 2,097,152 bytes (128 banks) | **1,048,576 bytes (64 banks)** |
| Content | 1,154,855 bytes | 943,900 bytes |
| Free space | 942,297 bytes | 104,676 bytes |

The figures are for Silver, from the summary in rgblink's map file; Gold is within a few hundred bytes. The debug ROMs, which add the debug room, are 1 MB too.

To set up the repository, see [INSTALL.md](INSTALL.md). `make` builds `pokegold.gbc`, `pokesilver.gbc` and the debug ROMs, and fails if one does not fit in 1 MB. `make compare` checks that the build reproduces the ROMs listed in `roms.sha1`, which are this fork's, not the originals.


## What changed

**Text compression** (`tools/textdict.py`, `home/text.asm`). Text is encoded with a dictionary of about 2,900 frequent substrings, from two-letter pairs like `"e "` up to whole phrases like `"#MON CENTER"`. The `text`, `line`, `para`, `cont`, `next` and `page` macros, Pokédex entries, move and item descriptions, the item, move and trainer class names, trainer names, landmark names and the credits use a `dict` charmap, so rgbasm picks dictionary entries itself and the source text stays readable. rgbasm picks the longest entry at each point, which is not always best, so where another choice of entries is shorter the charmap maps the whole run of text to it. One-byte codes reuse character values below `$60` that English text never prints (Japanese kana with dakuten, and the control characters of Japanese text, which `PlaceString` no longer handles). Codes 1–18 are prefixes for two-byte codes whose second byte is `$60`–`$fe`, so no byte of a code looks like a control character to code that scans text for `"@"` or `"<NEXT>"`, or like the `$ff` that ends a trainer's party. `PlaceString` prints an entry by switching to the dictionary bank and printing it recursively. Pokémon names stay plain, since they are copied into nicknames. This shrinks the text from 253 KB to 134 KB, dictionary included.

**1 MB layout** (`layout.link`). Sections that lived in banks `$40`–`$7f` now float, and rgblink packs them into free space in banks `$01`–`$3f`. Each map's scripts are their own section so they can fill small gaps. `tools/section_xref.py` reads the object files and reports code that uses another section's addresses without asking for its bank. It found which sections must share a bank: three pairs of maps, glued with `SECTION FRAGMENT`. The Pokédex entries stay in four consecutive banks because their bank is computed from the species. The Stadium 2 checksums move to the end of the 1 MB ROM, and `tools/stadium` handles any ROM size.

**Optimal LZ compression.** Graphics are compressed with `tools/lzcompress`'s optimal mode instead of byte-for-byte matching settings. The Pack's and the trainer card's graphics, which were stored uncompressed, are compressed too.

**Compressed map blocks** (`home/map.asm`). Map block data is LZ-compressed like graphics. When a map loads, its blocks and those of each connected map are decompressed in turn to the SRAM scratch buffer, and copied from there.

**Compressed overworld sprites** (`engine/overworld/overworld.asm`). Overworld sprite tiles are LZ-compressed, except the player, rival, Mom, Poké Ball and monster, whose tiles other code loads directly (the monster is Substitute's doll). `GetSprite` decompresses them to a 384-byte SRAM buffer placed in space the save layout leaves free. Nine standing sprites have fewer tiles than `GetSprite` loads, so the original games load the start of the next sprites after them; their compressed graphics include those tiles.

**Unused tileset blocks** (`tools/trim_metatiles.py`). Indoor tilesets had blocks that no map can show: not in any map's blocks or border, nor placed by a script, Cut, Whirlpool or a decoration in the player's room. Their metatiles and collision are removed, blocks that look and behave the same as an earlier one are merged into it, and the other blocks are renumbered in the maps' blocks and everything else that refers to them. (Outdoor tilesets keep their numbering, since the edges of connected maps are drawn with the current map's tileset.) Then the tiles of the tilesets' graphics that no metatile shows (nor the Magnet Train, which draws with the station's tiles) are blanked, which compresses better (`tools/blank_unused_tiles.py`).

**Compact map events** (`macros/scripts/maps.asm`, `home/map.asm`). Each map object's `object_event` leaves out the fields that have their usual value (no movement radius, no hour limits, the sprite's own palette, a plain script, no sight range, no event flag), and starts with a byte that says which are there; 1,343 objects take 13 bytes each in the original. `CopyMapObjectEvents` fills in the rest, so the map objects in RAM are the same as before. Coordinate events leave out their three filler bytes.

**Base data** (`home/pokemon.asm`). Each species' base data leaves out the 7 bytes that are the same for every species (the dex number, two unknown values and the unused beta pic pointers); `GetBaseData` fills them in, so `wCurBaseData` is the same as before.

**Script subroutines** (`tools/scriptcalls.py`, `audio/engine.asm`). Runs of commands that a section of songs, sound effects or cries repeats, or that the battle animations repeat, are moved into subroutines that the scripts call (`sound_call`, `anim_call`), or, where one copy already ends a subroutine, the others call into it. The sound engine can now call a subroutine from a subroutine, keeping the second return address in two bytes of each channel's state that were unused. Unreachable sound data and unused header bytes are removed.

**Duplicate graphics** (`gfx/footprints.asm`, `engine/menus/trainer_card.asm`). Each distinct Pokédex footprint is stored once, with a table mapping species to footprints; 61 of 251 were duplicates. The trainer card's Gym Leader faces and badges were stored twice; they are now stored once.

**Dead code and data** (`tools/find_dead_code.py`). Code and data that nothing can reach are removed: beta map blocks, unused graphics and text, the debug color picker, Safari Zone leftovers, and so on. The tool follows references and fallthrough from code and scripts.

**Peephole optimizations** (`tools/peephole.py`). Tail calls become jumps, jumps to `ret` become `ret cc`, near `jp`s become `jr`, and pairs of constant loads become `lb`. Every rewrite is smaller and no slower; serial, link, printer and infrared code is left alone. Scripts that only open a text box, show one text and close it use `jumptext` or `jumptextfaceplayer`, which do the same. `tools/tailmerge.py` replaces each code block that is identical to an earlier one in the same section with a jump to it, and a block that ends with the same instructions as an earlier one with a jump into those instructions. `tools/outline.py` moves runs of at least 5 bytes of straight-line instructions (no jumps, calls, returns or stack operations) that a section repeats into subroutines that the copies call, with a comment at each call saying what it does; it leaves alone home code, code that runs every frame for each object or sprite, and functions whose timing or stack matters, and checks that each file it changes runs the same instructions once the calls are expanded.

**Indexed far calls** (`tools/farcall_targets.py`, `home/farcall.asm`, `home/predef.asm`). A `farcall` or `callfar` is 6 bytes. To one of the 146 functions that are far-called more than once, it is now `rst FarCallIndexed` and an index into a table in ROM0, 2 bytes, which calls the function with the same registers and flags. Likewise `predef` is `rst PredefIndexed` and the predef's id, 2 bytes instead of 5. These used the two `rst` vectors that were free.

Savings by step (Silver, bytes): text dictionary 121,811; dead code 18,254; LZ 13,867; overworld sprites 10,708; map blocks 10,684; duplicate graphics 3,944; peephole 1,899; duplicate code 3,245; `jumptext` 1,357; base data 1,728; music and sound effects 3,231; battle animations 925; indexed far calls 2,207; outlined code 1,595; tileset blocks 7,911.


## What is unchanged

- RAM, SRAM and link data layouts, so trades and battles with the original games still work, and their saves load in this fork. (The sprite buffer uses SRAM that the save layout leaves free.) A save holds the script addresses of the people and items on the current map, and those moved, so Continue reloads them from the map. The original games don't, so moving a save the other way is not safe.
- All text, as printed on screen. `tools/verify_text.py` decodes every text in a build and compares it with the original ROM.
- Gameplay timing. Text prints at the same speed; some code runs slightly faster, far calls and outlined code run slightly slower, and loading compressed graphics can take a frame longer. (The games' random numbers mix in the CPU's cycle counter, so code that runs at a different speed draws different random numbers, as in any changed ROM.)


## Verification

- `tools/verify_text.py original.gbc pokesilver.gbc` checks every compressed string, 5,276 in all: texts, Pokédex entries, move and item descriptions, item, move and trainer class names, trainer names and parties, landmark names, and the credits.
- `tools/tests/verify_music.py` follows every channel of every song, sound effect and cry in a build and in the original ROM, through calls, loops and jumps, and checks that they play the same notes and commands. `tools/tests/verify_anims.py` does the same for every battle animation, with every value of its parameter. `tools/tests/music.py` plays them all in an emulator and hashes the sound engine's channel state at each update, to compare with the original ROM.
- `tools/tests/maps.py` loads all 368 maps and checks that the screen, the graphics of its tiles and the sprite tiles match the original ROM, and outdoor maps' blocks, with the strips of connected maps. (Indoor tilesets' blocks are renumbered.) `tools/tests/verify_sprites.py` checks the tiles of every overworld sprite.
- The changes were also played in an emulator (PyBoy) next to the original ROMs with the scenarios in `tools/tests`: the intro and new game, Elm's lab, menus, every Pokédex entry, the Pack, the Pokégear phone and radio, a Pokémon Center, a Mart, wild and trainer battles, Substitute, the Hall of Fame and credits, and the debug room. Apart from timing, the screens match. See [tools/tests/README.md](tools/tests/README.md).


## See also

- [**pret/pokegold**](https://github.com/pret/pokegold), the original disassembly
- [**Symbols**][symbols]
- [**Tools**][tools]

[symbols]: https://github.com/pret/pokegold/tree/symbols
[tools]: https://github.com/pret/gb-asm-tools
