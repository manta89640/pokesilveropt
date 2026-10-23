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
PicHeaderCounts:
	INCBIN "gfx/pic_codes.bin", 0, 2 * PIC_CODE_MAX_BITS
PicLiteralCounts:
	INCBIN "gfx/pic_codes.bin", PIC_CODE_SIZE, 2 * PIC_CODE_MAX_BITS
PicArgumentCounts:
	INCBIN "gfx/pic_codes.bin", 2 * PIC_CODE_SIZE, 2 * PIC_CODE_MAX_BITS
	assert HIGH(PicHeaderCounts) == HIGH(@ - 1)

DecompressPic:
; Decompress a picture from a:hl to de.
	ld [wLZBank], a
	ld a, l
	ld [wLZSource], a
	ld a, h
	ld [wLZSource + 1], a
	ld a, e
	ld [wLZAddress], a
	ld a, d
	ld [wLZAddress + 1], a
	ld a, %10000000 ; no bits left
	ld [wLZBits], a
	ld a, LOW(hLZBufferEnd) ; no bytes left
	ldh [hLZBufferPosition], a

.Main:
	call .DecodeHeader
	cp $ff ; end
	ret z
	ld b, a
	and %11100000
	cp %11100000
	jr nz, .short
	; 111xxxyy yyyyyyyy: command x, length y + 1
	ld a, b
	add a
	add a
	add a
	and %11100000
	push af
	ld a, b
	and %00000011
	push af
	call .GetArgument
	ld c, a
	pop af
	ld b, a
	jr .command

.short
	; xxxyyyyy: command x, length y + 1
	push af
	ld a, b
	and %00011111
	ld c, a
	ld b, 0

.command
	inc bc
	pop af
	bit 7, a
	jr nz, .Lookback
	cp 1 << 5
	jr z, .Iterate
	cp 2 << 5
	jr z, .Alternate
	cp 3 << 5
	jr z, .Zero

; Literal: bc bytes, each XORed with the byte output two bytes before it
.literal_loop
	push bc
	push de
	ld hl, PicLiteralCounts
	ld d, HIGH(PicLiteralSymbols)
	call .Decode
	pop de
	ld h, d
	ld l, e
	dec hl
	dec hl
	xor [hl]
	ld [de], a
	inc de
	pop bc
	dec bc
	ld a, b
	or c
	jr nz, .literal_loop
	jr .Main

.Iterate:
; Write the same byte for bc bytes.
	call .GetArgument
	jr .fill

.Zero:
; Write 0 for bc bytes.
	xor a
.fill
	ld [de], a
	inc de
	ld h, a
	dec bc
	ld a, b
	or c
	ld a, h
	jr nz, .fill
	jr .Main

.Alternate:
; Alternate two bytes for bc bytes.
	call .GetArgument
	ld h, a
	call .GetArgument
	ld l, a
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
	jr .Main

.Lookback:
; Copy bc bytes from earlier in the output.
	push af
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
	ld h, a
	call .GetArgument
	ld l, a
	push de
	ld a, [wLZAddress]
	ld e, a
	ld a, [wLZAddress + 1]
	ld d, a
	add hl, de
	pop de

.copy
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
	jp .Main

.Reverse:
	ld a, [hld]
	ld [de], a
	inc de
	dec bc
	ld a, b
	or c
	jr nz, .Reverse
	jp .Main

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
	jp .Main

.GetArgument:
; Return in a the next argument byte. Preserves bc and hl.
	push bc
	push de
	push hl
	ld hl, PicArgumentCounts
	ld d, HIGH(PicArgumentSymbols)
	call .Decode
	pop hl
	pop de
	pop bc
	ret

.DecodeHeader:
	push de
	ld hl, PicHeaderCounts
	ld d, HIGH(PicHeaderSymbols)
	call .Decode
	pop de
	ret

.Decode:
; Return in a the symbol of the next code, with hl = the code's counts and
; d = the page of its symbols.
	ld a, [wLZBits]
	ld c, a
	xor a ; how far the bits read are into the codes of this length
.decode_loop
	sla c
	call z, .NextBits
	rla
	sub [hl]
	jr c, .found
	inc hl
	jr .decode_loop

.found
	; the symbol's index is the number of codes up to this length, plus a
	ld b, a
	ld a, l
	add PIC_CODE_MAX_BITS
	ld l, a
	ld a, b
	add [hl]
	ld e, a
	ld a, c
	ld [wLZBits], a
	ld a, [de]
	ret

.NextBits:
; Read the next byte into c, followed by a 1 that marks the end of its bits,
; and return its first bit in carry. Preserves a.
	ld b, a
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
	ld a, b
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
