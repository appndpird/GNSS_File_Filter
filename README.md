# GNSS File Filter Tool

A lightweight desktop GUI tool that filters GNSS `.T04` receiver files to match the actual flight time window recorded by the onboard IMU. Built for aerial survey workflows using Headwall hyperspectral sensor systems with co-aligned GNSS/IMU hardware.

## The Problem

After a survey flight, the GNSS folder typically contains `.T04` files spanning the entire session. Only a subset of these files correspond to the actual in-air data collection window. Manually cross-referencing filenames against IMU logs to identify the correct files is tedious and error-prone.

## How It Works

1. **IMU Discovery** — Point the tool at your `T0_raw` folder. It recursively searches for `imu_gps.txt` files, validates each is a parseable tab-delimited text file (skipping binary IMU data), and extracts the UTC time range from the first and last records. If multiple `imu_gps.txt` files exist, candidates are tried in descending size order until one parses successfully.

2. **Filename Matching** — The tool extracts the `YYYYMMDDHHmm` timestamp embedded in each `.T04` filename (the last 12 digits before the extension) and checks whether it falls within the IMU time window.

3. **Filtered Output** — Matching files are copied (originals preserved) into a `gnss_filtered/` subfolder inside the GNSS directory.

## Expected File Formats

### `.T04` Filenames

The tool expects GNSS filenames with an embedded 12-digit UTC timestamp:

```
6241C03148202604140439.T04
          ^^^^^^^^^^^^
          YYYYMMDDHHmm
```

Where the prefix (e.g. `6241C03148`) is a receiver/session identifier.

### `imu_gps.txt`

Tab-delimited text file with a `Gps_UTC_Date&Time` column containing timestamps in the format `YYYY/Mon/DD HH:MM:SS.ffffff`:

```
Roll	Pitch	Yaw	Lat	Lon	Alt	GPS_UTC	Gps_UTC_Date&Time	...
0.000	0.000	0.000	-34.530	138.688	61.44	...	2026/Apr/14 04:35:14.900000	...
```

## Screenshot

```
┌─ GNSS Flight Filter ──────────────────────────────────────┐
│                                                            │
│  Step 1: T0_raw Folder (contains imu_gps.txt)             │
│  [C:/WORKSPACE/CaliWeek/T0_raw                ] [Browse…] │
│  IMU file: session_01/imu_gps.txt                          │
│  Flight window (UTC): 04:35:14 – 05:01:33                 │
│                                                            │
│  Step 2: GNSS Folder (contains .T04 files)                │
│  [C:/WORKSPACE/CaliWeek/T1_Proc/gnss_all      ] [Browse…] │
│                                                            │
│  [              Filter & Copy                            ] │
│                                                            │
│  Log ──────────────────────────────────────────────────── │
│  Found 3 imu_gps.txt files (sorted by size):              │
│    27,189,248 bytes  ...\100038_...\imu_gps.txt           │
│    21,389,312 bytes  ...\20260413UQ_...\imu_gps.txt       │
│       119,581 bytes  ...\100037_...\imu_gps.txt           │
│                                                            │
│  Trying: ...\100038_...\imu_gps.txt (27,189,248 bytes)…  │
│    SKIP — could not parse (may be binary)                  │
│  Trying: ...\20260413UQ_...\imu_gps.txt (21,389,312)…    │
│    OK — parsed successfully.                               │
│                                                            │
│  Flight window (UTC):      04:35:14 – 05:01:33            │
│  Flight window (Adelaide): 02:05:14 PM – 02:31:33 PM      │
│                                                            │
│  Matched: 9   Skipped: 20                                  │
│  COPY  ...0436.T04  UTC 04:36 → Adelaide 02:06 PM         │
│  COPY  ...0439.T04  UTC 04:39 → Adelaide 02:09 PM         │
│  ...                                                       │
│  Done! 9 files copied to gnss_filtered/                    │
└────────────────────────────────────────────────────────────┘
```

## Requirements

- **Python 3.7+**
- **No external dependencies** — uses only the standard library (`tkinter`, `shutil`, `os`, `re`, `datetime`)

`tkinter` is included with standard Python on Windows. On Linux, install it with:

```bash
sudo apt install python3-tk    # Debian/Ubuntu
```

## Usage

### Double-click

On Windows, double-click `gnss_flight_filter.py` to launch (if `.py` files are associated with Python).

### Command line

```bash
python gnss_flight_filter.py
```

### Steps

1. Click **Browse** next to Step 1 and select the `T0_raw` folder (or any parent folder containing `imu_gps.txt` in its subfolders). The tool scans recursively and displays the detected flight time window in both UTC and Adelaide time.
2. Click **Browse** next to Step 2 and select the folder containing your `.T04` GNSS files.
3. Click **Filter & Copy**. Matched files are copied to a `gnss_filtered/` subfolder inside the GNSS directory. Original files are not modified.

## Typical Folder Structure

```
CaliWeek/
├── QLD_CALVIS_CALI/
│   ├── T0_raw/                          ← Step 1: browse here
│   │   ├── 100038_session/
│   │   │   └── imu_gps.txt             (binary — skipped)
│   │   ├── 20260413UQ_session/
│   │   │   └── imu_gps.txt             (text — used ✓)
│   │   └── 100037_dark_session/
│   │       └── imu_gps.txt             (small — lower priority)
│   └── T1_Proc/
│       └── gnss_all/                    ← Step 2: browse here
│           ├── 6241C03148...0338.T04
│           ├── 6241C03148...0339.T04
│           ├── ...
│           ├── 6241C03148...0500.T04
│           └── gnss_filtered/           ← output created here
│               ├── 6241C03148...0436.T04
│               ├── ...
│               └── 6241C03148...0500.T04
```

## Time Zones

All `.T04` filename timestamps and `imu_gps.txt` records are in **UTC**. The log displays both UTC and **Adelaide time (ACST, UTC+9:30)** for convenience.

## Notes

- If multiple `imu_gps.txt` files are found, candidates are tried largest-first. Binary or malformed files are automatically skipped.
- The tool validates that a file is parseable text (checks for tab delimiters and the `Gps_UTC_Date&Time` header) before attempting timestamp extraction.
- Files are copied with `shutil.copy2`, preserving original metadata (timestamps, permissions).
- The `gnss_filtered/` output folder is created inside the GNSS folder. Running the tool again will overwrite previously copied files.

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

## Author

**Bipul Neupane, PhD**
Research Scientist, DPIRD Node
Australian Plant Phenomics Network (APPN)
Department of Primary Industries and Regional Development (DPIRD), Western Australia
[bipul.neupane@dpird.wa.gov.au](mailto:bipul.neupane@dpird.wa.gov.au)

## Contributor

Bipul Neupane: [Github](https://github.com/bipulneupane)
