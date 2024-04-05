import re


def dehumanize_rate(ssize):
    """Converts rate string to number (like 231.89MB/s) of bytes per second """

    m = re.match(r'([\d\.]+)([BKMGTPEZY]?)B/s+$', ssize, flags=re.IGNORECASE)

    if not m:
        raise Exception(f'Wrong rate format {ssize}')

    u = m.group(2)
    ret = float(m.group(1))

    if u != '':
        for unit in "KMGTPEZY":
            ret *= 1000
            if unit == u.upper():
                break

    return ret


def elapsed_time(total, size, rate):
    eta = '  -:--:--'

    if size <= total and rate:
        sec_remaining = int((total - size) / rate)
        minutes, seconds = divmod(sec_remaining, 60)
        hours, minutes = divmod(minutes, 60)
        eta = f"{hours:3d}:{minutes:02d}:{seconds:02d}"

    return eta
