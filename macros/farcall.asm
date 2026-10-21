; Far calls to another bank

; There is no difference between `farcall` and `callfar`, except the arbitrary
; order in which they set `a` and `hl` before calling `FarCall`.
; We use the more natural name "farcall" for the more common order.

; A function in data/farcall_targets.asm is reached with "rst FarCallIndexed"
; and its index in FarCallTargets instead, which is shorter and does the same.

MACRO farcall ; bank, address
	if DEF(FARCALL_\1)
		rst FarCallIndexed
		db FARCALL_\1
	else
		ld a, BANK(\1)
		ld hl, \1
		rst FarCall
	endc
ENDM

MACRO callfar ; address, bank
	if DEF(FARCALL_\1)
		rst FarCallIndexed
		db FARCALL_\1
	else
		ld hl, \1
		ld a, BANK(\1)
		rst FarCall
	endc
ENDM

MACRO farcall_target
; Indexes of the functions in data/farcall_targets.asm
	DEF FARCALL_\1 EQU NUM_FARCALL_TARGETS
	DEF NUM_FARCALL_TARGETS += 1
ENDM

MACRO homecall
	ldh a, [hROMBank]
	push af
	ld a, BANK(\1)
	rst Bankswitch
	call \1
	pop af
	rst Bankswitch
ENDM
