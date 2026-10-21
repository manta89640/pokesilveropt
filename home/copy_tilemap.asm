LoadTilemapToTempTilemap::
; Load wTilemap into wTempTilemap
	hlcoord 0, 0
	decoord 0, 0, wTempTilemap
.tailmerge_5: ; (tools/tailmerge.py)
	ld bc, wTilemapEnd - wTilemap
	jp CopyBytes

SafeLoadTempTilemapToTilemap::
	xor a
	ldh [hBGMapMode], a
	call LoadTempTilemapToTilemap
	ld a, 1
	ldh [hBGMapMode], a
	ret

LoadTempTilemapToTilemap::
; Load wTempTilemap into wTilemap
	hlcoord 0, 0, wTempTilemap
	decoord 0, 0
	jr LoadTilemapToTempTilemap.tailmerge_5 ; same as there (tools/tailmerge.py)
