# JSync - Parallel Rsync Tool

The Parallel Rsync Tool is a powerful utility designed to significantly enhance the performance of synchronizing large file trees between remote hosts using the popular rsync tool. By harnessing parallel execution and leveraging multiple TCP streams, this tool offers substantial improvements in speed and efficiency compared to traditional rsync operations.

## Features

### Parallel Execution

The tool splits the file synchronization process into multiple parts and runs multiple rsync processes concurrently, maximizing resource utilization and reducing overall synchronization time.

### Optimized for Large File Trees

Whether dealing with massive file repositories or extensive directory structures, the tool efficiently handles synchronization tasks of any scale.

### Multiple TCP Streams

By utilizing multiple TCP streams for remote transfer, the tool maximizes network bandwidth usage over multipath networks, further enhancing synchronization speed and performance.

### Progress Reporting

Detailed progress reports provide real-time visibility into the synchronization process, allowing users to monitor the status of each file transfer and overall progress.

## How It Works

### FileList Calculation

The tool first calculates the list of files to be synchronized between the remote hosts, ensuring accuracy and completeness.
It does it running rsync in dry run (-n) mode and gathering output. 

## Partitioning

The file list is partitioned into equal chunks, optimizing the workload distribution for parallel execution.

## Parallel Rsync Execution

Multiple rsync processes are initiated simultaneously, each tasked with synchronizing a specific partition of the file list.
Orchestration: The tool orchestrates the execution of rsync processes, ensuring proper synchronization sequence and resource management.
Progress Reporting: Throughout the synchronization process, detailed progress reports are generated and displayed, keeping users informed about the status of individual transfers and overall progress.
Getting Started

### Installation

Clone the repository, build and install package

```shell
git clone https://github.com/vgrebenschikov/fsync.git
$ cd fsync
$ poetry build
Building jsync (0.1.8)
  - Building wheel
  - Built jsync-0.1.8-py3-none-any.whl
$ pip install dist/jsync-0.1.8-py3-none-any.whl
```

### Execute the tool

```shell
$ jsync --help
... to get help ...

$ jsync -j 8 <rsync-options>
... to execute rsync in 8 jobs parallel
```

Monitor the progress using total progress-bar and rsync progress-bar to track the synchronization process in real-time.

## Contributions and Support

Contributions to the Parallel Rsync Tool are welcome!
Feel free to submit bug reports, feature requests, or pull requests via GitHub.

## License

This project is licensed under the [MIT License](https://en.wikipedia.org/wiki/MIT_License).
