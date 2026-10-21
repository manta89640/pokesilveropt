#define PROGRAM_NAME "stadium"
#define USAGE_OPTS "pokegold.gbc"

#include "common.h"

// ROM banks are 0x4000 bytes
#define BANK_SIZE 0x4000

// The Game Boy cartridge header stores a global checksum at 0x014E-0x014F
#define GLOBAL_OFF 0x014E

// ASCII "N64PS3" header (Stadium G/S was the third Japanese Stadium release for N64)
uint8_t n64ps3[6] = {'N', '6', '4', 'P', 'S', '3'};

// "N64PS3" header + 2-byte CRC
#define N64PS3_HEADER_SIZE (COUNTOF(n64ps3) + 2)

// The CRC polynomial value
#define CRC_POLY 0xC387
// The CRC initial value (also used for checksums)
#define CRC_INIT 0xFEFE

#define SET_U16BE(file, v) do { \
	(file)[0] = (uint8_t)(((v) & 0xFF00) >> 8); \
	(file)[1] = (uint8_t)(((v) & 0x00FF) >> 0); \
} while (0)

uint16_t calculate_checksum(uint16_t checksum, uint8_t *file, size_t size) {
	for (size_t i = 0; i < size; i++) {
		checksum += file[i];
	}
	return checksum;
}

void calculate_checksums(uint8_t *file, size_t rom_size) {
	// 2-byte checksums per half-bank
	size_t num_banks = rom_size / BANK_SIZE;
	size_t data_size = num_banks * 2 * 2;
	// "N64PS3" header + CRC + half-bank checksums, stored at the end of the ROM
	size_t total_size = N64PS3_HEADER_SIZE + data_size;
	size_t n64ps3_off = rom_size - total_size;

	// Initialize the CRC table
	uint16_t crc_table[256];
	for (uint16_t i = 0; i < COUNTOF(crc_table); i++) {
		uint16_t rem = 0;
		for (uint16_t y = 0, c = i; y < 8; y++, c >>= 1) {
			rem = (rem >> 1) ^ ((rem ^ c) & 1 ? CRC_POLY : 0);
		}
		crc_table[i] = rem;
	}

	// Clear the global checksum
	SET_U16BE(file + GLOBAL_OFF, 0);

	// Initialize the Stadium data (this should be free space anyway)
	memset(file + n64ps3_off, 0, total_size);
	memcpy(file + n64ps3_off, n64ps3, COUNTOF(n64ps3));

	// Calculate the half-bank checksums
	for (size_t i = 0; i < num_banks * 2; i++) {
		uint16_t checksum = calculate_checksum(CRC_INIT, file + i * BANK_SIZE / 2, BANK_SIZE / 2);
		SET_U16BE(file + n64ps3_off + N64PS3_HEADER_SIZE + i * 2, checksum);
	}

	// Calculate the CRC of the half-bank checksums
	uint16_t crc = CRC_INIT;
	for (size_t i = 0; i < data_size; i++) {
		crc = (crc >> 8) ^ crc_table[(crc & 0xFF) ^ file[n64ps3_off + N64PS3_HEADER_SIZE + i]];
	}
	SET_U16BE(file + n64ps3_off + N64PS3_HEADER_SIZE - 2, crc);

	// Calculate the global checksum
	uint16_t globalsum = calculate_checksum(0, file, rom_size);
	SET_U16BE(file + GLOBAL_OFF, globalsum);
}

int main(int argc, char *argv[]) {
	if (argc < 2) {
		usage_exit(1);
	}

	char *filename = argv[1];
	long filesize;
	uint8_t *file = read_u8(filename, &filesize);
	// The checksums cover a whole power-of-two ROM of at least two banks
	if (filesize >= 2 * BANK_SIZE && (filesize & (filesize - 1)) == 0) {
		calculate_checksums(file, (size_t)filesize);
	}
	write_u8(filename, file, filesize);
	free(file);
	return 0;
}
