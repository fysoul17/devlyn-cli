def parse_selection(text):
    if not text.strip():
        return []
    result = []
    for part in text.split(','):
        if '-' in part:
            start, end = map(int, part.split('-'))
            result.extend(range(start, end + 1))
        else:
            result.append(int(part))
    return sorted(set(result))
