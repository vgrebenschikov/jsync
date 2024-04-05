import random
import re
from rich.progress import Progress, TaskID

from .rsync import RSync
from .utils import dehumanize_rate, elapsed_time


class Job:
    id: int
    files: list
    progress: Progress
    task: TaskID
    color: int
    running: bool
    rsync: RSync
    file: str
    size: int
    total: int
    percent: float
    rate: str
    callback: callable

    def __init__(
        self,
        id: int,
        files: list,
        progress: Progress,
        rsync: RSync,
        callback: callable,
    ) -> None:
        self.id = id
        self.files = files
        self.progress = progress
        self.rsync = rsync
        self.running = False
        self.color = random.randint(20, 230)
        self.rate = 0
        self.file = ''
        self.percent = 0
        self.size = 0
        self.total = 0
        self.callback = callback
        self.task = progress.add_task(
            f"rsync [bold yellow]#{id}",
            rate=0,
            filename='',
            percent='',
            eta='',
            total=0,
            style=f'[color({self.color})]',
        )

    def start(self):
        self.progress.start_task(self.task)
        cmd = ' '.join(self.rsync.transfer_command())
        self.progress.console.print(
            f"[bright_cyan]Starting job #{self.id}:[/bright_cyan] {cmd}"
        )
        self.running = True

    def active(self):
        return self.running

    def process_progress(self, line):
        # file transferred:
        #   folder1/folder2/IMG_7440.xmp
        # progress reported:
        #  123455332   0%  263.33MB/s    0:00:00 (xfr#2, to-chk=22854/22861)
        #     123345   0%    4.73MB/s    1:05:31
        #    4538368 100%  136.61kB/s    0:00:32 (xfr#554, to-chk=0/557)
        percent = 0
        delta = None
        if line[0] == ' ' and '% ' in line:
            ndone = ntotal = None
            if m := re.search(r'\(xfr#(\d+), to-chk=(\d+)/(\d+)\)', line):
                size, percent, rate, eta, _, rest = line.split(None, 6)
                ndone = int(m.group(1))
                ntotal = int(m.group(3))
            else:
                size, percent, rate, eta = line.split(None, 4)[:4]

            size = int(size)
            percent = int(percent.replace('%', ''))
            self.rate = dehumanize_rate(rate)

            if percent < 10 and ntotal:
                # within 10% - use number of files to estimate progress
                size_percent = 100 * ndone / ntotal
            else:
                size_percent = percent

            if size_percent > 0:
                total = int(size * 100 / size_percent)
                self.percent = percent
                delta = size - self.size
            else:
                percent = total = 0

            if self.total and not total:
                total = self.total

            # print(
            #       f'({self.id}) {line} total={total} size={size} '
            #       f'percent={percent}%({size_percent:4.2f}%) delta={delta} scan={ndone}/{ntotal}'
            # )

            self.progress.update(
                self.task,
                total=total,
                completed=size,
                rate=self.rate,
                eta=elapsed_time(total, size, self.rate),
            )
            self.total = total
            self.size = size

            # Update progress on current file
            self.callback(delta, self)
        else:
            self.file = line
            self.progress.console.print(
                f"[color({self.color})]{line}",
                highlight=False,
            )
            self.progress.update(self.task, filename=self.file)

    def process_error(self, err):
        self.progress.console.print(
            f"[red][bold]{self.id}[/bold][/red] Error: {err}"
        )

    async def transfer(self):
        if not self.files:
            self.progress.console.print(
                f"[bright_red]Job {self.id}: Nothing to do - no files",
                highlight=False,
            )
            return

        await self.rsync.transfer(
            self.files,
            progress_callback=self.process_progress,
            error_callback=self.process_error,
        )
