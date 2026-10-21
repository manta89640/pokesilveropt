BattleCommand_FrustrationPower:
; BUG: Return and Frustration deal no damage when the user's happiness is low or high, respectively (see docs/bugs_and_glitches.md)
	push bc
	ld hl, wBattleMonHappiness
	ldh a, [hBattleTurn]
	and a
	jr z, .got_happiness
	ld hl, wEnemyMonHappiness
.got_happiness
	ld a, $ff
	sub [hl]
	ldh [hMultiplicand + 2], a
	xor a
	ldh [hMultiplicand + 0], a
	ldh [hMultiplicand + 1], a
	jp BattleCommand_HappinessPower.tailmerge_15 ; same as there (tools/tailmerge.py)
