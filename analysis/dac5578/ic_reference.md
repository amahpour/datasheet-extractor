# DAC5578 / DAC6578 / DAC7578 — IC Quick Reference

> **Purpose:** Machine-readable companion to the extracted datasheet in this
> directory. Fills gaps left by the automated Docling extraction — particularly
> register bit-field layouts, the transfer function, and I2C protocol framing
> that were mangled during PDF-to-text conversion. An LLM consuming the `out/`
> folder should load this file first, then reference `document.json`, `tables/`,
> and `derived/` for deeper detail.

---

## 1. Device identity

| Field | Value |
|-------|-------|
| Manufacturer | Texas Instruments |
| Family | DACx578 |
| Variants | DAC5578 (8-bit), DAC6578 (10-bit), DAC7578 (12-bit) |
| Channels | 8 (A–H) |
| Interface | I2C (standard / fast / high-speed mode) |
| Supply range | 2.7 V – 5.5 V (AVDD) |
| Packages | TSSOP-16, QFN-24 |
| Temperature range | -40 C to +125 C |

---

## 2. Transfer function

```
VOUT = (D / 2^n) * VREF
```

| Variant | n (bits) | Max code | Full-scale output |
|---------|----------|----------|-------------------|
| DAC5578 | 8 | 255 | VREF * 255/256 |
| DAC6578 | 10 | 1023 | VREF * 1023/1024 |
| DAC7578 | 12 | 4095 | VREF * 4095/4096 |

- `D` = digital input code (unsigned integer)
- `VREF` = voltage on the VREFIN pin (external reference)
- Output is rail-to-rail: 0 V to AVDD

---

## 3. Data input register format (bit alignment)

All variants pack data into a 16-bit (2-byte) frame sent MSB-first over I2C.
Data is **left-aligned** in the 16-bit word. Unused LSBs are don't-care.

### DAC5578 (8-bit)

```
Bit:   15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
       D7  D6  D5  D4  D3  D2  D1  D0   X   X   X   X   X   X   X   X
       |------------- 8 data bits -------------|------- don't care ------|
```

MSDB = `D[7:0]` in bits [15:8], LSDB = `0x00` (don't care)

### DAC6578 (10-bit)

```
Bit:   15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
       D9  D8  D7  D6  D5  D4  D3  D2  D1  D0   X   X   X   X   X   X
       |------------- 10 data bits -------------------|-- don't care ---|
```

MSDB = `D[9:2]` in bits [15:8], LSDB = `D[1:0] << 6` in bits [7:6]

### DAC7578 (12-bit)

```
Bit:   15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
      D11 D10  D9  D8  D7  D6  D5  D4  D3  D2  D1  D0   X   X   X   X
       |------------------ 12 data bits ----------------------|-- DC --|
```

MSDB = `D[11:4]` in bits [15:8], LSDB = `D[3:0] << 4` in bits [7:4]

---

## 4. I2C slave address

Base address: `0b1001_XXX` (7-bit) where XXX is set by ADDR1 and ADDR0 pins.

| ADDR1 | ADDR0 | 7-bit address | 8-bit write | 8-bit read |
|-------|-------|---------------|-------------|------------|
| 0 | 0 | 0x48 | 0x90 | 0x91 |
| 0 | 1 | 0x49 | 0x92 | 0x93 |
| 1 | 0 | 0x4A | 0x94 | 0x95 |
| 1 | 1 | 0x4B | 0x96 | 0x97 |
| Float | 0 | 0x4C | 0x98 | 0x99 |
| Float | 1 | 0x4D | 0x9A | 0x9B |
| 0 | Float | 0x4E | 0x9C | 0x9D |
| 1 | Float | 0x4F | 0x9E | 0x9F |
| Float | Float | — (not supported) | — | — |

> For 16-pin package (TSSOP): only ADDR0 is exposed — ADDR1 is internally GND.

---

## 5. Command and access byte

Byte sent immediately after the address byte. Encodes the operation and target
channel.

```
Bit:    7    6    5    4    3    2    1    0
       C3   C2   C1   C0   A3   A2   A1   A0
       |--- command ---|   |--- channel ---|
```

### Command codes (C3:C0)

| C3 | C2 | C1 | C0 | Operation |
|----|----|----|------|-----------|
| 0 | 0 | 0 | 0 | Write to input register (channel n) |
| 0 | 0 | 0 | 1 | Update DAC register (channel n) — triggers output change |
| 0 | 0 | 1 | 0 | Write input register + update ALL DAC registers (software LDAC) |
| 0 | 0 | 1 | 1 | Write input register + update DAC register (channel n only) |
| 0 | 1 | 0 | 0 | Power down / power on DAC |
| 0 | 1 | 0 | 1 | Write clear code register |
| 0 | 1 | 1 | 0 | Write LDAC register |
| 0 | 1 | 1 | 1 | Software reset |

### Channel codes (A3:A0)

| A3 | A2 | A1 | A0 | Target |
|----|----|----|----|--------|
| 0 | 0 | 0 | 0 | Channel A |
| 0 | 0 | 0 | 1 | Channel B |
| 0 | 0 | 1 | 0 | Channel C |
| 0 | 0 | 1 | 1 | Channel D |
| 0 | 1 | 0 | 0 | Channel E |
| 0 | 1 | 0 | 1 | Channel F |
| 0 | 1 | 1 | 0 | Channel G |
| 0 | 1 | 1 | 1 | Channel H |
| 1 | 1 | 1 | 1 | All channels (broadcast) |

---

## 6. I2C write protocol

### Single-channel immediate write (most common)

Use command `0011` (write input + update DAC) for a fire-and-forget write:

```
[START] [ADDR+W] [ACK] [CMD_BYTE] [ACK] [MSDB] [ACK] [LSDB] [ACK] [STOP]
```

Example — set channel A to mid-scale on DAC7578 (addr 0x48):

```
START
  TX: 0x90          # address 0x48 + write bit
  TX: 0x30          # cmd=0011 (write+update), chan=0000 (A)
  TX: 0x80          # MSDB: D[11:4] = 0x80 → code 0x800 = 2048
  TX: 0x00          # LSDB: D[3:0] << 4 = 0x00
STOP
```

### Deferred write (double-buffered via LDAC)

1. Write to input register (cmd `0000`) for each channel — does NOT change output
2. Assert LDAC pin LOW (or send software LDAC cmd `0010`) to update all at once

### Read sequence

```
[START] [ADDR+W] [ACK] [CMD_BYTE] [ACK]
[Sr]    [ADDR+R] [ACK] [MSDB] [ACK] [LSDB] [NACK] [STOP]
```

Where `Sr` = repeated start. The read command codes mirror write: `0000` reads
input register, `0001` reads DAC register, etc.

---

## 7. Power-down modes

Sent via command `0100`. The MSDB encodes per-channel power-down selection and
mode bits.

| PD1 | PD0 | Mode |
|-----|-----|------|
| 0 | 0 | Normal operation (power on) |
| 0 | 1 | Power down — 1 kOhm to GND |
| 1 | 0 | Power down — 100 kOhm to GND |
| 1 | 1 | Power down — high-Z |

Channel select bits in MSDB[7:0] determine which of A–H are affected.

---

## 8. Reset behavior

| Condition | RSTSEL pin | Output resets to |
|-----------|-----------|-----------------|
| Power-on / CLR pulse | LOW | Zero scale (0 V) |
| Power-on / CLR pulse | HIGH | Mid scale (VREF/2) |
| Software reset (cmd `0111`) | — | Same as power-on for current RSTSEL state |

- TSSOP-16 package: RSTSEL is not bonded out — device always resets to **zero scale**
- QFN-24 package: RSTSEL is pin 9

Default register state after reset: all input registers and DAC registers = 0,
LDAC register = 0 (all channels respond to external LDAC pin).

---

## 9. Key electrical specs (quick reference)

| Parameter | Min | Typ | Max | Unit |
|-----------|-----|-----|-----|------|
| Supply voltage (AVDD) | 2.7 | — | 5.5 | V |
| Supply current (normal, all ch) | — | 0.13/ch | — | mA |
| INL (DAC7578) | — | +/-0.3 | +/-1 | LSB |
| DNL (DAC7578) | — | +/-0.1 | +/-0.25 | LSB |
| Offset error | — | 0.5 | +/-4 | mV |
| Gain error | — | +/-0.01 | +/-0.15 | % FSR |
| Settling time (1/4 to 3/4 scale) | — | 7 | — | us |
| Slew rate | — | 0.75 | — | V/us |
| Glitch energy (1 LSB) | — | 0.15 | — | nV-s |
| Output impedance (mid-scale) | — | 4.5 | — | Ohm |
| I2C clock (standard) | 0.1 | — | — | MHz |
| I2C clock (fast) | — | — | 0.4 | MHz |
| I2C clock (high-speed) | — | — | 3.4 | MHz |

---

## 10. Suggested driver API

```c
// Initialization
dac7578_err_t dac7578_init(dac7578_t *dev, i2c_port_t port, uint8_t addr);

// Set single channel (immediate update)
dac7578_err_t dac7578_set_channel(dac7578_t *dev, uint8_t channel, uint16_t code);

// Set single channel (deferred — must call update_all or pulse LDAC)
dac7578_err_t dac7578_write_input(dac7578_t *dev, uint8_t channel, uint16_t code);

// Update all DAC outputs from input registers (software LDAC)
dac7578_err_t dac7578_update_all(dac7578_t *dev);

// Power-down control
dac7578_err_t dac7578_power_down(dac7578_t *dev, uint8_t channel_mask,
                                  dac7578_pd_mode_t mode);

// Read back DAC register
dac7578_err_t dac7578_read_channel(dac7578_t *dev, uint8_t channel,
                                    uint16_t *code_out);

// Software reset
dac7578_err_t dac7578_reset(dac7578_t *dev);

// Write LDAC register (per-channel LDAC pin enable/disable)
dac7578_err_t dac7578_set_ldac_mask(dac7578_t *dev, uint8_t mask);

// Write clear code register
dac7578_err_t dac7578_set_clear_code(dac7578_t *dev, uint8_t code);
```

---

## TODOs — Extraction gaps that still need work

The automated extraction pipeline (Docling + local/external LLM) produced
useful results but left the following gaps. These should be addressed either
by improving the extraction code or by manual curation.

### Critical (blocks driver generation)

- [ ] **Register bit-field tables are garbled** (Tables 10–12 in the PDF).
      Docling rendered the bit-position diagrams as scattered text
      (`DB15 D7 DB8 D4 D0 D2 X D1 D3...`). The corrected layouts are provided
      in Section 3 above, but were reconstructed manually. The extractor should
      handle grid/cell-based table layouts better.

- [ ] **Transfer function equation missing from extracted text.** The formula
      `VOUT = (D / 2^n) * VREF` does not appear in `document.json`. Docling
      likely dropped or mangled the equation image/MathML. Added manually in
      Section 2 above.

- [ ] **I2C framing sequences (Tables 22–26) are header-only.** The extracted
      tables have column headers (`Start | Address | ACK | ...`) but no data
      rows — the frame diagrams were image-based, not real HTML/text tables.
      Corrected protocol descriptions are in Section 6 above.

### Important (affects completeness)

- [ ] **No figures classified as `register_map`.** Zero of the 221 extracted
      figures were tagged as register map diagrams by either the local or
      external LLM. The register layouts in this datasheet appear as formatted
      text tables, not standalone figures, so the figure pipeline missed them.
      Consider a post-processing pass that scans the markdown text for
      bit-field patterns.

- [ ] **DAC6578 register format (Table 11) entirely missing.** Docling
      replaced Table 11 with `<!-- image -->` — it was apparently rendered as
      an image in the PDF rather than text. The 10-bit format in Section 3
      above was reconstructed from known TI conventions.

- [ ] **Power-down register data byte layout not extracted.** The MSDB for the
      power-down command has per-channel select bits (DB7–DB0 for channels
      H–A) and mode bits (PD1=DB15, PD0=DB14 for 7578; PD1=DB14, PD0=DB13
      for 5578). This was partially mangled in extraction.

- [ ] **Clear code register values.** The clear code register accepts a 2-bit
      code (DB1:DB0) that sets the value outputs clear to: `00`=zero scale,
      `01`=mid scale, `10`=full scale, `11`=no operation. This was not
      surfaced in the extracted tables.

### Nice to have

- [ ] **Oscilloscope captures classified as `screenshot`.** 18 figures showing
      scope waveforms were classified as `screenshot` rather than
      `timing_diagram` or a dedicated `oscilloscope` type. The structured data
      is correct but the classification could be more specific.

- [ ] **Plot data point density.** The external LLM digitized characteristic
      curves using "envelope" approximations (6–7 points per series). For
      engineering use, denser sampling (50+ points) would be needed. Consider
      a specialized plot digitizer tool.

- [ ] **One misclassification.** fig_0084 (LDAC feed-through oscilloscope
      capture) was classified as `schematic` by the external LLM. The
      description text is correct, only the type tag is wrong.

- [ ] **Adafruit breakout board PDF not yet processed by external LLM.** The
      `adafruit-dac7578-8-x-channel-12-bit-i2c-dac` extraction exists in
      `out/` but was not included in the external LLM processing pass.
