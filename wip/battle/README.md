# Unfinished battle rewrites

These patches, made with `git format-patch`, implement part of the battle-code audit. They are **untested and not merged**: each folder is a series of commits on top of cdafa7ff, one series per area (battle animations, effect commands, battle core, AI and trainer data). The series were written in parallel and may conflict with each other.

To use one: `git checkout -b battle-core cdafa7ff && git am wip/battle/core/*.patch`. Before merging, run `tools/tests/battles.py` on the old and new ROMs and diff the logs, and run the offline checkers that the patches add.
