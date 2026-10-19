import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def plot_execution_times(csv_path: Path, output: Path | None = None) -> None:
    with csv_path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.reader(file)
        headers = next(reader, None)

        if not headers or len(headers) < 2:
            raise ValueError(
                "The CSV file must contain an approach column "
                "and at least one step column."
            )

        approaches = []
        step_times = []

        for line_number, row in enumerate(reader, start=2):
            if not row or all(not value.strip() for value in row):
                continue

            if len(row) != len(headers):
                raise ValueError(
                    f"Line {line_number}: expected {len(headers)} "
                    f"columns, got {len(row)}."
                )

            approaches.append(row[0].strip())

            try:
                step_times.append([float(value) for value in row[1:]])
            except ValueError as exc:
                raise ValueError(
                    f"Line {line_number}: execution times must be numeric."
                ) from exc

    if not approaches:
        raise ValueError("The CSV file contains no data rows.")

    if any(value < 0 for row in step_times for value in row):
        raise ValueError("Execution times must not be negative.")

    step_names = headers[1:]
    values = np.array(step_times)
    totals = values.sum(axis=1)

    # Create the stacked bar chart.
    fig, ax = plt.subplots(figsize=(10, 6))

    x = np.arange(len(approaches))
    bottom = np.zeros(len(approaches))

    # Use a distinct color for each processing step.
    colors = plt.get_cmap("tab20")(
        np.linspace(0, 1, len(step_names))
    )

    for i, (step_name, color) in enumerate(zip(step_names, colors)):
        bars = ax.bar(
            x,
            values[:, i],
            bottom=bottom,
            label=step_name,
            color=color,
            edgecolor="white",
            linewidth=0.5,
        )

        # Optionally display the value inside each segment.
        for j, bar in enumerate(bars):
            height = bar.get_height()
            if height > 0 and height >= totals[j] * 0.05:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bottom[j] + height / 2,
                    f"{height:.2f}",
                    ha="center",
                    va="center",
                    fontsize=8,
                )

        bottom += values[:, i]

    ax.set_xticks(x)
    ax.set_xticklabels(approaches)
    ax.set_xlabel("Approach")
    ax.set_ylabel("Execution time (seconds)")
    ax.set_title("Execution Time by Approach")
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    # Display total execution time above each bar.
    for i, total in enumerate(totals):
        ax.annotate(
            f"{total:.2f} s",
            (x[i], total),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax.legend(
        title="Processing step",
        loc="upper left",
    )

    fig.tight_layout()

    if output:
        fig.savefig(output, dpi=300, bbox_inches="tight")
        print(f"Chart saved to {output}")
    else:
        plt.show()

    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a stacked bar chart from execution-time CSV data."
    )
    parser.add_argument(
        "--csv_file",
        type=Path,
        help="Path to the input CSV file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Optional output image path (e.g. chart.png). "
             "If omitted, display the chart interactively.",
    )

    args = parser.parse_args()

    if not args.csv_file.is_file():
        parser.error(f"CSV file does not exist: {args.csv_file}")

    plot_execution_times(args.csv_file, args.output)


if __name__ == "__main__":
    main()