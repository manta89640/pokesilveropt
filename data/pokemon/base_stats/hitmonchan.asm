	; HITMONCHAN ; dex number 107

	db  50, 105,  79,  76,  35, 110
	;   hp  atk  def  spd  sat  sdf

	db FIGHTING, FIGHTING ; type
	db 45 ; catch rate
	db 140 ; base exp
	db NO_ITEM, NO_ITEM ; items
	db GENDER_F0 ; gender ratio
	; unknown 1 (BASE_UNKNOWN_1_VALUE)
	db 25 ; step cycles to hatch
	; unknown 2 (BASE_UNKNOWN_2_VALUE)
IF DEF(_GOLD)
	INCBIN "gfx/pokemon/hitmonchan/front_gold.dimensions"
ELIF DEF(_SILVER)
	INCBIN "gfx/pokemon/hitmonchan/front_silver.dimensions"
ENDC
	; unused beta front/back pics (NULL)
	db GROWTH_MEDIUM_FAST ; growth rate
	dn EGG_HUMANSHAPE, EGG_HUMANSHAPE ; egg groups

	; tm/hm learnset
	tmhm DYNAMICPUNCH, HEADBUTT, CURSE, TOXIC, ROCK_SMASH, HIDDEN_POWER, SUNNY_DAY, SNORE, PROTECT, ENDURE, FRUSTRATION, RETURN, MUD_SLAP, DOUBLE_TEAM, ICE_PUNCH, SWAGGER, SLEEP_TALK, SWIFT, THUNDERPUNCH, DETECT, REST, ATTRACT, THIEF, FIRE_PUNCH, STRENGTH
	; end
