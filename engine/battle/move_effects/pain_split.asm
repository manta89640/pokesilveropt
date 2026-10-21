BattleCommand_PainSplit:
	ld a, [wAttackMissed]
	and a
	jp nz, .ButItFailed
	call CheckSubstituteOpp
	jr nz, .ButItFailed
	call AnimateCurrentMove
	ld hl, wBattleMonMaxHP + 1
	ld de, wEnemyMonMaxHP + 1
	call .PlayerShareHP
	ld a, $1
	ld [wWhichHPBar], a
	hlcoord 10, 9
	predef AnimateHPBar
	ld hl, wEnemyMonHP
	ld a, [hli]
	ld [wHPBuffer2 + 1], a
	ld a, [hli]
	ld [wHPBuffer2], a
	call DoEnemyDamage_Shared ; ld a, [hli] / ld [wHPBuffer1 + 1], a / ld a, [hl] / ...
	call .EnemyShareHP
	xor a
	ld [wWhichHPBar], a
	call ResetDamage
	hlcoord 2, 2
	predef AnimateHPBar

	ld hl, SharedPainText
	jp StdBattleTextbox

.PlayerShareHP:
	call BattleCommand_CheckFaint_Shared2 ; ld a, [hld] / ld [wHPBuffer1], a / ld a, [hld] / ...
	ld a, [hld]
	ld b, a
	ld [wHPBuffer2], a
	ld a, [hl]
	ld [wHPBuffer2 + 1], a
	dec de
	dec de
	ld a, [de]
	dec de
	add b
	ld [wCurDamage + 1], a
	ld b, [hl]
	ld a, [de]
	adc b
	srl a
	ld [wCurDamage], a
	ld a, [wCurDamage + 1]
	rr a
	ld [wCurDamage + 1], a
	inc hl
	inc hl
	inc hl
	inc de
	inc de
	inc de

.EnemyShareHP:
	ld c, [hl]
	dec hl
	ld a, [wCurDamage + 1]
	sub c
	ld b, [hl]
	dec hl
	ld a, [wCurDamage]
	sbc b
	jr nc, .skip

	call BattleCommand_Recoil_Shared ; ld a, [wCurDamage] / ld b, a / ld a, [wCurDamage + 1] / ...
.skip
	ld a, c
	ld [hld], a
	ld [wHPBuffer3], a
	ld a, b
	ld [hli], a
	ld [wHPBuffer3 + 1], a
	ret

.ButItFailed:
	jp PrintDidntAffect2
