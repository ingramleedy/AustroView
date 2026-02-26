# AustroView

Convert Diamond DA40NG Austro Engine AE300 data logs into CSV spreadsheets.

AustroView reads the `.ae3` hex dump files created by the AE300 Wizard software and produces per-session CSV files containing 16 engine parameters recorded at 1-second intervals. Each CSV represents one engine run (start to shutdown), making it easy to review engine performance in Excel, Google Sheets, or any data tool.

---

> **Disclaimer**
>
> This tool is an independent, community-developed project. It is **not endorsed, approved, or supported by Diamond Aircraft, Austro Engine, or any affiliated entity**. Use of this tool does not imply any relationship with or authorization from these companies.
>
> **Safety Notice**: The data produced by this tool is for **informational and educational purposes only**. It must not be used as the sole basis for any maintenance, airworthiness, or flight safety decisions. Always consult a qualified A&P mechanic or authorized maintenance organization for any engine-related concerns. All maintenance actions must comply with the applicable Type Certificate, manufacturer service documentation, and regulatory requirements (FAA, EASA, etc.).
>
> This software is provided "as-is" without warranty of any kind. The authors assume no liability for any use of this tool or the data it produces. **You are solely responsible for how you use this information.**

---

## What You Get

Each CSV file contains one engine session (engine start to shutdown) with these 16 parameters recorded every second:

| Parameter                 | Unit   | What It Tells You                                                 |
|---------------------------|--------|-------------------------------------------------------------------|
| Boost Pressure            | hPa    | Manifold pressure -- indicates engine power output                |
| Ambient Air Pressure      | hPa    | Outside atmospheric pressure (altitude indicator)                 |
| Propeller Speed           | rpm    | Propeller RPM                                                     |
| Engine Oil Pressure       | hPa    | Oil system pressure                                               |
| Rail Pressure             | bar    | Fuel rail (injection system) pressure                             |
| Power Lever Position      | %      | Throttle position as a percentage                                 |
| Coolant Temperature       | deg C  | Engine coolant temperature                                        |
| Intake Air Temperature    | deg C  | Air temperature entering the engine                               |
| Battery Voltage           | V      | Electrical system voltage                                         |
| Fuel Pressure             | hPa    | Fuel supply pressure                                              |
| Gearbox Oil Temperature   | deg C  | Reduction gearbox oil temperature                                 |
| Engine Oil Temperature    | deg C  | Engine oil temperature                                            |
| Prop Actuator Duty Cycle  | %      | Propeller governor actuator duty cycle                            |
| Engine Status             | bin    | ECU status flags (binary)                                         |
| Engine Oil Level          | mm     | Oil level sensor reading                                          |
| Engine Load               | %      | Engine load percentage                                            |

## Quick Start

### Requirements

- Python 3.8 or later
- One or more `.ae3` hex dump files from the AE300 Wizard software

### Install

```bash
pip install pycryptodome
```

Or using the included requirements file:

```bash
pip install -r requirements.txt
```

### Run

Process a single file:

```bash
python austroview.py MyHexDump.ae3
```

Process all `.ae3` files in a folder:

```bash
python austroview.py Data/
```

CSV files are written to `./output/` by default. Change this with `--output-dir`:

```bash
python austroview.py -o results/ MyHexDump.ae3
```

### Quick Summary

To get a fast overview of what's in a file without generating CSVs:

```bash
python austroview.py --summary MyHexDump.ae3
```

This prints a session table showing each engine run with start/end times, duration, record count, max RPM, and max coolant temperature:

```
AustroView Summary: DataLog_20240819.ae3
===============================================================================================
   #   Start               End                  Duration  Records  Max RPM  Max Coolant
 ---   ------------------- ------------------- ---------  -------  -------  -----------
   1   2024-07-26 17:06    2024-07-26 17:32      0:25:25     1525     2333       84.2 C
   2   2024-07-29 14:32    2024-07-26 17:31      1:33:50     5630     2333       84.2 C
   3   2024-07-29 14:32    2024-07-29 16:23      1:25:34     5134     2323       84.0 C
   ...
===============================================================================================
 15 sessions | 12:30:06 total engine time | Latest: 2024-08-19
```

### All Options

```
python austroview.py [OPTIONS] FILE_OR_DIR [FILE_OR_DIR ...]

Options:
  --summary, -s      Print session summary only (no CSV files)
  --output-dir, -o   Output directory (default: ./output/)
  --keep-xml         Also save the intermediate decrypted XML
  -h, --help         Show help message with full disclaimer
```

## How to Collect .ae3 Files

The `.ae3` hex dump files are created using the **AE300 Wizard** software provided by Austro Engine. Here's the general process:

1. **Connect** the USB diagnostic dongle to the ECU diagnostic port on the aircraft (located in the engine compartment)
2. **Launch** the AE300 Wizard software on a Windows laptop
3. **Read Hex Dump** -- use the "Read HexDump" function to download the data logger contents from the ECU's flash memory
4. **Save** -- the Wizard saves the file as a `.ae3` file (e.g., `DataLog_20240819.ae3`)

The hex dump contains all recorded engine sessions stored in the ECU's flash memory. Depending on flight activity, this can include dozens of sessions spanning weeks or months.

> **Note**: The AE300 Wizard software is typically available through Diamond Aircraft service centers or Austro Engine authorized maintenance organizations. Access to the ECU diagnostic port may require cowling removal.

## Understanding the Output

### Sessions

Each `.ae3` hex dump file contains multiple **sessions**. A session is one continuous engine run -- from engine start to engine shutdown. The ECU records 16 parameters once per second throughout each session.

Sessions are numbered starting from 00, with lower numbers being older recordings and higher numbers being more recent. The ECU uses a ring buffer, so very old sessions are eventually overwritten by new ones.

### CSV File Naming

Output files follow this pattern:

```
DataLog_20240819_session07_20240818_174831.csv
|                |         |
|                |         +-- Session start: 2024-08-18 at 17:48:31 UTC
|                +------------ Session number (00 = oldest)
+----------------------------- Original file name
```

### Timestamps

- All timestamps are in **UTC** (the ECU records in UTC)
- The `Timestamp` column in each CSV increments by 1 second per row
- Session start/end times come from the ECU's internal clock

### Sample CSV Output

```csv
Timestamp,Boost Pressure [hPa],Ambient Air Pressure [hPa],Propeller Speed [rpm],Engine Oil Pressure [hPa],Rail Pressure [bar],Power Lever Position [%],Coolant Temperature [deg C],Intake Air Temperature [deg C],Battery Voltage [V],Fuel Pressure [hPa],Gearbox Oil Temperature [deg C],Engine Oil Temperature [deg C],Prop Actuator Duty Cycle [%],Engine Status [bin],Engine Oil Level [mm],Engine Load [%]
2024-08-18 17:48:31,1009,1018,0,0,10.9,0.0,32.3,28.4,24.7,4383,32.2,-273.1,0.0,18,0,0.0
2024-08-18 17:48:32,1009,1018,0,0,10.9,0.0,32.3,28.4,24.5,4322,32.2,-273.1,0.0,18,0,0.0
2024-08-18 17:48:33,1009,1018,0,0,10.9,0.0,32.3,28.4,24.7,4334,32.2,-273.1,0.0,18,0,0.0
```

> **Note**: A value of `-273.1` for a temperature channel indicates the sensor was not yet reporting valid data (this clears up within seconds of engine start as the ECU initializes).

## Example

The `examples/` folder contains a real `.ae3` file and its processed output so you can see what to expect:

- `examples/DataLog_20240819.ae3` -- the original hex dump file (15 sessions)
- `examples/output/` -- the 15 CSV files produced by AustroView
- `examples/summary.txt` -- the `--summary` output

You can browse these on GitHub without installing anything, or run the tool yourself:

```bash
python austroview.py examples/DataLog_20240819.ae3
```

## FAQ

**What aircraft does this work with?**
The Diamond DA40NG equipped with the Austro Engine AE300 diesel engine. Other Diamond aircraft using the AE300 (DA42NG, DA62) likely use the same data format but have not been tested.

**What is the AE300?**
The Austro Engine AE300 is a 168 HP turbocharged diesel (Jet-A) aircraft engine based on the Mercedes-Benz OM640 automotive engine. It uses a dual-ECU (FADEC) system.

**Do I need the AE300 Wizard software?**
Yes, to download the hex dump from the aircraft's ECU. AustroView processes the resulting `.ae3` files on your own computer.

**How much data does one file contain?**
A single hex dump can contain weeks or months of flight data depending on flight frequency. The ECU's flash memory holds approximately 120+ sessions before older data is overwritten.

**Are both ECUs recorded?**
The AE300 has dual ECUs (A and B). Each ECU records its own data log independently. You would get separate `.ae3` files for each ECU.

**What do the Engine Status values mean?**
The Engine Status field contains binary status flags from the ECU. Common values: `18` = normal idle/ground, higher values indicate various engine states. These are internal ECU status codes.

**Can I use this data for maintenance decisions?**
This data can help you and your mechanic understand engine trends and behavior. However, **all maintenance decisions must be made by qualified personnel** using approved procedures and documentation. See the disclaimer at the top of this page.

## License

MIT License. See source code for details.
