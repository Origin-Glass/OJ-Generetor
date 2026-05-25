from __future__ import annotations

from .code_runner import CodeRunner
from .models import GeneratedProblem, TestRunResult


class TestcaseRunner:
    def __init__(self, code_runner: CodeRunner) -> None:
        self.code_runner = code_runner

    def run(self, problem: GeneratedProblem, compare_bruteforce: bool = True) -> TestRunResult:
        return self.code_runner.validate(
            problem.reference_solution_cpp17,
            problem.brute_force_solution_python,
            problem.hidden_test_generator_python,
            problem.samples,
            compare_bruteforce=compare_bruteforce,
        )
