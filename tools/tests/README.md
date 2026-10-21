# Emulator tests

These scripts play scenarios in [PyBoy](https://github.com/Baekalfen/PyBoy) on the original ROM and on this fork's ROM, and compare the screens and game state. Install PyBoy with `pip install pyboy`.

Build the original ROMs from [pret/pokegold](https://github.com/pret/pokegold) to compare against; each ROM needs its `.sym` file next to it.

```sh
# Scenarios that start a new game
tools/tests/compare.py original/pokesilver.gbc pokesilver.gbc tools/tests/scenarios/intro.txt
tools/tests/compare.py original/pokesilver.gbc pokesilver.gbc tools/tests/scenarios/new_game.txt

# Make a save with a full Pokédex, items and a party (on the original ROM),
# then run the scenarios that start from it
tools/tests/play.py original/pokesilver.gbc test_output/save tools/tests/scenarios/make_save.txt
for s in continue pokedex pack pokegear phone radio trainer_card battle services npc_text; do
	tools/tests/compare.py original/pokesilver.gbc pokesilver.gbc tools/tests/scenarios/$s.txt test_output/save/save.ram
done
```

`maps.py` enters every map from the save and prints a hash of its blocks (with the strips of connected maps), so two ROMs can be compared map by map:

```sh
tools/tests/maps.py original/pokesilver.gbc test_output/save/save.ram > original.txt
tools/tests/maps.py pokesilver.gbc test_output/save/save.ram > new.txt
diff original.txt new.txt
```

`compare.py` writes the differing screenshots side by side to `test_output/<scenario>_diff.png`. Changed code can shift timing by a frame, so expect some differences in partly printed text, blinking cursors, wandering NPCs and random battles; look at the sheet. `intro.txt` matches exactly.

Separately, `tools/verify_text.py original.gbc new.gbc` checks every text in the ROM without an emulator.
