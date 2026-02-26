# AustroView - Project Memory

## What This Project Does

Converts Diamond DA40NG Austro Engine AE300 `.ae3` hex dump files into per-session CSV spreadsheets with 16 engine parameters at 1 Hz.

**Pipeline**: `.ae3` file -> decrypt -> parse XML -> extract sessions -> CSV

## Key Files

- `austroview.py` - Single unified script: decrypt, parse, and convert to CSV
- `requirements.txt` - Single dependency: `pycryptodome`
- `examples/` - Demo `.ae3` file with pre-generated CSV output

## Usage

```bash
python austroview.py MyHexDump.ae3           # generate CSVs
python austroview.py --summary MyHexDump.ae3 # quick overview table
python austroview.py -o results/ Data/       # process all files in folder
```

## Architecture

- Decryption: Encrypted `.ae3` files are decrypted and decompressed (constants are base64-encoded in source)
- Parsing: Stream-parses XML hex dump for sector data (sectors 16-139 = data logger)
- Sessions: Detected by scanning for boundary markers in the concatenated payload
- Conversion: Raw int16 values -> physical units via coefficient + offset

## Related Private Repository

Detailed internal notes and reference materials are in a separate private repository. This public repo contains only the tool and user-facing documentation.
