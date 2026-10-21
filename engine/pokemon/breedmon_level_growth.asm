GetBreedMon1LevelGrowth:
	ld hl, wBreedMon1
	ld de, wTempMon
	ld bc, BOXMON_STRUCT_LENGTH
	call CopyBytes
	callfar CalcLevel
	ld a, [wBreedMon1Level]
.tailmerge_8: ; (tools/tailmerge.py)
	ld b, a
	ld a, d
	ld e, a
	sub b
	ld d, a
	ret

GetBreedMon2LevelGrowth:
	ld hl, wBreedMon2
	ld de, wTempMon
	ld bc, BOXMON_STRUCT_LENGTH
	call CopyBytes
	callfar CalcLevel
	ld a, [wBreedMon2Level]
	jr GetBreedMon1LevelGrowth.tailmerge_8 ; same as there (tools/tailmerge.py)
