def overlaps(left, right):
    return left[0] < right[1] and right[0] < left[1]


def merge(windows):
    result = []
    for start, end in sorted(windows):
        if result and start <= result[-1][1]:
            result[-1][1] = max(end, result[-1][1])
        else:
            result.append([start, end])
    return result


def intersect(first, second):
    return merge((max(a, c), min(b, d)) for a, b in first for c, d in second
                 if max(a, c) < min(b, d))
