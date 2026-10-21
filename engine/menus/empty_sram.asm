EmptyAllSRAMBanks:
	ld a, 0
	call .EmptyBank
	ld a, 1
	call .EmptyBank
	ld a, 2
	call .EmptyBank
	ld a, 3
	jr .EmptyBank

.EmptyBank:
	call OpenSRAM
	ld hl, STARTOF(SRAM)
	ld bc, SIZEOF(SRAM)
	xor a
	call ByteFill
	jp CloseSRAM
