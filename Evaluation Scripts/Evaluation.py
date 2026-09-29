import argparse
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from diefpy import load_trace, plot_all_answer_traces, continuous_efficiency_with_diefk, \
    plot_continuous_efficiency_with_diefk, plot_performance_of_approaches_with_dieft, \
    performance_of_approaches_with_dieft

parser = argparse.ArgumentParser(description="Create evaluations for DIEF")
parser.add_argument("--kg-access-method",)
parser.add_argument("--dataset-name")
parser.add_argument("--dir",
                    type=Path,
                    required=True)
parser.add_argument("--type",
                    type=str,
                    choices=("traces", "dief@t", "dief@k"),
                    required=True)
parser.add_argument("--at-time",
                    type=float)

colors = ["#D62828", "#0077B6", "#2A9D8F", "#6A4C93", "#E76F00", "#4C9F38", "#C2185B", "#6D597A"]

def load_traces_dir():
    traces = list()
    for file in arguments.dir.iterdir():
        if file.suffix == ".csv":
            traces.append(load_trace(file))

    return np.concatenate(traces)

def metrics_from_traces(traces):
    metrics = []

    tests = np.unique(traces['test'])

    for test in tests:
        test_traces = traces[traces['test'] == test]
        for approach in np.unique(test_traces['approach']):
            rows = test_traces[test_traces['approach'] == approach]
            metrics.append((test, approach, rows['time'].min(), rows['time'].max(), len(rows)))
    return np.array(metrics, dtype=[('test', traces['test'].dtype), ('approach', traces['approach'].dtype), ('tfft', float), ('totaltime', float), ('comp', int)])

def handle_traces():
    all_traces = load_traces_dir()
    for plot in plot_all_answer_traces(all_traces, colors):
        plt.legend(loc="lower right")
        plot.show()

def handle_dief_t():
    all_traces = load_traces_dir()
    metrics = metrics_from_traces(all_traces)
    exp = performance_of_approaches_with_dieft(all_traces, metrics)
    plot_performance_of_approaches_with_dieft(exp, arguments.dataset_name, colors).show()

def handle_dief_k():
    all_traces = load_traces_dir()
    con_efficiency = continuous_efficiency_with_diefk(all_traces)
    plot_continuous_efficiency_with_diefk(con_efficiency, arguments.dataset_name, colors).show()

if __name__ == "__main__":
    arguments = parser.parse_args()
    match arguments.type:
        case "traces":
            handle_traces()
        case "dief@t":
            handle_dief_t()
        case "dief@k":
            handle_dief_k()