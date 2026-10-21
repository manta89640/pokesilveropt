BattleCommand_Snore:
	ld a, BATTLE_VARS_STATUS
	call GetBattleVar
	and SLP_MASK
	ret nz
	call ResetDamage
	call RaiseStat.shared6 ; ld a, $1 / ld [wAttackMissed], a
	call FailMove
	jp EndMoveEffect
