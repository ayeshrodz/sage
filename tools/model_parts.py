"""Split a large file into parts small enough for GitHub, and join them back, with checksums.

GitHub refuses files over 100 MB in a normal push and warns above 50 MB, so the
stage 1a model (about 1.1 GB) travels as numbered parts of 45 MiB on a separate
branch, with a SHA-256 checksum of every part and of the whole file.

  python tools/model_parts.py split MODEL.gguf OUTDIR [--part-mb 45]
  python tools/model_parts.py join PARTSDIR OUTFILE

`split` writes OUTDIR/<name>.part000, .part001, ... and OUTDIR/SHA256SUMS, and
prints the whole file's SHA-256 to compare with the one on the download page.
`join` checks every part, rebuilds the file, checks the whole, and refuses to
leave anything behind that does not match. Needs only the Python standard library.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

SUMS = "SHA256SUMS"
PART = re.compile(r"\.part(\d{3})$")


def split(src: Path, out: Path, part_bytes: int) -> str:
    """Write the parts and SHA256SUMS; return the whole file's SHA-256."""
    out.mkdir(parents=True, exist_ok=True)
    whole, lines = hashlib.sha256(), []
    with open(src, "rb") as f:
        for i, data in enumerate(iter(lambda: f.read(part_bytes), b"")):
            whole.update(data)
            part = out / f"{src.name}.part{i:03d}"
            part.write_bytes(data)
            lines.append(f"{hashlib.sha256(data).hexdigest()}  {part.name}")
    (out / SUMS).write_text("\n".join([f"{whole.hexdigest()}  {src.name}"] + lines) + "\n")
    return whole.hexdigest()


def join(parts_dir: Path, dest: Path) -> str:
    """Rebuild the file listed in PARTSDIR/SHA256SUMS at `dest`; return its SHA-256. Raises on any mismatch."""
    sums = dict(reversed(line.split(None, 1)) for line in (parts_dir / SUMS).read_text().splitlines() if line.strip())
    wholes = [n for n in sums if not PART.search(n)]
    parts = sorted(n for n in sums if PART.search(n))
    if len(wholes) != 1 or [PART.search(n).group(1) for n in parts] != [f"{i:03d}" for i in range(len(parts))]:
        raise ValueError(f"{SUMS} must list one whole file and parts numbered from 000 without gaps")
    tmp = dest.with_name(dest.name + ".tmp")
    whole = hashlib.sha256()
    try:
        with open(tmp, "wb") as out:
            for name in parts:
                data = (parts_dir / name).read_bytes()
                if hashlib.sha256(data).hexdigest() != sums[name]:
                    raise ValueError(f"{name} does not match its checksum")
                whole.update(data)
                out.write(data)
        if whole.hexdigest() != sums[wholes[0]]:
            raise ValueError("the rebuilt file does not match its checksum")
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)
    return whole.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("split")
    s.add_argument("src", type=Path)
    s.add_argument("out", type=Path)
    s.add_argument("--part-mb", type=int, default=45, help="part size in MiB (default 45; 24 for GitHub's web uploader)")
    j = sub.add_parser("join")
    j.add_argument("parts_dir", type=Path)
    j.add_argument("dest", type=Path)
    args = ap.parse_args()
    if args.cmd == "split":
        digest = split(args.src, args.out, args.part_mb << 20)
        n = len(list(args.out.glob(f"{args.src.name}.part*")))
        print(f"{n} parts and {SUMS} written to {args.out}\nSHA-256 of {args.src.name}: {digest}")
    else:
        try:
            digest = join(args.parts_dir, args.dest)
        except (OSError, ValueError) as e:
            sys.exit(f"join failed, nothing written: {e}")
        print(f"rebuilt {args.dest}, all checksums match\nSHA-256: {digest}")


if __name__ == "__main__":
    main()
