#!/usr/bin/env python3
"""Analyse Part 2B benchmark results.

Reads raw_results.csv, validates it, computes per-implementation per-thread
statistics (mean, sample standard deviation, speedup, efficiency), writes a
long summary plus three wide report-friendly tables, and saves PNG plots.

Usage: python3 analyse_results.py
"""

import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError as exc:
    sys.exit("ERROR: pandas is required to run this script: " + str(exc))

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError as exc:
    sys.exit("ERROR: matplotlib is required to run this script: " + str(exc))


SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_CSV = SCRIPT_DIR / "raw_results.csv"
RESULTS_DIR = SCRIPT_DIR / "results"

IMPLEMENTATIONS = [
    "bench_basic",
    "bench_red_default",
    "bench_red_forces_cyclic",
    "bench_red_all_cyclic",
]
DISPLAY_NAMES = {
    "bench_basic": "Basic",
    "bench_red_default": "Reduced Default",
    "bench_red_forces_cyclic": "Reduced Forces Cyclic",
    "bench_red_all_cyclic": "Reduced All Cyclic",
}
THREAD_COUNTS = [1, 4, 8, 16, 32]
RUNS_PER_COMBO = 5
REQUIRED_COLUMNS = ["implementation", "threads", "run", "elapsed_seconds"]


def abort(errors):
    """Print all validation errors and exit with a failure status."""
    sys.stderr.write("Validation failed:\n")
    for message in errors:
        sys.stderr.write("  - " + message + "\n")
    sys.exit(1)


def format_rows(index):
    """Format a small set of DataFrame row positions as CSV line numbers."""
    labels = [str(int(i) + 2) for i in index[:10]]
    text = ", ".join(labels)
    if len(index) > 10:
        text += ", ..."
    return text


def load_and_validate(path):
    """Load the CSV and run all validation checks. Exits on any problem."""
    if not path.is_file():
        sys.exit("ERROR: input file not found: " + str(path))

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        sys.exit("ERROR: could not read " + str(path) + ": " + str(exc))

    errors = []

    missing = [name for name in REQUIRED_COLUMNS if name not in df.columns]
    if missing:
        errors.append("missing required column(s): " + ", ".join(missing))
    if errors:
        abort(errors)

    df = df[REQUIRED_COLUMNS].copy()

    df["elapsed_seconds"] = pd.to_numeric(df["elapsed_seconds"], errors="coerce")
    bad_elapsed = df["elapsed_seconds"].isna()
    if bad_elapsed.any():
        errors.append("elapsed_seconds has non-numeric value(s) on CSV line(s): "
                      + format_rows(df.index[bad_elapsed]))
    else:
        nonpositive = df["elapsed_seconds"] <= 0
        if nonpositive.any():
            errors.append("elapsed_seconds must be positive; invalid CSV line(s): "
                          + format_rows(df.index[nonpositive]))

    df["threads"] = pd.to_numeric(df["threads"], errors="coerce")
    bad_threads = df["threads"].isna()
    if bad_threads.any():
        errors.append("threads has non-numeric value(s) on CSV line(s): "
                      + format_rows(df.index[bad_threads]))
    else:
        df["threads"] = df["threads"].astype(int)

    present_impls = set(df["implementation"].dropna().astype(str))
    if present_impls != set(IMPLEMENTATIONS):
        errors.append("implementations do not match; expected "
                      + str(sorted(IMPLEMENTATIONS)) + ", found "
                      + str(sorted(present_impls)))

    if not bad_threads.any():
        present_threads = set(df["threads"].tolist())
        if present_threads != set(THREAD_COUNTS):
            errors.append("thread counts do not match; expected "
                          + str(sorted(THREAD_COUNTS)) + ", found "
                          + str(sorted(present_threads)))

    if not errors:
        counts = df.groupby(["implementation", "threads"]).size()
        for impl in IMPLEMENTATIONS:
            for threads in THREAD_COUNTS:
                found = int(counts.get((impl, threads), 0))
                if found != RUNS_PER_COMBO:
                    errors.append("combination " + impl + " / " + str(threads)
                                  + " has " + str(found) + " run(s); expected "
                                  + str(RUNS_PER_COMBO))

    if errors:
        abort(errors)

    return df


def analyse(df):
    """Compute mean, sample std, speedup and efficiency per combination."""
    grouped = df.groupby(["implementation", "threads"])["elapsed_seconds"]
    summary = grouped.agg(
        runs="count",
        mean_seconds="mean",
        std_seconds="std",  # pandas uses ddof=1, i.e. the sample std
    ).reset_index()

    summary = summary.sort_values(
        ["implementation", "threads"]
    ).reset_index(drop=True)

    baselines = dict(
        summary.loc[summary["threads"] == 1,
                    ["implementation", "mean_seconds"]].values
    )
    summary["speedup"] = [
        baselines[row.implementation] / row.mean_seconds
        for row in summary.itertuples(index=False)
    ]
    summary["efficiency"] = summary["speedup"] / summary["threads"]

    summary = summary[
        ["implementation", "threads", "runs", "mean_seconds",
         "std_seconds", "speedup", "efficiency"]
    ]
    return summary


def build_wide(summary, value_column):
    """Pivot one metric into a thread-count by implementation table."""
    wide = summary.pivot(
        index="threads", columns="implementation", values=value_column
    )
    wide = wide.reindex(index=THREAD_COUNTS)
    wide = wide.rename(columns=DISPLAY_NAMES)
    wide = wide[[DISPLAY_NAMES[name] for name in IMPLEMENTATIONS]]
    wide.index.name = "threads"
    return wide


def plot_metric(summary, value_column, title, y_label, output_path, ideal=None):
    """Save one line-and-marker plot for a metric."""
    fig, ax = plt.subplots()

    for impl in IMPLEMENTATIONS:
        subset = summary[summary["implementation"] == impl].sort_values("threads")
        ax.plot(subset["threads"], subset[value_column],
                marker="o", label=DISPLAY_NAMES[impl])

    if ideal == "linear":
        ax.plot(THREAD_COUNTS, THREAD_COUNTS, linestyle="--", label="Ideal")
    elif ideal == "one":
        ax.axhline(1.0, linestyle="--", label="Ideal")

    ax.set_xlabel("Number of Threads")
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.set_xticks(THREAD_COUNTS)
    ax.legend()
    ax.grid(True)

    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def plot_runtime_with_std(summary, output_path):
    """Save a runtime plot with sample-standard-deviation error bars."""
    fig, ax = plt.subplots()

    for impl in IMPLEMENTATIONS:
        subset = summary[summary["implementation"] == impl].sort_values("threads")
        ax.errorbar(subset["threads"], subset["mean_seconds"],
                    yerr=subset["std_seconds"], marker="o", linestyle="-",
                    capsize=4, label=DISPLAY_NAMES[impl])

    ax.set_xlabel("Number of Threads")
    ax.set_ylabel("Mean Execution Time (s)")
    ax.set_title("Runtime vs Number of Threads (with Std Dev)")
    ax.set_xticks(THREAD_COUNTS)
    ax.legend()
    ax.grid(True)

    fig.tight_layout()
    fig.savefig(output_path, dpi=300)
    plt.close(fig)


def main():
    df = load_and_validate(INPUT_CSV)
    summary = analyse(df)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    summary_csv = RESULTS_DIR / "summary.csv"
    runtime_csv = RESULTS_DIR / "runtime_table.csv"
    speedup_csv = RESULTS_DIR / "speedup_table.csv"
    efficiency_csv = RESULTS_DIR / "efficiency_table.csv"
    runtime_png = RESULTS_DIR / "runtime_vs_threads.png"
    speedup_png = RESULTS_DIR / "speedup_vs_threads.png"
    efficiency_png = RESULTS_DIR / "efficiency_vs_threads.png"
    speedup_ideal_png = RESULTS_DIR / "speedup_with_ideal.png"
    runtime_std_png = RESULTS_DIR / "runtime_with_std.png"

    summary_out = summary.copy()
    summary_out["implementation"] = summary_out["implementation"].map(DISPLAY_NAMES)
    summary_out.to_csv(summary_csv, index=False)

    build_wide(summary, "mean_seconds").to_csv(runtime_csv)
    build_wide(summary, "speedup").to_csv(speedup_csv)
    build_wide(summary, "efficiency").to_csv(efficiency_csv)

    plot_metric(summary, "mean_seconds", "Runtime vs Number of Threads",
                "Mean Execution Time (s)", runtime_png)
    plot_metric(summary, "speedup", "Speedup vs Number of Threads",
                "Speedup", speedup_png)
    plot_metric(summary, "speedup", "Speedup vs Number of Threads",
                "Speedup", speedup_ideal_png, ideal="linear")
    plot_runtime_with_std(summary, runtime_std_png)
    plot_metric(summary, "efficiency", "Efficiency vs Number of Threads",
                "Efficiency", efficiency_png, ideal="one")

    print("Input rows: " + str(len(df)))
    print("Analysed combinations: " + str(len(summary)))
    print("CSV files:")
    for path in (summary_csv, runtime_csv, speedup_csv, efficiency_csv):
        print("  " + str(path))
    print("PNG files:")
    for path in (runtime_png, runtime_std_png, speedup_png, speedup_ideal_png,
                 efficiency_png):
        print("  " + str(path))


if __name__ == "__main__":
    main()
