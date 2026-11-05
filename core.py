"""Data operations for v1.2; compatible with v1.0/v1.1 JSON."""
import copy
import json
import math
import os
import random
import re
import tempfile
from pathlib import Path

TABS = ['キャラクター', '衣装', 'ポーズ・構図', '背景・雰囲気', '画質・生成設定']
WEIGHT_VALUES = tuple(round(n / 10, 1) for n in range(5, 16))


def atomic_save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def weight_value(value):
    if isinstance(value, bool):
        raise ValueError('強調度は0.5〜1.5、0.1刻みで指定してください')
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        raise ValueError('強調度は数値で指定してください') from None
    if not math.isfinite(number) or not 0.5 <= number <= 1.5 or abs(number * 10 - round(number * 10)) > 1e-8:
        raise ValueError('強調度は0.5〜1.5、0.1刻みで指定してください')
    return round(number, 1)


def validate_weights(weights):
    if not isinstance(weights, dict) or any(not isinstance(k, str) for k in weights):
        raise ValueError('強調度データが不正です')
    return {k: weight_value(v) for k, v in weights.items()}


def validate(rows):
    if not isinstance(rows, list):
        raise ValueError('プリセットは配列が必要です')
    ids = set()
    for r in rows:
        if not isinstance(r, dict) or any(not isinstance(r.get(k), str) for k in ['id', 'tab', 'category', 'ja', 'en', 'target', 'group']):
            raise ValueError('プリセット形式が不正です')
        if (r['id'] in ids or not r['id'] or not r['ja'].strip() or not r['en'].strip()
                or not r['category'].strip() or r['tab'] not in TABS or r['target'] not in ['positive', 'negative']):
            raise ValueError('プリセットの値が不正です')
        r['weight'] = weight_value(r.get('weight', 1.0))
        ids.add(r['id'])
    return rows


def migrate_presets(rows, defaults, from_version=0):
    """Add only entries introduced after the saved catalog version."""
    result = copy.deepcopy(validate(rows))
    ids = {r['id'] for r in result}
    tags = {(r['target'], r['en'].strip().casefold()) for r in result}
    names = {(r['target'], r['tab'], r['category'], r['ja'].strip().casefold()) for r in result}
    for r in defaults:
        key = (r['target'], r['en'].strip().casefold())
        name = (r['target'], r['tab'], r['category'], r['ja'].strip().casefold())
        match = re.match(r'builtin_v(\d+)_', r['id'])
        introduced = int(match.group(1)) if match else 0
        if introduced > from_version and r['id'] not in ids and key not in tags and name not in names:
            result.append(copy.deepcopy(r))
            ids.add(r['id'])
            tags.add(key)
            names.add(name)
    return result


STRICT_GROUPS = ('年齢', '身長', '体型', 'バストサイズ')
STRICT_TAG_GROUPS = {
    'teenage': '年齢', 'early 20s': '年齢', 'late 20s': '年齢', '30s': '年齢',
    'petite': '身長', 'average height': '身長', 'tall woman': '身長',
    'slim body': '体型', 'average body': '体型', 'curvy body': '体型',
    'small breasts': 'バストサイズ', 'medium breasts': 'バストサイズ', 'large breasts': 'バストサイズ',
}


def strict_group(row):
    if row['target'] != 'positive' or row['tab'] != 'キャラクター':
        return ''
    # Equivalent older user presets keep their IDs and fields, but participate
    # in the same single-selection rule as the new built-ins.
    return STRICT_TAG_GROUPS.get(row['en'].strip().casefold(),
                                 row['group'] if row['group'] in STRICT_GROUPS else (row['category'] if row['category'] in STRICT_GROUPS else ''))


def normalize_selection(rows, selected, locks=()):
    """Repair conflicting imported selections in memory; never alter JSON here."""
    result = set(selected)
    used = set()
    ordered = sorted(enumerate(rows), key=lambda pair: (pair[1]['id'] not in locks, pair[0]))
    for _, r in ordered:
        group = strict_group(r)
        if r['id'] in result and group:
            if group in used:
                result.discard(r['id'])
            else:
                used.add(group)
    return result


def set_selected(rows, selected, item_id, on=True):
    """Manual selection: the last chosen entry replaces its group's old choice."""
    result = set(selected)
    row = next((r for r in rows if r['id'] == item_id), None)
    if not on:
        result.discard(item_id)
    elif row is not None:
        group = strict_group(row)
        if group:
            result.difference_update(r['id'] for r in rows if strict_group(r) == group)
        result.add(item_id)
    return result


def split_tags(text):
    """Don't break parenthesized groups or escaped punctuation."""
    parts, current = [], []
    depth = 0
    escaped = False
    for ch in text:
        if escaped:
            current.append(ch)
            escaped = False
            continue
        if ch == '\\':
            current.append(ch)
            escaped = True
            continue
        if ch in '([<':
            depth += 1
        elif ch in ')]>':
            depth = max(0, depth - 1)
        if ch == ',' and depth == 0:
            if ''.join(current).strip():
                parts.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
    if ''.join(current).strip():
        parts.append(''.join(current).strip())
    return parts


def bare_tag(tag):
    match = re.fullmatch(r'\((.*):[0-9]+(?:\.[0-9]+)?\)', tag.strip())
    return (match.group(1) if match else tag.strip()).casefold()


def conflicts(rows, selected):
    groups, warnings, pos, neg = {}, [], set(), set()
    for r in rows:
        if r['id'] not in selected:
            continue
        (pos if r['target'] == 'positive' else neg).update(bare_tag(t) for t in split_tags(r['en']))
        if r['group'] and r['target'] == 'positive':
            group=r['group']
            if group=='基本服' and r['tab']=='衣装':
                tag=r['en'].casefold()
                if any(t in tag for t in ('coat','cape','poncho')):group+='・上着'
                elif any(t in tag for t in ('jacket','blazer','vest')):group+='・羽織り'
                elif any(t in tag for t in ('sweater','cardigan','turtleneck')) and 'dress' not in tag:group+='・ニット'
                elif any(t in tag for t in ('dress','gown','overalls','jumpsuit')):group+='・ワンピース'
                else:group+='・トップス'
            groups.setdefault(group, []).append(r['ja'])
    for group, names in groups.items():
        if len(names) > 1:
            warnings.append(group + '：' + ' / '.join(names))
    if 'solo' in pos and pos & {'2girls', '3girls', 'multiple girls'}:
        warnings.append('人数：単独と複数人が同時に選択されています')
    warnings.extend('Positive/Negativeの両方：' + tag for tag in sorted(pos & neg))
    return warnings


def randomize(rows, selected, locks, categories, rng=None):
    rng = rng or random.Random()
    known = {r['id']: r for r in rows}
    selected = normalize_selection(rows, selected, locks)
    result = {i for i in selected if i in locks and i in known}
    used = {strict_group(known[i]) or known[i]['group'] for i in result if (strict_group(known[i]) or known[i]['group']) and known[i]['target'] == 'positive'}
    for tab, cat in categories:
        if any(known[i]['tab'] == tab and known[i]['category'] == cat for i in result):
            continue
        choices = [r for r in rows if r['tab'] == tab and r['category'] == cat
                   and r['target'] == 'positive' and r.get('randomizable', True)
                   and r['id'] not in locks and (not (strict_group(r) or r['group']) or (strict_group(r) or r['group']) not in used)]
        if choices:
            r = rng.choice(choices)
            result.add(r['id'])
            if strict_group(r) or r['group']:
                used.add(strict_group(r) or r['group'])
    return result


def generate(rows, selected, model, weights=None, colors=None):
    if colors:
        from features import colorize_rows
        rows = colorize_rows(rows, colors)
    weights = weights or {}
    selected = normalize_selection(rows, selected)
    picked = [r for r in rows if r['id'] in selected]
    prefix = model.get('prefix', '')
    if any(r['target'] == 'positive' and r['en'] in ('2girls', '3girls', 'multiple girls') for r in picked):
        prefix = ', '.join(t for t in split_tags(prefix) if bare_tag(t) not in ('1girl', 'solo'))

    def output(target, before, after):
        result = {}
        def insert(text, weight=1.0, explicit=False):
            for tag in split_tags(text):
                key = bare_tag(tag)
                rendered = tag if weight == 1.0 else f'({tag}:{weight:.1f})'
                # User-selected presets override unweighted model defaults.
                # First selected occurrence wins for overlapping combination presets.
                if key not in result or (explicit and not result[key][1]):
                    result[key] = (rendered, explicit)
        insert(before)
        for r in picked:
            if r['target'] == target:
                insert(r['en'], weight_value(weights.get(r['id'], r.get('weight', 1.0))), True)
        insert(after)
        return ', '.join(value[0] for value in result.values())

    return (output('positive', prefix, model.get('suffix', '')),
            output('negative', model.get('negative', ''), ''))


def preset_prompt(row, weight=None, colors=None):
    """Use normal generation without model defaults or other selected presets."""
    weights = {} if weight is None else {row['id']: weight_value(weight)}
    positive, negative = generate([row], {row['id']}, {}, weights, colors)
    return positive if row['target'] == 'positive' else negative
