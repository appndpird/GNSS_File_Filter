"""
GNSS Flight Filter Tool
========================
Filters .T04 GNSS files to match the flight time window recorded in imu_gps.txt.

Usage: Double-click to run, or: python gnss_flight_filter.py

Workflow:
  1. Browse to the T0_raw folder (searches for imu_gps.txt recursively; uses largest if multiple found)
  2. Browse to the GNSS folder containing .T04 files
  3. Click "Filter" to copy matching T04 files into a "gnss_filtered" output folder
"""

import os
import re
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from datetime import datetime, timedelta
from pathlib import Path


class GNSSFlightFilterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GNSS Flight Filter")
        self.root.resizable(True, True)
        self.root.minsize(700, 520)

        # State
        self.t0_raw_path = tk.StringVar()
        self.gnss_path = tk.StringVar()
        self.imu_file_found = tk.StringVar(value="—")
        self.imu_time_range = tk.StringVar(value="—")
        self.imu_info = None  # dict with start_utc, end_utc, filepath

        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        pad = dict(padx=10, pady=4)

        # --- T0_raw folder ---
        frame1 = tk.LabelFrame(self.root, text="Step 1: T0_raw Folder (contains imu_gps.txt)", padx=8, pady=6)
        frame1.pack(fill="x", **pad)

        row1 = tk.Frame(frame1)
        row1.pack(fill="x")
        tk.Entry(row1, textvariable=self.t0_raw_path, state="readonly").pack(side="left", fill="x", expand=True)
        tk.Button(row1, text="Browse…", command=self._browse_t0_raw).pack(side="right", padx=(6, 0))

        info_frame = tk.Frame(frame1)
        info_frame.pack(fill="x", pady=(4, 0))
        tk.Label(info_frame, text="IMU file:").pack(side="left")
        tk.Label(info_frame, textvariable=self.imu_file_found, fg="#555555", anchor="w").pack(side="left", padx=(4, 16))
        tk.Label(info_frame, text="Flight window (UTC):").pack(side="left")
        tk.Label(info_frame, textvariable=self.imu_time_range, fg="#006600", anchor="w").pack(side="left", padx=(4, 0))

        # --- GNSS folder ---
        frame2 = tk.LabelFrame(self.root, text="Step 2: GNSS Folder (contains .T04 files)", padx=8, pady=6)
        frame2.pack(fill="x", **pad)

        row2 = tk.Frame(frame2)
        row2.pack(fill="x")
        tk.Entry(row2, textvariable=self.gnss_path, state="readonly").pack(side="left", fill="x", expand=True)
        tk.Button(row2, text="Browse…", command=self._browse_gnss).pack(side="right", padx=(6, 0))

        # --- Filter button ---
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(fill="x", **pad)
        self.filter_btn = tk.Button(btn_frame, text="Filter & Copy", command=self._run_filter,
                                    bg="#2266aa", fg="white", font=("Segoe UI", 11, "bold"),
                                    height=2, cursor="hand2")
        self.filter_btn.pack(fill="x")

        # --- Log ---
        log_frame = tk.LabelFrame(self.root, text="Log", padx=8, pady=6)
        log_frame.pack(fill="both", expand=True, **pad)
        self.log = scrolledtext.ScrolledText(log_frame, height=14, font=("Consolas", 9), state="disabled")
        self.log.pack(fill="both", expand=True)

    # ------------------------------------------------------------------ Browse
    def _browse_t0_raw(self):
        folder = filedialog.askdirectory(title="Select T0_raw folder")
        if not folder:
            return
        self.t0_raw_path.set(folder)
        self._scan_imu(folder)

    def _browse_gnss(self):
        folder = filedialog.askdirectory(title="Select GNSS folder with .T04 files")
        if not folder:
            return
        self.gnss_path.set(folder)
        t04_count = sum(1 for f in os.listdir(folder) if f.upper().endswith(".T04"))
        self._log(f"GNSS folder selected: {folder}  ({t04_count} .T04 files found)")

    # ------------------------------------------------------------------ IMU scan
    def _scan_imu(self, folder):
        self._log(f"Scanning for imu_gps.txt in: {folder}")
        candidates = []
        for dirpath, _, filenames in os.walk(folder):
            for fn in filenames:
                if fn.lower() == "imu_gps.txt":
                    fp = os.path.join(dirpath, fn)
                    sz = os.path.getsize(fp)
                    candidates.append((fp, sz))

        if not candidates:
            self.imu_file_found.set("NOT FOUND")
            self.imu_time_range.set("—")
            self.imu_info = None
            self._log("ERROR: No imu_gps.txt found in any subfolder.")
            messagebox.showwarning("Not Found", "No imu_gps.txt found in the selected folder or its subfolders.")
            return

        # Sort by size (largest first) and try each until one parses
        candidates.sort(key=lambda x: x[1], reverse=True)

        if len(candidates) > 1:
            self._log(f"Found {len(candidates)} imu_gps.txt files (sorted by size):")
            for fp, sz in candidates:
                self._log(f"  {sz:>12,} bytes  {fp}")

        # Try each candidate until we find one that parses successfully
        chosen_path = None
        start_utc = None
        end_utc = None

        for fp, sz in candidates:
            self._log(f"\nTrying: {fp} ({sz:,} bytes)...")
            s, e = self._parse_imu_time_range(fp)
            if s and e:
                chosen_path = fp
                start_utc, end_utc = s, e
                self._log(f"  OK — parsed successfully.")
                break
            else:
                self._log(f"  SKIP — could not parse timestamps (may be binary or different format).")

        if chosen_path and start_utc and end_utc:
            rel = os.path.relpath(chosen_path, folder)
            self.imu_file_found.set(rel)
            self.imu_info = {"start_utc": start_utc, "end_utc": end_utc, "filepath": chosen_path}
            adelaide = timedelta(hours=9, minutes=30)
            s_adl = start_utc + adelaide
            e_adl = end_utc + adelaide
            utc_str = f"{start_utc.strftime('%H:%M:%S')} – {end_utc.strftime('%H:%M:%S')}"
            adl_str = f"{s_adl.strftime('%I:%M:%S %p')} – {e_adl.strftime('%I:%M:%S %p')}"
            self.imu_time_range.set(utc_str)
            self._log(f"\nUsing: {os.path.relpath(chosen_path, folder)}")
            self._log(f"Flight window (UTC):      {utc_str}")
            self._log(f"Flight window (Adelaide): {adl_str}")
        else:
            self.imu_file_found.set("NO VALID FILE")
            self.imu_time_range.set("PARSE ERROR")
            self.imu_info = None
            self._log("\nERROR: None of the imu_gps.txt files could be parsed.")

    def _parse_imu_time_range(self, filepath):
        """Read first and last data lines of imu_gps.txt to get UTC time range."""
        start_utc = None
        end_utc = None
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                header = f.readline()

                # Verify this looks like a valid text IMU file
                if "Gps_UTC_Date&Time" not in header and "\t" not in header:
                    return None, None

                # Find the Gps_UTC_Date&Time column index
                cols = header.strip().split("\t")
                try:
                    ts_col = cols.index("Gps_UTC_Date&Time")
                except ValueError:
                    # Fallback: try column index 7
                    ts_col = 7

                # First data line
                first_line = f.readline()
                if first_line:
                    fields = first_line.strip().split("\t")
                    if len(fields) > ts_col:
                        start_utc = self._parse_timestamp(fields[ts_col].strip())

                if not start_utc:
                    return None, None  # Can't parse even the first line

                # Last data line — read to end
                last_line = first_line
                for line in f:
                    if line.strip():
                        last_line = line
                if last_line:
                    fields = last_line.strip().split("\t")
                    if len(fields) > ts_col:
                        end_utc = self._parse_timestamp(fields[ts_col].strip())

        except Exception as e:
            return None, None
        return start_utc, end_utc

    @staticmethod
    def _parse_timestamp(ts_str):
        """Parse timestamps like '2026/Apr/14 04:35:14.900000'."""
        for fmt in ("%Y/%b/%d %H:%M:%S.%f", "%Y/%b/%d %H:%M:%S",
                    "%Y/%m/%d %H:%M:%S.%f", "%Y/%m/%d %H:%M:%S"):
            try:
                return datetime.strptime(ts_str, fmt)
            except ValueError:
                continue
        return None

    # ------------------------------------------------------------------ Filter
    def _run_filter(self):
        if not self.imu_info:
            messagebox.showwarning("Missing", "Please select a valid T0_raw folder first (Step 1).")
            return
        gnss_folder = self.gnss_path.get()
        if not gnss_folder or not os.path.isdir(gnss_folder):
            messagebox.showwarning("Missing", "Please select a GNSS folder (Step 2).")
            return

        start_utc = self.imu_info["start_utc"]
        end_utc = self.imu_info["end_utc"]

        # Collect .T04 files
        t04_files = [f for f in os.listdir(gnss_folder) if f.upper().endswith(".T04")]
        if not t04_files:
            messagebox.showwarning("No Files", "No .T04 files found in the GNSS folder.")
            return

        self._log(f"\n{'='*60}")
        self._log(f"Filtering {len(t04_files)} .T04 files against IMU window "
                   f"{start_utc.strftime('%H:%M:%S')} – {end_utc.strftime('%H:%M:%S')} UTC")

        # Pattern: last 12 digits before extension = YYYYMMDDHHmm
        ts_pattern = re.compile(r"(\d{12})\.\w+$")

        matched = []
        skipped = []

        for fn in sorted(t04_files):
            m = ts_pattern.search(fn)
            if not m:
                skipped.append((fn, "no timestamp"))
                continue
            ts_digits = m.group(1)  # e.g. 202604140439
            try:
                file_dt = datetime.strptime(ts_digits, "%Y%m%d%H%M")
            except ValueError:
                skipped.append((fn, "bad timestamp"))
                continue

            if start_utc <= file_dt <= end_utc:
                matched.append(fn)
            else:
                skipped.append((fn, file_dt.strftime("%H:%M UTC — outside window")))

        self._log(f"Matched: {len(matched)}   Skipped: {len(skipped)}")

        if skipped:
            self._log("\nSkipped files:")
            for fn, reason in skipped:
                self._log(f"  SKIP  {fn}  ({reason})")

        if not matched:
            messagebox.showinfo("No Match", "No .T04 files matched the IMU flight time window.")
            return

        # Create output folder
        output_dir = os.path.join(gnss_folder, "gnss_filtered")
        os.makedirs(output_dir, exist_ok=True)

        self._log(f"\nCopying {len(matched)} files to: {output_dir}")
        adelaide = timedelta(hours=9, minutes=30)
        copied = 0
        for fn in matched:
            src = os.path.join(gnss_folder, fn)
            dst = os.path.join(output_dir, fn)
            try:
                shutil.copy2(src, dst)
                # Extract time for display
                m = ts_pattern.search(fn)
                ts_digits = m.group(1)
                file_dt = datetime.strptime(ts_digits, "%Y%m%d%H%M")
                adl = file_dt + adelaide
                sz = os.path.getsize(src)
                self._log(f"  COPY  {fn}  ({sz:>10,} bytes)  "
                          f"UTC {file_dt.strftime('%H:%M')} → Adelaide {adl.strftime('%I:%M %p')}")
                copied += 1
            except Exception as e:
                self._log(f"  ERROR copying {fn}: {e}")

        self._log(f"\nDone! {copied} files copied to gnss_filtered/")
        messagebox.showinfo("Complete", f"{copied} .T04 files copied to:\n{output_dir}")

    # ------------------------------------------------------------------ Log
    def _log(self, msg):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")
        self.root.update_idletasks()


# ------------------------------------------------------------------ Main
if __name__ == "__main__":
    root = tk.Tk()
    app = GNSSFlightFilterApp(root)
    root.mainloop()