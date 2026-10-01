# PDC Assignment 2 — OpenMP N-Body Simulation

## Repository

Repository: [https://github.com/TJgreentea/pdc-assignment2](https://github.com/TJgreentea/pdc-assignment2)

Part 2A implements two synchronization strategies for shared-force accumulation: an OpenMP critical section and per-particle OpenMP locks. Part 2B compares four OpenMP N-body implementations and scheduling variants: Basic, Reduced — Default Scheduling, Reduced — Forces Cyclic, and Reduced — All Cyclic.

## Development Environment

The assignment was tested using the supplied PDC Dev Container:

- Image: `ghcr.io/uadelaide/pdc:2026.S2.0`
- Linux x86_64
- GCC 11.4.0
- OpenMP
- 8 logical CPUs visible during the benchmark

The required 16- and 32-thread benchmark configurations therefore use oversubscription on this tested environment. Other environments may also be suitable.

## Repository Structure

```text
part2a/
  nbody_shared_forces.c
  part2a_critical.c
  part2a_locks.c
  timer.h
  validation/

part2b/
  omp_nbody_basic.c
  omp_nbody_red.c
  omp_nbody_red_default.c
  omp_nbody_red_all_cyclic.c
  validation/
  benchmark/
    run_benchmarks.sh
    raw_results.csv
    analyse_results.py
    results/
```

## Part 2A — Build and Run

Run these commands from `part2a/`.

Compile:

```sh
gcc -g -Wall -fopenmp -o part2a_critical part2a_critical.c -lm
gcc -g -Wall -fopenmp -o part2a_locks part2a_locks.c -lm
```

Run syntax:

```text
./part2a_critical <threads> <particles> <timesteps> <delta_t> <output_freq> <g|i>
./part2a_locks <threads> <particles> <timesteps> <delta_t> <output_freq> <g|i>
```

Example:

```sh
./part2a_critical 4 8 5 0.01 5 g
./part2a_locks 4 8 5 0.01 5 g
```

`g` generates initial conditions; `i` reads initial conditions from stdin.

**Validation:** The Part 2A implementations were validated with multiple OpenMP thread counts against the supplied shared-force reference implementation. Validation records are stored under `part2a/validation/`.

## Part 2B — Build

Run these commands from `part2b/`.

Normal output builds:

```sh
gcc -g -Wall -fopenmp -o omp_nbody_basic omp_nbody_basic.c -lm
gcc -g -Wall -fopenmp -o omp_nbody_red_default omp_nbody_red_default.c -lm
gcc -g -Wall -fopenmp -o omp_nbody_red omp_nbody_red.c -lm
gcc -g -Wall -fopenmp -o omp_nbody_red_all_cyclic omp_nbody_red_all_cyclic.c -lm
```

### Benchmark Builds

Detailed simulation output is disabled with `NO_OUTPUT`. Use these executable names because `run_benchmarks.sh` expects them:

```sh
gcc -g -Wall -fopenmp -DNO_OUTPUT -o bench_basic omp_nbody_basic.c -lm
gcc -g -Wall -fopenmp -DNO_OUTPUT -o bench_red_default omp_nbody_red_default.c -lm
gcc -g -Wall -fopenmp -DNO_OUTPUT -o bench_red_forces_cyclic omp_nbody_red.c -lm
gcc -g -Wall -fopenmp -DNO_OUTPUT -o bench_red_all_cyclic omp_nbody_red_all_cyclic.c -lm
```

## Part 2B — Performance Experiment

The reported benchmark uses 4000 particles, 20 timesteps, `delta_t` 0.01, output frequency 20, generated initialisation (`g`), thread counts 1, 4, 8, 16, and 32, five repetitions per implementation/thread combination, and `OMP_DYNAMIC=FALSE`.

That is 4 implementations × 5 thread counts × 5 repetitions = 100 raw timing measurements. To reproduce the benchmark from `part2b/`:

```sh
bash benchmark/run_benchmarks.sh
```

Raw timings are written to `benchmark/raw_results.csv`.

## Result Analysis

From `part2b/`, run:

```sh
python3 benchmark/analyse_results.py
```

The script validates `raw_results.csv` and calculates mean execution time, sample standard deviation, speedup, and efficiency:

$$
S_p = T_1 / T_p
$$

$$
E_p = S_p / p
$$

Each implementation uses its own 1-thread mean as `T_1`.

Generated result files:

- `benchmark/results/summary.csv`
- `benchmark/results/runtime_table.csv`
- `benchmark/results/speedup_table.csv`
- `benchmark/results/efficiency_table.csv`

Generated plots:

- `benchmark/results/runtime_vs_threads.png`
- `benchmark/results/runtime_with_std.png`
- `benchmark/results/speedup_vs_threads.png`
- `benchmark/results/speedup_with_ideal.png`
- `benchmark/results/efficiency_vs_threads.png`

## Notes

- Detailed output is disabled only for performance testing.
- All four implementations use the same simulation parameters during the reported benchmark.
- 16- and 32-thread runs exceed the 8 logical CPUs visible in the tested container and therefore represent oversubscribed execution.
- Generated binaries are not required in the repository; build them using the commands above.
