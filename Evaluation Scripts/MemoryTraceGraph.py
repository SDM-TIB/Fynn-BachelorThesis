import argparse
from pathlib import Path

import matplotlib.pyplot as plt


def read_dat_file(file_path: Path):
    """Read memory usage and timestamps from a .dat file."""
    memory = []
    timestamps = []

    with file_path.open("r", encoding="utf-8") as file:
        for line in file:
            parts = line.split()

            if len(parts) != 3 or parts[0] != "MEM":
                continue

            try:
                memory.append(float(parts[1]))
                timestamps.append(float(parts[2]))
            except ValueError:
                continue

    if not timestamps:
        raise ValueError(f"No valid MEM entries found in {file_path}")

    # Convert Unix timestamps to elapsed time in seconds.
    start_time = timestamps[0]
    elapsed_time = [timestamp - start_time for timestamp in timestamps]

    return elapsed_time, memory

def calculate_memory_usage(elapsed_time: list[float], memory: list[float]):
    """Calculate peak and average memory consumption.

    Args:
        elapsed_time: Elapsed time in seconds.
        memory: Memory usage at each timestamp, in MiB.

    Returns:
        A tuple containing peak memory (MiB) and average memory (MiB).
    """
    if not memory or len(elapsed_time) != len(memory):
        raise ValueError("Elapsed time and memory must have equal, non-zero lengths.")

    peak_memory = max(memory)

    if len(elapsed_time) == 1 or elapsed_time[-1] == elapsed_time[0]:
        average_memory = memory[0]
    else:
        area = sum(
            (elapsed_time[i] - elapsed_time[i - 1])
            * (memory[i] + memory[i - 1]) / 2
            for i in range(1, len(elapsed_time))
        )

        average_memory = area / (elapsed_time[-1] - elapsed_time[0])

    return peak_memory, average_memory, area

def plot_memory_usage(folder: Path, output: Path, normalize_time: bool = False):
    """Plot memory usage over time for all .dat files in a folder."""
    dat_files = sorted(folder.glob("*.dat"))

    if not dat_files:
        raise FileNotFoundError(f"No .dat files found in {folder}")

    plt.rc('font', size=15)
    # plt.rc('legend', fontsize=10)
    plt.figure(figsize=(12, 7))

    for file_path in dat_files:
        try:
            elapsed_time, memory = read_dat_file(file_path)
        except ValueError as error:
            print(f"Skipping {file_path.name}: {error}")
            continue

        if normalize_time:
            total_runtime = elapsed_time[-1]

            if total_runtime > 0:
                elapsed_time = [
                    timestamp / total_runtime * 100
                    for timestamp in elapsed_time
                ]
            else:
                print(
                    f"Warning: {file_path.name} has zero runtime; "
                    "cannot normalize its time axis."
                )
                continue

        plt.plot(
            elapsed_time,
            memory,
            label=file_path.stem,
            linewidth=2.5,
        )

        elapsed_time, memory = read_dat_file(file_path)

        peak_memory, average_memory, area = calculate_memory_usage(elapsed_time, memory)
        print(file_path.stem)
        print(f"Peak memory: {peak_memory:.2f} MiB")
        print(f"Average memory: {average_memory:.2f} MiB")
        print(f"Area of memory consumption: {area:.2f} MiB")
    plt.xlabel(
        "Runtime (%)" if normalize_time else "Time passed (seconds)",
        fontsize=18
    )
    plt.ylabel("Memory usage (MiB)", fontsize=18)
    plt.title(
        "Memory Traces"
        if normalize_time
        else "Memory Usage Over Time"
        , fontsize=22
    )

    if normalize_time:
        plt.xlim(0, 100)

    # plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0.)
    plt.legend()
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    if output:
        plt.savefig(output, format="pdf")
        print(f"Chart saved to {output}")
    plt.show()

def main():
    parser = argparse.ArgumentParser(
        description="Plot memory usage from .dat files."
    )
    parser.add_argument(
        "--dir",
        type=Path,
        help="Folder containing .dat files",
    )
    parser.add_argument(
        "-o",
        type=Path
    )
    parser.add_argument(
        "--normalize-time",
        action="store_true",
        help="Normalize each run's runtime to a 0–100%% x-axis",
    )
    parser.add_argument(
        "--output",
        type=Path,
    )
    args = parser.parse_args()

    if not args.dir.is_dir():
        parser.error(f"Not a directory: {args.dir}")

    plot_memory_usage(args.dir, args.output, args.normalize_time)


if __name__ == "__main__":
    main()