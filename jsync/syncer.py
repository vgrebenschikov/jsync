import asyncio
import re
from types import TracebackType
from typing import Optional, Type
from humanize import naturalsize
from rich.progress import (
    TaskID,
    Progress,
    SpinnerColumn,
    BarColumn,
    TaskProgressColumn,
)

from .job import Job
from .rsync import RSync
from .columns import FlexiColumn
from .utils import elapsed_time


class Syncer:
    jobs: list
    njobs: int
    total: int
    progress: Progress
    master: TaskID
    rsync: RSync

    def __init__(self, njobs, rsync=None) -> None:
        self.rsync = rsync or RSync()
        self.total = 0

        def sz(size):
            return naturalsize(size, gnu=True)

        def rt(size):
            ret = naturalsize(size, gnu=True)
            return ret + ("/s" if ret[-1].lower() == 'b' else "B/s")

        self.progress = Progress(
            "{task.description}",
            SpinnerColumn(),
            BarColumn(),
            TaskProgressColumn(
                text_format='[bright_magenta]{task.percentage:>3.0f}%'
            ),
            FlexiColumn(
                lambda t: f'{sz(t.completed):>8} / {sz(t.total):<8}',
                style="progress.download",
            ),
            FlexiColumn(lambda t: f'{t.fields["eta"]}', style='cyan'),
            FlexiColumn(
                lambda t: f'{rt(t.fields["rate"]):>12}', style='bright_green'
            ),
            FlexiColumn(
                lambda t: f'  {t.fields["style"]}{t.fields["filename"]:<64}'
            ),
        )

        self.master = self.progress.add_task(
            "total",
            rate=0,
            filename='',
            percent='',
            style='',
            eta='',
        )

        self.jobs = []
        self.njobs = njobs

    def process_progress(self, advance, job):
        rate = sum([j.rate for j in self.jobs])
        size = sum([j.size for j in self.jobs])
        total = sum([j.total for j in self.jobs])

        self.progress.update(
            self.master,
            rate=rate,
            total=total,
            completed=size,
            eta=elapsed_time(total, size, rate),
        )

    def process_itemize_progress(self, line):
        if '%' in line:
            ndone = ntotal = None
            if m := re.search(r'\(xfr#(\d+), ir-chk=(\d+)/(\d+)\)', line):
                size, percent, rate, eta, _, rest = line.split(None, 6)
                ndone = int(m.group(1))
                ntotal = int(m.group(3))
            else:
                return

            task = self.progress._tasks[self.master]
            if task.total != ntotal:
                self.progress.update(
                    self.master, total=ntotal, completed=ndone
                )
            else:
                self.progress.advance(
                    self.master, advance=(ndone - task.completed)
                )

    def process_itemize_error(self, err):
        self.progress.console.print(f"[red][bold]Error[/bold][/red]: {err}")

    async def itemize(self):
        cmd = ' '.join(self.rsync.itemize_command())
        self.progress.console.print(
            "Calculating list of files for synchronization"
        )
        self.progress.console.print(
            f"[bright_cyan]Executing:[/bright_cyan] {cmd}",
            highlight=False,
        )

        files = await self.rsync.itemize(
            progress_callback=self.process_itemize_progress,
            error_callback=self.process_itemize_error,
        )

        if not files:
            raise Exception('Nothing to do - no files to sync')

        size = len(files) // self.njobs
        self.progress.update(self.master, total=len(files))

        for i in range(self.njobs):
            fstart = i * size
            fend = fstart + size if i < self.njobs - 1 else len(files)
            self.jobs.append(
                Job(
                    i + 1,
                    files[fstart:fend],
                    progress=self.progress,
                    rsync=self.rsync,
                    callback=self.process_progress,
                )
            )

    def start(self):
        self.progress.start()

    def __enter__(self):
        self.start()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ):

        self.progress.stop()

    def active(self):
        return any(map(lambda j: j.active(), self.jobs))

    async def transfer(self):
        self.progress.start_task(self.master)

        for j in self.jobs:
            j.start()

        await asyncio.gather(*[job.transfer() for job in self.jobs])
