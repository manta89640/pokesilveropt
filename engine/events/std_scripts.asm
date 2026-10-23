MACRO add_stdscript
\1StdScript::
	dba \1
ENDM

StdScripts::
	add_stdscript PokecenterNurseScript
	add_stdscript DifficultBookshelfScript
	add_stdscript PictureBookshelfScript
	add_stdscript MagazineBookshelfScript
	add_stdscript TeamRocketOathScript
	add_stdscript IncenseBurnerScript
	add_stdscript MerchandiseShelfScript
	add_stdscript TownMapScript
	add_stdscript WindowScript
	add_stdscript TVScript
	add_stdscript HomepageScript ; unused
	add_stdscript Radio1Script
	add_stdscript Radio2Script
	add_stdscript TrashCanScript
	add_stdscript StrengthBoulderScript
	add_stdscript SmashRockScript
	add_stdscript PokecenterSignScript
	add_stdscript MartSignScript
	add_stdscript GoldenrodRocketsScript
	add_stdscript RadioTowerRocketsScript
	add_stdscript ElevatorButtonScript
	add_stdscript DayToTextScript
	add_stdscript BugContestResultsWarpScript
	add_stdscript BugContestResultsScript
	add_stdscript InitializeEventsScript
	add_stdscript AskNumber1MScript
	add_stdscript AskNumber2MScript
	add_stdscript RegisteredNumberMScript
	add_stdscript NumberAcceptedMScript
	add_stdscript NumberDeclinedMScript
	add_stdscript PhoneFullMScript
	add_stdscript RematchMScript
	add_stdscript AskNumber1FScript
	add_stdscript AskNumber2FScript
	add_stdscript RegisteredNumberFScript
	add_stdscript NumberAcceptedFScript
	add_stdscript NumberDeclinedFScript
	add_stdscript PhoneFullFScript
	add_stdscript RematchFScript
	add_stdscript GymStatue1Script
	add_stdscript GymStatue2Script
	add_stdscript ReceiveItemScript
	add_stdscript ReceiveTogepiEggScript
	add_stdscript PCScript
	add_stdscript GameCornerCoinVendorScript
	add_stdscript HappinessCheckScript

PokecenterNurseScript:
	opentext
	checktime MORN
	iftrue .morn
	checktime DAY
	iftrue .day
	checktime NITE
	iftrue .nite
	sjump .ok

.morn
	writetext NurseMornText
	promptbutton
	sjump .ok

.day
	writetext NurseDayText
	promptbutton
	sjump .ok

.nite
	writetext NurseNiteText
	promptbutton
	sjump .ok

.ok
	writetext NurseAskHealText
	yesorno
	iffalse .done

	writetext NurseTakePokemonText
	pause 20
	turnobject LAST_TALKED, LEFT
	pause 10
	special HealParty
	playmusic MUSIC_NONE
	setval HEALMACHINE_POKECENTER
	special HealMachineAnim
	pause 30
	special RestartMapMusic
	turnobject LAST_TALKED, DOWN
	pause 10

	checkphonecall ; elm already called about pokerus
	iftrue .no
	checkflag ENGINE_CAUGHT_POKERUS
	iftrue .no
	special CheckPokerus
	iftrue .pokerus
.no
	writetext NurseReturnPokemonText
	pause 20

.done
	writetext NurseGoodbyeText

	turnobject LAST_TALKED, UP
	pause 10
	turnobject LAST_TALKED, DOWN
	pause 10

	waitbutton
	closetext
	end

.pokerus
	writetext NursePokerusText
	waitbutton
	closetext
	setflag ENGINE_CAUGHT_POKERUS
	specialphonecall SPECIALCALL_POKERUS
	end

DifficultBookshelfScript:
	jumptext DifficultBookshelfText

PictureBookshelfScript:
	jumptext PictureBookshelfText

MagazineBookshelfScript:
	jumptext MagazineBookshelfText

TeamRocketOathScript:
	jumptext TeamRocketOathText

IncenseBurnerScript:
	jumptext IncenseBurnerText

MerchandiseShelfScript:
	jumptext MerchandiseShelfText

TownMapScript:
	opentext
	writetext LookTownMapText
	waitbutton
	special OverworldTownMap
	closetext
	end

WindowScript:
	jumptext WindowText

TVScript:
	jumptext TVText

HomepageScript:
	jumptext HomepageText

Radio1Script:
	opentext
	setval MAPRADIO_POKEMON_CHANNEL
	special MapRadio
	closetext
	end

Radio2Script:
; Lucky Channel
	opentext
	setval MAPRADIO_LUCKY_CHANNEL
	special MapRadio
	closetext
	end

TrashCanScript:
	jumptext TrashCanText

PCScript:
	opentext
	special PokemonCenterPC
	closetext
	end

ElevatorButtonScript:
	playsound SFX_READ_TEXT_2
	pause 15
	playsound SFX_ELEVATOR_END
	end

StrengthBoulderScript:
	farsjump AskStrengthScript

SmashRockScript:
	farsjump AskRockSmashScript

PokecenterSignScript:
	jumptext PokecenterSignText

MartSignScript:
	jumptext MartSignText

DayToTextScript:
	readvar VAR_WEEKDAY
	ifequal MONDAY, .Monday
	ifequal TUESDAY, .Tuesday
	ifequal WEDNESDAY, .Wednesday
	ifequal THURSDAY, .Thursday
	ifequal FRIDAY, .Friday
	ifequal SATURDAY, .Saturday
	getstring STRING_BUFFER_3, .SundayText
	end
.Monday:
	getstring STRING_BUFFER_3, .MondayText
	end
.Tuesday:
	getstring STRING_BUFFER_3, .TuesdayText
	end
.Wednesday:
	getstring STRING_BUFFER_3, .WednesdayText
	end
.Thursday:
	getstring STRING_BUFFER_3, .ThursdayText
	end
.Friday:
	getstring STRING_BUFFER_3, .FridayText
	end
.Saturday:
	getstring STRING_BUFFER_3, .SaturdayText
	end
.SundayText:
	db "SUNDAY@"
.MondayText:
	db "MONDAY@"
.TuesdayText:
	db "TUESDAY@"
.WednesdayText:
	db "WEDNESDAY@"
.ThursdayText:
	db "THURSDAY@"
.FridayText:
	db "FRIDAY@"
.SaturdayText:
	db "SATURDAY@"

GoldenrodRocketsScript:
	clearevent EVENT_GOLDENROD_CITY_ROCKET_TAKEOVER
	end

RadioTowerRocketsScript:
	setflag ENGINE_ROCKETS_IN_RADIO_TOWER
	setevent EVENT_GOLDENROD_CITY_CIVILIANS
	setevent EVENT_RADIO_TOWER_BLACKBELT_BLOCKS_STAIRS
	clearevent EVENT_RADIO_TOWER_ROCKET_TAKEOVER
	clearevent EVENT_USED_THE_CARD_KEY_IN_THE_RADIO_TOWER
	setevent EVENT_MAHOGANY_TOWN_POKEFAN_M_BLOCKS_EAST
	specialphonecall SPECIALCALL_WEIRDBROADCAST
	setmapscene MAHOGANY_TOWN, SCENE_MAHOGANYTOWN_NOOP
	end

BugContestResultsWarpScript:
	special ClearBGPalettes
	scall BugContestResults_CopyContestantsToResults
	setevent EVENT_ROUTE_36_NATIONAL_PARK_GATE_OFFICER_CONTEST_DAY
	clearevent EVENT_ROUTE_36_NATIONAL_PARK_GATE_OFFICER_NOT_CONTEST_DAY
	setevent EVENT_WARPED_FROM_ROUTE_35_NATIONAL_PARK_GATE
	warp ROUTE_36_NATIONAL_PARK_GATE, 0, 4
	applymovement PLAYER, Movement_ContestResults_WalkAfterWarp

BugContestResultsScript:
	clearflag ENGINE_BUG_CONTEST_TIMER
	clearevent EVENT_WARPED_FROM_ROUTE_35_NATIONAL_PARK_GATE
	clearevent EVENT_CONTEST_OFFICER_HAS_SUN_STONE
	clearevent EVENT_CONTEST_OFFICER_HAS_EVERSTONE
	clearevent EVENT_CONTEST_OFFICER_HAS_GOLD_BERRY
	clearevent EVENT_CONTEST_OFFICER_HAS_BERRY
	opentext
	writetext ContestResults_ReadyToJudgeText
	waitbutton
	special BugContestJudging
	getnum STRING_BUFFER_3
	ifequal 1, BugContestResults_FirstPlace
	ifequal 2, BugContestResults_SecondPlace
	ifequal 3, BugContestResults_ThirdPlace
	writetext ContestResults_ConsolationPrizeText
	promptbutton
	waitsfx
	verbosegiveitem BERRY
	iffalse BugContestResults_NoRoomForBerry

BugContestResults_DidNotWin:
	writetext ContestResults_DidNotWinText
	promptbutton
	sjump BugContestResults_FinishUp

BugContestResults_ReturnAfterWinnersPrize:
	writetext ContestResults_JoinUsNextTimeText
	promptbutton

BugContestResults_FinishUp:
	checkevent EVENT_LEFT_MONS_WITH_CONTEST_OFFICER
	iffalse BugContestResults_DidNotLeaveMons
	writetext ContestResults_ReturnPartyText
	waitbutton
	special ContestReturnMons
BugContestResults_DidNotLeaveMons:
	special CheckPartyFullAfterContest
	ifequal BUGCONTEST_CAUGHT_MON, BugContestResults_CleanUp
	ifequal BUGCONTEST_NO_CATCH, BugContestResults_CleanUp
	; BUGCONTEST_BOXED_MON
	writetext ContestResults_PartyFullText
	waitbutton
BugContestResults_CleanUp:
	closetext
	setscene SCENE_ROUTE36NATIONALPARKGATE_NOOP
	setmapscene ROUTE_35_NATIONAL_PARK_GATE, SCENE_ROUTE35NATIONALPARKGATE_NOOP
	setevent EVENT_BUG_CATCHING_CONTESTANT_1A
	setevent EVENT_BUG_CATCHING_CONTESTANT_2A
	setevent EVENT_BUG_CATCHING_CONTESTANT_3A
	setevent EVENT_BUG_CATCHING_CONTESTANT_4A
	setevent EVENT_BUG_CATCHING_CONTESTANT_5A
	setevent EVENT_BUG_CATCHING_CONTESTANT_6A
	setevent EVENT_BUG_CATCHING_CONTESTANT_7A
	setevent EVENT_BUG_CATCHING_CONTESTANT_8A
	setevent EVENT_BUG_CATCHING_CONTESTANT_9A
	setevent EVENT_BUG_CATCHING_CONTESTANT_10A
	setevent EVENT_BUG_CATCHING_CONTESTANT_1B
	setevent EVENT_BUG_CATCHING_CONTESTANT_2B
	setevent EVENT_BUG_CATCHING_CONTESTANT_3B
	setevent EVENT_BUG_CATCHING_CONTESTANT_4B
	setevent EVENT_BUG_CATCHING_CONTESTANT_5B
	setevent EVENT_BUG_CATCHING_CONTESTANT_6B
	setevent EVENT_BUG_CATCHING_CONTESTANT_7B
	setevent EVENT_BUG_CATCHING_CONTESTANT_8B
	setevent EVENT_BUG_CATCHING_CONTESTANT_9B
	setevent EVENT_BUG_CATCHING_CONTESTANT_10B
	setflag ENGINE_DAILY_BUG_CONTEST
	special PlayMapMusic
	end

BugContestResults_FirstPlace:
	setevent EVENT_TEMPORARY_UNTIL_MAP_RELOAD_1
	getitemname STRING_BUFFER_4, SUN_STONE
	writetext ContestResults_PlayerWonAPrizeText
	waitbutton
	verbosegiveitem SUN_STONE
	iffalse BugContestResults_NoRoomForSunStone
	sjump BugContestResults_ReturnAfterWinnersPrize

BugContestResults_SecondPlace:
	getitemname STRING_BUFFER_4, EVERSTONE
	writetext ContestResults_PlayerWonAPrizeText
	waitbutton
	verbosegiveitem EVERSTONE
	iffalse BugContestResults_NoRoomForEverstone
	sjump BugContestResults_ReturnAfterWinnersPrize

BugContestResults_ThirdPlace:
	getitemname STRING_BUFFER_4, GOLD_BERRY
	writetext ContestResults_PlayerWonAPrizeText
	waitbutton
	verbosegiveitem GOLD_BERRY
	iffalse BugContestResults_NoRoomForGoldBerry
	sjump BugContestResults_ReturnAfterWinnersPrize

BugContestResults_NoRoomForSunStone:
	writetext BugContestPrizeNoRoomText
	promptbutton
	setevent EVENT_CONTEST_OFFICER_HAS_SUN_STONE
	sjump BugContestResults_ReturnAfterWinnersPrize

BugContestResults_NoRoomForEverstone:
	writetext BugContestPrizeNoRoomText
	promptbutton
	setevent EVENT_CONTEST_OFFICER_HAS_EVERSTONE
	sjump BugContestResults_ReturnAfterWinnersPrize

BugContestResults_NoRoomForGoldBerry:
	writetext BugContestPrizeNoRoomText
	promptbutton
	setevent EVENT_CONTEST_OFFICER_HAS_GOLD_BERRY
	sjump BugContestResults_ReturnAfterWinnersPrize

BugContestResults_NoRoomForBerry:
	writetext BugContestPrizeNoRoomText
	promptbutton
	setevent EVENT_CONTEST_OFFICER_HAS_BERRY
	sjump BugContestResults_DidNotWin

BugContestResults_CopyContestantsToResults:
	checkevent EVENT_BUG_CATCHING_CONTESTANT_1A
	iftrue .skip1
	clearevent EVENT_BUG_CATCHING_CONTESTANT_1B
.skip1
	checkevent EVENT_BUG_CATCHING_CONTESTANT_2A
	iftrue .skip2
	clearevent EVENT_BUG_CATCHING_CONTESTANT_2B
.skip2
	checkevent EVENT_BUG_CATCHING_CONTESTANT_3A
	iftrue .skip3
	clearevent EVENT_BUG_CATCHING_CONTESTANT_3B
.skip3
	checkevent EVENT_BUG_CATCHING_CONTESTANT_4A
	iftrue .skip4
	clearevent EVENT_BUG_CATCHING_CONTESTANT_4B
.skip4
	checkevent EVENT_BUG_CATCHING_CONTESTANT_5A
	iftrue .skip5
	clearevent EVENT_BUG_CATCHING_CONTESTANT_5B
.skip5
	checkevent EVENT_BUG_CATCHING_CONTESTANT_6A
	iftrue .skip6
	clearevent EVENT_BUG_CATCHING_CONTESTANT_6B
.skip6
	checkevent EVENT_BUG_CATCHING_CONTESTANT_7A
	iftrue .skip7
	clearevent EVENT_BUG_CATCHING_CONTESTANT_7B
.skip7
	checkevent EVENT_BUG_CATCHING_CONTESTANT_8A
	iftrue .skip8
	clearevent EVENT_BUG_CATCHING_CONTESTANT_8B
.skip8
	checkevent EVENT_BUG_CATCHING_CONTESTANT_9A
	iftrue .skip9
	clearevent EVENT_BUG_CATCHING_CONTESTANT_9B
.skip9
	checkevent EVENT_BUG_CATCHING_CONTESTANT_10A
	iftrue .skip10
	clearevent EVENT_BUG_CATCHING_CONTESTANT_10B
.skip10
	end

InitializeEventsScript:
	callasm InitializeEvents
	setflag ENGINE_ROCKET_SIGNAL_ON_CH20
	setflag ENGINE_ROCKETS_IN_MAHOGANY
	variablesprite SPRITE_WEIRD_TREE, SPRITE_SUDOWOODO
	variablesprite SPRITE_OLIVINE_RIVAL, SPRITE_RIVAL
	variablesprite SPRITE_AZALEA_ROCKET, SPRITE_ROCKET
	variablesprite SPRITE_FUCHSIA_GYM_1, SPRITE_JANINE
	variablesprite SPRITE_FUCHSIA_GYM_2, SPRITE_JANINE
	variablesprite SPRITE_FUCHSIA_GYM_3, SPRITE_JANINE
	variablesprite SPRITE_FUCHSIA_GYM_4, SPRITE_JANINE
	variablesprite SPRITE_COPYCAT, SPRITE_LASS
	variablesprite SPRITE_JANINE_IMPERSONATOR, SPRITE_LASS
	endcallback

InitializeEvents:
; Set the events of InitialEventFlags.
	ld de, InitialEventFlags
.loop
	ld a, [de]
	inc de
	cp -1
	ret z
	ld c, a
	ld b, 0
	ld hl, wEventFlags
	add hl, bc
	ld a, [de]
	inc de
	or [hl]
	ld [hl], a
	jr .loop

MACRO initial_event
	DEF _byte = (\1) / 8
	if !DEF(INITIAL_EVENT_BYTE_{d:_byte})
		DEF INITIAL_EVENT_BYTE_{d:_byte} = 0
	endc
	DEF INITIAL_EVENT_BYTE_{d:_byte} |= 1 << ((\1) % 8)
ENDM

MACRO initial_event_flags
; Each byte of wEventFlags that has events set, and the bits to set in it
	for _byte, (NUM_EVENTS + 7) / 8
		if DEF(INITIAL_EVENT_BYTE_{d:_byte})
			assert _byte != -1 & $ff
			db _byte, INITIAL_EVENT_BYTE_{d:_byte}
		endc
	endr
	db -1
ENDM

InitialEventFlags:
; The events set at the start of a new game
	initial_event EVENT_EARLS_ACADEMY_EARL
	initial_event EVENT_RADIO_TOWER_ROCKET_TAKEOVER
	initial_event EVENT_GOLDENROD_CITY_ROCKET_TAKEOVER
	initial_event EVENT_RADIO_TOWER_CIVILIANS_AFTER
	initial_event EVENT_ILEX_FOREST_APPRENTICE
	initial_event EVENT_ILEX_FOREST_FARFETCHD_1
	initial_event EVENT_ILEX_FOREST_FARFETCHD_2
	initial_event EVENT_ILEX_FOREST_FARFETCHD_3
	initial_event EVENT_ILEX_FOREST_FARFETCHD_4
	initial_event EVENT_ILEX_FOREST_FARFETCHD_5
	initial_event EVENT_ILEX_FOREST_FARFETCHD_6
	initial_event EVENT_ILEX_FOREST_FARFETCHD_7
	initial_event EVENT_ILEX_FOREST_FARFETCHD_8
	initial_event EVENT_ILEX_FOREST_FARFETCHD_9
	initial_event EVENT_ILEX_FOREST_FARFETCHD_10
	initial_event EVENT_ILEX_FOREST_CHARCOAL_MASTER
	initial_event EVENT_MAHOGANY_MART_LANCE_AND_DRAGONITE
	initial_event EVENT_TEAM_ROCKET_BASE_B2F_GRUNT_WITH_EXECUTIVE
	initial_event EVENT_TEAM_ROCKET_BASE_B2F_EXECUTIVE
	initial_event EVENT_TEAM_ROCKET_BASE_B2F_DRAGONITE
	initial_event EVENT_RIVAL_TEAM_ROCKET_BASE
	initial_event EVENT_BLACKTHORN_CITY_SUPER_NERD_DOES_NOT_BLOCK_GYM
	initial_event EVENT_USED_THE_CARD_KEY_IN_THE_RADIO_TOWER
	initial_event EVENT_RIVAL_CHERRYGROVE_CITY
	initial_event EVENT_RIVAL_AZALEA_TOWN
	initial_event EVENT_RIVAL_GOLDENROD_UNDERGROUND
	initial_event EVENT_AZALEA_TOWN_SLOWPOKES
	initial_event EVENT_KURTS_HOUSE_SLOWPOKE
	initial_event EVENT_GUIDE_GENT_VISIBLE_IN_CHERRYGROVE
	initial_event EVENT_ELMS_AIDE_IN_VIOLET_POKEMON_CENTER
	initial_event EVENT_COP_IN_ELMS_LAB
	initial_event EVENT_RUINS_OF_ALPH_OUTSIDE_SCIENTIST
	initial_event EVENT_RUINS_OF_ALPH_RESEARCH_CENTER_SCIENTIST
	initial_event EVENT_BOULDER_IN_ICE_PATH_1A
	initial_event EVENT_BOULDER_IN_ICE_PATH_2A
	initial_event EVENT_BOULDER_IN_ICE_PATH_3A
	initial_event EVENT_BOULDER_IN_ICE_PATH_4A
	initial_event EVENT_ROUTE_30_YOUNGSTER_JOEY
	initial_event EVENT_BUG_CATCHING_CONTESTANT_1A
	initial_event EVENT_BUG_CATCHING_CONTESTANT_2A
	initial_event EVENT_BUG_CATCHING_CONTESTANT_3A
	initial_event EVENT_BUG_CATCHING_CONTESTANT_4A
	initial_event EVENT_BUG_CATCHING_CONTESTANT_5A
	initial_event EVENT_BUG_CATCHING_CONTESTANT_6A
	initial_event EVENT_BUG_CATCHING_CONTESTANT_7A
	initial_event EVENT_BUG_CATCHING_CONTESTANT_8A
	initial_event EVENT_BUG_CATCHING_CONTESTANT_9A
	initial_event EVENT_BUG_CATCHING_CONTESTANT_10A
	initial_event EVENT_BUG_CATCHING_CONTESTANT_1B
	initial_event EVENT_BUG_CATCHING_CONTESTANT_2B
	initial_event EVENT_BUG_CATCHING_CONTESTANT_3B
	initial_event EVENT_BUG_CATCHING_CONTESTANT_4B
	initial_event EVENT_BUG_CATCHING_CONTESTANT_5B
	initial_event EVENT_BUG_CATCHING_CONTESTANT_6B
	initial_event EVENT_BUG_CATCHING_CONTESTANT_7B
	initial_event EVENT_BUG_CATCHING_CONTESTANT_8B
	initial_event EVENT_BUG_CATCHING_CONTESTANT_9B
	initial_event EVENT_BUG_CATCHING_CONTESTANT_10B
	initial_event EVENT_FAST_SHIP_1F_GENTLEMAN
	initial_event EVENT_FAST_SHIP_B1F_SAILOR_RIGHT
	initial_event EVENT_FAST_SHIP_CABINS_NNW_NNE_NE_SAILOR
	initial_event EVENT_LAKE_OF_RAGE_CIVILIANS
	initial_event EVENT_MAHOGANY_MART_OWNERS
	initial_event EVENT_TIN_TOWER_ROOF_HO_OH
	initial_event EVENT_WHIRL_ISLAND_LUGIA_CHAMBER_LUGIA
	initial_event EVENT_PLAYERS_HOUSE_2F_CONSOLE
	initial_event EVENT_PLAYERS_HOUSE_2F_DOLL_1
	initial_event EVENT_PLAYERS_HOUSE_2F_DOLL_2
	initial_event EVENT_PLAYERS_HOUSE_2F_BIG_DOLL
	initial_event EVENT_DECO_BED_1
	initial_event EVENT_DECO_POSTER_1
	initial_event EVENT_GOLDENROD_TRAIN_STATION_GENTLEMAN
	initial_event EVENT_OLIVINE_GYM_JASMINE
	initial_event EVENT_BLACKTHORN_CITY_GRAMPS_NOT_BLOCKING_DRAGONS_DEN
	initial_event EVENT_MET_BILL
	initial_event EVENT_ECRUTEAK_POKE_CENTER_BILL
	initial_event EVENT_MYSTERY_GIFT_DELIVERY_GUY
	initial_event EVENT_LAKE_OF_RAGE_LANCE
	initial_event EVENT_GOLDENROD_DEPT_STORE_B1F_LAYOUT_1
	initial_event EVENT_GOLDENROD_UNDERGROUND_WAREHOUSE_BLOCKED_OFF
	initial_event EVENT_DRAGONS_DEN_CLAIR
	initial_event EVENT_RIVAL_OLIVINE_CITY
	initial_event EVENT_RIVAL_VICTORY_ROAD
	initial_event EVENT_RIVAL_DRAGONS_DEN
	initial_event EVENT_LANCES_ROOM_OAK_AND_MARY
	initial_event EVENT_FAST_SHIP_CABINS_SE_SSE_CAPTAINS_CABIN_TWIN_1
	initial_event EVENT_BURNED_TOWER_B1F_BEASTS_1
	initial_event EVENT_RED_IN_MT_SILVER
	initial_event EVENT_OLIVINE_PORT_SPRITES_AFTER_HALL_OF_FAME
	initial_event EVENT_FAST_SHIP_PASSENGERS_EASTBOUND
	initial_event EVENT_FAST_SHIP_PASSENGERS_WESTBOUND
	initial_event EVENT_OLIVINE_PORT_PASSAGE_POKEFAN_M
	initial_event EVENT_KURTS_HOUSE_KURT_2
	initial_event EVENT_BURNED_TOWER_FIREBREATHER_DICK_ASHES
	initial_event EVENT_ECRUTEAK_TIN_TOWER_ENTRANCE_SAGE_LEFT
	initial_event EVENT_PLAYERS_HOUSE_MOM_2
	initial_event EVENT_FOUND_MACHINE_PART_IN_CERULEAN_GYM
	initial_event EVENT_CERULEAN_GYM_ROCKET
	initial_event EVENT_ROUTE_24_ROCKET
	initial_event EVENT_ROUTE_25_MISTY_BOYFRIEND
	initial_event EVENT_TRAINERS_IN_CERULEAN_GYM
	initial_event EVENT_COPYCATS_HOUSE_2F_DOLL
	initial_event EVENT_VIRIDIAN_GYM_BLUE
	initial_event EVENT_SEAFOAM_GYM_GYM_GUIDE
	initial_event EVENT_MT_MOON_SQUARE_CLEFAIRY
	initial_event EVENT_SAFFRON_TRAIN_STATION_POPULATION
	initial_event EVENT_INDIGO_PLATEAU_POKECENTER_RIVAL
	initial_event EVENT_INITIALIZED_EVENTS
	initial_event_flags

AskNumber1MScript:
	writetext AskNumber1MText
	end

AskNumber2MScript:
	writetext AskNumber2MText
	end

RegisteredNumberMScript:
	writetext RegisteredNumberMText
	playsound SFX_REGISTER_PHONE_NUMBER
	waitsfx
	promptbutton
	end

NumberAcceptedMScript:
	writetext NumberAcceptedMText
	waitbutton
	closetext
	end

NumberDeclinedMScript:
	writetext NumberDeclinedMText
	waitbutton
	closetext
	end

PhoneFullMScript:
	writetext PhoneFullMText
	waitbutton
	closetext
	end

RematchMScript:
	writetext RematchMText
	waitbutton
	closetext
	end

AskNumber1FScript:
	writetext AskNumber1FText
	end

AskNumber2FScript:
	writetext AskNumber2FText
	end

RegisteredNumberFScript:
	writetext RegisteredNumberFText
	playsound SFX_REGISTER_PHONE_NUMBER
	waitsfx
	promptbutton
	end

NumberAcceptedFScript:
	writetext NumberAcceptedFText
	waitbutton
	closetext
	end

NumberDeclinedFScript:
	writetext NumberDeclinedFText
	waitbutton
	closetext
	end

PhoneFullFScript:
	writetext PhoneFullFText
	waitbutton
	closetext
	end

RematchFScript:
	writetext RematchFText
	waitbutton
	closetext
	end

GymStatue1Script:
	getcurlandmarkname STRING_BUFFER_3
	jumptext GymStatue_CityGymText

GymStatue2Script:
	getcurlandmarkname STRING_BUFFER_3
	opentext
	writetext GymStatue_CityGymText
	promptbutton
	writetext GymStatue_WinningTrainersText
	waitbutton
	closetext
	end

ReceiveItemScript:
	waitsfx
	writetext ReceivedItemText
	playsound SFX_ITEM
	waitsfx
	end

ReceiveTogepiEggScript:
	waitsfx
	writetext ReceivedItemText
	playsound SFX_GET_EGG
	waitsfx
	end

GameCornerCoinVendorScript:
	faceplayer
	opentext
	writetext CoinVendor_WelcomeText
	promptbutton
	checkitem COIN_CASE
	iftrue CoinVendor_IntroScript
	writetext CoinVendor_NoCoinCaseText
	waitbutton
	closetext
	end

CoinVendor_IntroScript:
	writetext CoinVendor_IntroText

.loop
	special DisplayMoneyAndCoinBalance
	loadmenu .MenuHeader
	verticalmenu
	closewindow
	ifequal 1, .Buy50
	ifequal 2, .Buy500
	sjump .Cancel

.Buy50:
	checkcoins MAX_COINS - 50
	ifequal HAVE_MORE, .CoinCaseFull
	checkmoney YOUR_MONEY, 1000
	ifequal HAVE_LESS, .NotEnoughMoney
	givecoins 50
	takemoney YOUR_MONEY, 1000
	waitsfx
	playsound SFX_TRANSACTION
	writetext CoinVendor_Buy50CoinsText
	waitbutton
	sjump .loop

.Buy500:
	checkcoins MAX_COINS - 500
	ifequal HAVE_MORE, .CoinCaseFull
	checkmoney YOUR_MONEY, 10000
	ifequal HAVE_LESS, .NotEnoughMoney
	givecoins 500
	takemoney YOUR_MONEY, 10000
	waitsfx
	playsound SFX_TRANSACTION
	writetext CoinVendor_Buy500CoinsText
	waitbutton
	sjump .loop

.NotEnoughMoney:
	writetext CoinVendor_NotEnoughMoneyText
	waitbutton
	closetext
	end

.CoinCaseFull:
	writetext CoinVendor_CoinCaseFullText
	waitbutton
	closetext
	end

.Cancel:
	writetext CoinVendor_CancelText
	waitbutton
	closetext
	end

.MenuHeader:
	db MENU_BACKUP_TILES ; flags
	menu_coords 0, 4, 15, TEXTBOX_Y - 1
	dw .MenuData
	db 1 ; default option

.MenuData:
	db STATICMENU_CURSOR ; flags
	db 3 ; items
	db " 50 :  ¥1000@"
	db "500 : ¥10000@"
	db "CANCEL@"

HappinessCheckScript:
	faceplayer
	opentext
	special GetFirstPokemonHappiness
	ifless 50, .Unhappy
	ifless 150, .KindaHappy
	writetext HappinessText3
	waitbutton
	closetext
	end

.KindaHappy:
	writetext HappinessText2
	waitbutton
	closetext
	end

.Unhappy:
	writetext HappinessText1
	waitbutton
	closetext
	end

Movement_ContestResults_WalkAfterWarp:
	step RIGHT
	step DOWN
	turn_head UP
	step_end

INCLUDE "data/text/std_text.asm"
