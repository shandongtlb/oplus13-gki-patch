#!/usr/bin/env python3
"""Recover AArch64 PREL32 exports and direct u32 modversion CRCs from an Image.

The matching export/CRC index is the kernel module loader's mapping. Kallsyms
provides section boundaries and independent names/addresses, not CRC values.
Only the Linux 6.6 direct-u32 CRC representation is supported here.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILES = {
    "include/linux/export-internal.h":
        "__KSYM_REF emits self-relative signed 32-bit offsets; SYMBOL_CRC emits .long crc",
    "include/asm-generic/vmlinux.lds.h":
        "ksymtab and kcrctab independently SORT their per-symbol sections by the same suffix",
    "kernel/module/main.c":
        "find_exported_symbol_in_section uses symversion(crcs, sym - start)",
    "kernel/module/version.c":
        "check_version reads crcval = *crc and compares the u32 value",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def label(path):
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def provenance(path):
    data = path.read_bytes()
    return {"path": label(path), "sha256": sha256(data), "bytes": len(data)}


def extract(image, symbols):
    require(image[56:60] == b"ARM\x64", "not an uncompressed arm64 Image")
    by_name = defaultdict(list)
    for symbol in symbols:
        by_name[symbol["name"]].append(int(symbol["address"], 16))

    def unique(name):
        addresses = by_name[name]
        require(len(addresses) == 1, f"missing or ambiguous symbol: {name}")
        return addresses[0]

    base = unique("_text")
    for symbol in symbols:
        require(int(symbol["address"], 16) - base == symbol["relative_offset"],
                f"kallsyms address/offset mismatch: {symbol['name']}")

    def image_offset(address, size=1):
        offset = address - base
        require(0 <= offset <= len(image) - size,
                f"address outside Image: {hex(address)}, size={size}")
        return offset

    def c_string(address):
        offset = image_offset(address)
        end = image.find(b"\0", offset, min(len(image), offset + 1024))
        require(end >= 0, f"unterminated export string at {hex(address)}")
        return image[offset:end].decode("ascii")

    exports, sections = [], []
    recovered_entries = {(s["name"][10:], int(s["address"], 16)) for s in symbols
                         if s["name"].startswith("__ksymtab_")}
    require(len(recovered_entries) == sum(s["name"].startswith("__ksymtab_")
                                        for s in symbols), "duplicate export symbols")
    for suffix, export_type in (("", "EXPORT_SYMBOL"), ("_gpl", "EXPORT_SYMBOL_GPL")):
        start, stop = (unique(prefix + "___ksymtab" + suffix)
                       for prefix in ("__start", "__stop"))
        crc_start, crc_stop = (unique(prefix + "___kcrctab" + suffix)
                               for prefix in ("__start", "__stop"))
        size, crc_size = stop - start, crc_stop - crc_start
        require(start % 4 == crc_start % 4 == 0, "unaligned export/CRC section")
        require(size >= 0 and size % 12 == 0, "invalid PREL32 export section size")
        require(crc_size >= 0 and crc_size % 4 == 0, "invalid u32 CRC section size")
        count = size // 12
        require(count == crc_size // 4, "export/CRC section counts differ")
        offset, crc_offset = image_offset(start, size), image_offset(crc_start, crc_size)
        names = []
        for index in range(count):
            address = start + index * 12
            value_delta, name_delta, namespace_delta = struct.unpack_from(
                "<iii", image, offset + index * 12)
            value_address = address + value_delta
            name_address = address + 4 + name_delta
            namespace_address = address + 8 + namespace_delta
            name, namespace = c_string(name_address), c_string(namespace_address)
            require(re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_.$]*", name) is not None,
                    f"invalid export name: {name!r}")
            require(unique("__ksymtab_" + name) == address,
                    f"export entry disagrees with kallsyms: {name}")
            require(value_address in by_name[name],
                    f"export value disagrees with kallsyms: {name}")
            crc_address = crc_start + index * 4
            crc = struct.unpack_from("<I", image, crc_offset + index * 4)[0]
            names.append(name)
            exports.append({
                "name": name, "namespace": namespace, "export_type": export_type,
                "section": "__ksymtab" + suffix, "section_index": index,
                "entry_address": hex(address), "entry_image_offset": address - base,
                "value_address": hex(value_address),
                "name_address": hex(name_address),
                "namespace_address": hex(namespace_address),
                "crc_address": hex(crc_address), "crc_image_offset": crc_address - base,
                "crc": f"0x{crc:08x}",
            })
        require(names == sorted(names), f"export section is not sorted: {suffix!r}")
        require(len(names) == len(set(names)), f"duplicate names in section: {suffix!r}")
        sections.append({
            "export_section": "__ksymtab" + suffix,
            "export_start": hex(start), "export_stop": hex(stop),
            "export_bytes": size, "export_entry_bytes": 12,
            "export_sha256": sha256(image[offset:offset + size]),
            "crc_section": "__kcrctab" + suffix,
            "crc_start": hex(crc_start), "crc_stop": hex(crc_stop),
            "crc_bytes": crc_size, "crc_entry_bytes": 4,
            "crc_sha256": sha256(image[crc_offset:crc_offset + crc_size]),
            "count": count, "names_sorted": True,
        })
    extracted_entries = {(e["name"], int(e["entry_address"], 16)) for e in exports}
    require(extracted_entries == recovered_entries, "kallsyms export coverage mismatch")
    require(len({e["name"] for e in exports}) == len(exports),
            "duplicate names between export sections")
    return {
        "format": "arm64 little-endian Image; 12-byte PREL32 kernel_symbol; direct u32 CRC",
        "image_virtual_base": hex(base), "export_count": len(exports),
        "namespace_counts": dict(sorted(Counter(e["namespace"] for e in exports).items())),
        "sections": sections,
        "validation": {
            "all_kallsyms_export_entries_covered": True,
            "all_export_names_match_kallsyms": True,
            "all_export_value_addresses_match_kallsyms": True,
            "all_export_and_crc_section_counts_match": True,
            "all_export_sections_sorted": True,
            "crc_mapping": "same index within matching normal or GPL section",
            "crc_values_source": "literal four bytes from stock Image, not inferred from source or candidate",
        },
        "limitations": [
            "CRC agreement is a module-version check, not proof of equal layouts, behavior, or complete kABI.",
            "Export names, namespaces and addresses are recovered independently; CRC order follows the verified section sizes and kernel loader convention.",
            "This report covers the built-in Image export tables only; no vendor modules were inspected.",
        ],
        "exports": exports,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--kallsyms", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config_lines = set(args.config.read_text().splitlines())
    for option in ("CONFIG_64BIT=y", "CONFIG_HAVE_ARCH_PREL32_RELOCATIONS=y", "CONFIG_MODVERSIONS=y"):
        require(option in config_lines, f"unsupported stock configuration: {option} missing")
    require("CONFIG_MODULE_REL_CRCS=y" not in config_lines,
            "relative CRC configuration is not supported")
    report = extract(args.image.read_bytes(), json.loads(args.kallsyms.read_text()))
    report["provenance"] = {
        "image": provenance(args.image), "kallsyms": provenance(args.kallsyms),
        "config": provenance(args.config), "extractor": provenance(Path(__file__)),
        "source_format_references": [dict(provenance(args.source / name), basis=basis)
                                     for name, basis in SOURCE_FILES.items()],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"output": label(args.output), "export_count": report["export_count"],
                      "section_counts": {s["export_section"]: s["count"] for s in report["sections"]}}))


if __name__ == "__main__":
    main()
