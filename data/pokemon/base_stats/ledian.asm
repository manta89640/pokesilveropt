	; LEDIAN ; dex number 166

	db  55,  35,  50,  85,  55, 110
	;   hp  atk  def  spd  sat  sdf

	db BUG, FLYING ; type
	db 90 ; catch rate
	db 134 ; base exp
	db NO_ITEM, NO_ITEM ; items
	db GENDER_F50 ; gender ratio
	; unknown 1 (BASE_UNKNOWN_1_VALUE)
	db 15 ; step cycles to hatch
	; unknown 2 (BASE_UNKNOWN_2_VALUE)
IF DEF(_GOLD)
	INCBIN "gfx/pokemon/ledian/front_gold.dimensions"
ELIF DEF(_SILVER)
	INCBIN "gfx/pokemon/ledian/front_silver.dimensions"
ENDC
	; unused beta front/back pics (NULL)
	db GROWTH_FAST ; growth rate
	dn EGG_BUG, EGG_BUG ; egg groups

	; tm/hm learnset
	tmhm DYNAMICPUNCH, HEADBUTT, CURSE, ROLLOUT, TOXIC, HIDDEN_POWER, SUNNY_DAY, SWEET_SCENT, SNORE, HYPER_BEAM, PROTECT, GIGA_DRAIN, ENDURE, FRUSTRATION, SOLARBEAM, RETURN, DIG, DOUBLE_TEAM, ICE_PUNCH, SWAGGER, SLEEP_TALK, SWIFT, THUNDERPUNCH, REST, ATTRACT, THIEF, FLASH
	; end
