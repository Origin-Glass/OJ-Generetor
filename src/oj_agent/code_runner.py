from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from .models import RunResult, SampleCase, TestRunResult
from .utils import normalize_output


@dataclass
class CodeRunner:
    compile_timeout_sec: int = 20
    run_timeout_sec: int = 3
    max_input_bytes: int = 200000
    max_tests: int = 100

    def compile_cpp17(self, source: str, workdir: Path) -> tuple[Path | None, RunResult]:
        source_path = workdir / "reference.cpp"
        binary_path = workdir / "reference"
        self._write_cpp_compat_header(workdir)
        source_path.write_text(source, encoding="utf-8")
        base_cmd = ["g++", "-std=c++17", "-O2", "-pipe", "-I", str(workdir), str(source_path), "-o", str(binary_path)]
        if platform.system().lower() == "linux":
            static_cmd = ["g++", "-std=c++17", "-O2", "-pipe", "-static", "-s", "-I", str(workdir), str(source_path), "-o", str(binary_path)]
            result = self._run_process(static_cmd, "", self.compile_timeout_sec, workdir)
            if result.exit_code == 0:
                return binary_path, result
        result = self._run_process(base_cmd, "", self.compile_timeout_sec, workdir)
        return (binary_path if result.exit_code == 0 else None), result

    def run_binary(self, binary: Path, input_text: str, timeout: int | None = None) -> RunResult:
        self._check_input_size(input_text)
        return self._run_process([str(binary)], input_text, timeout or self.run_timeout_sec, binary.parent)

    def run_python(self, source: str, input_text: str = "", timeout: int | None = None) -> RunResult:
        self._check_input_size(input_text)
        with tempfile.TemporaryDirectory(prefix="oj-agent-py-") as tmp:
            workdir = Path(tmp)
            script = workdir / "script.py"
            script.write_text(source, encoding="utf-8")
            return self._run_process([sys.executable, str(script)], input_text, timeout or self.run_timeout_sec, workdir)

    def validate(
        self,
        reference_cpp: str,
        brute_python: str,
        generator_python: str,
        samples: list[SampleCase],
        *,
        compare_bruteforce: bool = True,
    ) -> TestRunResult:
        result = TestRunResult(accepted=False)
        with tempfile.TemporaryDirectory(prefix="oj-agent-cpp-") as tmp:
            workdir = Path(tmp)
            binary, compile_result = self.compile_cpp17(reference_cpp, workdir)
            result.compile_result = compile_result
            if binary is None:
                result.errors.append("C++17 compilation failed")
                return result
            for i, sample in enumerate(samples, start=1):
                run = self.run_binary(binary, sample.input)
                ok = run.exit_code == 0 and normalize_output(run.stdout) == normalize_output(sample.output)
                result.sample_results.append(
                    {
                        "index": i,
                        "accepted": ok,
                        "stdout": run.stdout,
                        "stderr": run.stderr,
                        "expected": sample.output,
                    }
                )
                if not ok:
                    result.errors.append(f"sample {i} mismatch or runtime error")
            hidden_inputs = self.generate_hidden_inputs(generator_python)
            for i, case_input in enumerate(hidden_inputs[: self.max_tests], start=1):
                ref = self.run_binary(binary, case_input)
                item = {"index": i, "accepted": ref.exit_code == 0, "reference": ref.stdout, "stderr": ref.stderr}
                if compare_bruteforce and brute_python.strip():
                    brute = self.run_python(brute_python, case_input)
                    item["brute"] = brute.stdout
                    item["accepted"] = (
                        item["accepted"]
                        and brute.exit_code == 0
                        and normalize_output(ref.stdout) == normalize_output(brute.stdout)
                    )
                result.hidden_results.append(item)
                if not item["accepted"]:
                    result.errors.append(f"hidden {i} failed")
                    break
        result.accepted = not result.errors
        return result

    def generate_hidden_inputs(self, generator_python: str) -> list[str]:
        if not generator_python.strip():
            return []
        run = self.run_python(generator_python, timeout=self.run_timeout_sec)
        if run.exit_code != 0:
            return []
        text = run.stdout.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                cases: list[str] = []
                for item in parsed:
                    if isinstance(item, dict) and "input" in item:
                        cases.append(str(item["input"]))
                    elif isinstance(item, str):
                        cases.append(item)
                return cases
        except json.JSONDecodeError:
            pass
        if "\n---\n" in text:
            return [part.strip() + "\n" for part in text.split("\n---\n") if part.strip()]
        return [text + "\n"]

    def _run_process(self, command: list[str], input_text: str, timeout: int, cwd: Path) -> RunResult:
        start = time.monotonic()
        try:
            completed = subprocess.run(
                command,
                input=input_text.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(cwd),
                timeout=timeout,
                check=False,
            )
            return RunResult(
                command=command,
                exit_code=completed.returncode,
                stdout=completed.stdout.decode("utf-8", errors="replace"),
                stderr=completed.stderr.decode("utf-8", errors="replace"),
                timed_out=False,
                duration_sec=time.monotonic() - start,
            )
        except subprocess.TimeoutExpired as exc:
            return RunResult(
                command=command,
                exit_code=-1,
                stdout=(exc.stdout or b"").decode("utf-8", errors="replace"),
                stderr=(exc.stderr or b"").decode("utf-8", errors="replace"),
                timed_out=True,
                duration_sec=time.monotonic() - start,
            )

    def _check_input_size(self, input_text: str) -> None:
        if len(input_text.encode("utf-8")) > self.max_input_bytes:
            raise ValueError("input exceeds max_input_bytes")

    def _write_cpp_compat_header(self, workdir: Path) -> None:
        bits = workdir / "bits"
        bits.mkdir(exist_ok=True)
        header = bits / "stdc++.h"
        if header.exists():
            return
        header.write_text(
            "\n".join(
                [
                    "#pragma once",
                    "#include <algorithm>",
                    "#include <array>",
                    "#include <bitset>",
                    "#include <cassert>",
                    "#include <cctype>",
                    "#include <cerrno>",
                    "#include <cfloat>",
                    "#include <chrono>",
                    "#include <climits>",
                    "#include <cmath>",
                    "#include <complex>",
                    "#include <cstdio>",
                    "#include <cstdlib>",
                    "#include <cstring>",
                    "#include <deque>",
                    "#include <functional>",
                    "#include <iomanip>",
                    "#include <iostream>",
                    "#include <iterator>",
                    "#include <limits>",
                    "#include <list>",
                    "#include <map>",
                    "#include <numeric>",
                    "#include <queue>",
                    "#include <random>",
                    "#include <set>",
                    "#include <sstream>",
                    "#include <stack>",
                    "#include <string>",
                    "#include <tuple>",
                    "#include <unordered_map>",
                    "#include <unordered_set>",
                    "#include <utility>",
                    "#include <vector>",
                    "",
                ]
            ),
            encoding="utf-8",
        )
