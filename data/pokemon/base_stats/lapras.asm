	; LAPRAS ; dex number 131

	db 130,  85,  80,  60,  85,  95
	;   hp  atk  def  spd  sat  sdf

	db WATER, ICE ; type
	db 45 ; catch rate
	db 219 ; base exp
	db NO_ITEM, NO_ITEM ; items
	db GENDER_F50 ; gender ratio
	; unknown 1 (BASE_UNKNOWN_1_VALUE)
	db 40 ; step cycles to hatch
	; unknown 2 (BASE_UNKNOWN_2_VALUE)
IF DEF(_GOLD)
	INCBIN "gfx/pokemon/lapras/front_gold.dimensions"
ELIF DEF(_SILVER)
	INCBIN "gfx/pokemon/lapras/front_silver.dimensions"
ENDC
	; unused beta front/back pics (NULL)
	db GROWTH_SLOW ; growth rate
	dn EGG_MONSTER, EGG_WATER_1 ; egg groups

	; tm/hm learnset
	tmhm HEADBUTT, CURSE, TOXIC, ZAP_CANNON, ROCK_SMASH, HIDDEN_POWER, SNORE, BLIZZARD, HYPER_BEAM, ICY_WIND, PROTECT, RAIN_DANCE, ENDURE, FRUSTRATION, IRON_TAIL, DRAGONBREATH, THUNDER, RETURN, PSYCHIC_M, DOUBLE_TEAM, SWAGGER, SLEEP_TALK, DREAM_EATER, REST, ATTRACT, NIGHTMARE, SURF, STRENGTH, WHIRLPOOL
	; end
