"""Parse human-friendly page range strings into 0-indexed (start, end) tuples."""


def parse_ranges(text: str, total_pages: int) -> list[tuple[int, int]]:
    """
    Parse a string like "1-3, 5, 8-end" into a list of (start, end) tuples
    (0-indexed, inclusive).  Raises ValueError on bad input.
    """
    ranges = []
    for part in (p.strip() for p in text.split(",") if p.strip()):
        if "-" in part:
            sides = part.split("-", 1)
            start_s, end_s = sides[0].strip(), sides[1].strip().lower()

            start = _parse_page(start_s, total_pages)
            end   = total_pages if end_s in ("end", "last") else _parse_page(end_s, total_pages)

            if start > end:
                raise ValueError(f'Range "{part}": start must be ≤ end')
            ranges.append((start - 1, end - 1))
        else:
            page = _parse_page(part, total_pages)
            ranges.append((page - 1, page - 1))

    if not ranges:
        raise ValueError("No valid ranges found")
    return ranges


def _parse_page(s: str, total: int) -> int:
    try:
        n = int(s)
    except ValueError:
        raise ValueError(f'"{s}" is not a valid page number')
    if n < 1:
        raise ValueError(f'Page number must be ≥ 1, got {n}')
    if n > total:
        raise ValueError(f'Page {n} exceeds document length ({total} pages)')
    return n
