; Each connection in data/maps/attributes.asm is the connected map and its
; offset. When a map loads, _GetMapConnections works out the rest of each
; connection's struct the way the connection macro used to, from the two maps'
; sizes: where the strip of the connected map's blocks next to this map starts
; in its blocks and goes in wOverworldMapBlocks, how long it is, where the
; player stands and what the screen shows after crossing.

; Values for the connection being worked out, in otherwise unused HRAM
DEF hConnectionDirection   EQUS "hPrintNumBuffer + 0" ; 0 north, 1 south, 2 west, 3 east
DEF hConnectionOffset      EQUS "hPrintNumBuffer + 1"
DEF hConnectionSource      EQUS "hPrintNumBuffer + 2" ; where the strip starts in the connected map
DEF hConnectionTarget      EQUS "hPrintNumBuffer + 3" ; ...and in this map, along the edge
DEF hConnectionWidth       EQUS "hPrintNumBuffer + 4" ; the connected map's width
DEF hConnectionAcross      EQUS "hPrintNumBuffer + 5" ; its size across the edge
DEF hConnectionAlong       EQUS "hPrintNumBuffer + 6" ; ...and along it
DEF hConnectionThisAcross  EQUS "hPrintNumBuffer + 7" ; this map's size across the edge
DEF hConnectionThisAlong   EQUS "hPrintNumBuffer + 8" ; ...and along it
DEF hConnectionBank        EQUS "hPrintNumBuffer + 9"

	assert HIGH(wNorthMapConnection) == HIGH(wEastMapConnection + MAP_CONNECTION_LENGTH - 1)

_GetMapConnections::
; Fill the connection structs from the map's connections at b:de.
	ld a, b
	ldh [hConnectionBank], a
	ld a, $ff
	ld [wNorthConnectedMapGroup], a
	ld [wSouthConnectedMapGroup], a
	ld [wWestConnectedMapGroup], a
	ld [wEastConnectedMapGroup], a
	ld h, d
	ld l, e
	ld de, wNorthMapConnection
	ld a, [wMapConnections]
	swap a ; NORTH, SOUTH, WEST, EAST from bit 7 down
	ld c, 0
.loop
	add a
	push af
	push bc
	push de
	call c, .GetConnection
	pop de
	pop bc
	pop af
	ld b, a
	ld a, e
	add MAP_CONNECTION_LENGTH
	ld e, a
	inc c
	ld a, b
	and a
	jr nz, .loop
	ret

.GetConnection:
; Fill the struct at de for direction c from the connection at hl.
	ld a, c
	ldh [hConnectionDirection], a
	call .GetByte
	ld [de], a ; group
	inc de
	ld b, a
	call .GetByte
	ld [de], a ; number
	inc de
	ld c, a
	call .GetByte
	ldh [hConnectionOffset], a
	push hl
	push de

	; the connected map's height and width
	push bc
	ld de, MAP_MAPATTRIBUTES
	call GetAnyMapField
	ld h, b
	ld l, c
	pop bc
	call GetAnyMapAttributesBank
	ld b, a
	inc hl
	call GetFarByte
	ld c, a ; height
	inc hl
	ld a, b
	call GetFarByte
	ldh [hConnectionWidth], a
	ld b, a ; width
	; for north and south, the edge runs along the width
	ldh a, [hConnectionDirection]
	cp 2 ; west
	jr c, .got_target_size
	ld a, b
	ld b, c
	ld c, a
.got_target_size
	ld a, b
	ldh [hConnectionAlong], a
	ld a, c
	ldh [hConnectionAcross], a
	ld a, [wMapWidth]
	ld b, a
	ld a, [wMapHeight]
	ld c, a
	ldh a, [hConnectionDirection]
	cp 2 ; west
	jr c, .got_size
	ld a, b
	ld b, c
	ld c, a
.got_size
	ld a, b
	ldh [hConnectionThisAlong], a
	ld a, c
	ldh [hConnectionThisAcross], a

	; the strip starts 3 blocks before the offset, in the padding around this map
	ld b, 0
	ldh a, [hConnectionOffset]
	add MAP_CONNECTION_PADDING_WIDTH
	bit 7, a
	jr z, .got_target
	; ...or as far into the connected map, if that is before this map's padding
	cpl
	inc a
	ld b, a
	xor a
.got_target
	ldh [hConnectionTarget], a
	ld a, b
	ldh [hConnectionSource], a
	pop de

	; strip pointer: in the connected map's blocks (decompressed to sScratch),
	; the 3 rows or columns at its far edge, or at its near edge for south and
	; east, from the strip's start
	ldh a, [hConnectionSource]
	ld b, a
	ldh a, [hConnectionWidth]
	ld c, a
	ldh a, [hConnectionAcross]
	sub MAP_CONNECTION_PADDING_WIDTH
	call .NearZero
	ld hl, sScratch
	call .BlockAddress
	call .PutHL

	; strip location: the padding at this map's edge
	ldh a, [hConnectionTarget]
	ld b, a
	ld a, [wMapWidth]
	add MAP_CONNECTION_PADDING_WIDTH * 2
	ld c, a
	ldh a, [hConnectionThisAcross]
	add MAP_CONNECTION_PADDING_WIDTH
	call .FarZero
	ld hl, wOverworldMapBlocks
	call .BlockAddress
	call .PutHL

	; strip length: the rest of the connected map, or up to the end of this
	; map's padding
	ldh a, [hConnectionOffset]
	ld b, a
	ldh a, [hConnectionThisAlong]
	add MAP_CONNECTION_PADDING_WIDTH
	sub b
	ld b, a
	ldh a, [hConnectionAlong]
	cp b
	jr c, .got_length
	ld a, b
.got_length
	ld hl, hConnectionSource
	sub [hl]
	ld [de], a
	inc de

	; connected map's width
	ldh a, [hConnectionWidth]
	ld [de], a
	inc de

	; y and x after crossing: at the far edge of the connected map (its near
	; edge for south and east), and moved by the offset along it
	ldh a, [hConnectionOffset]
	add a
	cpl
	inc a
	ld b, a
	ldh a, [hConnectionAcross]
	add a
	dec a
	call .NearZero
	push de
	ld d, a
	ld e, b
	call .Order
	ld a, d
	ld b, e
	pop de
	ld [de], a ; y
	inc de
	ld a, b
	ld [de], a ; x
	inc de

	; window: where the screen's top left block is, before adding the
	; position along the edge
	ld b, 1
	ldh a, [hConnectionWidth]
	add MAP_CONNECTION_PADDING_WIDTH * 2
	ld c, a
	ldh a, [hConnectionAcross]
	call .NearZero
	and a
	jr nz, .got_window_row
	inc a
.got_window_row
	ld hl, wOverworldMapBlocks
	call .BlockAddress
	call .PutHL

	pop hl
	ret

.GetByte:
	ldh a, [hConnectionBank]
	call GetFarByte
	inc hl
	ret

.PutHL:
	ld a, l
	ld [de], a
	inc de
	ld a, h
	ld [de], a
	inc de
	ret

.BlockAddress:
; hl += a block's offset in rows of c blocks: a blocks across the edge,
; b blocks along it.
	push de
	ld d, a
	ld e, b
	call .Order
	ld a, d
	ld b, 0
	call AddNTimes
	ld d, 0
	add hl, de
	pop de
	ret

.Order:
; d and e are across and along the edge; make them the row and the column.
	ldh a, [hConnectionDirection]
	cp 2 ; west
	ret c
	ld a, d
	ld d, e
	ld e, a
	ret

.FarZero:
; a = 0 for a connection to the north or west.
	push bc
	ld c, 0
	jr .ZeroIf

.NearZero:
; a = 0 for a connection to the south or east.
	push bc
	ld c, 1
.ZeroIf:
	ld b, a
	ldh a, [hConnectionDirection]
	and 1
	cp c
	ld a, b
	pop bc
	ret nz
	xor a
	ret

LoadBlockData::
	ld hl, wOverworldMapBlocks
	ld bc, wOverworldMapBlocksEnd - wOverworldMapBlocks
	xor a
	call ByteFill
	call ChangeMap
	call FillMapConnections
	ld a, MAPCALLBACK_TILES
	jp RunMapCallback

ChangeMap::
; Map blocks are compressed; decompress them to sScratch first.
	ld a, BANK(sScratch)
	call OpenSRAM
	ld hl, wMapBlocksPointer
	ld a, [hli]
	ld h, [hl]
	ld l, a
	ld a, [wMapBlocksBank]
	ld de, sScratch
	call FarDecompress
	; copy them inside the padding around the map
	ld a, [wMapWidth]
	ldh [hConnectedMapWidth], a
	add MAP_CONNECTION_PADDING_WIDTH * 2
	ld c, a
	ld b, 0
	ld hl, wOverworldMapBlocks + MAP_CONNECTION_PADDING_WIDTH
rept MAP_CONNECTION_PADDING_WIDTH
	add hl, bc
endr
	ld d, h
	ld e, l
	ld hl, sScratch
	ld a, [wMapHeight]
	ld b, a
	ld a, [wMapWidth]
	ld c, a
	call CopyMapBlocks
	jp CloseSRAM

FillMapConnections:
; Each connected map's blocks are decompressed to sScratch in turn, and the
; strip next to this map is copied from them.
	ld a, BANK(sScratch)
	call OpenSRAM
	ld hl, wNorthMapConnection
.loop
	push hl
	ld a, [hli]
	cp $ff
	jr z, .next
	ld b, a
	ld c, [hl]
	inc hl
	call DecompressAnyMapBlocks
	ld a, [hli]
	ld e, a
	ld a, [hli]
	ld d, a
	push de ; strip pointer
	ld a, [hli]
	ld e, a
	ld a, [hli]
	ld d, a ; strip location
	ld a, [hli]
	ld c, a ; strip length
	ld a, [hl]
	ldh [hConnectedMapWidth], a
	; north and south strips are 3 rows, west and east strips 3 columns
	ld a, l
	cp LOW(wWestMapConnection + MAP_CONNECTION_WIDTH)
	pop hl ; strip pointer
	ld b, MAP_CONNECTION_PADDING_WIDTH
	jr c, .got_size
	ld a, b
	ld b, c
	ld c, a
.got_size
	call CopyMapBlocks
.next
	pop hl
	ld bc, MAP_CONNECTION_LENGTH
	add hl, bc
	ld a, l
	cp LOW(wEastMapConnection + MAP_CONNECTION_LENGTH)
	jr nz, .loop
	jp CloseSRAM

CopyMapBlocks:
; Copy b rows of c blocks from hl, in rows of [hConnectedMapWidth] blocks, to
; de in wOverworldMapBlocks.
.row
	push bc
	push de
	push hl
.col
	ld a, [hli]
	ld [de], a
	inc de
	dec c
	jr nz, .col
	pop hl
	ldh a, [hConnectedMapWidth]
	ld c, a
	ld b, 0
	add hl, bc
	pop de
	ld a, [wMapWidth]
	add MAP_CONNECTION_PADDING_WIDTH * 2
	add e
	ld e, a
	jr nc, .no_carry
	inc d
.no_carry
	pop bc
	dec b
	jr nz, .row
	ret

EnterMapConnection::
; Return carry if a connection has been entered.
	ld a, [wPlayerStepDirection]
	cp RIGHT + 1
	ret nc
	ld e, a
	ld d, 0
	ld hl, .Connections
	add hl, de
	ld l, [hl]
	ld h, HIGH(wNorthMapConnection)
	ld a, [hli]
	ld [wMapGroup], a
	ld a, [hli]
	ld [wMapNumber], a
	ld de, MAP_CONNECTION_WIDTH - MAP_CONNECTION_STRIP_POINTER
	add hl, de
	ld a, [hli]
	add MAP_CONNECTION_PADDING_WIDTH * 2
	ld e, a ; rows of the connected map's blocks, for west and east
	ld a, [hli]
	ld b, a ; y offset
	ld a, [hli]
	ld c, a ; x offset
	ld a, [hli]
	ld h, [hl]
	ld l, a ; window
	ld a, [wPlayerStepDirection]
	cp LEFT
	jr nc, .west_east
	; north and south: the y offset is the new y, and x moves by the x offset
	ld a, b
	ld [wYCoord], a
	ld a, [wXCoord]
	add c
	ld [wXCoord], a
	ld e, 1
	jr .got_coord

.west_east
	; west and east: the x offset is the new x, and y moves by the y offset
	ld a, c
	ld [wXCoord], a
	ld a, [wYCoord]
	add b
	ld [wYCoord], a
.got_coord
	; the window moves a row or column of blocks for every 2 steps
	srl a
	ld c, e
	ld b, 0
	call AddNTimes
	ld a, l
	ld [wOverworldMapAnchor], a
	ld a, h
	ld [wOverworldMapAnchor + 1], a
	scf
	ret

.Connections:
	db LOW(wSouthMapConnection) ; DOWN
	db LOW(wNorthMapConnection) ; UP
	db LOW(wWestMapConnection)  ; LEFT
	db LOW(wEastMapConnection)  ; RIGHT

DecompressAnyMapBlocks:
; Decompress the blocks of group b map c to sScratch, which must be open.
	push hl
	push de
	push bc

	push bc
	ld de, MAP_MAPATTRIBUTES
	call GetAnyMapField
	ld l, c
	ld h, b
	pop bc

	push hl
	ld de, MAP_MAPATTRIBUTES_BANK
	call GetAnyMapField
	pop hl

	inc hl
	inc hl
	inc hl ; blocks bank, then blocks pointer
	ld a, c
	call GetFarByte
	push af
	inc hl
	ld a, c
	call GetFarWord
	pop af
	ld de, sScratch
	call FarDecompress

	pop bc
	pop de
	pop hl
	ret
