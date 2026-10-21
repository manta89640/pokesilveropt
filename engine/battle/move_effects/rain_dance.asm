BattleCommand_StartRain:
	ld a, WEATHER_RAIN
	call BattleCommand_StartRain_Shared ; ld [wBattleWeather], a / ld a, 5 / ld [wWeatherCount], a
	call AnimateCurrentMove
	ld hl, DownpourText
	jp StdBattleTextbox

BattleCommand_StartRain_Shared: ; (tools/outline.py)
	ld [wBattleWeather], a
	ld a, 5
	ld [wWeatherCount], a
	ret
