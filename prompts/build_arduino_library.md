Given this extracted datasheet folder (`OUT_PDF_DIR`), generate a minimal but
correct Arduino I2C driver library for the chip family using built-in Wire
only.

Optional: if `ANALYSIS_PDF_DIR` is provided (for example
`analysis/<pdf_stem>`), use it to improve correctness/coverage where external
figure analysis exists.

  - library.properties
  - one basic example sketch

  Prioritize correctness of:
  - I2C addressing (all address pin combinations)

  If extracted data is ambiguous, call it out and use safe defaults, but always allow explicit user-set I2C address override.

  After coding, run an Arduino compile check (arduino-cli) and report:
  - what you implemented
  - the address mapping you used
  - any ambiguities or assumptions.

  The library should be named `DACx578` and should be placed in the `arduino/DACx578` directory.
