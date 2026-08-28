import argparse
from pathlib import Path
import numpy as np
from diefpy import load_trace, plot_all_answer_traces

parser = argparse.ArgumentParser(description="Create evaluations for DIEF")
parser.add_argument("--kg-access-method",)

parser.add_argument("--dir",
                    type=Path,
                    required=True)
parser.add_argument("--at-time",
                    type=float)

if __name__ == "__main__":
    arguments = parser.parse_args()
    traces = list()
    for file in arguments.dir.iterdir():
        if file.suffix == ".csv":
            traces.append(load_trace(file))

    all_traces = np.concatenate(traces)
    for plot in plot_all_answer_traces(all_traces, ["#D62828","#0077B6","#2A9D8F","#6A4C93","#E76F00","#4C9F38","#C2185B","#6D597A"]):
        plot.show()