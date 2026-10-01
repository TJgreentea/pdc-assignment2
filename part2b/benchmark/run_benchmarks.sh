#!/usr/bin/env bash
#
# Part 2B benchmark driver.
# Runs each implementation at each thread count, several times, and records
# every individual run (no averaging) to raw_results.csv.
#
set -euo pipefail

# Required OpenMP setting for reproducible thread counts.
export OMP_DYNAMIC=FALSE

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The bench_* executables live in the part2b directory (parent of benchmark/).
BIN_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_CSV="${SCRIPT_DIR}/raw_results.csv"

# Simulation parameters (fixed for this benchmark).
PARTICLES=4000
TIMESTEPS=20
DELTA_T=0.01
OUTPUT_FREQ=20
MODE=g

RUNS_PER_COMBO=5
THREAD_COUNTS=(1 4 8 16 32)
IMPLEMENTATIONS=(bench_basic bench_red_default bench_red_forces_cyclic bench_red_all_cyclic)

# Fresh CSV with header.
printf 'implementation,threads,run,elapsed_seconds\n' > "${OUTPUT_CSV}"

rows_written=0

for impl in "${IMPLEMENTATIONS[@]}"; do
   exec_path="${BIN_DIR}/${impl}"
   if [[ ! -x "${exec_path}" ]]; then
      echo "ERROR: executable not found or not executable: ${exec_path}" >&2
      exit 1
   fi

   for threads in "${THREAD_COUNTS[@]}"; do
      for run in $(seq 1 "${RUNS_PER_COMBO}"); do
         # Stop on execution error (set -e aborts if the program fails).
         output="$("${exec_path}" "${threads}" "${PARTICLES}" "${TIMESTEPS}" "${DELTA_T}" "${OUTPUT_FREQ}" "${MODE}")"

         # Parse only the numeric value: "Elapsed time = <value> seconds".
         elapsed="$(printf '%s\n' "${output}" | sed -n 's/^Elapsed time = \(.*\) seconds[[:space:]]*$/\1/p')"

         if [[ -z "${elapsed}" ]]; then
            echo "ERROR: could not parse elapsed time for ${impl} (threads=${threads}, run=${run})" >&2
            exit 1
         fi
         if [[ ! "${elapsed}" =~ ^[0-9]+([.][0-9]+)?([eE][+-]?[0-9]+)?$ ]]; then
            echo "ERROR: parsed elapsed time is not numeric ('${elapsed}') for ${impl} (threads=${threads}, run=${run})" >&2
            exit 1
         fi

         # Record the value exactly as printed (full precision preserved).
         printf '%s,%s,%s,%s\n' "${impl}" "${threads}" "${run}" "${elapsed}" >> "${OUTPUT_CSV}"
         rows_written=$((rows_written + 1))
      done
   done
done

echo "Wrote ${rows_written} data rows to ${OUTPUT_CSV}"
