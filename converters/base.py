import csv
from pathlib import Path


def write_csv(outfile, rows):
    writer = csv.DictWriter(outfile, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)


def out_path(explicit, output_dir, filename):
    if explicit:
        return explicit
    if output_dir:
        return str(Path(output_dir) / filename)
    return filename
