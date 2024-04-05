"""Python class to wrap running of rsync binary in asynchroneous way"""
import asyncio
import re


class RSync:
    rsync_cmd = 'rsync'
    args_transfer = [
        '--files-from=-',
        '--info=progress2',
        '--no-v',
        '--no-h',
        '-v'
    ]

    args_itemize = [
        '--dry-run',
        '--itemize-changes',
        '--no-v',
        '--no-h',
        '--info=progress2',
    ]

    def __init__(self, *args) -> None:
        self.opts = list(filter(lambda x: x[0] == '-', args))
        self.args = list(filter(lambda x: x[0] != '-', args))
        self.args_transfer = self.opts + RSync.args_transfer
        self.args_itemize = self.opts + RSync.args_itemize

    def sources(self):
        """all source aguments"""
        return self.args[0:-1]

    def destination(self):
        """destination argiment"""
        return self.args[-1]

    def source(self):
        """common source argument"""
        ret = []
        srcs = self.sources()
        for i in range(0, len(srcs[0].split('/'))):
            p = srcs[0].split('/')[i]
            for s in srcs[1:]:
                if p != s.split('/')[i]:
                    return '/'.join(ret[0:-1])

            ret.append(p)

        if len(ret) > 1:
            return '/'.join(ret[0:-1])

        return '.'

    def get_readlinecr(self):
        async def readlinecr(self):
            """overrides StreamReader.readline to make \r delimiter"""
            sep = b'\r'
            seplen = len(sep)
            try:
                line = await self.readuntil(sep)
            except asyncio.exceptions.IncompleteReadError as e:
                return e.partial
            except asyncio.exceptions.LimitOverrunError as e:
                if self._buffer.startswith(sep, e.consumed):
                    del self._buffer[:e.consumed + seplen]
                else:
                    self._buffer.clear()
                self._maybe_resume_transport()
                raise ValueError(e.args[0])
            return line
        return readlinecr

    def itemize_command(self):
        return [self.rsync_cmd] + self.args + self.args_itemize

    async def read_listing(self, proc, files, callback):
        while buf := await proc.stdout.readline():
            for line in re.split(r'[\r\n]+', buf.decode()):
                if line:
                    if line[0] == ' ':
                        callback(line)
                    else:
                        attr, filename = line[:12], line[13:]

                        # cut trailing slash
                        # (due to different meaning in rsync files-from)
                        if filename[-1] == '/':
                            filename = filename[0:-1]

                        files.append((filename, attr))

        proc._transport.get_pipe_transport(1).close()

    async def itemize(self, progress_callback, error_callback):
        proc = await asyncio.create_subprocess_exec(
                        *self.itemize_command(),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
        )

        files = []
        await asyncio.gather(
            self.read_listing(proc, files, progress_callback),
            self.read_errors(proc, error_callback)
        )

        await proc.wait()

        if proc.returncode != 0:
            raise Exception(
                f'Error collecting list of files for synchronization: '
                f'rc={proc.returncode}'
            )

        return files

    async def feed_input(self, proc, files):
        for f in files:
            proc.stdin.write((f[0] + '\n').encode('utf-8'))
            await proc.stdin.drain()

        proc.stdin.close()

    async def read_progress(self, proc, callback):
        while buf := await proc.stdout.readlinecr():
            for line in re.split(r'[\r\n]+', buf.decode()):
                if line in ("sending incremental file list",
                            "building file list ... done"):
                    continue

                if re.match(
                    r'sent \S+ bytes  received \S+ bytes  \S+ bytes/sec',
                    line
                ):
                    continue

                if re.match(r'total size is \S+  speedup is \S+', line):
                    continue

                if line:
                    callback(line)

        proc._transport.get_pipe_transport(1).close()

    async def read_errors(self, proc, callback):
        while line := await proc.stderr.readline():
            err = line.decode().replace('\n', '')
            callback(err)

        proc._transport.get_pipe_transport(2).close()

    def transfer_command(self):
        return [self.rsync_cmd] + self.args_transfer + \
            [self.source(), self.destination()]

    async def transfer(self, files, progress_callback, error_callback):
        asyncio.StreamReader.readlinecr = self.get_readlinecr()

        proc = await asyncio.create_subprocess_exec(
                        *self.transfer_command(),
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
        )

        await asyncio.gather(
            self.feed_input(proc, files),
            self.read_progress(proc, progress_callback),
            self.read_errors(proc, error_callback)
        )

        await proc.wait()

        if proc.returncode != 0:
            raise Exception(f'Error running rsync: rc={proc.returncode}')
