Predef::
; Call predefined function a.
; Preserves bc, de, hl and f.

	ld [wPredefID], a
	ldh a, [hROMBank]
	push af

	ld a, BANK(GetPredefPointer)
	rst Bankswitch
	call GetPredefPointer ; stores hl in wPredefHL

; Switch to the new function's bank
	rst Bankswitch

; Instead of directly calling stuff,
; push it to the stack in reverse.

	ld hl, .Return
	push hl

; Call the Predef function
	ld a, [wPredefAddress]
	ld h, a
	ld a, [wPredefAddress + 1]
	ld l, a
	push hl

; Get hl back
	ld a, [wPredefHL]
	ld h, a
	ld a, [wPredefHL + 1]
	ld l, a
	ret

.Return:
; Clean up after the Predef call

	ld a, h
	ld [wPredefHL], a
	ld a, l
	ld [wPredefHL + 1], a

	pop hl
	ld a, h
	rst Bankswitch

	ld a, [wPredefHL]
	ld h, a
	ld a, [wPredefHL + 1]
	ld l, a
	ret

_PredefIndexed::
; "rst PredefIndexed" followed by a predef id does what predef does: call
; Predef with a = the id, and the caller's flags, bc, de and hl.
	push af
	push hl
	; get the id, and return after it
	ld hl, sp + 4
	push de
	ld e, [hl]
	inc hl
	ld d, [hl]
	ld a, [de]
	inc de
	ld [hl], d
	dec hl
	ld [hl], e
	ld [wPredefID], a
	pop de
	pop hl
	pop af
	ld a, [wPredefID]
	jp Predef
