DoItemEffect::
	farcall _DoItemEffect
	ret

CheckTossableItem::
	push hl
	push de
	push bc
	farcall _CheckTossableItem
	pop bc
	pop de
	pop hl
	ret

TossItem::
	push hl
	push de
	push bc
	ldh a, [hROMBank]
	push af
	ld a, BANK(_TossItem)
	rst Bankswitch

	call _TossItem

.tailmerge_26: ; (tools/tailmerge.py)
	pop bc
	ld a, b
	rst Bankswitch
	pop bc
	pop de
	pop hl
	ret

ReceiveItem::
	push bc
	ldh a, [hROMBank]
	push af
	ld a, BANK(_ReceiveItem)
	rst Bankswitch
	push hl
	push de

	call _ReceiveItem

	pop de
	jp GetMapSceneID.done ; same as there (tools/tailmerge.py)

CheckItem::
	push hl
	push de
	push bc
	ldh a, [hROMBank]
	push af
	ld a, BANK(_CheckItem)
	rst Bankswitch

	call _CheckItem

	jr TossItem.tailmerge_26 ; same as there (tools/tailmerge.py)
