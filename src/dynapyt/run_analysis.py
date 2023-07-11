from typing import List
import json
import argparse
import importlib
from os.path import abspath
from shutil import rmtree
import sys
import signal
from pathlib import Path
from filelock import FileLock
import dynapyt.runtime as _rt


def run_analysis(
    entry: str, analyses: List[str], name: str = None, coverage: bool = False
):
    if coverage:
        Path("/tmp/dynapyt_coverage").mkdir(exist_ok=True)
    else:
        rmtree("/tmp/dynapyt_coverage", ignore_errors=True)
    my_analyses = []
    try:
        for analysis in analyses:
            module = importlib.import_module(".".join(analysis.split(".")[:-1]))
            class_ = getattr(module, analysis.split(".")[-1])
            my_analyses.append(class_())
    except TypeError as e:
        raise
    except ImportError as e:
        raise

    if Path("/tmp/dynapyt_analyses.txt").exists():
        Path("/tmp/dynapyt_analyses.txt").unlink()
    with open("/tmp/dynapyt_analyses.txt", "w") as f:
        f.write("\n".join(analyses))
    _rt.set_analysis(my_analyses)

    def end_execution():
        if _rt.covered is not None:
            with FileLock("/tmp/dynapyt_coverage/covered.txt.lock"):
                with open("/tmp/dynapyt_coverage/covered.txt", "w") as f:
                    json.dump(_rt.covered, f, indent=4)
        try:
            for my_analysis in my_analyses:
                func = getattr(my_analysis, "end_execution")
                func()
        except AttributeError:
            pass

    # allow dynapyt to exit gracefully
    signal.signal(signal.SIGINT, end_execution)
    signal.signal(signal.SIGTERM, end_execution)

    if not name is None:
        for my_analysis in my_analyses:
            getattr(my_analysis, "add_metadata", lambda: None)({"name": name})

    try:
        for my_analysis in my_analyses:
            func = getattr(my_analysis, "begin_execution")
            func()
    except AttributeError:
        pass
    if entry.endswith(".py"):
        sys.argv = [entry]
        exec(open(abspath(entry)).read(), globals())
    else:
        importlib.import_module(entry)
    end_execution()


parser = argparse.ArgumentParser()
parser.add_argument("--entry", help="Entry file for execution")
parser.add_argument("--analysis", help="Analysis class name(s)", nargs="+")
parser.add_argument("--name", help="Associates a given name with current run")
parser.add_argument("--coverage", help="Enables coverage", action="store_true")

if __name__ == "__main__":
    args = parser.parse_args()
    name = args.name
    analyses = args.analysis
    run_analysis(args.entry, analyses, name, args.coverage)
