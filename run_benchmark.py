# run_benchmark.py
# Helper script to run the full benchmark suite
from src.pipeline import run_full_benchmark

if __name__ == "__main__":
    print("Starting SpecMutate Full Benchmark Run (15 tasks)...")
    summary = run_full_benchmark("results/benchmark_results.json")
    print("\nBenchmark Run Finished successfully!")
    print(f"Summary saved to: results/benchmark_results.json")
