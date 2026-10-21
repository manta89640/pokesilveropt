_UpdatePlayerSprite::
	call GetPlayerSprite
	ld a, [wUsedSprites]
	ld c, a
	ld a, [wUsedSprites + 1]
	ld b, a
	jp GetUsedSprite

LoadStandingSpritesGFX::
	ld hl, wSpriteFlags
	ld a, [hl]
	push af
	res SPRITES_SKIP_STANDING_GFX_F, [hl]
	set SPRITES_SKIP_WALKING_GFX_F, [hl]
.tailmerge_15: ; (tools/tailmerge.py)
	call LoadUsedSpritesGFX
	pop af
	ld [wSpriteFlags], a
	ret

LoadWalkingSpritesGFX::
	ld hl, wSpriteFlags
	ld a, [hl]
	push af
	set SPRITES_SKIP_STANDING_GFX_F, [hl]
	res SPRITES_SKIP_WALKING_GFX_F, [hl]
	jr LoadStandingSpritesGFX.tailmerge_15 ; same as there (tools/tailmerge.py)

RefreshSprites::
	call .Refresh
	jp LoadUsedSpritesGFX

.Refresh:
	xor a
	ld bc, wUsedSpritesEnd - wUsedSprites
	ld hl, wUsedSprites
	call ByteFill
	call GetPlayerSprite
	jr AddMapSprites

GetPlayerSprite:
; Get Chris's sprite.
	ld a, [wPlayerState]
	ld c, a
	ld hl, ChrisStateSprites
.loop
	ld a, [hli]
	cp c
	jr z, .good
	inc hl
	cp -1
	jr nz, .loop

; Any player state not in the array defaults to Chris's sprite.
	xor a ; ld a, PLAYER_NORMAL
	ld [wPlayerState], a
	ld a, SPRITE_CHRIS
	jr .finish

.good
	ld a, [hl]

.finish
	ld [wUsedSprites + 0], a
	ld [wPlayerSprite], a
	ld [wPlayerObjectSprite], a
	ret

INCLUDE "data/sprites/player_sprites.asm"

AddMapSprites:
	call GetMapEnvironment
	call CheckOutdoorMap
	jr z, .outdoor
	jr AddIndoorSprites

.outdoor
	jr AddOutdoorSprites

AddIndoorSprites:
	ld hl, wMap2ObjectSprite
	ld a, 2
.loop
	push af
	ld a, [hl]
	call AddSpriteGFX
	ld de, MAPOBJECT_LENGTH
	add hl, de
	pop af
	inc a
	cp NUM_OBJECTS
	jr nz, .loop
	ret

AddOutdoorSprites:
	ld a, [wMapGroup]
	dec a
	ld c, a
	ld b, 0
	ld hl, OutdoorSprites
	add hl, bc
	add hl, bc
	ld a, [hli]
	ld h, [hl]
	ld l, a
	ld c, MAX_OUTDOOR_SPRITES
.loop
	push bc
	ld a, [hli]
	call AddSpriteGFX
	pop bc
	dec c
	jr nz, .loop

	ld a, [wUnusedAddOutdoorSpritesReturnValue]
	ld c, a
	ret

AddSpriteGFX:
	and a
	ret z
	ld c, a
	call _DoesSpriteHaveFacings
	jr nc, .nope
	ld de, wUsedSprites + (SPRITE_GFX_LIST_CAPACITY - 2) * 2
	ld b, 2
	call .Loop
	ret nc
.nope
	ld de, wUsedSprites + 2
	ld b, SPRITE_GFX_LIST_CAPACITY - 3
	jr .Loop
.ok:
	ret

.Loop:
	ld a, [de]
	and a
	jr z, .new
	cp c
	jr z, .exists
	inc de
	inc de
	dec b
	jr nz, .Loop
	scf
	ret
.new:
	ld a, c
	ld [de], a
	xor a
	ret
.exists:
	xor a
	ret

LoadUsedSpritesGFX:
	ld a, MAPCALLBACK_SPRITES
	call RunMapCallback
	call GetUsedSprites
	ret c

	call LoadStillSpriteTiles
	jr LoadMiscTiles

GetUsedSprites:
	xor a
	ldh [hUsedSpriteTile], a
	ld hl, wUsedSprites
	ld a, SPRITE_GFX_LIST_CAPACITY - 2

.loop
	push af
	ld a, [hli]
	ldh [hUsedSpriteIndex], a
	and a
	jr z, .dont_set

	call GetSprite
	push hl
	push bc
	ldh a, [hUsedSpriteTile]
	call CopyToVram
	call CloseSRAM
	pop bc
	pop hl
	ldh a, [hUsedSpriteTile]
	ld [hl], a
	add c
	ldh [hUsedSpriteTile], a
	cp $80
	jr nc, .done

.dont_set
	inc hl
	pop af
	dec a
	jr nz, .loop

	xor a
	ret

.done
	pop af
	scf
	ret

LoadStillSpriteTiles:
	ld a, [wUsedSprites + (SPRITE_GFX_LIST_CAPACITY - 2) * 2]
	and a
	jr z, .no_still_sprite_1
	call GetSprite
	ld hl, vTiles0 tile $78
	call Get2bpp
	call CloseSRAM
.no_still_sprite_1
	ld a, $78
	ld [wUsedSprites + (SPRITE_GFX_LIST_CAPACITY - 2) * 2 + 1], a

	ld a, [wUsedSprites + (SPRITE_GFX_LIST_CAPACITY - 1) * 2]
	and a
	jr z, .no_still_sprite_2
	call GetSprite
	ld hl, vTiles0 tile $7c
	call Get2bpp
	call CloseSRAM
.no_still_sprite_2
	ld a, $7c
	ld [wUsedSprites + (SPRITE_GFX_LIST_CAPACITY - 1) * 2 + 1], a
	ret

LoadMiscTiles:
	ld a, [wSpriteFlags]
	bit SPRITES_SKIP_WALKING_GFX_F, a
	ret nz

	ld c, EMOTE_SHADOW
	farcall LoadEmote
	call GetMapEnvironment
	call CheckOutdoorMap
	ld c, EMOTE_GRASS_RUSTLE
	jr z, .outdoor
	ld c, EMOTE_BOULDER_DUST
.outdoor
	farcall LoadEmote
	ret

GetSprite:
	call GetMonSprite
	ret c

	push hl
	ld hl, OverworldSprites + SPRITEDATA_ADDR
	call GetSprite_Shared ; dec a / ld c, a / ld b, 0 / ...
	call AddNTimes
	; load the address into de
	ld a, [hli]
	ld e, a
	ld a, [hli]
	ld d, a
	; load the length into c
	ld a, [hli]
	swap a
	ld c, a
	; load the sprite bank into b
	ld b, [hl]
	pop hl
	assert SPRITE_GFX_COMPRESSED == 1
	bit 4, c
	ret z
	res 4, c
; Decompress the tiles to sSpriteBuffer, and leave SRAM open for the caller to
; copy them; it must call CloseSRAM afterward.
	push hl
	push bc
	ld a, BANK(sSpriteBuffer)
	call OpenSRAM
	ld h, d
	ld l, e
	ld a, b
	ld de, sSpriteBuffer
	call FarDecompress
	pop bc
	pop hl
	ld de, sSpriteBuffer
	ret

GetMonSprite:
; Return carry if a monster sprite was loaded.

	cp SPRITE_POKEMON
	jr c, .Normal
	cp SPRITE_DAY_CARE_MON_1
	jr z, .BreedMon1
	cp SPRITE_DAY_CARE_MON_2
	jr z, .BreedMon2
	cp SPRITE_VARS
	jr nc, .Variable
	jr .Icon

.Normal:
	and a
	ret

.Icon:
	push hl
	sub SPRITE_POKEMON
	ld e, a
	ld d, 0
	ld hl, SpriteMons
	add hl, de
	ld a, [hl]
	pop hl
	jr .Mon

.BreedMon1
	ld a, [wBreedMon1Species]
	jr .Mon

.BreedMon2
	ld a, [wBreedMon2Species]

.Mon:
	ld e, a
	and a
	jr z, .NoBreedmon

	push hl
	farcall LoadOverworldMonIcon
	pop hl

	scf
	ret

.Variable:
	push hl
	sub SPRITE_VARS
	ld e, a
	ld d, 0
	ld hl, wVariableSprites
	add hl, de
	ld a, [hl]
	pop hl
	and a
	jr nz, GetMonSprite

.NoBreedmon:
	ld a, 1
	and a
	ret

_DoesSpriteHaveFacings::
; Checks to see whether we can apply a facing to a sprite.
; Returns carry unless the sprite is a Pokemon or a Still Sprite.
	cp SPRITE_POKEMON
	jr nc, .only_down

	push hl
	push bc
	ld hl, OverworldSprites + SPRITEDATA_TYPE
	call GetSprite_Shared ; dec a / ld c, a / ld b, 0 / ...
	call AddNTimes
	ld a, [hl]
	pop bc
	pop hl
	cp STILL_SPRITE
	jr nz, .only_down
	scf
	ret

.only_down
	and a
	ret

_GetSpritePalette::
	ld a, c
	call GetMonSprite
	jr c, .is_pokemon

	ld hl, OverworldSprites + SPRITEDATA_PALETTE
	call GetSprite_Shared ; dec a / ld c, a / ld b, 0 / ...
	call AddNTimes
	ld c, [hl]
	ret

.is_pokemon
	xor a
	ld c, a
	ret

CopyToVram:
	ld l, a
	ld h, 0
rept 4
	add hl, hl
endr
	ld a, l
	add LOW(vTiles0)
	ld l, a
	ld a, h
	adc HIGH(vTiles0)
	ld h, a
	push hl
	push de
	push bc
	ld a, [wSpriteFlags]
	bit SPRITES_SKIP_STANDING_GFX_F, a
	jr nz, .skip
	call Get2bpp

.skip:
	pop bc
	ld l, c
	ld h, 0
rept 4
	add hl, hl
endr
	pop de
	add hl, de
	ld e, l
	ld d, h
	pop hl
	ld a, h
	add HIGH(vTiles1 - vTiles0)
	ld h, a
	ldh a, [hUsedSpriteIndex]
	call _DoesSpriteHaveFacings
	ret c

	ld a, [wSpriteFlags]
	bit SPRITES_SKIP_WALKING_GFX_F, a
	ret nz

	call Get2bpp

.done:
	ret


GetUsedSprite:
; Input: b = tile id, c = index
	push bc
	ld a, c
	ldh [hUsedSpriteIndex], a
	call GetSprite
	pop af
	call CopyToVram
	jp CloseSRAM

LoadEmote::
; Get the address of the pointer to emote c.
	ld a, c
	ld bc, EMOTE_LENGTH
	ld hl, Emotes
	call AddNTimes
; Load the emote address into de
	ld e, [hl]
	inc hl
	ld d, [hl]
; load the length of the emote (in tiles) into c
	inc hl
	ld c, [hl]
	swap c
; load the emote pointer bank into b
	inc hl
	ld b, [hl]
; load the VRAM destination into hl
	inc hl
	ld a, [hli]
	ld h, [hl]
	ld l, a
; if the emote has a length of 0, do not proceed (error handling)
	ld a, c
	and a
	ret z
	jp Get2bpp

INCLUDE "data/sprites/emotes.asm"

INCLUDE "gfx/emotes.asm"

INCLUDE "data/sprites/sprite_mons.asm"

INCLUDE "data/maps/outdoor_sprites.asm"

INCLUDE "data/sprites/sprites.asm"

GetSprite_Shared: ; (tools/outline.py)
	dec a
	ld c, a
	ld b, 0
	ld a, NUM_SPRITEDATA_FIELDS
	ret
