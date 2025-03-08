import asyncio
import re
from types import TracebackType
from typing import Optional, Type, List
from humanize import naturalsize
from rich.console import Console
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
from .utils import elapsed_time, transfer_rate


class Syncer:
    jobs: List[Job]
    njobs: int
    total: int
    progress: Progress
    master: TaskID
    rsync: RSync

    def __init__(self, njobs, rsync=None) -> None:
        self.rsync = rsync or RSync()
        self.total = 0

        self.jobs = []
        self.njobs = njobs
        self.console = Console()
        self.progress = None

    def init_progress(self):
        def sz(size):
            return naturalsize(size, gnu=True)

        self.progress = Progress(
            "{task.description}",
            SpinnerColumn(),
            BarColumn(),
            TaskProgressColumn(text_format='[bright_magenta]{task.percentage:>3.0f}%'),
            FlexiColumn(
                lambda t: f'{sz(t.completed):>8} / {sz(t.total):<8}',
                style="progress.download",
            ),
            FlexiColumn(lambda t: f'{t.fields["eta"]:>10}', style='cyan'),
            FlexiColumn(lambda t: f'{transfer_rate(t.fields["rate"]):>12}', style='bright_green'),
            FlexiColumn(lambda t: f'  {t.fields["style"]}{t.fields["filename"]:<64}'),
        )

        self.master = self.progress.add_task(
            "total",
            rate=0,
            filename='',
            percent='',
            style='',
            eta='',
        )

        self.progress.start()

    def process_progress(self, advance, job):
        if not self.progress:
            self.init_progress()

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
        if not self.progress:
            self.init_progress()

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
                self.progress.update(self.master, total=ntotal, completed=ndone)
            else:
                self.progress.advance(self.master, advance=(ndone - task.completed))

    def process_itemize_error(self, err):
        if not self.progress:
            self.init_progress()

        self.progress.console.print(f"[red][bold]Error[/bold][/red]: {err}")

    async def itemize(self):
        cmd = ' '.join(self.rsync.itemize_command())
        self.console.print("Calculating list of files for synchronization")
        self.console.print(
            f"[bright_cyan]Executing:[/bright_cyan] {cmd}",
            highlight=False,
        )

        files = await self.rsync.itemize(
            progress_callback=self.process_itemize_progress,
            error_callback=self.process_itemize_error,
        )

        if not files:
            raise Exception('Nothing to do - no files to sync')

        if not self.progress:
            self.init_progress()

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
        if not self.progress:
            self.init_progress()

        self.progress.start()

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ):
        if self.progress:
            self.progress.stop()

    def active(self):
        return any(map(lambda j: j.active(), self.jobs))

    async def transfer(self):
        if not self.progress:
            self.init_progress()

        self.progress.start_task(self.master)

        for j in self.jobs:
            j.start()

        result = await asyncio.gather(
            *[job.transfer() for job in self.jobs], return_exceptions=True
        )

        nerrors = 0
        for r, j in zip(result, self.jobs):
            if isinstance(r, Exception):
                nerrors += 1
                self.progress.console.print(
                    f'[bright_red][bold]Job #{j.id} Error: {r}[/bold][/bright_red]\n',
                    j.error_buf,
                )

        if nerrors:
            raise Exception(f'{nerrors} rsyncs failed')
