ObjectActionPairPointers:
; entries correspond to OBJECT_ACTION_* constants (see constants/map_object_constants.asm)
	table_width 2 + 2
	;  normal action,                  frozen action
	dw SetFacingStanding,              SetFacingStanding
	dw SetFacingStandAction,           SetFacingCurrent
	dw SetFacingStepAction,            SetFacingCurrent
	dw SetFacingBumpAction,            SetFacingCurrent
	dw SetFacingCounterclockwiseSpin,  SetFacingCurrent
	dw SetFacingCounterclockwiseSpin2, SetFacingStanding
	dw SetFacingFish,                  SetFacingFish
	dw SetFacingShadow,                SetFacingStanding
	dw SetFacingEmote,                 SetFacingEmote
	dw SetFacingBigDollSym,            SetFacingBigDollSym
	dw SetFacingBounce,                SetFacingFreezeBounce
	dw SetFacingWeirdTree,             SetFacingCurrent
	dw SetFacingBigDollAsym,           SetFacingBigDollAsym
	dw SetFacingBigDoll,               SetFacingBigDoll
	dw SetFacingBoulderDust,           SetFacingStanding
	dw SetFacingGrassShake,            SetFacingStanding
	assert_table_length NUM_OBJECT_ACTIONS

SetFacingStanding:
	ld hl, OBJECT_FACING
.tailmerge_25: ; (tools/tailmerge.py)
	add hl, bc
	ld [hl], STANDING
	ret

SetFacingCurrent:
	call GetSpriteDirection
.tailmerge_31: ; (tools/tailmerge.py)
	or FACING_STEP_DOWN_0 ; useless
.tailmerge_32: ; (tools/tailmerge.py)
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], a
	ret

SetFacingStandAction:
	ld hl, OBJECT_FACING
	add hl, bc
	ld a, [hl]
	and 1
	jr nz, SetFacingStepAction
	jr SetFacingCurrent

SetFacingStepAction:
	ld hl, OBJECT_FLAGS1
	add hl, bc
	bit SLIDING_F, [hl]
	jr nz, SetFacingCurrent

	call SetFacingStepAction_Shared ; ld hl, OBJECT_STEP_FRAME / add hl, bc / ld a, [hl]
	inc a
	and %00001111
	ld [hl], a

	rrca
	rrca
	maskbits NUM_DIRECTIONS
.tailmerge_64: ; (tools/tailmerge.py)
	ld d, a

	call GetSpriteDirection
	or FACING_STEP_DOWN_0 ; useless
	or d
	jr SetFacingCurrent.tailmerge_32 ; same as there (tools/tailmerge.py)

SetFacingBumpAction:
	ld hl, OBJECT_FLAGS1
	add hl, bc
	bit SLIDING_F, [hl]
	jr nz, SetFacingCurrent

	ld hl, OBJECT_STEP_FRAME
	add hl, bc
	inc [hl]

	ld a, [hl]
	rrca
	rrca
	rrca
	maskbits NUM_DIRECTIONS
	jr SetFacingStepAction.tailmerge_64 ; same as there (tools/tailmerge.py)

SetFacingCounterclockwiseSpin:
	call CounterclockwiseSpinAction
	ld hl, OBJECT_DIRECTION
	add hl, bc
	ld a, [hl]
	jr SetFacingCurrent.tailmerge_31 ; same as there (tools/tailmerge.py)

SetFacingCounterclockwiseSpin2:
	call CounterclockwiseSpinAction
	jr SetFacingStanding

CounterclockwiseSpinAction:
; Here, OBJECT_STEP_FRAME consists of two 2-bit components,
; using only bits 0,1 and 4,5.
; bits 0,1 is a timer (4 overworld frames)
; bits 4,5 determines the facing - the direction is counterclockwise.
	call SetFacingStepAction_Shared ; ld hl, OBJECT_STEP_FRAME / add hl, bc / ld a, [hl]
	and %11110000
	ld e, a

	ld a, [hl]
	inc a
	and %00001111
	ld d, a
	cp 4
	jr c, .ok

	ld d, 0
	ld a, e
	add $10
	and %00110000
	ld e, a

.ok
	ld a, d
	or e
	ld [hl], a

	swap e
	ld d, 0
	ld hl, .facings
	add hl, de
	ld a, [hl]
.shared1: ; (tools/outline.py)
	ld hl, OBJECT_DIRECTION
	add hl, bc
	ld [hl], a
	ret

.facings:
	db OW_DOWN
	db OW_RIGHT
	db OW_UP
	db OW_LEFT

SetFacingFish:
	call GetSpriteDirection
	rrca
	rrca
	add FACING_FISH_DOWN
	jp SetFacingCurrent.tailmerge_32 ; same as there (tools/tailmerge.py)

SetFacingShadow:
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], FACING_SHADOW
	ret

SetFacingEmote:
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], FACING_EMOTE
	ret

SetFacingBigDollSym:
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], FACING_BIG_DOLL_SYM
	ret

SetFacingBounce:
	call SetFacingStepAction_Shared ; ld hl, OBJECT_STEP_FRAME / add hl, bc / ld a, [hl]
	inc a
	and %00001111
	ld [hl], a
	and %00001000
	jr z, SetFacingFreezeBounce
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], FACING_STEP_UP_0
	ret

SetFacingFreezeBounce:
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], FACING_STEP_DOWN_0
	ret

SetFacingWeirdTree:
	call SetFacingStepAction_Shared ; ld hl, OBJECT_STEP_FRAME / add hl, bc / ld a, [hl]
	inc a
	ld [hl], a
	maskbits NUM_DIRECTIONS, 2
	rrca
	rrca
	add FACING_WEIRD_TREE_0
	jp SetFacingCurrent.tailmerge_32 ; same as there (tools/tailmerge.py)

SetFacingBigDollAsym:
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], FACING_BIG_DOLL_ASYM
	ret

SetFacingBigDoll:
	ld a, [wVariableSprites + SPRITE_BIG_DOLL - SPRITE_VARS]
	ld d, FACING_BIG_DOLL_SYM ; symmetric
	cp SPRITE_BIG_SNORLAX
	jr z, .ok
	cp SPRITE_BIG_LAPRAS
	jr z, .ok
	ld d, FACING_BIG_DOLL_ASYM ; asymmetric

.ok
	ld hl, OBJECT_FACING
	add hl, bc
	ld [hl], d
	ret

SetFacingBoulderDust:
	call SetFacingBoulderDust_Shared ; ld hl, OBJECT_STEP_FRAME / add hl, bc / inc [hl] / ...
	and 2
	ld a, FACING_BOULDER_DUST_1
	jr z, .ok
	assert FACING_BOULDER_DUST_1 + 1 == FACING_BOULDER_DUST_2
	inc a
.ok
	ld [hl], a
	ret

SetFacingGrassShake:
	call SetFacingBoulderDust_Shared ; ld hl, OBJECT_STEP_FRAME / add hl, bc / inc [hl] / ...
	and 4
	ld a, FACING_GRASS_1
	jr z, .ok
	assert FACING_GRASS_1 + 1 == FACING_GRASS_2
	inc a
.ok
	ld [hl], a
	ret

SetFacingBoulderDust_Shared: ; (tools/outline.py)
	ld hl, OBJECT_STEP_FRAME
	add hl, bc
	inc [hl]
	ld a, [hl]
	ld hl, OBJECT_FACING
	add hl, bc
	ret

SetFacingStepAction_Shared: ; (tools/outline.py)
	ld hl, OBJECT_STEP_FRAME
	add hl, bc
	ld a, [hl]
	ret
