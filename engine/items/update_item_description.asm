UpdateItemDescription:
	ld a, [wMenuSelection]
	ld [wCurSpecies], a
	hlcoord 0, 12
	lb bc, 4, SCREEN_WIDTH - 2
	call Textbox
	call UpdateItemDescription_Shared ; ld a, [wMenuSelection] / cp -1
	ret z
	decoord 1, 14
	farcall PrintItemDescription
	ret

UpdateItemDescription_Shared: ; (tools/outline.py)
	ld a, [wMenuSelection]
	cp -1
	ret
