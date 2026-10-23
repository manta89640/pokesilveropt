#define PROGRAM_NAME "lzhuff"
#define USAGE_OPTS "train tables.bin infiles... | compress tables.bin infile outfile | decompress tables.bin infile outfile"

#include "common.h"

// The same commands as the LZ format that lzcompress writes, read from a stream of bits:
// - each command byte (and the $ff that ends the data) is a symbol of the header code,
// - each literal byte is a symbol of the literal code, XORed with the byte output two before it
//   (so no literal may be among the first two bytes),
// - every other byte (the second byte of a long command, the bytes of iterate and alternate,
//   and offsets) is a symbol of the argument code.
// The codes are canonical Huffman codes. tables.bin holds, for each, the number of codes of each
// length from 1 to MAX_BITS, then the number of codes up to each length (modulo 256), then the
// 256 symbols in the order of their codes.

#define MAX_BITS 15
#define TABLE_SIZE (2 * MAX_BITS + 256)

#define SHORT_MAX_LENGTH (1 << 5)
#define LONG_MAX_LENGTH (1 << 10)
#define LOOKBACK_MAX_OFFSET (1 << 7)

enum lz_command {
	LZ_LITERAL, LZ_ITERATE, LZ_ALTERNATE, LZ_ZERO, LZ_REPEAT, LZ_FLIP, LZ_REVERSE, LZ_LONG,
	LZ_END = 0xff,
};

struct command {
	enum lz_command cmd;
	unsigned int length;
	int offset; // offset for lookback commands; bytes for iterate and alternate
};

struct code {
	uint8_t lengths[256];
	uint16_t codes[256];
};

enum { HEADER, LITERAL, ARGUMENT, NUM_CODES };
struct code codes[NUM_CODES];

/********************************************* Codes **********************************************/

// Huffman code lengths for these counts, at most MAX_BITS long
void build_lengths(const unsigned long *counts, uint8_t *lengths) {
	unsigned long weights[256];
	for (int i = 0; i < 256; i++) {
		weights[i] = counts[i] + 1; // every symbol gets a code
	}
	for (;;) {
		// Huffman's algorithm, O(n^2) is fine for 256 symbols
		unsigned long w[512];
		int parent[512], alive[512], n = 256;
		for (int i = 0; i < 256; i++) {
			w[i] = weights[i];
			alive[i] = 1;
		}
		for (int k = 0; k < 255; k++) {
			int a = -1, b = -1;
			for (int i = 0; i < n; i++) {
				if (!alive[i]) continue;
				if (a < 0 || w[i] < w[a]) {
					b = a;
					a = i;
				} else if (b < 0 || w[i] < w[b]) {
					b = i;
				}
			}
			alive[a] = alive[b] = 0;
			parent[a] = parent[b] = n;
			w[n] = w[a] + w[b];
			alive[n] = 1;
			n++;
		}
		int max = 0;
		for (int i = 0; i < 256; i++) {
			int len = 0;
			for (int j = i; j != n - 1; j = parent[j]) {
				len++;
			}
			lengths[i] = len;
			if (len > max) max = len;
		}
		if (max <= MAX_BITS) {
			return;
		}
		for (int i = 0; i < 256; i++) {
			weights[i] = (weights[i] + 1) / 2;
		}
	}
}

// Canonical codes: shorter codes first, then by symbol
void assign_codes(struct code *code) {
	unsigned int c = 0;
	for (int len = 1; len <= MAX_BITS; len++) {
		for (int s = 0; s < 256; s++) {
			if (code->lengths[s] == len) {
				code->codes[s] = c++;
			}
		}
		c <<= 1;
	}
}

void write_table(const struct code *code, uint8_t *table) {
	uint8_t *symbols = table + 2 * MAX_BITS;
	int total = 0;
	for (int len = 1; len <= MAX_BITS; len++) {
		int n = 0;
		for (int s = 0; s < 256; s++) {
			if (code->lengths[s] == len) {
				*symbols++ = s;
				n++;
			}
		}
		if (n > 255) {
			error_exit("too many codes of length %d\n", len);
		}
		total += n;
		table[len - 1] = n;
		table[MAX_BITS + len - 1] = total & 0xff;
	}
}

void read_table(const uint8_t *table, struct code *code) {
	const uint8_t *symbols = table + 2 * MAX_BITS;
	memset(code->lengths, 0, sizeof(code->lengths));
	for (int len = 1; len <= MAX_BITS; len++) {
		for (int n = table[len - 1]; n; n--) {
			code->lengths[*symbols++] = len;
		}
	}
	for (int s = 0; s < 256; s++) {
		if (!code->lengths[s]) {
			error_exit("symbol $%02x has no code\n", s);
		}
	}
	assign_codes(code);
}

void read_tables(const char *filename) {
	long size;
	uint8_t *tables = read_u8(filename, &size);
	if (size != NUM_CODES * TABLE_SIZE) {
		error_exit("%s is not %d bytes\n", filename, NUM_CODES * TABLE_SIZE);
	}
	for (int code = 0; code < NUM_CODES; code++) {
		read_table(tables + code * TABLE_SIZE, &codes[code]);
	}
	free(tables);
}

/****************************************** Compression *******************************************/

uint8_t *raw_data;
unsigned int raw_data_size;
unsigned long *literal_costs; // literal_costs[i] = bits for the literals raw_data[2..i)

uint8_t flip_f(uint8_t v) {
	return ((v & 1) << 7) | ((v & 2) << 5) | ((v & 4) << 3) | ((v & 8) << 1)
	     | ((v & 16) >> 1) | ((v & 32) >> 3) | ((v & 64) >> 5) | ((v & 128) >> 7);
}

uint8_t header_symbol(const struct command *command, bool *is_long) {
	unsigned int n = command->length - 1;
	*is_long = n >= SHORT_MAX_LENGTH;
	return *is_long ? (LZ_LONG << 5) | (command->cmd << 2) | (n >> 8) : (command->cmd << 5) | n;
}

uint8_t literal_symbol(unsigned int pos) {
	return raw_data[pos] ^ raw_data[pos - 2];
}

unsigned long argument_bits(uint8_t byte) {
	return codes[ARGUMENT].lengths[byte];
}

unsigned long command_bits(const struct command *command, unsigned int end) {
	bool is_long;
	unsigned long bits = codes[HEADER].lengths[header_symbol(command, &is_long)];
	if (is_long) {
		bits += argument_bits((command->length - 1) & 0xff);
	}
	switch (command->cmd) {
	case LZ_LITERAL:
		return bits + literal_costs[end] - literal_costs[end - command->length];
	case LZ_ITERATE:
		return bits + argument_bits(command->offset);
	case LZ_ALTERNATE:
		return bits + argument_bits(command->offset & 0xff) + argument_bits(command->offset >> 8);
	case LZ_ZERO:
		return bits;
	default:
		if (command->offset < 0) {
			return bits + argument_bits((command->offset ^ 0x7f) & 0xff);
		}
		return bits + argument_bits(command->offset >> 8) + argument_bits(command->offset & 0xff);
	}
}

unsigned long *best_bits;
struct command *best_commands;

void consider(unsigned int end, const struct command *command) {
	unsigned long bits = best_bits[end - command->length] + command_bits(command, end);
	if (bits < best_bits[end]) {
		best_bits[end] = bits;
		best_commands[end] = *command;
	}
}

unsigned int min(unsigned int a, unsigned int b) {
	return a < b ? a : b;
}

int encode_offset(int pos, int at) {
	return at - pos >= -LOOKBACK_MAX_OFFSET ? at - pos : at;
}

// Fills commands with the commands that take the fewest bits, and returns how many there are
unsigned int find_optimal_commands(struct command **commands) {
	best_bits = xmalloc(sizeof(*best_bits) * (raw_data_size + 1));
	best_commands = xmalloc(sizeof(*best_commands) * (raw_data_size + 1));
	literal_costs = xmalloc(sizeof(*literal_costs) * (raw_data_size + 1));
	literal_costs[0] = literal_costs[1] = literal_costs[2] = 0;
	for (unsigned int i = 2; i < raw_data_size; i++) {
		literal_costs[i + 1] = literal_costs[i] + codes[LITERAL].lengths[literal_symbol(i)];
	}

	best_bits[0] = 0;
	for (unsigned int i = 1; i <= raw_data_size; i++) {
		best_bits[i] = -1ul;
	}

	for (unsigned int i = 1; i <= raw_data_size; i++) {
		uint8_t byte = raw_data[i - 1];
		for (unsigned int prev = i > LONG_MAX_LENGTH ? i - LONG_MAX_LENGTH : 0; prev < i; prev++) {
			if (prev >= 2) {
				consider(i, &(struct command){LZ_LITERAL, i - prev, 0});
			}
		}

		unsigned int len = 0;
		do {
			len++;
			consider(i, &(struct command){byte ? LZ_ITERATE : LZ_ZERO, len, byte});
		} while (len < LONG_MAX_LENGTH && len < i && raw_data[i - (len + 1)] == byte);

		if (i > 1) {
			len = 1;
			do {
				len++;
				if (len >= 3) {
					int bytes = (raw_data[i - len + 1] << 8) | (raw_data[i - len]);
					consider(i, &(struct command){LZ_ALTERNATE, len, bytes});
				}
			} while (len < LONG_MAX_LENGTH && len < i && raw_data[i - (len + 1)] == raw_data[i - (len - 1)]);
		}

		unsigned int pos = i - 1;
		for (unsigned int at = 0; at < pos; at++) {
			unsigned int k = 0;
			while (pos + k < raw_data_size && k < LONG_MAX_LENGTH && raw_data[pos + k] == raw_data[at + k]) {
				k++;
				if (k >= 2) consider(pos + k, &(struct command){LZ_REPEAT, k, encode_offset(pos, at)});
			}
			k = 0;
			while (pos + k < raw_data_size && k < LONG_MAX_LENGTH && k <= at && raw_data[pos + k] == raw_data[at - k]) {
				k++;
				if (k >= 2) consider(pos + k, &(struct command){LZ_REVERSE, k, encode_offset(pos, at)});
			}
			k = 0;
			while (pos + k < raw_data_size && k < LONG_MAX_LENGTH && flip_f(raw_data[pos + k]) == raw_data[at + k]) {
				k++;
				if (k >= 2) consider(pos + k, &(struct command){LZ_FLIP, k, encode_offset(pos, at)});
			}
		}
	}

	unsigned int count = 0;
	for (unsigned int pos = raw_data_size; pos > 0; pos -= best_commands[pos].length) {
		count++;
	}
	*commands = xmalloc(sizeof(**commands) * count);
	unsigned int n = count;
	for (unsigned int pos = raw_data_size; pos > 0; pos -= best_commands[pos].length) {
		(*commands)[--n] = best_commands[pos];
	}

	free(best_bits);
	free(best_commands);
	free(literal_costs);
	return count;
}

struct bits {
	uint8_t *data;
	unsigned int size; // in bits
};

void put_bits(struct bits *out, unsigned int value, int n) {
	while (n--) {
		if (!(out->size & 7)) {
			out->data[out->size >> 3] = 0;
		}
		if ((value >> n) & 1) {
			out->data[out->size >> 3] |= 0x80 >> (out->size & 7);
		}
		out->size++;
	}
}

unsigned long (*symbol_counts)[256]; // counts of the symbols written, if not NULL

void put_symbol(struct bits *out, int code, uint8_t symbol) {
	put_bits(out, codes[code].codes[symbol], codes[code].lengths[symbol]);
	if (symbol_counts) {
		symbol_counts[code][symbol]++;
	}
}

void write_commands(struct bits *out, const struct command *commands, unsigned int count) {
	unsigned int pos = 0;
	for (unsigned int i = 0; i < count; i++) {
		const struct command *command = &commands[i];
		bool is_long;
		put_symbol(out, HEADER, header_symbol(command, &is_long));
		if (is_long) {
			put_symbol(out, ARGUMENT, (command->length - 1) & 0xff);
		}
		switch (command->cmd) {
		case LZ_LITERAL:
			for (unsigned int j = 0; j < command->length; j++) {
				put_symbol(out, LITERAL, literal_symbol(pos + j));
			}
			break;
		case LZ_ITERATE:
			put_symbol(out, ARGUMENT, command->offset);
			break;
		case LZ_ALTERNATE:
			put_symbol(out, ARGUMENT, command->offset & 0xff);
			put_symbol(out, ARGUMENT, command->offset >> 8);
			break;
		case LZ_ZERO:
			break;
		default:
			if (command->offset < 0) {
				put_symbol(out, ARGUMENT, (command->offset ^ 0x7f) & 0xff);
			} else {
				put_symbol(out, ARGUMENT, command->offset >> 8);
				put_symbol(out, ARGUMENT, command->offset & 0xff);
			}
		}
		pos += command->length;
	}
	put_symbol(out, HEADER, LZ_END);
}

unsigned int compress(const char *filename, uint8_t *output) {
	long size;
	raw_data = read_u8(filename, &size);
	raw_data_size = size;
	struct command *commands;
	unsigned int count = find_optimal_commands(&commands);
	struct bits out = {output, 0};
	write_commands(&out, commands, count);
	free(commands);
	free(raw_data);
	return (out.size + 7) / 8;
}

void train(const char *tables_name, int num_files, char *filenames[]) {
	uint8_t *output = xmalloc(1 << 16);
	for (int code = 0; code < NUM_CODES; code++) {
		memset(codes[code].lengths, 8, sizeof(codes[code].lengths));
		assign_codes(&codes[code]);
	}
	unsigned long best_total = -1ul;
	uint8_t tables[NUM_CODES * TABLE_SIZE], best_tables[NUM_CODES * TABLE_SIZE];
	for (int round = 0; round < 30; round++) {
		unsigned long counts[NUM_CODES][256] = {{0}};
		unsigned long total = 0;
		symbol_counts = counts;
		for (int i = 0; i < num_files; i++) {
			total += compress(filenames[i], output);
		}
		symbol_counts = NULL;
		fprintf(stderr, "round %d: %lu bytes\n", round, total);
		// (the first round uses 8 bits for every symbol, which is never the best)
		if (round && total < best_total) {
			best_total = total;
			memcpy(best_tables, tables, sizeof(tables));
		} else if (round > 1) {
			break;
		}
		for (int code = 0; code < NUM_CODES; code++) {
			build_lengths(counts[code], codes[code].lengths);
			assign_codes(&codes[code]);
			write_table(&codes[code], tables + code * TABLE_SIZE);
		}
	}
	write_u8(tables_name, best_tables, sizeof(best_tables));
	free(output);
}

/***************************************** Decompression ******************************************/

struct reader {
	const uint8_t *data;
	unsigned int pos; // in bits
};

unsigned int get_bits(struct reader *in, int n) {
	unsigned int v = 0;
	while (n--) {
		v = (v << 1) | ((in->data[in->pos >> 3] >> (7 - (in->pos & 7))) & 1);
		in->pos++;
	}
	return v;
}

uint8_t get_symbol(struct reader *in, int code) {
	unsigned int c = 0;
	for (int len = 1; len <= MAX_BITS; len++) {
		c = (c << 1) | get_bits(in, 1);
		for (int s = 0; s < 256; s++) {
			if (codes[code].lengths[s] == len && codes[code].codes[s] == c) {
				return s;
			}
		}
	}
	error_exit("invalid code\n");
}

void decompress(const char *input_name, const char *output_name) {
	long size;
	uint8_t *input = read_u8(input_name, &size);
	struct reader in = {input, 0};
	uint8_t *out = xmalloc(1 << 16);
	unsigned int n_out = 0;
	for (;;) {
		uint8_t symbol = get_symbol(&in, HEADER);
		if (symbol == LZ_END) break;
		unsigned int cmd = symbol >> 5, length;
		if (cmd == LZ_LONG) {
			cmd = (symbol >> 2) & 7;
			length = (((symbol & 3) << 8) | get_symbol(&in, ARGUMENT)) + 1;
		} else {
			length = (symbol & 31) + 1;
		}
		if (cmd == LZ_LITERAL) {
			for (unsigned int j = 0; j < length; j++, n_out++) {
				if (n_out < 2) error_exit("literal in the first two bytes\n");
				out[n_out] = get_symbol(&in, LITERAL) ^ out[n_out - 2];
			}
		} else if (cmd == LZ_ITERATE || cmd == LZ_ZERO) {
			uint8_t v = cmd == LZ_ITERATE ? get_symbol(&in, ARGUMENT) : 0;
			while (length--) out[n_out++] = v;
		} else if (cmd == LZ_ALTERNATE) {
			uint8_t v[2] = {get_symbol(&in, ARGUMENT), get_symbol(&in, ARGUMENT)};
			for (unsigned int j = 0; j < length; j++) out[n_out++] = v[j & 1];
		} else {
			unsigned int b = get_symbol(&in, ARGUMENT), base;
			if (b & 0x80) {
				base = n_out - (b & 0x7f) - 1;
			} else {
				base = (b << 8) | get_symbol(&in, ARGUMENT);
			}
			for (unsigned int j = 0; j < length; j++, n_out++) {
				out[n_out] = cmd == LZ_REPEAT ? out[base + j]
				           : cmd == LZ_FLIP ? flip_f(out[base + j]) : out[base - j];
			}
		}
	}
	write_u8(output_name, out, n_out);
	free(out);
	free(input);
}

/********************************************** Main **********************************************/

int main(int argc, char *argv[]) {
	if (argc >= 3 && !strcmp(argv[1], "train")) {
		train(argv[2], argc - 3, argv + 3);
	} else if (argc == 5 && !strcmp(argv[1], "compress")) {
		read_tables(argv[2]);
		uint8_t *output = xmalloc(1 << 16);
		unsigned int size = compress(argv[3], output);
		write_u8(argv[4], output, size);
		free(output);
	} else if (argc == 5 && !strcmp(argv[1], "decompress")) {
		read_tables(argv[2]);
		decompress(argv[3], argv[4]);
	} else {
		usage_exit(1);
	}
	return 0;
}
