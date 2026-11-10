"""Hunk matching and application.

Split out of ``apex.apply_patch`` so that the package keeps one
responsibility per module.
"""

from __future__ import annotations

from .apply_patch_types import PatchError, _Hunk

__all__ = [
    "_apply_hunks",
    "_detect_eol",
    "_find_match",
    "_join_lines",
    "_match_all_hunks",
    "_new_block",
    "_old_block",
    "_split_lines",
]


def _old_block(hunk: _Hunk) -> list[str]:
    return [text for prefix, text in hunk.ops if prefix in (" ", "-")]


def _new_block(hunk: _Hunk) -> list[str]:
    return [text for prefix, text in hunk.ops if prefix in (" ", "+")]


def _forward_positions(total: int, width: int, start: int) -> list[int]:
    """The positions to try, forwards first."""
    candidates = list(range(start, total - width + 1))
    candidates.extend(range(start - 1, -1, -1))
    return candidates


def _centred_positions(total: int, width: int, start: int) -> list[int]:
    """The positions to try, around the expected one."""
    candidates = []
    max_distance = max(start, total - width - start)
    for distance in range(max_distance + 1):
        after = start + distance
        before = start - distance
        if after <= total - width:
            candidates.append(after)
        if distance and before >= 0:
            candidates.append(before)
    return candidates


def _candidate_positions(total: int, width: int, start: int, prefer_forward: bool) -> list[int]:
    """The positions to try, in the order the caller prefers."""
    if prefer_forward:
        return _forward_positions(total, width, start)
    return _centred_positions(total, width, start)


def _find_match(
    lines: list[str],
    block: list[str],
    expected: int,
    *,
    prefer_forward: bool,
) -> int | None:
    """The position of *block* in *lines*, or ``None``."""
    total = len(lines)
    width = len(block)
    if width == 0:
        return min(max(expected, 0), total)
    if width > total:
        return None

    start = min(max(expected, 0), total - width)
    for position in _candidate_positions(total, width, start, prefer_forward):
        if lines[position : position + width] == block:
            return position
    return None


def _match_all_hunks(
    old_text: str, hunks: list[_Hunk], relative: str, *, codex: bool
) -> list[tuple[int, int, list[str], _Hunk, int]]:
    """Locate every hunk in the source text."""
    lines = _split_lines(old_text)
    matched: list[tuple[int, int, list[str], _Hunk, int]] = []
    cursor = 0
    for number, hunk in enumerate(hunks, start=1):
        block = _old_block(hunk)
        expected = _expected_position(hunk, cursor)
        found = _find_match(lines, block, expected, prefer_forward=codex)
        if found is None:
            raise PatchError(
                "context_mismatch",
                f"hunk {number} does not match the current file content",
                relative,
            )
        matched.append((found, found + len(block), _new_block(hunk), hunk, number))
        cursor = found + len(block)

    _reject_overlapping_hunks(matched, relative)
    return matched


def _expected_position(hunk: _Hunk, cursor: int) -> int:
    """Where the hunk is expected, from its header or from the previous one."""
    if hunk.old_start is None:
        return cursor
    return hunk.old_start if hunk.old_count == 0 else hunk.old_start - 1


def _reject_overlapping_hunks(
    matched: list[tuple[int, int, list[str], _Hunk, int]], relative: str
) -> None:
    """Refuse hunks that modify overlapping regions."""
    ordered = sorted(matched, key=lambda item: (item[0], item[1]))
    previous_start = -1
    previous_end = -1
    for start, end, _, _, _ in ordered:
        if start < previous_end:
            raise PatchError(
                "overlapping_hunks",
                "two hunks modify overlapping regions",
                relative,
            )
        if start == previous_start == end == previous_end and start == end:
            raise PatchError(
                "overlapping_hunks",
                "two insertion hunks target the same position",
                relative,
            )
        previous_start, previous_end = start, end


def _apply_hunks(old_text: str, hunks: list[_Hunk], relative: str) -> tuple[str, list[str]]:
    """Apply every hunk to the source text."""
    lines = _split_lines(old_text)
    codex = all(hunk.old_start is None for hunk in hunks)
    matched = _match_all_hunks(old_text, hunks, relative, codex=codex)

    # Explicit line numbers only exist in unified diffs.  Report fuzz visibly.
    warnings = _fuzz_warnings(matched, relative)

    ordered = sorted(matched, key=lambda item: (item[0], item[1]))
    output: list[str] = []
    position = 0
    for start, end, replacement, _hunk, _number in ordered:
        output.extend(lines[position:start])
        output.extend(replacement)
        position = end
    output.extend(lines[position:])

    final_newline = _final_newline(old_text, output, ordered, len(lines))
    eol = _detect_eol(old_text)
    return _join_lines(output, eol, final_newline), warnings


def _fuzz_warning(relative: str, number: int, start: int, expected: int) -> str:
    """The warning that reports one hunk landing away from its position."""
    return f"{relative}: hunk {number} applied at line {start + 1} (offset {start - expected:+d})"


def _fuzz_warnings(
    matched: list[tuple[int, int, list[str], _Hunk, int]], relative: str
) -> list[str]:
    """Report the hunks that landed away from their declared position."""
    warnings: list[str] = []
    for start, _end, _replacement, hunk, number in matched:
        if hunk.old_start is None:
            continue
        expected = hunk.old_start if hunk.old_count == 0 else hunk.old_start - 1
        if start != expected:
            warnings.append(_fuzz_warning(relative, number, start, expected))
    return warnings


def _last_hunk_at_end(
    ordered: list[tuple[int, int, list[str], _Hunk, int]], line_count: int
) -> _Hunk | None:
    """The hunk that touches the end of the file, if any."""
    end_hunks = [item for item in ordered if item[1] == line_count]
    if not end_hunks:
        return None
    return end_hunks[-1][3]


def _last_output_prefix(hunk: _Hunk) -> str | None:
    """The prefix of the last line the hunk keeps."""
    return next((prefix for prefix, _ in reversed(hunk.ops) if prefix != "-"), None)


def _last_source_prefix(hunk: _Hunk) -> str | None:
    """The prefix of the last line of the source."""
    return hunk.ops[-1][0] if hunk.ops else None


def _newline_after_last_hunk(hunk: _Hunk, old_final_newline: bool) -> bool:
    """The trailing-newline state the patched file ends with."""
    if hunk.new_no_newline:
        return False
    last_output = _last_output_prefix(hunk)
    if last_output == "+":
        return True
    if last_output == " ":
        # A context line that is still the final source line keeps the
        # source's trailing-newline state.  If it was followed by
        # removed lines, the context line necessarily had a newline.
        return old_final_newline if _last_source_prefix(hunk) == " " else True
    # The hunk removed the trailing lines; the remaining line came
    # from earlier in the file and therefore had a newline.
    return True


def _final_newline(
    old_text: str,
    output: list[str],
    ordered: list[tuple[int, int, list[str], _Hunk, int]],
    line_count: int,
) -> bool:
    """Whether the patched file keeps a trailing newline."""
    old_final_newline = old_text.endswith(("\n", "\r"))
    if not output:
        return False
    last_hunk = _last_hunk_at_end(ordered, line_count)
    if last_hunk is None:
        return old_final_newline
    return _newline_after_last_hunk(last_hunk, old_final_newline)


def _split_lines(text: str) -> list[str]:
    """Split a text into lines, without the trailing empty one."""
    if not text:
        return []
    normalised = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalised.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _detect_eol(text: str) -> str:
    if "\r\n" in text:
        return "\r\n"
    if "\n" in text:
        return "\n"
    if "\r" in text:
        return "\r"
    return "\n"


def _join_lines(lines: list[str], eol: str, final_newline: bool) -> str:
    if not lines:
        return ""
    text = eol.join(lines)
    return text + eol if final_newline else text
