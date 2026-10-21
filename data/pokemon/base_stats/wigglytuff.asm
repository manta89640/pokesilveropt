	; WIGGLYTUFF ; dex number 040

	db 140,  70,  45,  45,  75,  50
	;   hp  atk  def  spd  sat  sdf

	db NORMAL, NORMAL ; type
	db 50 ; catch rate
	db 109 ; base exp
	db NO_ITEM, NO_ITEM ; items
	db GENDER_F75 ; gender ratio
	; unknown 1 (BASE_UNKNOWN_1_VALUE)
	db 10 ; step cycles to hatch
	; unknown 2 (BASE_UNKNOWN_2_VALUE)
IF DEF(_GOLD)
	INCBIN "gfx/pokemon/wigglytuff/front_gold.dimensions"
ELIF DEF(_SILVER)
	INCBIN "gfx/pokemon/wigglytuff/front_silver.dimensions"
ENDC
	; unused beta front/back pics (NULL)
	db GROWTH_FAST ; growth rate
	dn EGG_FAIRY, EGG_FAIRY ; egg groups

	; tm/hm learnset
	tmhm DYNAMICPUNCH, HEADBUTT, CURSE, ROLLOUT, TOXIC, ZAP_CANNON, PSYCH_UP, HIDDEN_POWER, SUNNY_DAY, SNORE, BLIZZARD, HYPER_BEAM, PROTECT, RAIN_DANCE, ENDURE, FRUSTRATION, SOLARBEAM, THUNDER, RETURN, PSYCHIC_M, SHADOW_BALL, MUD_SLAP, DOUBLE_TEAM, ICE_PUNCH, SWAGGER, SLEEP_TALK, FIRE_BLAST, DEFENSE_CURL, THUNDERPUNCH, DREAM_EATER, DETECT, REST, ATTRACT, FIRE_PUNCH, NIGHTMARE, STRENGTH, FLASH
	; end
