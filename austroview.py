#!/usr/bin/env python3
"""AustroView - Convert Diamond DA40NG Austro Engine AE300 data logs to CSV.

Reads .ae3 hex dump files from the AE300 Wizard software and produces
per-session CSV files with 16 engine parameters at 1 Hz resolution.

Usage:
    python austroview.py MyHexDump.ae3
    python austroview.py Data/                  # process all .ae3 in folder
    python austroview.py --summary MyHexDump.ae3  # quick session overview
"""

import argparse
import csv
import gzip
import hashlib
import struct
import sys
import xml.dom.minidom
import xml.etree.ElementTree as ET
from base64 import b64decode
from dataclasses import dataclass
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Optional

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# ------------------------------------------------------------------------------
# AE300 file format parameters
# ------------------------------------------------------------------------------
_P = b64decode("RTRXdjExMDBQVw==")
_S = b64decode("EBESExQVFhcYGQoLDA==")
_V = b64decode("EBESExQVFhcYGQoLDA0ODw==")

DISCLAIMER = """\
DISCLAIMER: This tool is an independent, community-developed project. It is NOT
endorsed, approved, or supported by Diamond Aircraft, Austro Engine, or any
affiliated entity. The data produced is for informational and educational
purposes only. It must not be used as the sole basis for any maintenance,
airworthiness, or flight safety decisions. Always consult a qualified A&P
mechanic or authorized maintenance organization for engine-related concerns.
This software is provided "as-is" without warranty of any kind.\
"""


# ------------------------------------------------------------------------------
# Signal conversion table
# Each entry: (coefficient, offset, unit)
# ------------------------------------------------------------------------------
SIG_CLASS = [
    (10.0,         0.0,      "rpm/s"),      # 0
    (0.01955034,   0.0,      "V"),          # 1
    (9.424778,     0.0,      "W"),          # 2
    (0.0001220703, 0.0,      "-"),          # 3
    (0.1,          0.0,      "Nm"),         # 4
    (1.0,          0.0,      "hPa"),        # 5
    (1.0,          0.0,      "hPa"),        # 6
    (0.0234375,    0.0,      "deg CrS"),    # 7
    (0.1,         -273.14,   "deg C"),      # 8
    (1.0,          0.0,      "deg C/s"),    # 9
    (0.01,         0.0,      "mm3/cyc"),    # 10
    (0.1,          0.0,      "bar"),        # 11
    (0.01,         0.0,      "%"),          # 12
    (0.1,          0.0,      "mm"),         # 13
    (0.1,          0.0,      "Nm"),         # 14
    (0.01220703,   0.0,      "%"),          # 15
    (0.01,         0.0,      "mm3/hub"),    # 16
    (1.0,          0.0,      "mA"),         # 17
    (0.01,         0.0,      "l/h"),        # 18
    (4.887586,     0.0,      "mV"),         # 19
    (1.0,          0.0,      "-"),          # 20
    (1.0,          0.0,      "us"),         # 21
    (1.0,          0.0,      "s"),          # 22
    (1.0,          0.0,      "rpm"),        # 23
    (0.0234375,    0.0,      "deg CrS"),    # 24
    (1.0,          0.0,      "bin"),        # 25
]

# ------------------------------------------------------------------------------
# Data log channel definitions
# Channel code -> (name, signal_class_index, y_min, y_max)
# ------------------------------------------------------------------------------
CHANNELS = {
    800: ("Boost Pressure",           6,  0,    3500),
    801: ("Ambient Air Pressure",     6,  400,  1200),
    802: ("Propeller Speed",          23, 0,    2500),
    803: ("Engine Oil Pressure",      6,  0,    8000),
    804: ("Rail Pressure",            11, 0,    2000),
    805: ("Power Lever Position",     15, 0,    100),
    806: ("Coolant Temperature",      8,  -40,  160),
    807: ("Intake Air Temperature",   8,  -40,  160),
    808: ("Battery Voltage",          1,  16,   36),
    809: ("Fuel Pressure",            6,  0,    8000),
    810: ("Gearbox Oil Temperature",  8,  -40,  160),
    811: ("Engine Oil Temperature",   8,  -40,  160),
    812: ("Prop Actuator Duty Cycle", 12, -100, 100),
    813: ("Engine Status",            25, 0,    256),
    814: ("Engine Oil Level",         13, 0,    100),
    815: ("Engine Load",              15, 0,    100),
}

# Default channel configuration (16 channels: 800-815)
_DEFAULT_CONFIG = bytes([
    50, 3, 33, 50, 35, 35, 50, 67, 37, 50, 99, 39,
    50, 131, 41, 50, 163, 43, 50, 195, 45, 50, 227, 47
])

SECTOR_PAYLOAD_SIZE = 65528


# ==============================================================================
# Decryption
# ==============================================================================
def _derive_key(password: bytes, salt: bytes, iterations: int = 100, keylen: int = 24) -> bytes:
    """Derive the decryption key from password and salt."""
    base = hashlib.sha1(password + salt).digest()
    for _ in range(iterations - 2):
        base = hashlib.sha1(base).digest()
    result = bytearray(hashlib.sha1(base).digest())
    counter = 1
    while len(result) < keylen:
        result.extend(hashlib.sha1(str(counter).encode("ascii") + base).digest())
        counter += 1
    return bytes(result[:keylen])


def decrypt_file(filepath: str) -> str:
    """Decrypt and decompress an .ae3 file, returning the XML content."""
    key = _derive_key(_P, _S)
    with open(filepath, "rb") as f:
        encrypted = f.read()
    cipher = AES.new(key, AES.MODE_CBC, _V)
    decrypted = unpad(cipher.decrypt(encrypted), AES.block_size)
    decompressed = gzip.decompress(decrypted)
    return decompressed.decode("utf-8-sig")


# ==============================================================================
# BCD timestamp helpers
# ==============================================================================
def _bcd(b: int) -> int:
    return (b >> 4) * 10 + (b & 0x0F)


def _parse_bcd_timestamp(data: list[int], offset: int) -> Optional[datetime]:
    """Parse 6 BCD bytes into a datetime (year, month, day, hour, min, sec)."""
    yr  = _bcd(data[offset])
    mon = _bcd(data[offset + 1])
    day = _bcd(data[offset + 2])
    hr  = _bcd(data[offset + 3])
    mn  = _bcd(data[offset + 4])
    sec = _bcd(data[offset + 5])
    if 0 <= yr < 120 and 1 <= mon <= 12 and 1 <= day <= 31 and 0 <= hr < 24 and 0 <= mn < 60 and 0 <= sec < 60:
        return datetime(2000 + yr, mon, day, hr, mn, sec)
    return None


# ==============================================================================
# Channel configuration parsing
# ==============================================================================
def _parse_channel_config(config_bytes: bytes) -> list[int]:
    """Parse 24 config bytes into 16 channel numbers via nibble extraction."""
    nibbles = []
    for b in config_bytes:
        nibbles.append((b >> 4) & 0x0F)
        nibbles.append(b & 0x0F)
    channels = []
    for k in range(0, len(nibbles), 3):
        ch = (nibbles[k] << 8) | ((nibbles[k + 1] & 0x0F) << 4) | (nibbles[k + 2] & 0x0F)
        channels.append(ch)
    return channels


# ==============================================================================
# Sector handling
# ==============================================================================
def _decode_sector_type(raw: list[int]) -> str:
    code = raw[-4:]
    if code == [0xAA, 0xAA, 0xAA, 0xAA]:
        return "active"
    if code == [0xA8, 0xA8, 0xA8, 0xA8]:
        return "fullNotLocked"
    if code == [0x00, 0x00, 0x00, 0x00]:
        return "locked"
    if code == [0xFE, 0xFE, 0xFE, 0xFE]:
        return "erased"
    if code == [0xFF, 0xFF, 0xFF, 0xFF]:
        return "notModified"
    return "unknown"


def _extract_payload(raw: list[int]) -> list[int]:
    """Extract payload: skip first 2 bytes, remove last 8 bytes."""
    return raw[2:-8]


# ==============================================================================
# Session detection and data extraction
# ==============================================================================
@dataclass
class Session:
    lead_in_ix: int
    lead_out_ix: int
    lead_in_time: Optional[datetime]
    lead_out_time: Optional[datetime]
    channels: list[int]
    data: list[list[float]]
    timestamps: list[datetime]


def _extract_records(payload, data_start, data_end, channels):
    """Extract data records between data_start and data_end."""
    record_size = len(channels) * 2
    records = []
    pos = data_start
    while pos + record_size <= data_end:
        start_sector = pos // SECTOR_PAYLOAD_SIZE
        end_sector = (pos + record_size - 1) // SECTOR_PAYLOAD_SIZE
        if start_sector != end_sector:
            pos = end_sector * SECTOR_PAYLOAD_SIZE
            continue
        record = []
        for ch_idx in range(len(channels)):
            off = pos + ch_idx * 2
            raw_val = (payload[off] << 8) | payload[off + 1]
            if ch_idx == 13:  # Engine Status - unsigned
                record.append(float(raw_val & 0xFFFF))
            else:
                if raw_val >= 0x8000:
                    raw_val -= 0x10000
                record.append(float(raw_val))
        records.append(record)
        pos += record_size
    return records


def _find_sessions(payload: list[int]) -> list[Session]:
    """Find recording sessions by scanning for boundary markers.

    Each engine start/stop creates a boundary: a 32-byte lead-out followed
    by a 32-byte lead-in with BCD timestamps and channel configuration.
    Sessions are the data regions between consecutive boundaries.
    """
    boundaries = []
    n = len(payload) - 1
    zero_count = 0
    while n >= 32:
        if payload[n] == 0:
            zero_count += 1
            if zero_count == 25:
                zero_count = 0
                boundaries.append(n)
        else:
            zero_count = 0
        n -= 1

    if not boundaries:
        return []

    boundaries.reverse()

    sessions = []
    num_boundaries = len(boundaries)

    for i in range(num_boundaries + 1):
        if i == 0:
            data_start = 0
            data_end = boundaries[0]
            li_block_start = None
            lo_block_start = boundaries[0]
        elif i == num_boundaries:
            data_start = boundaries[i - 1] + 64
            data_end = len(payload)
            li_block_start = boundaries[i - 1] + 32
            lo_block_start = None
        else:
            data_start = boundaries[i - 1] + 64
            data_end = boundaries[i]
            li_block_start = boundaries[i - 1] + 32
            lo_block_start = boundaries[i]

        # Parse lead-in: [6 BCD timestamp][24 config][1 checksum][1 spare]
        li_time = None
        channels = _parse_channel_config(_DEFAULT_CONFIG)
        if li_block_start is not None and li_block_start + 32 <= len(payload):
            li_chk = sum(payload[li_block_start:li_block_start + 32]) & 0xFF
            li_time = _parse_bcd_timestamp(payload, li_block_start)
            config_data = bytes(payload[li_block_start + 6:li_block_start + 30])
            if config_data != bytes(24):
                channels = _parse_channel_config(config_data)
            if li_chk != 0xFF:
                continue

        # Parse lead-out: [25 zeros][6 BCD timestamp][1 checksum]
        lo_time = None
        if lo_block_start is not None and lo_block_start + 32 <= len(payload):
            lo_time = _parse_bcd_timestamp(payload, lo_block_start + 25)

        records = _extract_records(payload, data_start, data_end, channels)
        if not records:
            continue

        # Build timestamps (1 Hz recording rate)
        base_time = li_time
        if base_time is None and lo_time is not None:
            base_time = lo_time - timedelta(seconds=len(records))
        if base_time is None:
            base_time = datetime(2049, 1, 1)
        timestamps = [base_time + timedelta(seconds=s) for s in range(len(records))]
        if lo_time is None and li_time is not None:
            lo_time = li_time + timedelta(seconds=len(records))

        sessions.append(Session(
            lead_in_ix=data_start,
            lead_out_ix=data_end,
            lead_in_time=li_time or base_time,
            lead_out_time=lo_time,
            channels=channels,
            data=records,
            timestamps=timestamps,
        ))

    return sessions


# ==============================================================================
# Signal conversion
# ==============================================================================
def _convert_values(sessions: list[Session]):
    """Convert raw values to physical units in-place."""
    for session in sessions:
        for record in session.data:
            for ch_idx, ch_code in enumerate(session.channels):
                if ch_code in CHANNELS:
                    sig_class_idx = CHANNELS[ch_code][1]
                    coef, offset, _ = SIG_CLASS[sig_class_idx]
                    record[ch_idx] = coef * record[ch_idx] + offset


# ==============================================================================
# XML parsing
# ==============================================================================
def _parse_xml_sectors(xml_content: str) -> list[tuple[int, list[int]]]:
    """Parse hex dump XML content, returning (sector_id, raw_bytes) tuples."""
    sectors = []
    current_id = None
    current_bytes = None
    in_sector = False
    # Stream-parse from string
    for event, elem in ET.iterparse(StringIO(xml_content), events=["start", "end"]):
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if event == "start" and tag == "SECTOR":
            in_sector = True
            current_id = None
            current_bytes = []
        elif event == "end" and tag == "ID" and in_sector and current_id is None:
            current_id = int(elem.text)
        elif event == "end" and tag == "B" and in_sector:
            current_bytes.append(int(elem.text))
            elem.clear()
        elif event == "end" and tag == "SECTOR":
            if current_id is not None and current_bytes:
                sectors.append((current_id, current_bytes))
            in_sector = False
            current_id = None
            current_bytes = None
            elem.clear()
    return sectors


# ==============================================================================
# Summary output
# ==============================================================================
def _format_duration(td: timedelta) -> str:
    total_secs = int(td.total_seconds())
    h, rem = divmod(total_secs, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"


def print_summary(sessions: list[Session], filename: str):
    """Print a pilot-friendly session summary table."""
    print(f"\nAustroView Summary: {filename}")
    print("=" * 95)
    print(f" {'#':>3}   {'Start':<20}{'End':<20}{'Duration':>9}  {'Records':>7}  {'Max RPM':>7}  {'Max Coolant':>11}")
    print(f" {'---':>3}   {'-' * 19} {'-' * 19} {'-' * 9}  {'-' * 7}  {'-' * 7}  {'-' * 11}")

    total_records = 0
    total_seconds = 0

    for i, session in enumerate(sessions):
        if not session.data:
            continue

        start = session.lead_in_time.strftime("%Y-%m-%d %H:%M") if session.lead_in_time else "unknown"
        end = session.lead_out_time.strftime("%Y-%m-%d %H:%M") if session.lead_out_time else "in progress"

        duration = timedelta(seconds=len(session.data))
        dur_str = _format_duration(duration)

        # Find max RPM (channel index 2 = Propeller Speed)
        max_rpm = 0
        max_coolant = -999
        for record in session.data:
            rpm_idx = None
            coolant_idx = None
            for ch_idx, ch_code in enumerate(session.channels):
                if ch_code == 802:
                    rpm_idx = ch_idx
                elif ch_code == 806:
                    coolant_idx = ch_idx
            if rpm_idx is not None:
                max_rpm = max(max_rpm, record[rpm_idx])
            if coolant_idx is not None:
                max_coolant = max(max_coolant, record[coolant_idx])
            break  # only need indices once

        # Actually scan all records for max values
        rpm_idx = None
        coolant_idx = None
        for ch_idx, ch_code in enumerate(session.channels):
            if ch_code == 802:
                rpm_idx = ch_idx
            elif ch_code == 806:
                coolant_idx = ch_idx
        max_rpm = max((r[rpm_idx] for r in session.data), default=0) if rpm_idx is not None else 0
        max_coolant = max((r[coolant_idx] for r in session.data), default=-999) if coolant_idx is not None else -999

        coolant_str = f"{max_coolant:.1f} C" if max_coolant > -999 else "N/A"

        print(f" {i + 1:3d}   {start:<20}{end:<20}{dur_str:>9}  {len(session.data):>7}  {max_rpm:>7.0f}  {coolant_str:>11}")

        total_records += len(session.data)
        total_seconds += len(session.data)

    total_dur = _format_duration(timedelta(seconds=total_seconds))
    latest = max((s.lead_in_time for s in sessions if s.lead_in_time), default=None)
    latest_str = latest.strftime("%Y-%m-%d") if latest else "unknown"
    print("=" * 95)
    print(f" {len(sessions)} sessions | {total_dur} total engine time | Latest: {latest_str}")
    print()


def summary_to_string(sessions: list[Session], filename: str) -> str:
    """Return the summary as a string (for saving to file)."""
    import io
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    print_summary(sessions, filename)
    sys.stdout = old_stdout
    return buf.getvalue()


# ==============================================================================
# Main processing pipeline
# ==============================================================================
def process_file(filepath: str, output_dir: Path, keep_xml: bool = False,
                 summary_only: bool = False) -> list[Session]:
    """Full pipeline: decrypt -> parse -> convert -> CSV."""
    filepath = Path(filepath)
    print(f"\nProcessing: {filepath.name}")

    # Step 1: Decrypt
    print("  Decrypting...", end=" ", flush=True)
    xml_content = decrypt_file(str(filepath))
    print("OK")

    # Optionally save XML
    if keep_xml:
        xml_out = output_dir / filepath.with_suffix(".xml").name
        if xml_content.lstrip().startswith("<?xml"):
            try:
                pretty = xml.dom.minidom.parseString(xml_content).toprettyxml(indent="  ")
                xml_out.write_text(pretty, encoding="utf-8")
            except Exception:
                xml_out.write_text(xml_content, encoding="utf-8")
        else:
            xml_out.write_text(xml_content, encoding="utf-8")
        print(f"  XML saved: {xml_out}")

    # Step 2: Parse sectors from XML
    print("  Parsing sectors...", end=" ", flush=True)
    sectors_raw = _parse_xml_sectors(xml_content)
    print(f"{len(sectors_raw)} sectors found")

    # Filter data log sectors (IDs 16-139) and extract payloads
    dl_sectors = []
    for sid, raw in sectors_raw:
        if sid < 16 or sid >= 140:
            continue
        stype = _decode_sector_type(raw)
        if stype in ("active", "locked", "fullNotLocked"):
            dl_sectors.append((sid, stype, _extract_payload(raw)))

    if not dl_sectors:
        print("  No usable data log sectors found.")
        return []

    # Sort and apply ring buffer ordering
    dl_sectors.sort(key=lambda x: x[0])
    active_idx = None
    for i, (sid, stype, _) in enumerate(dl_sectors):
        if stype == "active":
            active_idx = i
    if active_idx is not None:
        ordered = dl_sectors[active_idx + 1:] + dl_sectors[:active_idx + 1]
    else:
        ordered = dl_sectors

    payload = []
    for sid, stype, p in ordered:
        payload.extend(p)
    print(f"  Payload: {len(payload):,} bytes from {len(ordered)} sectors")

    # Step 3: Find sessions
    sessions = _find_sessions(payload)
    print(f"  Found {len(sessions)} recording sessions")

    if not sessions:
        return []

    # Step 4: Convert raw values to physical units
    _convert_values(sessions)

    # Step 5: Print summary
    print_summary(sessions, filepath.name)

    if summary_only:
        return sessions

    # Step 6: Write CSV files
    stem = filepath.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    for i, session in enumerate(sessions):
        if not session.data:
            continue

        time_suffix = ""
        if session.lead_in_time:
            time_suffix = f"_{session.lead_in_time.strftime('%Y%m%d_%H%M%S')}"
        csv_name = f"{stem}_session{i:02d}{time_suffix}.csv"
        csv_path = output_dir / csv_name

        headers = ["Timestamp"]
        for ch_code in session.channels:
            if ch_code in CHANNELS:
                name, sig_idx, _, _ = CHANNELS[ch_code]
                _, _, unit = SIG_CLASS[sig_idx]
                headers.append(f"{name} [{unit}]")
            else:
                headers.append(f"Channel {ch_code}")

        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for ts, record in zip(session.timestamps, session.data):
                row = [ts.strftime("%Y-%m-%d %H:%M:%S")]
                for ch_idx, ch_code in enumerate(session.channels):
                    if ch_code in CHANNELS:
                        sig_idx = CHANNELS[ch_code][1]
                        fmt = ".1f" if sig_idx in (1, 8, 11, 12, 15) else ".0f"
                        row.append(f"{record[ch_idx]:{fmt}}")
                    else:
                        row.append(f"{record[ch_idx]:.0f}")
                writer.writerow(row)

        duration = session.timestamps[-1] - session.timestamps[0] if len(session.timestamps) > 1 else timedelta(0)
        print(f"  Session {i:02d}: {csv_path.name}")

    print(f"\n  {len(sessions)} CSV files written to: {output_dir}")
    return sessions


# ==============================================================================
# CLI
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        prog="austroview",
        description="Convert AE300 .ae3 hex dump files into per-session CSV spreadsheets.",
        epilog=DISCLAIMER,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input", nargs="+",
        help="One or more .ae3 files or directories containing .ae3 files",
    )
    parser.add_argument(
        "--output-dir", "-o", type=Path, default=Path("output"),
        help="Directory for output files (default: ./output/)",
    )
    parser.add_argument(
        "--summary", "-s", action="store_true",
        help="Print session summary table only (no CSV files generated)",
    )
    parser.add_argument(
        "--keep-xml", action="store_true",
        help="Save the intermediate decrypted XML file",
    )
    args = parser.parse_args()

    # Collect all .ae3 files from inputs
    ae3_files = []
    for inp in args.input:
        p = Path(inp)
        if p.is_dir():
            ae3_files.extend(sorted(p.glob("*.ae3")))
        elif p.is_file() and p.suffix.lower() == ".ae3":
            ae3_files.append(p)
        else:
            print(f"Skipping: {p} (not an .ae3 file or directory)")

    if not ae3_files:
        print("No .ae3 files found.")
        sys.exit(1)

    print(f"AustroView - AE300 Data Log Converter")
    print(f"Found {len(ae3_files)} file(s) to process")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    for filepath in ae3_files:
        try:
            process_file(str(filepath), args.output_dir,
                         keep_xml=args.keep_xml, summary_only=args.summary)
        except Exception as e:
            print(f"  Error processing {filepath.name}: {e}")


if __name__ == "__main__":
    main()
