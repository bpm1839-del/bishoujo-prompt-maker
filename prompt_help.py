"""Local translation lookup and tolerant, offset-preserving prompt analysis.

No network access. Preset names take precedence over optional dictionary entries.
"""
from bisect import bisect_right
from dataclasses import dataclass
import math
import re


def canonical(text):
    return ' '.join(text.split()).casefold()


def validate_translations(data):
    if not isinstance(data, dict) or any(not isinstance(k, str) or not k.strip() or not isinstance(v, str) or not v.strip() for k, v in data.items()):
        raise ValueError('翻訳辞書は英語タグと日本語訳の文字列マップで指定してください')
    return data


@dataclass(frozen=True)
class HoverTag:
    start: int
    end: int
    text: str
    weight: float = 1.0
    weighted: bool = False


def prompt_spans(text):
    """Split commas/newlines outside balanced groups; descend into emphasis.

    Escaped punctuation is literal. Unmatched brackets remain literal rather
    than swallowing the rest of a manually edited prompt. Max nesting is 64.
    Scheduling syntax is deliberately left as an unknown literal token.
    """
    pairs, stack = {}, []
    closing = {')': '(', ']': '[', '>': '<'}
    escaped = False
    for i, ch in enumerate(text):
        if escaped:
            escaped = False
            continue
        if ch == '\\':
            escaped = True
        elif ch in '([<':
            stack.append((ch, i))
        elif ch in closing and stack and stack[-1][0] == closing[ch]:
            _, start = stack.pop()
            pairs[start] = i
    result = []

    def walk(start, end, weight=1.0, weighted=False, level=0):
        while start < end and text[start].isspace(): start += 1
        while end > start and text[end-1].isspace(): end -= 1
        if start >= end: return
        if level >= 64:
            result.append(HoverTag(start, end, text[start:end], weight, weighted))
            return
        # Use the same balanced-group/escaped-comma semantics as core.split_tags.
        chunks, left, i = [], start, start
        while i < end:
            if text[i] == '\\':
                i += 2
                continue
            if i in pairs and pairs[i] < end:
                i = pairs[i] + 1
                continue
            if text[i] in ',\r\n':
                chunks.append((left, i))
                left = i + 1
            i += 1
        if chunks:
            chunks.append((left, end))
            for a, b in chunks: walk(a, b, weight, weighted, level+1)
            return
        if text[start] in '([' and pairs.get(start) == end-1:
            inner_start, inner_end = start+1, end-1
            factor, explicit = 1.0, False
            if text[start] == '(':
                match = re.search(r':([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*$', text[inner_start:inner_end])
                if match:
                    preceding = text[inner_start:inner_start+match.start()]
                    if (len(preceding)-len(preceding.rstrip('\\')))%2:match = None
                if match:
                    number = float(match.group(1))
                    if math.isfinite(number) and math.isfinite(weight*number):
                        factor, explicit = number, True
                        inner_end = inner_start + match.start()
            # Scheduling expressions are not treated as ordinary square emphasis.
            if text[start] == '[' and ':' in text[inner_start:inner_end]:
                result.append(HoverTag(start, end, text[start:end], weight, weighted))
                return
            before = len(result)
            walk(inner_start, inner_end, weight*factor, weighted or explicit, level+1)
            if len(result) == before+1:
                tag = result[-1]
                result[-1] = HoverTag(start, end, tag.text, tag.weight, tag.weighted)
            return
        result.append(HoverTag(start, end, text[start:end], weight, weighted))

    walk(0, len(text))
    return result


def tag_at(spans, offset, starts=None):
    starts = starts if starts is not None else [s.start for s in spans]
    index = bisect_right(starts, offset)-1
    if index >= 0 and spans[index].start <= offset < spans[index].end:
        return spans[index]
    return None


class TranslationIndex:
    def __init__(self, rows, extras=None):
        self.extras = {canonical(k): v for k, v in validate_translations(extras or {}).items()}
        self.rebuild(rows)

    def rebuild(self, rows):
        self.maps = {}
        for target in ('positive', 'negative'):
            ordered = [r for r in rows if r['target'] == target] + [r for r in rows if r['target'] != target]
            exact, fragments = {}, {}
            for r in ordered:
                # Strip numeric emphasis using the same analyzer as the hover.
                atoms = prompt_spans(r['en'])
                if len(atoms) == 1:
                    exact.setdefault(canonical(atoms[0].text), r['ja'])
                exact.setdefault(canonical(r['en']), r['ja'])
                for atom in atoms:
                    fragments.setdefault(canonical(atom.text), r['ja']+'（複合プリセットの一部）' if len(atoms)>1 else r['ja'])
            self.maps[target] = (exact, fragments)

    def lookup(self, tag, target):
        exact, fragments = self.maps[target]
        key = canonical(tag.text)
        label = exact.get(key, fragments.get(key, self.extras.get(key, '日本語訳未登録')))
        if tag.weighted:
            label += f'（強調度{tag.weight:.6g}）'
        return label


def popup_position(pointer_x, pointer_y, width, height, bounds):
    left, top, right, bottom = bounds
    x, y = pointer_x+14, pointer_y+20
    if x+width > right: x = pointer_x-width-10
    if y+height > bottom: y = pointer_y-height-10
    return (max(left, min(x, max(left, right-width))),
            max(top, min(y, max(top, bottom-height))))
