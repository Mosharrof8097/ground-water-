"""
MASTER PIPELINE
===============
Runs the project end to end, raw BGS data -> modelling frame.

    python run_pipeline.py            # all implemented stages
    python run_pipeline.py --stage 1  # one stage

Stage 3 (methods) is not implemented yet; see 03_methods/README.md for the
protocol it will follow. Verification lives in 05_tests/test_pipeline.py and is
run separately so a failing check cannot be mistaken for a pipeline crash.
"""

import importlib.util
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

STAGES = [
    (1, "01_data_cleaning", "clean_bgs", "Data cleaning"),
    (2, "02_preprocessing", "build_features", "Preprocessing & design"),
]


def run_stage(folder, module_name):
    script = ROOT / folder / f"{module_name}.py"
    if not script.exists():
        raise FileNotFoundError(f"stage script missing: {script}")
    spec = importlib.util.spec_from_file_location(module_name, script)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(script.parent))
    try:
        spec.loader.exec_module(mod)
        mod.main()
    finally:
        sys.path.remove(str(script.parent))


def main():
    target = None
    if "--stage" in sys.argv:
        target = int(sys.argv[sys.argv.index("--stage") + 1])

    print("\n" + "=" * 70)
    print("  LOW-COST SURROGATE SCREENING FOR TRACE METALS")
    print("  BGS/DPHE Bangladesh special study areas, N = 271")
    print("=" * 70)

    for num, folder, module, label in STAGES:
        if target and num != target:
            continue
        print(f"\n{'-' * 70}")
        print(f"  STAGE {num} — {label}")
        print(f"{'-' * 70}")
        t0 = time.time()
        try:
            run_stage(folder, module)
            print(f"  elapsed {time.time() - t0:.1f}s")
        except Exception as exc:
            print(f"\n  STAGE {num} FAILED: {exc}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    if not target:
        print("\n" + "=" * 70)
        print("  PIPELINE COMPLETE")
        print("  Verify:  python 05_tests/test_pipeline.py")
        print("  Next:    stage 3 — see 03_methods/README.md")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
