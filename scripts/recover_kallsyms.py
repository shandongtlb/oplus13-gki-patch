#!/usr/bin/env python3
"""Recover this Image's 6.6 base-relative kallsyms without executing it.

Format reference: common/scripts/kallsyms.c and common/kernel/kallsyms.c.
Only the inspected little-endian, 64-bit, non-ABSOLUTE_PERCPU format is supported.
"""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True, help="uncompressed ARM64 Image")
    parser.add_argument("--output", type=Path, required=True, help="output directory")
    parser.add_argument("--btf-offset", type=lambda s: int(s, 0), required=True,
                        help="independently verified __start_BTF file offset; decimal or hex")
    args = parser.parse_args()
    image = args.image.read_bytes()
    if image[56:60] != b"ARM\x64":
        raise ValueError("not an uncompressed arm64 Image")
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    tables = []
    digits = b"".join(bytes((i, 0)) for i in range(48, 58))
    for match in re.finditer(digits, image):
        start = match.start()
        for _ in range(48):
            start = image.rfind(b"\0", 0, start - 1) + 1
        cur, offsets, tokens = start, [], []
        for _ in range(256):
            end = image.find(b"\0", cur)
            offsets.append(cur - start)
            tokens.append(image[cur:end])
            cur = end + 1
        if max(offsets) >= 65536:
            continue
        index = (cur + 7) & ~7
        if image[index:index + 512] == struct.pack("<256H", *offsets):
            tables.append((start, index, tokens))
    if len(tables) != 1:
        raise ValueError(f"Expected one verified token table, found {len(tables)}")
    token_start, index_start, tokens = tables[0]
    valid = []
    for padding in (0, 4):
        marker_end = token_start - padding
        cur, previous = marker_end - 4, 0xffffffff
        while cur >= 0:
            value = struct.unpack_from("<I", image, cur)[0]
            if value >= previous:
                break
            previous = value
            if value == 0:
                break
            cur -= 4
        marker_start = cur
        marker_count = (marker_end - marker_start) // 4
        if marker_count < 2 or previous != 0:
            continue
        markers = struct.unpack_from(f"<{marker_count}I", image, marker_start)
        # This is a bounded format probe for the supplied Image, not a generic tool.
        for pos in range((max(0, marker_start - 4000000) + 7) & ~7, marker_start - 4, 8):
            count = struct.unpack_from("<I", image, pos)[0]
            if not (256 * (marker_count - 1) < count <= 256 * marker_count):
                continue
            names_start = cur = pos + 8
            names = []
            for i in range(count):
                if cur >= marker_start or (i % 256 == 0 and cur - names_start != markers[i // 256]):
                    break
                size = image[cur]
                cur += 1
                if size & 128:
                    size = (size & 127) | (image[cur] << 7)
                    cur += 1
                if size == 0 or cur + size > marker_start:
                    break
                names.append(b"".join(tokens[c] for c in image[cur:cur + size]).decode("ascii"))
                cur += size
            if len(names) == count and (cur + 7) & ~7 == marker_start:
                valid.append((pos, names_start, marker_start, markers, names))
    if len(valid) != 1:
        raise ValueError(f"Expected one verified names stream, found {len(valid)}")
    count_start, names_start, marker_start, markers, names = valid[0]
    address_start = (index_start + 512 + 7) & ~7
    count = len(names)
    offsets = struct.unpack_from(f"<{count}I", image, address_start)
    base_pos = (address_start + 4 * count + 7) & ~7
    base = struct.unpack_from("<Q", image, base_pos)[0]
    assert base >> 48 == 0xffff
    assert all(a <= b for a, b in zip(offsets, offsets[1:]))
    records = [dict(name=s[1:], kind=s[0], address=hex(base + offset), relative_offset=offset)
               for s, offset in zip(names, offsets)]
    by_name = {s["name"]: s for s in records}
    assert by_name["_text"]["relative_offset"] == 0
    assert by_name["__start_BTF"]["relative_offset"] == args.btf_offset
    assert image[by_name["linux_banner"]["relative_offset"]:].startswith(b"Linux version ")
    # Sequence table must be a permutation, and sorted by names as generated.
    seq_start = (base_pos + 8 + 7) & ~7
    seq = [int.from_bytes(image[seq_start + 3*i:seq_start + 3*i + 3], "big") for i in range(count)]
    assert sorted(seq) == list(range(count))
    ordered = [names[i][1:] for i in seq]
    assert ordered == sorted(ordered)
    (output / "kallsyms.json").write_text(json.dumps(records, indent=2) + "\n")
    (output / "System.map.recovered").write_text("".join(f"{base + o:016x} {s[0]} {s[1:]}\n" for s, o in zip(names, offsets)))
    targets = [s for s in records if "hmbird" in s["name"]]
    (output / "hmbird-symbols.json").write_text(json.dumps(targets, indent=2) + "\n")
    result = dict(image_sha256=hashlib.sha256(image).hexdigest(), symbol_count=count,
                  hmbird_named_symbols=len(targets), token_table_offset=token_start,
                  token_index_offset=index_start, num_syms_offset=count_start,
                  names_offset=names_start, markers_offset=marker_start,
                  marker_count=len(markers), offsets_offset=address_start,
                  relative_base_offset=base_pos, relative_base=hex(base),
                  seqs_offset=seq_start, sequence_permutation_and_name_sort_verified=True,
                  start_BTF_and_linux_banner_mapping_verified=True,
                  mapping="link-time VA = relative_base + Image file offset for checked symbols; not runtime KASLR addresses",
                  class_symbol=by_name.get("hmbird_sched_class"))
    (output / "kallsyms-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
