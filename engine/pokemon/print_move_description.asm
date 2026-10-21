PrintMoveDescription:
	push hl
	ld hl, MoveDescriptions
	call PrintItemDescription_Shared ; ld a, [wCurSpecies] / dec a / ld c, a / ...
	ld a, BANK(MoveDescriptions)
	call GetFarWord
	ld d, h
	ld e, l
	pop hl
	ld a, BANK(MoveDescriptions)
	jp PlaceFarString
