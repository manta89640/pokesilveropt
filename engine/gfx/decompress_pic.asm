; Pictures (Pokémon, trainers, the egg, the player's back) are compressed by
; tools/lzhuff.c. They use the commands of the LZ format that Decompress reads
; (see home/decompress.asm), read from a stream of bits, most significant bit
; first:
; - each command byte, and the $ff that ends the data, is a code of the header
;   Huffman code,
; - each literal byte is a code of the literal Huffman code, XORed with the
;   byte output two bytes before it (the data never starts with a literal),
; - every other byte (the second byte of a long command, the bytes to iterate
;   or alternate, and offsets) is a code of the argument Huffman code.
; gfx/pic_codes.bin holds the codes, which are canonical: for each, the number
; of codes of each length from 1 to PIC_CODE_MAX_BITS, the number of codes up to
; each length, then the 256 symbols in the order of their codes. To make it
; again from the pictures, run tools/lzhuff train gfx/pic_codes.bin with every
; picture's 2bpp file.

DEF PIC_CODE_MAX_BITS EQU 15
DEF PIC_CODE_SIZE EQU 2 * PIC_CODE_MAX_BITS + 256

; This section is aligned so that each code's symbols take a whole page.
PicHeaderSymbols:
	INCBIN "gfx/pic_codes.bin", 2 * PIC_CODE_MAX_BITS, 256
PicLiteralSymbols:
	INCBIN "gfx/pic_codes.bin", PIC_CODE_SIZE + 2 * PIC_CODE_MAX_BITS, 256
PicArgumentSymbols:
	INCBIN "gfx/pic_codes.bin", 2 * PIC_CODE_SIZE + 2 * PIC_CODE_MAX_BITS, 256
	assert LOW(PicHeaderSymbols) == 0

; Each code's counts take 32 bytes: the counts of codes of each length, then
; at +16 the counts up to each length, so set 4, l goes from one to the other.
MACRO pic_code_counts
	INCBIN "gfx/pic_codes.bin", (\1) * PIC_CODE_SIZE, PIC_CODE_MAX_BITS
	db 0
	INCBIN "gfx/pic_codes.bin", (\1) * PIC_CODE_SIZE + PIC_CODE_MAX_BITS, PIC_CODE_MAX_BITS
	db 0
ENDM
	assert PIC_CODE_MAX_BITS < 16
PicHeaderCounts:
	pic_code_counts 0
PicLiteralCounts:
	pic_code_counts 1
PicArgumentCounts:
	pic_code_counts 2
	assert LOW(PicHeaderCounts) % 32 == 0 && HIGH(PicHeaderCounts) == HIGH(@ - 1)

DecompressPic:
; Decompress a picture from a:hl to de.
; c holds the bits of the current byte not read yet, then a 1 that marks their
; end; it is kept in wLZBits while other commands run.
	ld [wLZBank], a
	ld a, l
	ld [wLZSource], a
	ld a, h
	ld [wLZSource + 1], a
	ld a, e
	ld [wLZAddress], a
	ld a, d
	ld [wLZAddress + 1], a
	ld a, LOW(hLZBufferEnd) ; no bytes read yet
	ldh [hLZBufferPosition], a
	ld c, %10000000 ; no bits left

.NextCommand:
	ld hl, PicHeaderCounts
	ld b, HIGH(PicHeaderSymbols)
	call .Decode
	inc a ; $ff ends the data
	ret z
	dec a
	ld b, a
	and %11100000
	cp %11100000
	jr z, .long
	; xxxyyyyy: command x, length y + 1
	xor b
	ld l, a
	ld h, 0
	ld a, b
	and %11100000
	jr .command

.long
	; 111xxxyy yyyyyyyy: command x, length y + 1
	ld a, b
	add a
	add a
	add a
	and %11100000
	push af
	ld a, b
	and %00000011
	ld h, a
	push hl
	call .GetArgument
	pop hl
	ld l, a
	pop af

.command
	inc hl
	bit 7, a
	jp nz, .Lookback
	cp 1 << 5
	jp z, .Iterate
	cp 2 << 5
	jp z, .Alternate
	cp 3 << 5
	jp z, .Zero

; Literal: hl bytes, each XORed with the byte output two bytes before it.
; b counts them, and hLZLiteralRounds the rounds of 256 after b's.
	ld b, l
	ld a, l
	and a
	ld a, h
	jr nz, .got_rounds
	dec a
.got_rounds
	ldh [hLZLiteralRounds], a
.literal_loop
	ld hl, PicLiteralCounts
	xor a ; how far the bits read are into the codes of this length
for n, 1, PIC_CODE_MAX_BITS + 1
	if n == 13
		jr .literal_length_13
.literal_found
		; the literal's index is the number of codes up to this length, plus a
		set 4, l
		add [hl]
		ld l, a
		ld h, HIGH(PicLiteralSymbols)
		ld a, [hl]
		ld h, d
		ld l, e
		dec hl
		dec hl
		xor [hl]
		ld [de], a
		inc de
		dec b
		jp nz, .literal_loop
		ldh a, [hLZLiteralRounds]
		and a
		jr z, .literals_done
		dec a
		ldh [hLZLiteralRounds], a
		jp .literal_loop
.literal_length_13
	endc
	sla c
	call z, .NextBits
	rla
	sub [hl]
	jr c, .literal_found
	inc l
endr
.literals_done
	jp .NextCommand

.Lookback:
; Copy hl bytes from earlier in the output.
	push af
	push hl
	call .GetArgument
	bit 7, a
	jr z, .absolute
	; %1nnnnnnn: n + 1 bytes back
	and %01111111
	cpl
	ld l, a
	ld h, $ff
	add hl, de
	jr .copy

.absolute
	; %0nnnnnnn nnnnnnnn: n bytes after the start
	push af
	call .GetArgument
	ld l, a
	pop af
	ld h, a
	push de
	ld a, [wLZAddress]
	ld e, a
	ld a, [wLZAddress + 1]
	ld d, a
	add hl, de
	pop de

.copy
	call .SaveBits
	pop bc
	pop af
	cp 5 << 5
	jr z, .Flip
	cp 6 << 5
	jr z, .Reverse

.Repeat:
	ld a, [hli]
	ld [de], a
	inc de
	dec bc
	ld a, b
	or c
	jr nz, .Repeat
	jr .LoadBits

.Reverse:
	ld a, [hld]
	ld [de], a
	inc de
	dec bc
	ld a, b
	or c
	jr nz, .Reverse
	jr .LoadBits

.Flip:
; Copy with the bits of each byte reversed.
	push bc
	ld a, [hli]
	ld b, a
	ld c, 1
.flip_bits
	rr b
	rl c
	jr nc, .flip_bits
	ld a, c
	pop bc
	ld [de], a
	inc de
	dec bc
	ld a, b
	or c
	jr nz, .Flip
	jr .LoadBits

.Iterate:
; Write the same byte for hl bytes.
	push hl
	call .GetArgument
	pop hl
	jr .fill

.Zero:
; Write 0 for hl bytes.
	xor a
.fill
	call .SaveBits
	ld b, h
	ld c, l
	ld h, a
.fill_loop
	ld a, h
	ld [de], a
	inc de
	dec bc
	ld a, b
	or c
	jr nz, .fill_loop
	jr .LoadBits

.Alternate:
; Alternate two bytes for hl bytes.
	push hl
	call .GetArgument
	push af
	call .GetArgument
	ld l, a
	pop af
	ld h, a
	call .SaveBits
	pop bc
.alternate_loop
	ld a, h
	ld [de], a
	inc de
	ld h, l
	ld l, a
	dec bc
	ld a, b
	or c
	jr nz, .alternate_loop
.LoadBits:
	ld a, [wLZBits]
	ld c, a
	jp .NextCommand

.SaveBits:
; Keep c in wLZBits. Preserves a.
	push af
	ld a, c
	ld [wLZBits], a
	pop af
	ret

.GetArgument:
; Return in a the next argument byte.
	ld hl, PicArgumentCounts
	ld b, HIGH(PicArgumentSymbols)
.Decode:
; Return in a the symbol of the next code, with hl = the code's counts and
; b = the page of its symbols. Preserves de.
	xor a ; how far the bits read are into the codes of this length
.decode_loop
	sla c
	call z, .NextBits
	rla
	sub [hl]
	jr c, .found
	inc l
	jr .decode_loop

.found
	; the symbol's index is the number of codes up to this length, plus a
	set 4, l
	add [hl]
	ld l, a
	ld h, b
	ld a, [hl]
	ret

.NextBits:
; Read the next byte into c, followed by a 1 that marks the end of its bits,
; and return its first bit in carry. Preserves a, b, de and hl.
	ldh [hLZSavedA], a
	ldh a, [hLZBufferPosition]
	cp LOW(hLZBufferEnd)
	call z, .FillBuffer
	ld c, a
	inc a
	ldh [hLZBufferPosition], a
	ldh a, [c]
	scf
	rla
	ld c, a
	ldh a, [hLZSavedA]
	ret

.FillBuffer:
; Copy the next bytes of the picture to hLZBuffer, and return a = LOW(hLZBuffer).
	push bc
	push de
	push hl
	ld hl, wLZSource
	ld a, [hli]
	ld h, [hl]
	ld l, a
	ld de, hLZBuffer
	ld bc, hLZBufferEnd - hLZBuffer
	ld a, [wLZBank]
	call FarCopyBytes
	ld a, l
	ld [wLZSource], a
	ld a, h
	ld [wLZSource + 1], a
	pop hl
	pop de
	pop bc
	ld a, LOW(hLZBuffer)
	ret
