#!/usr/bin/env python3
"""Compare an AArch64 ET_REL function with a bounded stock Image fragment.

Resolve named relocation destinations only when the recovered stock name is
unique. Section symbols and ambiguous/missing names remain unresolved. This is
a byte comparison aid, not a blanket semantic-equivalence classifier.
"""
import argparse
import hashlib
import json
import struct
from collections import defaultdict
from pathlib import Path

from elftools.elf.elffile import ELFFile

RELOCATIONS = {
    273: "R_AARCH64_LD_PREL_LO19", 274: "R_AARCH64_ADR_PREL_LO21",
    275: "R_AARCH64_ADR_PREL_PG_HI21", 276: "R_AARCH64_ADR_PREL_PG_HI21_NC",
    277: "R_AARCH64_ADD_ABS_LO12_NC", 278: "R_AARCH64_LDST8_ABS_LO12_NC",
    279: "R_AARCH64_TSTBR14", 280: "R_AARCH64_CONDBR19",
    282: "R_AARCH64_JUMP26", 283: "R_AARCH64_CALL26",
    284: "R_AARCH64_LDST16_ABS_LO12_NC", 285: "R_AARCH64_LDST32_ABS_LO12_NC",
    286: "R_AARCH64_LDST64_ABS_LO12_NC", 299: "R_AARCH64_LDST128_ABS_LO12_NC",
}


def encode_relocation(word, kind, pc, target):
    """Apply one supported instruction relocation, checking opcode/alignment/range."""
    if kind in (274, 275, 276):
        opcode = 0x10000000 if kind == 274 else 0x90000000
        assert word & 0x9F000000 == opcode, "unexpected ADR/ADRP opcode"
        delta = target - pc if kind == 274 else ((target >> 12) - (pc >> 12))
        if kind != 276:
            assert -(1 << 20) <= delta < 1 << 20, "ADR/ADRP range overflow"
        imm = delta & ((1 << 21) - 1)
        return (word & ~0x60FFFFE0) | ((imm & 3) << 29) | ((imm >> 2) << 5)
    if kind == 277:
        assert word & 0x7FC00000 == 0x11000000, "unexpected ADD opcode/shift"
        return (word & ~0x003FFC00) | ((target & 0xFFF) << 10)
    if kind in (282, 283):
        opcode = 0x94000000 if kind == 283 else 0x14000000
        assert word & 0xFC000000 == opcode, "unexpected B/BL opcode"
        delta = target - pc
        assert delta % 4 == 0 and -(1 << 27) <= delta < 1 << 27, "B/BL range/alignment"
        return opcode | ((delta >> 2) & 0x03FFFFFF)
    if kind in (273, 279, 280):
        delta = target - pc
        bits = 14 if kind == 279 else 19
        if kind == 279:
            assert word & 0x7E000000 == 0x36000000, "unexpected TBZ/TBNZ opcode"
        elif kind == 280:
            assert (word & 0xFF000010 == 0x54000000 or
                    word & 0x7E000000 == 0x34000000), "unexpected conditional branch opcode"
        else:
            assert word & 0x3B000000 == 0x18000000, "unexpected literal-load opcode"
        assert delta % 4 == 0 and -(1 << (bits + 1)) <= delta < 1 << (bits + 1), "relative range/alignment"
        mask = ((1 << bits) - 1) << 5
        return (word & ~mask) | (((delta >> 2) & ((1 << bits) - 1)) << 5)
    if kind in (278, 284, 285, 286, 299):
        scale = {278: 0, 284: 1, 285: 2, 286: 3, 299: 4}[kind]
        assert word & 0x3B000000 == 0x39000000, "unexpected unsigned-offset LD/ST opcode"
        encoded_scale = (word >> 30) & 3
        vector_q = (word & 0x04000000) and ((word >> 22) & 3) >= 2
        assert scale == (4 if vector_q else encoded_scale), "LD/ST width mismatch"
        assert target % (1 << scale) == 0, "LD/ST target alignment"
        return (word & ~0x003FFC00) | (((target & 0xFFF) >> scale) << 10)
    raise ValueError(f"unsupported relocation type {kind}")


def compare_function(elf, image, stock_symbols, name, stock_address_override=None):
    symbols = elf.get_section_by_name(".symtab")
    matches = [s for s in (symbols.get_symbol_by_name(name) or [])
               if s["st_info"]["type"] == "STT_FUNC"]
    if len(matches) != 1:
        return {"name": name, "status": "unresolved", "reason": "candidate function missing or ambiguous"}
    symbol = matches[0]
    section_index = symbol["st_shndx"]
    if not isinstance(section_index, int):
        return {"name": name, "status": "unresolved", "reason": "candidate function has no defined section"}
    section = elf.get_section(section_index)
    by_name = defaultdict(list)
    for stock_symbol in stock_symbols:
        by_name[stock_symbol["name"]].append(int(stock_symbol["address"], 16))
    assert len(by_name["_text"]) == 1, "missing or ambiguous Image base"
    image_base = by_name["_text"][0]
    if stock_address_override is None:
        if len(by_name[name]) != 1:
            return {"name": name, "status": "unresolved", "reason": "stock function missing or ambiguous"}
        address = by_name[name][0]
    else:
        address = stock_address_override
        assert address in by_name[name], "override must be a recovered address for this exact name"
    start, size = symbol["st_value"], symbol["st_size"]
    assert start % 4 == size % 4 == 0 and size > 0
    assert 0 <= address - image_base <= len(image) - size
    code = bytearray(section.data()[start:start + size])
    relocations, unresolved, excluded_offsets, relocation_offsets = [], [], set(), set()
    for reloc_section in elf.iter_sections():
        if reloc_section["sh_type"] != "SHT_RELA" or reloc_section["sh_info"] != section_index:
            continue
        reloc_symbols = elf.get_section(reloc_section["sh_link"])
        for relocation in reloc_section.iter_relocations():
            offset = relocation["r_offset"] - start
            if not 0 <= offset < size:
                continue
            relocation_offsets.add(offset)
            target_symbol = reloc_symbols.get_symbol(relocation["r_info_sym"])
            target_name = target_symbol.name
            kind = relocation["r_info_type"]
            entry = {"offset": offset, "stock_pc": hex(address + offset),
                     "type": RELOCATIONS.get(kind, str(kind)), "symbol": target_name,
                     "addend": relocation["r_addend"]}
            reason = None
            if target_symbol["st_info"]["type"] == "STT_SECTION":
                reason = "section-symbol target is not mapped speculatively"
                entry["candidate_section"] = elf.get_section(target_symbol["st_shndx"]).name
            elif len(by_name[target_name]) != 1:
                reason = "stock target name missing or ambiguous"
                entry["stock_name_matches"] = [hex(a) for a in by_name[target_name]]
            if reason is None:
                target = by_name[target_name][0] + relocation["r_addend"]
                word = struct.unpack_from("<I", code, offset)[0]
                try:
                    result = encode_relocation(word, kind, address + offset, target)
                except (AssertionError, ValueError) as exc:
                    reason = str(exc)
                else:
                    struct.pack_into("<I", code, offset, result)
                    entry.update(target=hex(target), unlinked_word=f"0x{word:08x}",
                                 linked_word=f"0x{result:08x}")
                    relocations.append(entry)
            if reason is not None:
                entry["reason"] = reason
                unresolved.append(entry)
                excluded_offsets.add(offset)
    # The assembler may resolve a local B/BL to another function in this same
    # input section. Such instructions have no ELF relocation, but their
    # relative distance changes when that target is placed in the stock Image.
    local_targets = defaultdict(list)
    for target_symbol in symbols.iter_symbols():
        if (target_symbol["st_info"]["type"] == "STT_FUNC" and
                target_symbol["st_shndx"] == section_index):
            local_targets[target_symbol["st_value"]].append(target_symbol.name)
    local_branches = []
    for offset in range(0, size, 4):
        if offset in relocation_offsets:
            continue
        word = struct.unpack_from("<I", code, offset)[0]
        if word & 0x7C000000 != 0x14000000:
            continue
        delta = word & 0x03FFFFFF
        if delta & 0x02000000:
            delta -= 1 << 26
        target_offset = start + offset + (delta << 2)
        if start <= target_offset < start + size:
            continue  # internal relative branch; exact word comparison suffices
        entry = {"offset": offset, "stock_pc": hex(address + offset),
                 "type": "encoded_BL" if word & 0x80000000 else "encoded_B",
                 "candidate_target_offset": hex(target_offset)}
        names = local_targets[target_offset]
        if len(names) != 1 or len(by_name[names[0]]) != 1:
            entry.update(reason="encoded out-of-body branch target is not a unique named function entry",
                         candidate_names=names)
            unresolved.append(entry)
            excluded_offsets.add(offset)
            continue
        target = by_name[names[0]][0]
        kind = 283 if word & 0x80000000 else 282
        try:
            result = encode_relocation(word, kind, address + offset, target)
        except AssertionError as exc:
            entry["reason"] = str(exc)
            unresolved.append(entry)
            excluded_offsets.add(offset)
            continue
        struct.pack_into("<I", code, offset, result)
        entry.update(symbol=names[0], target=hex(target),
                     unlinked_word=f"0x{word:08x}", linked_word=f"0x{result:08x}")
        local_branches.append(entry)
    stock = image[address - image_base:address - image_base + size]
    mismatches = []
    matched = 0
    for offset in range(0, size, 4):
        if offset in excluded_offsets:
            continue
        a, b = struct.unpack_from("<I", code, offset)[0], struct.unpack_from("<I", stock, offset)[0]
        if a == b:
            matched += 1
        else:
            mismatches.append({"offset": offset, "stock_pc": hex(address + offset),
                               "candidate_relocated": f"0x{a:08x}", "stock": f"0x{b:08x}"})
    after = [int(s["address"], 16) for s in stock_symbols if int(s["address"], 16) > address]
    span = min(after) - address if after else None
    return {
        "name": name, "status": "different" if mismatches else ("unresolved" if unresolved else "exact_relocated_body"),
        "stock_address": hex(address), "candidate_elf_address": hex(start),
        "candidate_section": section.name, "candidate_elf_size": size,
        "stock_span_to_next_symbol": span, "matched_instruction_words": matched,
        "relocations": relocations, "encoded_local_branches": local_branches,
        "unresolved_relocations": unresolved, "mismatches": mismatches,
        "relocated_candidate_sha256": hashlib.sha256(code).hexdigest(),
        "stock_comparison_range_sha256": hashlib.sha256(stock).hexdigest(),
        "boundary_caveat": "Comparison length is candidate ELF size. Independently inspect stock control flow and its next-symbol bound before treating a matching prefix as a complete body.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--object", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True, help="uncompressed stock ARM64 Image")
    parser.add_argument("--kallsyms", type=Path, required=True, help="recovered stock kallsyms JSON")
    parser.add_argument("--function", action="append", required=True)
    parser.add_argument("--stock-address", type=lambda s: int(s, 0), help="only with one function; resolves duplicate function name")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    assert args.stock_address is None or len(args.function) == 1
    image = args.image.read_bytes()
    assert image[56:60] == b"ARM\x64", "not an uncompressed arm64 Image"
    stock_symbols = json.loads(args.kallsyms.read_text())
    with args.object.open("rb") as f:
        elf = ELFFile(f)
        assert elf["e_machine"] == "EM_AARCH64" and elf["e_type"] == "ET_REL"
        assert elf.elfclass == 64 and elf.little_endian
        results = [compare_function(elf, image, stock_symbols, name, args.stock_address) for name in args.function]
    result = {
        "candidate_object": str(args.object),
        "candidate_object_sha256": hashlib.sha256(args.object.read_bytes()).hexdigest(),
        "stock_image_sha256": hashlib.sha256(image).hexdigest(),
        "stock_kallsyms_sha256": hashlib.sha256(args.kallsyms.read_bytes()).hexdigest(),
        "functions": results,
        "limits": ["A mismatch is not by itself a behavioral difference: compiler register allocation, instruction ordering and layout may differ.",
                   "No recursive callee comparison; unsupported, section-symbol and ambiguous-name relocations remain unresolved.",
                   "Already encoded internal branches are compared at their actual relative offsets; no control-flow similarity heuristic is used."]}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps([{k: f[k] for k in ("name", "status", "matched_instruction_words") if k in f} for f in results], indent=2))
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
