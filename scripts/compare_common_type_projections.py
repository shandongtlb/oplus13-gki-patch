#!/usr/bin/env python3
"""Compare available named common types, recursively through by-value members.

Inputs are JSON from ``bpftool -j btf dump ... format raw``. Only 64-bit ARM64
inputs with 8-byte pointers are supported; this assumption is not inferred from
the JSON. Pointers stop at their representation. This is a limited layout and
scalar representation comparison, not a proof of the complete ABI.
"""
import argparse
import collections
import functools
import hashlib
import json
from pathlib import Path

KINDS = {'STRUCT', 'UNION', 'ENUM', 'ENUM64'}


def load(path):
    types = json.loads(path.read_text())['types']
    by_id = {t['id']: t for t in types}

    @functools.lru_cache(None)
    def signature(index):
        if index == 0:
            return ('VOID',)
        t = by_id[index]
        kind = t['kind']
        if kind in {'TYPEDEF', 'CONST', 'VOLATILE', 'RESTRICT', 'TYPE_TAG'}:
            return signature(t['type_id'])
        if kind == 'PTR':
            return ('PTR', 8)  # Caller must supply 64-bit ARM64 inputs.
        if kind == 'ARRAY':
            return (kind, t['nr_elems'], signature(t['type_id']))
        if kind in {'STRUCT', 'UNION'}:
            return (kind, t['size'], tuple(
                (m['name'], m['bits_offset'], m.get('bitfield_size', 0), signature(m['type_id']))
                for m in t['members']))
        if kind in {'ENUM', 'ENUM64'}:
            return (kind, t['size'], t.get('encoding'),
                    tuple((v['name'], v['val']) for v in t['values']))
        if kind == 'INT':
            return (kind, t['size'], t.get('bits_offset'), t.get('nr_bits'), t.get('encoding'))
        if kind == 'FLOAT':
            return (kind, t['size'])
        raise ValueError(f'Unsupported by-value type: {t}')

    return types, signature


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':')).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stock', required=True, type=Path,
                        help='Stock BTF JSON from bpftool -j btf dump ... format raw')
    parser.add_argument('--candidate', required=True, action='append', type=Path,
                        help='Candidate BTF JSON; repeat for each available input')
    parser.add_argument('--output', required=True, type=Path,
                        help='Output JSON report; parent directories are created as needed')
    args = parser.parse_args()

    stock_path = args.stock
    stock, stock_signature = load(stock_path)
    named_stock = collections.defaultdict(list)
    for t in stock:
        if t['kind'] in KINDS and t['name'] != '(anon)':
            named_stock[t['kind'], t['name']].append(t)
    groups = []
    for path in args.candidate:
        candidate, candidate_signature = load(path)
        records, absent = [], []
        for t in candidate:
            if t['kind'] not in KINDS or t['name'] == '(anon)':
                continue
            options = named_stock[t['kind'], t['name']]
            if not options:
                absent.append({'kind': t['kind'], 'name': t['name'], 'candidate_id': t['id']})
                continue
            sig = candidate_signature(t['id'])
            matching = [v['id'] for v in options if sig == stock_signature(v['id'])]
            records.append({'kind': t['kind'], 'name': t['name'], 'size': t.get('size'),
                            'candidate_id': t['id'], 'stock_ids': [v['id'] for v in options],
                            'matching_stock_ids': matching, 'projection_equal': bool(matching),
                            'candidate_projection_sha256': digest(sig)})
        group = {'candidate_btf': str(path),
                 'candidate_btf_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                 'compared_records': len(records), 'equal_records': sum(x['projection_equal'] for x in records),
                 'candidate_named_types_absent_from_stock': absent, 'records': records}
        groups.append(group)
    result = {'stock_btf': str(stock_path),
              'stock_btf_sha256': hashlib.sha256(stock_path.read_bytes()).hexdigest(),
              'architecture_assumption': '64-bit ARM64 with 8-byte pointers; not inferred from JSON.',
              'method': 'Match kind+name; preserve duplicate stock ids and accept any exactly matching projection. Recurse through by-value aggregates/arrays and scalar encodings; pointers stop at 8-byte representation; strip qualifiers/typedef aliases.',
              'groups': groups,
              'limits': ['Only named types emitted in the supplied candidate inputs are compared, not all common types.',
                         'Does not prove pointer targets, qualifiers, typedef identity, function prototypes, alignment requirements, symbol CRCs, semantic field use or runtime compatibility.',
                         'Absent named types and duplicate ids remain explicit; name matching alone is never counted as equal.',
                         'Exit status is nonzero for compared types with different projections; absent types are reported separately.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps([{k: g[k] for k in ('candidate_btf', 'compared_records', 'equal_records',
                                       'candidate_named_types_absent_from_stock')} for g in groups], indent=2))
    if any(g['compared_records'] != g['equal_records'] for g in groups):
        raise SystemExit('Type projection mismatch; inspect report')


if __name__ == '__main__':
    main()
