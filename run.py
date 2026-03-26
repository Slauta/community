#!/usr/bin/env python3

# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "openpyxl",
#     "pdfplumber",
# ]
# ///

"""Scan an input directory, auto-detect broker converters, and convert all
recognised files to CSV. Outputs are written to a single output directory
which is cleared before each run.

Usage:
    python run.py [--input-dir data/] [--output-dir output/]
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

from converters import REGISTRY, detect_converter
from converters.base import write_csv


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _label(entry):
    return f"{entry['broker']} · {entry['report_type']}"


def _run_converter(entry, filepath, output_dir):
    stem = filepath.stem
    suffix = os.urandom(3).hex()
    trades, income = [], []

    if entry['input_type'] == 'csv':
        with open(filepath, 'r', encoding='utf-8') as f:
            trades, income = entry['convert'](f)
    else:  # xlsx, pdf — pass file path
        trades, income = entry['convert'](str(filepath))

    if trades:
        out = output_dir / f'result_trades_{stem}_{suffix}.csv'
        with open(out, 'w', newline='') as f:
            write_csv(f, trades)
        print(f"    {len(trades)} trade(s)        → {out.name}")

    if income:
        out = output_dir / f'result_income_{stem}_{suffix}.csv'
        with open(out, 'w', newline='') as f:
            write_csv(f, income)
        print(f"    {len(income)} income record(s) → {out.name}")

    if not trades and not income:
        print("    (no output rows)")


# ---------------------------------------------------------------------------
# Interactive menu
# ---------------------------------------------------------------------------

def _show_plan(detections):
    """Print the file/converter plan table."""
    numbered = [(f, c) for f, c in detections if c is not None]
    skipped  = [(f, c) for f, c in detections if c is None]

    print()
    if numbered:
        col = max(len(f.name) for f, _ in numbered) + 2
        for i, (f, c) in enumerate(numbered, 1):
            print(f"  {i:2}.  {f.name:<{col}} → {_label(c)}")
    if skipped:
        col = max(len(f.name) for f, _ in skipped) + 2
        for f, _ in skipped:
            print(f"        {f.name:<{col}}   (not recognized — will skip)")
    print()


def _choose_converter_for(filepath, detected):
    """Ask the user to pick a converter (or skip) for one file."""
    print(f"  Change converter for: {filepath.name}")
    print(f"    0.  Skip this file")
    for i, entry in enumerate(REGISTRY, 1):
        marker = "  ← detected" if detected and entry['id'] == detected['id'] else ""
        print(f"    {i}.  {_label(entry)}{marker}")

    default = 0
    if detected:
        default = next(i for i, e in enumerate(REGISTRY, 1) if e['id'] == detected['id'])

    while True:
        raw = input(f"  Choice [{default}]: ").strip()
        if raw == '':
            choice = default
        else:
            try:
                choice = int(raw)
            except ValueError:
                print("  Please enter a number.")
                continue
        if choice == 0:
            return None
        if 1 <= choice <= len(REGISTRY):
            return REGISTRY[choice - 1]
        print(f"  Enter a number between 0 and {len(REGISTRY)}.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Scan input directory and convert broker reports to CSV.'
    )
    parser.add_argument(
        '--input-dir', default='data',
        help='Directory with broker report files (default: data/)'
    )
    parser.add_argument(
        '--output-dir', default='output',
        help='Directory for output CSV files (default: output/)'
    )
    args = parser.parse_args()

    input_dir  = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        print(f"Error: input directory '{input_dir}' does not exist.")
        sys.exit(1)

    # Prepare output directory
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    # Scan and detect
    files = sorted(
        f for f in input_dir.iterdir()
        if f.is_file() and not f.name.startswith('.')
    )

    print(f"\nScanning {input_dir}/ ...")
    detections = [(f, detect_converter(f)) for f in files]

    convertible = [(f, c) for f, c in detections if c is not None]
    if not convertible:
        print("No recognisable files found. Exiting.")
        sys.exit(0)

    skipped = [(f, c) for f, c in detections if c is None]
    prompt = "Press Enter to convert all, or enter file numbers to change converter (e.g. '1 3'): "

    while True:
        _show_plan(convertible + skipped)
        print(f"  Output → {output_dir}/\n")
        raw = input(prompt).strip()

        if not raw:
            break

        to_change = set()
        for token in raw.split():
            try:
                to_change.add(int(token))
            except ValueError:
                pass

        new_convertible = []
        for i, (f, c) in enumerate(convertible, 1):
            if i in to_change:
                new_c = _choose_converter_for(f, c)
                new_convertible.append((f, new_c))
            else:
                new_convertible.append((f, c))
        convertible = new_convertible
        print()

    # Final list (drop skipped)
    to_process = [(f, c) for f, c in convertible if c is not None]

    if not to_process:
        print("\nNothing to convert.")
        sys.exit(0)

    print(f"\nConverting {len(to_process)} file(s) → {output_dir}/\n")

    ok = 0
    for filepath, entry in to_process:
        print(f"  {filepath.name}  ({_label(entry)})")
        try:
            _run_converter(entry, filepath, output_dir)
            ok += 1
        except Exception as e:
            print(f"    ✗ Failed: {e}")
        print()

    print(f"Done. {ok}/{len(to_process)} file(s) converted.")


if __name__ == '__main__':
    main()
