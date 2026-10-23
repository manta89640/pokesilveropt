StubbedGetFrontpic::
	ret

LoadSGBPokedexGFX:
	ld hl, SGBPokedexGFX_LZ
	ld de, vTiles2 tile $31
	jp Decompress

LoadSGBPokedexGFX2:
	ld hl, SGBPokedexGFX_LZ
	ld de, vTiles2 tile $31
	lb bc, BANK(SGBPokedexGFX_LZ), 58
	jp DecompressRequest2bpp

SGBPokedexGFX_LZ:
INCBIN "gfx/pokedex/pokedex_sgb.2bpp.lz"

LoadQuestionMarkPic:
	ld hl, .QuestionMarkLZ
	ld de, sScratch
	jp Decompress

.QuestionMarkLZ:
INCBIN "gfx/pokedex/question_mark.2bpp.lz"

DrawPokedexListWindow:
	ld hl, .Draw
	call Pokedex_Draw
	ld hl, .ScrollBar
	ld a, [wCurDexMode]
	cp DEXMODE_OLD
	jr nz, .draw
	ld hl, .NoScrollBar
.draw
	jp Pokedex_Draw

.Draw:
	dexdraw ROW, 0, 17
	db $32, 12
	dexdraw CLEAR, 0, 1
	db 15, 11
	dexdraw ROW, 0, 0
	db $34, 11
	dexdraw ROW, 0, 16
	db $39, 11
	dexdraw TILE, 5, 0
	db $3f
	dexdraw TILE, 5, 16
	db $40
	db 0

.ScrollBar:
	dexdraw TILE, 11, 0
	db $50
	dexdraw COLUMN, 11, 1
	db $51, SCREEN_HEIGHT - 3
	dexdraw TILE, 11, 16
	db $52
	db 0

.NoScrollBar:
	dexdraw TILE, 11, 0
	db $66
	dexdraw COLUMN, 11, 1
	db $67, SCREEN_HEIGHT - 3
	dexdraw TILE, 11, 16
	db $68
	db 0

DrawPokedexSearchResultsWindow:
	ld hl, .Draw
	jp Pokedex_Draw

.Draw:
	dexdraw ROW, 0, 0
	db $34, 11
	dexdraw ROW, 0, 10
	db $39, 11
	dexdraw TILE, 5, 0
	db $3f
	dexdraw TILE, 5, 10
	db $40
	dexdraw TILE, 11, 0
	db $66
	dexdraw COLUMN, 11, 1
	db $67, SCREEN_HEIGHT / 2
	dexdraw TILE, 11, 10
	db $68
	dexdraw ROW, 0, 11
	db $34, 11
	dexdraw ROW, 0, 17
	db $39, 11
	dexdraw TILE, 11, 11
	db $66
	dexdraw COLUMN, 11, 12
	db $67, 5
	dexdraw TILE, 11, 17
	db $68
	dexdraw CLEAR, 0, 12
	db 5, 11
	dexdraw TEXT, 0, 12
; (SEARCH R)
	db   "ESULTS"
	next ""
; (### FOUN)
	next "D!@"
	db 0

DrawDexEntryScreenRightEdge:
	ldh a, [hBGMapAddress]
	ld l, a
	ldh a, [hBGMapAddress + 1]
	ld h, a
	push hl
	inc hl
	call DrawDexEntryScreenRightEdge.shared1 ; ld a, l / ldh [hBGMapAddress], a / ld a, h / ...
	ld hl, .Draw
	call Pokedex_Draw
	xor a
	ld b, SCREEN_HEIGHT
	hlcoord 19, 0, wAttrmap
	call Pokedex_FillColumn
	call WaitBGMap2
	pop hl
.shared1: ; (tools/outline.py)
	ld a, l
	ldh [hBGMapAddress], a
	ld a, h
	ldh [hBGMapAddress + 1], a
	ret

.Draw:
	dexdraw TILE, 19, 0
	db $66
	dexdraw COLUMN, 19, 1
	db $67, 15
	dexdraw TILE, 19, 16
	db $68
	dexdraw TILE, 19, 17
	db $3c
	db 0
