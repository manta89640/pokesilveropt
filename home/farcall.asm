FarCall_hl::
; Call a:hl.
; Preserves other registers.
	ld [wTempBank], a
	ldh a, [hROMBank]
	push af
	ld a, [wTempBank]
	rst Bankswitch
	call FarCall_JumpToHL

; We want to retain the contents of f.
; To do this, we can pop to bc instead of af.
	ld a, b
	ld [wFarCallBC], a
	ld a, c
	ld [wFarCallBC + 1], a

; Restore the working bank.
	pop bc
	ld a, b
	rst Bankswitch

; Restore the contents of bc.
	ld a, [wFarCallBC]
	ld b, a
	ld a, [wFarCallBC + 1]
	ld c, a
	ret

FarCall_JumpToHL::
	jp hl

_FarCallIndexed::
; "rst FarCallIndexed" followed by an index in FarCallTargets does what
; farcall does for that function: call it with a = its bank, hl = its address
; and the caller's flags, bc and de.
	push af
	push de
	; get the index, and return after it
	ld hl, sp + 4
	ld e, [hl]
	inc hl
	ld d, [hl]
	ld a, [de]
	inc de
	ld [hl], d
	dec hl
	ld [hl], e
	; FarCallTargets + index * 3
	ld e, a
	ld d, 0
	ld hl, FarCallTargets
	add hl, de
	add hl, de
	add hl, de
	ld a, [hli]
	ld [wTempBank], a
	ld a, [hli]
	ld h, [hl]
	ld l, a
	pop de
	pop af
	ld a, [wTempBank]
	jp FarCall_hl
