BattleCommand_Teleport:
	ld a, [wBattleType]
	cp BATTLETYPE_FORCESHINY
	jr z, .failed
	cp BATTLETYPE_TRAP
	jr z, .failed

	ld a, BATTLE_VARS_SUBSTATUS5_OPP
	call GetBattleVar
	bit SUBSTATUS_CANT_RUN, a
	jr nz, .failed
	ldh a, [hBattleTurn]
	and a
	jr nz, .enemy_turn

	; Can't teleport from a trainer battle
	ld a, [wBattleMode]
	dec a
	jr nz, .failed
	; b = player level
	call BattleCommand_ForceSwitch_Shared4 ; ld a, [wCurPartyLevel] / ld b, a / ld a, [wBattleMonLevel] / ...
	jr nc, .run_away
	; c = player level + enemy level + 1
	add b
	ld c, a
	inc c
	; Generate a number less than c
.loop_player
	call BattleRandom
	cp c
	jr nc, .loop_player
	; b = enemy level / 4
	call BattleCommand_ForceSwitch_Shared3 ; srl b / srl b / cp b
	jr nc, .run_away

.failed
	call AnimateFailedMove
	jp PrintButItFailed

.enemy_turn
	; Can't teleport from a trainer battle
	ld a, [wBattleMode]
	dec a
	jr nz, .failed
	; b = enemy level
	call BattleCommand_ForceSwitch_Shared5 ; ld a, [wBattleMonLevel] / ld b, a / ld a, [wCurPartyLevel] / ...
	jr nc, .run_away
	; c = enemy level + player level + 1
	add b
	ld c, a
	inc c
	; Generate a number less than c
.loop_enemy
; BUG: Wild Pokémon can always Teleport regardless of level difference (see docs/bugs_and_glitches.md)
	call BattleRandom
	cp c
	jr nc, .loop_enemy
	; b = player level / 4
	call BattleCommand_ForceSwitch_Shared3 ; srl b / srl b / cp b
	jr nc, .run_away

.run_away
	call UpdateBattleMonInParty
	call BattleCommand_ForceSwitch_Shared ; xor a / ld [wBattleAfterAnim], a / inc a / ...
	ld a, 1
	ld [wBattleAnimParam], a
	call BattleCommand_LowerSub
	call LoadMoveAnim
	ld c, 20
	call DelayFrames
	ld a, DRAW
	ld [wBattleResult], a

	ld hl, FledFromBattleText
	jp StdBattleTextbox
