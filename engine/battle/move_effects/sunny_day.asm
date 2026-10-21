BattleCommand_StartSun:
	ld a, WEATHER_SUN
	call BattleCommand_StartRain_Shared ; ld [wBattleWeather], a / ld a, 5 / ld [wWeatherCount], a
	call AnimateCurrentMove
	ld hl, SunGotBrightText
	jp StdBattleTextbox
