import asyncio
import sys
import traceback

from .rsync import RSync
from .syncer import Syncer


def usage(e=''):
    print(
        f"""{e}

USAGE:

--job=<num-jobs> -j<n>  - Parallelize rsync run in number of jobs
... rsync options ...

""",
        file=sys.stderr,
    )
    sys.exit(1)


async def main(argv):
    jobs_num = 6
    verbose = False

    try:
        cut = None
        for i in range(len(argv)):
            a = argv[i]
            if a == '-j' or a == '--jobs':
                jobs_num = int(argv[i + 1])
                cut = (i, i + 2)
                break
            elif a.startswith('-j'):
                jobs_num = int(argv[i][2:])
                cut = (i, i + 1)
            elif a.startswith('--jobs='):
                jobs_num = int(argv[i][7:])
                cut = (i, i + 1)
            elif a == '--help' or a == '-h':
                usage()

            if len(a) > 1 and a[0] == '-' and a[1] != '-' and 'v' in a:
                verbose = True

        if cut:
            argv = argv[0:cut[0]] + argv[cut[1]:]

        if len(argv) < 2:
            raise Exception("Not enough rsync options provided")

    except Exception as e:
        usage(e)

    try:
        with Syncer(jobs_num, RSync(*argv)) as s:
            await s.itemize()
            await s.transfer()

    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        if verbose:
            print(*traceback.format_exception(e), file=sys.stderr)


def synchronize(*argv):
    try:
        asyncio.run(main(argv or sys.argv[1:]))
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)


if __name__ == '__main__':
    synchronize()
