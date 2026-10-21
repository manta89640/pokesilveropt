Music_LookRocket:
	channel_count 4
	channel 1, Music_LookRocket_Ch1
	channel 2, Music_LookRocket_Ch2
	channel 3, Music_LookRocket_Ch3
	channel 4, Music_LookRocket_Ch4

Music_LookRocket_Ch1:
	tempo 123
	volume 7, 7
	transpose 0, 2
	stereo_panning FALSE, TRUE
	duty_cycle 3
	sound_call Music_LookRocket_Shared2
	sound_call .sub1
	duty_cycle 1
.mainloop:
	volume_envelope 10, 8
	sound_call .sub2
	sound_call Music_LookRocket_Ch2.sub5
	octave 4
	note F#, 1
	rest 1
	volume_envelope 5, 3
	sound_call .sub3
	volume_envelope 12, 3
	sound_call .sub3
	volume_envelope 14, 3
	sound_call .sub3
	rest 16
	sound_loop 0, .mainloop

.sub1:
	sound_call Music_LookRocket_Shared4
	octave 2
	note F_, 1
	note G#, 1
	note B_, 1
.shared6: ; (tools/scriptcalls.py)
	octave 3
	note D_, 1
	note F_, 1
	note G#, 1
	sound_ret

.sub2:
	rest 2
	octave 3
	note D#, 1
	rest 5
	note D#, 4
	octave 2
	note A_, 2
	octave 3
	sound_call Music_LookRocket_Shared3
	octave 4
	note F#, 1
	rest 1
	sound_ret

.sub3:
	rest 2
	octave 2
	note B_, 1
	rest 7
	octave 3
	note C_, 1
	rest 5
	sound_ret

Music_LookRocket_Ch2:
	transpose 0, 2
	sound_call Music_LookRocket_Shared5
	stereo_panning TRUE, TRUE
	octave 5
	note C_, 1
	note D_, 1
	sound_call .sub1
.mainloop:
	volume_envelope 11, 7
	sound_call .sub5
	octave 5
	note C_, 1
	rest 1
	sound_call .sub2
	volume_envelope 5, 3
	sound_call .sub3
	volume_envelope 12, 3
	sound_call .sub3
	volume_envelope 14, 3
	sound_call .sub3
	sound_call .sub4
	sound_loop 0, .mainloop

.sub1:
	sound_call Music_LookRocket_Shared4
	octave 3
	note B_, 6
	duty_cycle 0
	sound_ret

.sub2:
	rest 2
	octave 4
	note D#, 1
	rest 5
	note F_, 4
	note C_, 1
	note D_, 1
	sound_call Music_LookRocket_Shared3
	octave 5
	note D#, 1
	rest 1
	sound_ret

.sub3:
	rest 2
	octave 3
	note F_, 1
	rest 7
	note F#, 1
	rest 5
	sound_ret

.sub4:
	volume_envelope 6, 3
	note G#, 1
	note F_, 1
	note D_, 1
	octave 2
	note B_, 1
	volume_envelope 10, 3
	octave 3
	note A_, 1
	note F#, 1
	note D#, 1
	note C_, 1
	volume_envelope 12, 3
	note A#, 1
	note G_, 1
	note E_, 1
	note C#, 1
	volume_envelope 15, 3
	note B_, 1
	note G#, 1
	note F_, 1
	note D_, 1
	sound_ret

.sub5:
	octave 3
	rest 2
	note G_, 1
	rest 5
	note A_, 8
	note A#, 6
	note A_, 1
	rest 3
	note A#, 1
	rest 1
	note A_, 1
	rest 1
	sound_ret

Music_LookRocket_Ch3:
	transpose 0, 2
	vibrato 4, 2, 2
	note_type 12, 1, 4
	stereo_panning TRUE, FALSE
	rest 2
	sound_call .sub1
.mainloop:
	sound_call .sub4
	sound_call .sub4
	volume_envelope 2, 4
	sound_call .sub5
	volume_envelope 1, 4
	sound_call .sub2
	sound_call .sub5
	sound_call .sub3
	sound_loop 0, .mainloop

.sub1:
	octave 3
	note F_, 1
	rest 1
	note G#, 1
	sound_call Music_ViridianCity_Shared1
	note D_, 1
	rest 3
	octave 3
	note D_, 6
	sound_ret

.sub2:
	sound_call Music_LookRocket_Shared1
	note C_, 1
	rest 1
	note F#, 1
	rest 1
	sound_ret

.sub3:
	volume_envelope 2, 4
	octave 2
	note G#, 1
	rest 1
	octave 3
	note F_, 1
	rest 1
	octave 2
	note A_, 1
	rest 1
	octave 3
	note F#, 1
	rest 1
	volume_envelope 1, 4
	octave 2
	note A#, 1
	rest 1
	sound_call Music_BugCatchingContest_Shared1.shared7
	note B_, 1
.shared7: ; (tools/scriptcalls.py)
	rest 1
	octave 3
	note G#, 1
	rest 1
	sound_ret

.sub4:
	note C_, 1
	sound_call Music_ViridianCity_Shared1
	octave 3
	note C_, 1
	rest 1
	note C_, 1
	sound_call Music_ViridianCity_Shared1
	octave 3
	note C_, 1
	rest 1
	note D#, 1
	rest 1
	note G_, 1
	rest 1
	note C_, 1
	rest 1
	note C_, 1
	rest 1
	note C_, 1
	rest 1
	note C_, 1
	rest 1
	note C_, 1
	rest 1
	note C_, 1
	rest 1
.shared8: ; (tools/scriptcalls.py)
	note F#, 1
	rest 1
	note A_, 1
	rest 1
	sound_ret

.sub5:
	sound_call Music_LookRocket_Shared1
	note G#, 1
	note F#, 1
	note D#, 1
	note C_, 1
	sound_ret

Music_LookRocket_Ch4:
	sound_call Music_ViridianCity_Shared2
	rest 2
	sound_call .sub1
.mainloop:
	sound_call .sub2
	sound_call .sub2
	sound_call .sub2
	sound_call .sub2
	sound_call .sub2
	sound_call .sub2
	sound_call .sub2
	sound_call .sub1
	sound_loop 0, .mainloop

.sub1:
	drum_note 1, 8
	drum_note 3, 2
	drum_note 4, 2
.shared9: ; (tools/scriptcalls.py)
	drum_note 2, 1
	drum_note 2, 1
	drum_note 3, 1
	drum_note 3, 1
	sound_ret

.sub2:
	sound_call Music_LookRocket_Ch4.shared10
.shared10: ; (tools/scriptcalls.py)
	drum_note 4, 2
	drum_note 7, 2
	drum_note 3, 2
	drum_note 7, 2
	sound_ret

Music_LookRocket_Shared1: ; (tools/scriptcalls.py)
	octave 2
	note G#, 1
	rest 1
	octave 3
	note G#, 1
	rest 1
	octave 2
	note G#, 1
	rest 1
	note G#, 1
	rest 1
	note A_, 1
	rest 1
	octave 3
	note A_, 1
	rest 1
	sound_ret

Music_LookRocket_Shared2: ; (tools/scriptcalls.py)
	vibrato 5, 6, 4
	note_type 12, 10, 8
	octave 4
	note C_, 1
	note D_, 1
	sound_ret

Music_LookRocket_Shared3: ; (tools/scriptcalls.py)
	note D#, 1
	note F_, 1
	note F#, 6
	note D#, 1
	rest 3
	note F#, 1
	rest 1
	note D#, 1
	rest 1
	sound_ret

Music_LookRocket_Shared4: ; (tools/scriptcalls.py)
	note D#, 1
	rest 1
	note D_, 1
	rest 1
	note C#, 1
	rest 1
	note C_, 1
	rest 3
	sound_ret

Music_LookRocket_Shared5: ; (tools/scriptcalls.py)
	vibrato 4, 6, 4
	duty_cycle 3
	note_type 12, 11, 7
	sound_ret
