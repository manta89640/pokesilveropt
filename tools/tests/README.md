# Emulator tests

These scripts play scenarios in [PyBoy](https://github.com/Baekalfen/PyBoy) on the original ROM and on this fork's ROM, and compare the screens and game state. Install PyBoy with `pip install pyboy`.

Build the original ROMs from [pret/pokegold](https://github.com/pret/pokegold) to compare against; each ROM needs its `.sym` file next to it.

```sh
# Scenarios that start a new game
tools/tests/compare.py original/pokesilver.gbc pokesilver.gbc tools/tests/scenarios/intro.txt
tools/tests/compare.py original/pokesilver.gbc pokesilver.gbc tools/tests/scenarios/new_game.txt

# Make a save with a full Pokédex, items and a party (on the original ROM,
# so loading it also checks that the original games' saves work),
# then run the scenarios that start from it
tools/tests/play.py original/pokesilver.gbc test_output/save tools/tests/scenarios/make_save.txt
for s in continue connections pokedex pack pokegear phone radio trainer_card battle trainer substitute services npc_text hall_of_fame; do
	tools/tests/compare.py original/pokesilver.gbc pokesilver.gbc tools/tests/scenarios/$s.txt test_output/save/save.ram
done
```

`debug_room.txt` is for the debug ROMs (`original/pokesilver_debug.gbc` and `pokesilver_debug.gbc`), from the same save.

`maps.py` enters every map from the save and prints a hash of its blocks (with the strips of connected maps), of the screen's tilemap, of the sprite tiles and of the graphics of the tiles on the screen, so two ROMs can be compared map by map. `tools/trim_metatiles.py` renumbers the blocks of indoor tilesets, so compare the other columns:

```sh
tools/tests/maps.py original/pokesilver.gbc test_output/save/save.ram | cut -d' ' -f1,2,4- > original.txt
tools/tests/maps.py pokesilver.gbc test_output/save/save.ram | cut -d' ' -f1,2,4- > new.txt
diff original.txt new.txt
```

`pics.py` loads every picture from the save with the game's own routines and prints a hash of each; the output should match the original ROM's exactly (set `PIC_TIMING=1` to also print how many frames each took):

```sh
tools/tests/pics.py original/pokesilver.gbc test_output/save/save.ram > original.txt
tools/tests/pics.py pokesilver.gbc test_output/save/save.ram > new.txt
diff original.txt new.txt
```

`compare.py` writes the differing screenshots side by side to `test_output/<scenario>_diff.png`, and reports a run that does not finish within `--timeout` seconds, which is how a crash usually shows up. Changed code can shift timing by a frame, so expect some differences in partly printed text, blinking cursors, wandering NPCs and random battles; look at the sheet. `intro.txt` matches exactly.

Separately, `tools/verify_text.py original.gbc new.gbc` checks every text in the ROM without an emulator, `tools/tests/verify_sprites.py original.gbc new.gbc` checks the tiles every overworld sprite loads, `tools/tests/verify_music.py original.gbc new.gbc` checks the notes and commands every song, sound effect and cry plays, and `tools/tests/verify_anims.py original.gbc new.gbc` the commands every battle animation runs.
