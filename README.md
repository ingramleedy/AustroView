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

The `.ae3` hex dump files are created using the **AE300 Wizard** software provided by Austro Engine (document E4.08.09, Rev 14). Here's the process:

### What You Need

- **AE300 Wizard software** -- available from the [Diamond Aircraft Partners Portal](https://partners.diamondaircraft.com/s/files) under Engine Documentation & Software > AE300-Wizard
- **USB/CAN diagnostic dongle** -- the PEAK PCAN-USB adapter included with the Wizard package. This also acts as a license dongle (Maintenance or Qualified Maintenance mode)
- **Windows PC** -- Windows 7 SP1 / 10 / 11, with .NET Framework 4.0
- **Ground power recommended** -- full data logger downloads can take up to 20 minutes per ECU and will drain the aircraft battery

### Download Steps (AE300 Wizard Manual, Section 8.2.3)

1. **Set up the aircraft** -- connect ground power, disable fuel pumps and alternator(s), engine must be stopped
2. **Connect** the USB/CAN dongle to the ECU diagnostic port (9-pin CAN connector in the engine compartment) and to your laptop's USB port
3. **Launch** AE300 Wizard and press **Connect ECU**
4. **Select the "Engine Logs" tab** and click **Save DataLog**
5. **Choose a filename** -- the Wizard suggests `DataLog_YYYYMMDD.ae3`
6. **Save** -- the file is stored in `My Documents\Austro Engine\AE300-Wizard\HexDump`

For a quick download of just the most recent flights, use **Save DataLog Fraction** (Section 8.2.4) and specify the number of recent flight hours.

> **Note**: The AE300 Wizard and dongle are available through Diamond Aircraft service centers or Austro Engine authorized maintenance organizations. The software can also be installed without a dongle for **offline analysis** of previously downloaded files (Section 4.5, 7.1).

The hex dump contains all recorded engine sessions stored in the ECU's flash memory. The ECU stores approximately **80-90 hours** of flight time in a ring buffer, always keeping the most recent data. Depending on flight activity, this can include dozens of sessions spanning weeks or months.

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

## LiveView Recording

### What is LiveView?

The AE300 Wizard's **LiveView** feature lets you monitor and record ECU data in real time while connected to the aircraft on the ground. Unlike the data logger (which records 16 channels at 1 Hz automatically during every engine run), LiveView gives you access to up to **170 signals** covering nearly every aspect of the engine's operation -- from individual cylinder injection timing to turbocharger control, propeller governor internals, and more.

LiveView recordings are saved as `LiveView_YYYYMMDD.ae3` files using the same encrypted format as hex dumps. AustroView does not yet parse LiveView files, but support is planned for a future version.

### How to Record a LiveView Session

**Requirements**: Same setup as downloading hex dumps -- PCAN-USB dongle connected to the ECU diagnostic port, AE300 Wizard running on a Windows PC. Engine can be running or stopped.

**Steps** (AE300 Wizard Manual, Section 8.3):

1. **Connect** the PCAN-USB dongle and launch AE300 Wizard
2. **Press Connect ECU** to establish communication
3. **Select the "LiveView" tab**
4. **Choose your signals** -- click signal names from the list to add them to the recording
5. **Set the sample interval** -- from 0.1 seconds (10 Hz, fastest) to 3 seconds
6. **Click Record** to start capturing data
7. **Click Stop** when finished -- the file is saved as `LiveView_YYYYMMDD.ae3`

### Standard vs Expert Mode

| Mode     | Signals Available | Access Level |
|----------|------------------:|--------------|
| Standard | Up to 52 per ECU  | Maintenance mode (standard dongle) |
| Expert   | Up to 158 per ECU | Qualified Maintenance mode |

Expert mode unlocks the full signal set including internal governor states, injection details, and diagnostic flags. Standard mode covers the most commonly needed parameters.

> **Important**: LiveView is for **ground testing only**. The AE300 Wizard Manual states that LiveView must not be used during flight (Section 8.3).

### Dual-ECU Recording

The AE300 has dual ECUs (A and B). LiveView can record signals from both ECUs simultaneously. Each ECU's data is stored separately in the recording file.

### Complete Signal Reference (170 Signals)

Below is the full list of signals available through LiveView, organized by category. The **Unit** column shows the physical unit after conversion from the ECU's raw values.

<details>
<summary><strong>Pressures & Fluid Levels</strong> (13 signals)</summary>

| Signal | Unit |
|--------|------|
| Atmospheric (barometric) pressure | hPa |
| Atmospheric pressure, linearized | hPa |
| Atmospheric pressure, raw signal | mV |
| Boost pressure, filtered | hPa |
| Boost pressure, phys value | hPa |
| Boost pressure, raw sensor value | mV |
| Engine oil pressure | hPa |
| Engine oil level | mm |
| Engine oil level, raw sensor value | mm |
| Fuel pressure | hPa |
| Fuel pressure, raw sensor value | mV |
| Rail pressure, peak value (last 10 ms) | bar |
| Rail pressure, sensor raw voltage | mV |

</details>

<details>
<summary><strong>Temperatures</strong> (16 signals)</summary>

| Signal | Unit |
|--------|------|
| Coolant temperature | deg C |
| Coolant temperature, rate of change | deg C/s |
| Coolant temperature, raw sensor value | mV |
| ECU temperature, with default | deg C |
| ECU temperature, without default | deg C |
| ECU temperature, raw sensor value | mV |
| Engine oil temperature | deg C |
| Engine oil temperature, raw sensor value | deg C |
| Fuel temperature | deg C |
| Fuel temperature, raw sensor value | mV |
| Fuel temperature, with substitute reaction | deg C |
| Gearbox oil temperature | deg C |
| Gearbox oil temperature, raw sensor value | mV |
| Intake air temperature | deg C |
| Intake air temperature, rate of change | deg C/s |
| Intake air temperature, raw sensor value | mV |

</details>

<details>
<summary><strong>Engine Speed & Position</strong> (12 signals)</summary>

| Signal | Unit |
|--------|------|
| Camshaft, current angular position | deg CrS |
| Camshaft-Crankshaft angular position difference | deg CrS |
| Crankshaft, current increment speed | rpm |
| Crankshaft, average speed | rpm |
| Crankshaft, current segment speed | rpm |
| Crankshaft, current angular position | deg CrS |
| Engine speed, average | rpm |
| Engine speed, average acceleration | rpm/s |
| Engine speed, current | rpm |
| Engine speed, phase wheel | rpm |
| Propeller speed | rpm |
| Propeller speed, set point | rpm |

</details>

<details>
<summary><strong>Power, Torque & Load</strong> (11 signals)</summary>

| Signal | Unit |
|--------|------|
| Engine power, calculated | W |
| Engine power, ratio to max power | % |
| Fuel consumption | l/h |
| Starting system, starting torque | Nm |
| Torque desired, after limitation | Nm |
| Torque, actual gearbox input | Nm |
| Torque, desired for minimum injection qty | Nm |
| Torque, inner torque desired value | Nm |
| Torque, inner torque set value | Nm |
| Torque, limitation | Nm |
| Torque, set value after limitation | Nm |

</details>

<details>
<summary><strong>Fuel Injection</strong> (8 signals)</summary>

| Signal | Unit |
|--------|------|
| Energizing time, average per cylinder | us |
| Injection characteristic, actual value | bin |
| Injection mass, engine speed limitation | mm3/cyc |
| Injection mass, max allowed | mm3/hub |
| Injection mass, smoke limitation | mm3/cyc |
| Injection, current quantity | mm3/cyc |
| Injection, Pilot 1 release state | bin |
| Injection, Pilot 2 release state | bin |

</details>

<details>
<summary><strong>Metering Unit (Fuel)</strong> (5 signals)</summary>

| Signal | Unit |
|--------|------|
| Metering unit, actual current | mA |
| Metering unit, current governor deviation | mA |
| Metering unit, duty cycle | % |
| Metering unit, duty cycle set value | % |
| Metering unit, electrical current set point | mA |

</details>

<details>
<summary><strong>Boost Pressure Control</strong> (10 signals)</summary>

| Signal | Unit |
|--------|------|
| Boost pressure actuator, duty cycle | % |
| Boost pressure, governor deviation | hPa |
| Boost pressure, governor output | % |
| Boost pressure, precontrol value | % |
| Boost pressure, regulation switch | bin |
| Boost pressure, set point | hPa |
| Boost pressure, set point without limits | hPa |
| Boost pressure, temperature corrected | hPa |
| BPA, coordinator output | % |
| BPA, correction value | % |

</details>

<details>
<summary><strong>Propeller Governor</strong> (6 signals)</summary>

| Signal | Unit |
|--------|------|
| Propeller gov. actuator, duty cycle | % |
| Propeller gov. actuator, endstop status | - |
| Propeller gov. actuator, endstop voltage | mV |
| Propeller gov. actuator, filtered voltage | mV |
| Propeller gov. actuator, raw voltage | mV |
| Propeller governor, current speed deviation | rpm |

</details>

<details>
<summary><strong>Rail Pressure Control</strong> (12 signals)</summary>

| Signal | Unit |
|--------|------|
| PCR, current working sphere | - |
| PCR, governor shut off state | - |
| PCV, duty cycle | % |
| PCV, duty cycle set point | % |
| PCV, electric current governor deviation | mA |
| PCV, electric current set point | mA |
| PCV, filtered electric current | mA |
| PCV, filtered electric current set point | mA |
| Rail pressure, governor deviation | bar |
| Rail pressure, governor state | - |
| Rail pressure, governor type | bin |
| Rail pressure, set point | bar |

</details>

<details>
<summary><strong>Idle Governor</strong> (4 signals)</summary>

| Signal | Unit |
|--------|------|
| Idle governor, limited output | Nm |
| Idle governor, set point speed | rpm |
| Idle governor, state | - |
| Idle governor, torque demanded | Nm |

</details>

<details>
<summary><strong>Power Lever</strong> (5 signals)</summary>

| Signal | Unit |
|--------|------|
| Power lever position | % |
| Power lever position, sensor 1 | % |
| Power lever position, sensor 2 | % |
| Power lever sensor 1, raw value | mV |
| Power lever sensor 2, raw value | mV |

</details>

<details>
<summary><strong>Electrical System</strong> (8 signals)</summary>

| Signal | Unit |
|--------|------|
| Actuator supply voltage, raw | mV |
| Battery voltage | V |
| Battery voltage, raw ADC value | mV |
| Battery voltage correction factor | - |
| Voter relay, highside raw voltage | mV |
| Voter relay, linearized differential voltage | mV |
| Voter relay, lowside raw voltage | mV |
| Sensor supply error flags | bin |

</details>

<details>
<summary><strong>Engine State & Starting</strong> (12 signals)</summary>

| Signal | Unit |
|--------|------|
| Afterrun, EEPROM storage status | - |
| Afterrun, internal state | - |
| Engine master switch, raw signal value | - |
| Engine master switch, state | - |
| Engine state, combined flags | bin |
| Engine, current state | bin |
| Engine, overrun state | - |
| Engine position, synchronisation state | - |
| Starting system, status | - |
| Squat switch (WoW), raw signal value | - |
| Squat switch (WoW), state | bin |
| Power stage diag status | bin |

</details>

<details>
<summary><strong>Self-Test</strong> (9 signals)</summary>

| Signal | Unit |
|--------|------|
| Selftest switch, raw signal value | - |
| Selftest switch, state | - |
| Selftest, ECU test internal state | - |
| Selftest, internal state | - |
| Selftest, propeller self test error flags | bin |
| Selftest, propeller test phase | - |
| Selftest, release condition flags | bin |
| Selftest, timeout flags | bin |
| Selftest, torque demanded | Nm |

</details>

<details>
<summary><strong>ECU Information & Run Times</strong> (13 signals)</summary>

| Signal | Unit |
|--------|------|
| ECU coding ID | - |
| ECU run time, accumulated engine control | s |
| ECU run time, accumulated power-on | s |
| ECU run time, since engine master on | s |
| ECU state (active/passive) | bin |
| ECU, proposed active ECU | - |
| Engine run time, accumulated | s |
| Data logger, release status | bin |
| Errors of ECU | - |
| Errors of twin ECU | - |
| Fault Code Memory, number of entries | - |
| Pre-Supply pump, output signal | - |
| Source of last reset | - |

</details>

<details>
<summary><strong>Real-Time Clock</strong> (9 signals)</summary>

| Signal | Unit |
|--------|------|
| RTC date, as YYMMDD | - |
| RTC time, as HHMMSS | - |
| RTC error flags (CTRL2) | bin |
| RTC, current year | - |
| RTC, current month | - |
| RTC, current day | - |
| RTC, current hours | - |
| RTC, current minute | - |
| RTC, current second | - |

</details>

<details>
<summary><strong>CAN Bus & Monitoring</strong> (5 signals)</summary>

| Signal | Unit |
|--------|------|
| CAN monitoring, fade out state | bin |
| CAN monitoring, state | bin |
| Caution lamp, status | bin |
| Main relay monitoring, current state | bin |
| Memory monitoring, status | bin |

</details>

<details>
<summary><strong>CAN Bus Mirror Signals</strong> (11 signals)</summary>

These signals are received from the other ECU (or cockpit displays) via the CAN bus. They mirror the primary sensor readings as seen by the aircraft's avionics:

| Signal | Unit |
|--------|------|
| CAN, battery voltage | V |
| CAN, caution lamp status | bin |
| CAN, coolant temperature | deg C |
| CAN, ECU active/passive | bin |
| CAN, engine performance | % |
| CAN, fuel flow | l/h |
| CAN, fuel pressure warning | bin |
| CAN, gearbox oil temperature | deg C |
| CAN, oil pressure | hPa |
| CAN, oil temperature | deg C |
| CAN, propeller speed | rpm |

</details>

<details>
<summary><strong>Other</strong> (1 signal)</summary>

| Signal | Unit |
|--------|------|
| AUX signal | - |

</details>

## FAQ

**What aircraft does this work with?**
The Diamond DA40NG equipped with the Austro Engine AE300 diesel engine. Other Diamond aircraft using the AE300 (DA42NG, DA62) likely use the same data format but have not been tested.

**What is the AE300?**
The Austro Engine AE300 is a 168 HP turbocharged diesel (Jet-A) aircraft engine based on the Mercedes-Benz OM640 automotive engine. It uses a dual-ECU (FADEC) system.

**Do I need the AE300 Wizard software?**
Yes, to download the hex dump from the aircraft's ECU. AustroView processes the resulting `.ae3` files on your own computer.

**How much data does one file contain?**
A single hex dump can contain weeks or months of flight data depending on flight frequency. The ECU's flash memory (RecMng-Flash) stores approximately **80-90 hours** of engine-on time in a ring buffer, always keeping the most recent data.

**Are both ECUs recorded?**
The AE300 has dual ECUs (A and B). Each ECU records its own data log independently. You would get separate `.ae3` files for each ECU.

**What do the Engine Status values mean?**
The Engine Status field is a combined bit mask (shown as a decimal number in the CSV). Each bit indicates a specific ECU state (from the AE300 Wizard Manual, Appendix 12.2.1):

| Bit | Value | Meaning |
|-----|-------|---------|
| 0   | 1     | Engine in "afterrun" state |
| 1   | 2     | Engine in "start" state |
| 2   | 4     | Engine in "normal" running state |
| 3   | 8     | Rail pressure governing via metering unit |
| 4   | 16    | Squat switch depressed (weight on wheels = aircraft on ground) |
| 5   | 32    | Proposed active ECU (0 = ECU-A, 1 = ECU-B) |
| 6   | 64    | Voter decision (0 = ECU-A, 1 = ECU-B) |
| 7   | 128   | ECU is passive (1) or active (0) |

Common values: `18` (decimal) = bits 1+4 = engine starting + on ground. `28` (decimal) = bits 2+3+4 = normal running + rail pressure governing + on ground. `12` = bits 2+3 = normal running + rail pressure governing (airborne -- squat switch released).

**What about the LiveView recordings?**
The AE300 Wizard also has a **LiveView** feature (Section 8.3) that can record up to 52 signals per ECU in standard mode or 158 signals in expert mode, at intervals as fast as 0.1 seconds. These recordings are saved as `LiveView_YYYYMMDD.ae3` files. AustroView does not currently parse LiveView files, but support could be added in a future version since they use the same file format. Note that LiveView requires a live connection to the ECU and is for **ground testing only** -- the Wizard manual states that using it during flight is not permitted.

**Can I use this data for maintenance decisions?**
This data can help you and your mechanic understand engine trends and behavior. However, **all maintenance decisions must be made by qualified personnel** using approved procedures and documentation. See the disclaimer at the top of this page.

**How do I interpret barometric pressure as altitude?**
The Ambient Air Pressure channel (measured inside the EECU enclosure) can be roughly converted to pressure altitude using the ISA standard atmosphere. For example: 1013 hPa = sea level, 977 hPa ~ 1000 ft, 915 hPa ~ 2800 ft. A drop in barometric pressure during a session indicates the aircraft is climbing.

**What does a value of -273.1 mean for temperature channels?**
This is the raw sensor reading before the ECU has initialized -- it corresponds to 0 on the raw scale with the temperature offset applied (0 * 0.1 - 273.14 = -273.1). It clears up within seconds of engine start as the sensors come online.

## References

- **AE300 Wizard Software & Manual** -- [Diamond Aircraft Partners Portal](https://partners.diamondaircraft.com/s/files) > Engine Documentation & Software > AE300-Wizard
- **AE300 Wizard User Guide** -- Document E4.08.09, Revision 14 (2023-Jul-31), Austro Engine GmbH

## License

MIT License. See source code for details.
