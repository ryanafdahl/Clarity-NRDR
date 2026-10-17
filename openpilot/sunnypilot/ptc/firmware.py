"""Offline identification of reviewed Clarity PTC files; does not query or flash EPS."""

import argparse
import hashlib
from pathlib import Path


PTC_FIRMWARE = {
  "d4fe903bcf347495f4321be65a3c650c8c931f1650c3bef6443721da0dd80f7d": "ClarityMax-PTM.rwd",
  "9e2e98857a6734f4631205cb9550bf7cb61720da566a4c117b9187a8ddf25d61":
    "ClarityMax-20260928-Pminus5-A280Flat-KFF45-Tracker3200-Norm1650-3840.rwd",
}


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("image", type=Path)
  args = parser.parse_args()
  try:
    digest = hashlib.sha256(args.image.read_bytes()).hexdigest()
  except OSError as error:
    parser.exit(1, f"Cannot read firmware: {error}\n")
  print(f"SHA-256: {digest}")
  name = PTC_FIRMWARE.get(digest)
  if name is None:
    print("Unknown image. Do not confirm it using the Clarity PTC firmware setting.")
    return 1
  print(f"Recognized: {name}")
  print("Uses the Clarity TRW-A020 PTC profile (linear command range 0..3840).")
  print("File identity only; this does not verify installed firmware or vehicle behavior.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
