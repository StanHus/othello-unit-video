#!/usr/bin/env python3
"""Make the published copies of images: downscale, re-encode as JPEG and drop every metadata block.

  python3 tools/art/export_web_copies.py --out assets/paintings --long-edge 1600 --quality 80 \
      in/venice-senate.jpg=venice-senate.jpg in/ottoman-fleet.jpg=ottoman-fleet.jpg ...

Each argument is SOURCE or SOURCE=OUTPUT_NAME. An image that needs no resizing and is already a JPEG is copied
losslessly with its APP1-APP15 and COM segments removed (EXIF, XMP, IPTC, C2PA/JUMBF provenance manifests,
encoder comments); everything else is resized with Lanczos and re-encoded without EXIF or ICC data. Writes
<out>/web-copies.json with each output's size, bytes and sha256 (no source paths).
"""
import argparse, hashlib, json, pathlib, sys
from PIL import Image


def strip_jpeg(data):
    """Drop APPn (n >= 1) and COM segments from a baseline/progressive JPEG without re-encoding."""
    if data[:2] != b"\xff\xd8":
        raise ValueError("not a JPEG")
    out, i = bytearray(b"\xff\xd8"), 2
    while i < len(data):
        if data[i] != 0xFF:
            raise ValueError(f"bad marker at {i}")
        marker = data[i + 1]
        if marker == 0xD9:                                  # EOI
            out += data[i:i + 2]; break
        if 0xD0 <= marker <= 0xD7 or marker == 0x01:        # standalone markers
            out += data[i:i + 2]; i += 2; continue
        length = int.from_bytes(data[i + 2:i + 4], "big")
        seg = data[i:i + 2 + length]
        if marker == 0xDA:                                  # SOS: copy the rest (scan data and any later segments)
            out += data[i:]; break
        if not (0xE1 <= marker <= 0xEF or marker == 0xFE):  # keep APP0 (JFIF), tables, frame headers
            out += seg
        i += 2 + length
    return bytes(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+", help="SOURCE or SOURCE=OUTPUT_NAME")
    ap.add_argument("--out", required=True)
    ap.add_argument("--long-edge", type=int, default=1600, help="0 keeps the original size")
    ap.add_argument("--quality", type=int, default=80)
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    report_path = out / "web-copies.json"
    report = json.loads(report_path.read_text()) if report_path.exists() else {"files": {}}
    report["processing"] = (f"long edge at most {a.long_edge or 'unchanged'} px (Lanczos), JPEG quality {a.quality}, "
                            "all metadata removed (EXIF, XMP, IPTC, ICC, C2PA/JUMBF, comments)")
    for spec in a.images:
        src, _, name = spec.partition("=")
        src = pathlib.Path(src)
        dst = out / (name or (src.stem + ".jpg"))
        with Image.open(src) as im:
            w, h = im.size
            scale = min(1.0, a.long_edge / max(w, h)) if a.long_edge else 1.0
            if scale == 1.0 and im.format == "JPEG":
                dst.write_bytes(strip_jpeg(src.read_bytes()))
                how = "lossless (metadata segments removed)"
            else:
                size = (round(w * scale), round(h * scale))
                im2 = im.convert("RGB")
                if size != (w, h):
                    im2 = im2.resize(size, Image.LANCZOS)
                im2.save(dst, "JPEG", quality=a.quality, optimize=True, progressive=True)
                how = f"resized to {size[0]}x{size[1]}, re-encoded" if size != (w, h) else "re-encoded as JPEG"
        with Image.open(dst) as chk:
            left = sorted(k for k in chk.info if k not in ("jfif", "jfif_version", "jfif_density", "jfif_unit", "progressive", "progression"))
            if left:
                sys.exit(f"{dst}: metadata left after export: {left}")
            dims = chk.size
        data = dst.read_bytes()
        report["files"][dst.name] = {"width": dims[0], "height": dims[1], "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "export": how}
        print(f"{dst.name:40s} {dims[0]}x{dims[1]} {len(data)/1e6:5.2f} MB  {how}")
    report["files"] = dict(sorted(report["files"].items()))
    report_path.write_text(json.dumps(report, indent=1) + "\n")


if __name__ == "__main__":
    main()
