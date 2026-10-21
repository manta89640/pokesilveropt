; Predef function calls

MACRO? lda_predef
; Some functions load the predef id
; without immediately calling Predef.
	ld a, (\1Predef - PredefPointers) / 3
ENDM

MACRO? predef
; "lda_predef \1" and "call Predef", in two bytes
	rst PredefIndexed
	db (\1Predef - PredefPointers) / 3
ENDM

MACRO? predef_jump
	lda_predef \1
	jp Predef
ENDM
