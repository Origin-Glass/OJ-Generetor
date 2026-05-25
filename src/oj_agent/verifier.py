from __future__ import annotations

from .code_runner import CodeRunner
from .config import AppConfig
from .counterexample import CounterexampleSearcher
from .llm_client import LLMClient
from .models import ChatMessage, GeneratedProblem, LLMReview, RoundResult, TaskSlot, VerificationReport, dump_model
from .prompts import final_review_prompt, verifier_prompt
from .similarity import SimilarityChecker
from .svg_generator import is_valid_svg
from .testcase_runner import TestcaseRunner
from .utils import normalize_output


class ProblemVerifier:
    def __init__(self, config: AppConfig, llm: LLMClient, similarity: SimilarityChecker) -> None:
        self.config = config
        self.llm = llm
        self.similarity = similarity

    def verify(self, problem: GeneratedProblem, slot: TaskSlot, revision_attempts: int = 0) -> VerificationReport:
        effort = self.config.verification.effort_for_level(slot.level)
        report = VerificationReport(slot_id=slot.slot_id, revision_attempts=revision_attempts)

        round1 = self._round1(problem, slot)
        report.rounds.append(round1)
        if round1.verdict != "ACCEPT":
            report.final_verdict = round1.verdict
            return report

        review = self._review(problem, slot, effort.verifier_max_tokens)
        round2 = RoundResult(round=2, name="LLM adversarial review", verdict=review.verdict, issues=review.issues, data=dump_model(review))
        report.rounds.append(round2)
        if round2.verdict != "ACCEPT":
            report.final_verdict = round2.verdict
            return report

        round3 = self._round3(problem, slot, effort.max_hidden_tests)
        report.rounds.append(round3)
        if round3.verdict != "ACCEPT":
            report.final_verdict = round3.verdict
            return report

        round4 = self._round4(problem, slot, effort.llm_counterexample_tests, effort.verifier_max_tokens)
        report.rounds.append(round4)
        if round4.verdict != "ACCEPT":
            report.final_verdict = round4.verdict
            return report

        final_data = self.llm.json_chat(
            [
                ChatMessage(role="system", content="You perform final OJ problem review. JSON only."),
                ChatMessage(role="user", content=final_review_prompt(problem, slot, {"rounds": [dump_model(r) for r in report.rounds]})),
            ],
            temperature=0.2,
            max_tokens=effort.verifier_max_tokens,
        )
        final_review = LLMReview(**final_data)
        round5 = RoundResult(round=5, name="Final review and answer authorization", verdict=final_review.verdict, issues=final_review.issues, data=dump_model(final_review))
        report.rounds.append(round5)
        report.final_verdict = round5.verdict
        report.summary = "all five verification stages completed" if round5.verdict == "ACCEPT" else "final review requested changes"
        return report

    def _round1(self, problem: GeneratedProblem, slot: TaskSlot) -> RoundResult:
        issues: list[str] = []
        if problem.difficulty_level != slot.level:
            issues.append("difficulty level does not match slot")
        if problem.tier != slot.tier:
            issues.append("tier does not match slot")
        if sorted(problem.tags) != sorted(slot.tags):
            issues.append("tags do not match planned tags")
        if problem.is_bonus != slot.bonus:
            issues.append("bonus flag does not match slot")
        required_text = [
            problem.title,
            problem.slug,
            problem.problem_statement,
            problem.input_description,
            problem.output_description,
            problem.intended_solution,
            problem.correctness_argument,
            problem.time_complexity,
            problem.memory_complexity,
            problem.reference_solution_cpp17,
            problem.hidden_test_generator_python,
        ]
        if any(not str(item).strip() for item in required_text):
            issues.append("one or more required text sections are empty")
        if not problem.samples:
            issues.append("samples are missing")
        if not problem.constraints:
            issues.append("constraints are missing")
        if not problem.brute_force_solution_python.strip():
            issues.append("Python brute force is missing")
        if "```" in problem.problem_statement:
            issues.append("problem statement contains markdown fence")
        if problem.requires_diagram and not is_valid_svg(problem.diagram_svg):
            issues.append("diagram_svg is not valid SVG")
        sim = self.similarity.check(problem.title, problem.problem_statement)
        if sim.blocked:
            issues.append(f"similarity blocked: {sim.reason} score={sim.score:.3f}")
        return RoundResult(
            round=1,
            name="Structural validation",
            verdict="ACCEPT" if not issues else "REVISE",
            issues=issues,
            data={"similarity_score": sim.score, "similarity_reason": sim.reason, "matched_title": sim.matched_title},
        )

    def _review(self, problem: GeneratedProblem, slot: TaskSlot, max_tokens: int) -> LLMReview:
        data = self.llm.json_chat(
            [
                ChatMessage(role="system", content="You are an adversarial OJ reviewer. Return JSON only."),
                ChatMessage(role="user", content=verifier_prompt(problem, slot)),
            ],
            temperature=0.2,
            max_tokens=max_tokens,
        )
        return LLMReview(**data)

    def _round3(self, problem: GeneratedProblem, slot: TaskSlot, max_hidden_tests: int) -> RoundResult:
        timeout = self.config.verification.high_difficulty_run_timeout_sec if slot.level >= 21 else self.config.verification.run_timeout_sec
        runner = TestcaseRunner(
            CodeRunner(
                compile_timeout_sec=self.config.verification.compile_timeout_sec,
                run_timeout_sec=timeout,
                max_input_bytes=self.config.verification.max_input_bytes,
                max_tests=max_hidden_tests,
            )
        )
        result = runner.run(problem, self.config.verification.compare_reference_with_bruteforce)
        return RoundResult(
            round=3,
            name="Code execution validation",
            verdict="ACCEPT" if result.accepted else "REVISE",
            issues=result.errors,
            data=dump_model(result),
        )

    def _round4(self, problem: GeneratedProblem, slot: TaskSlot, count: int, max_tokens: int) -> RoundResult:
        issues: list[str] = []
        plan = CounterexampleSearcher(self.llm).generate(problem, slot, count, max_tokens)
        concrete_inputs = [str(item.get("input", "")) for item in plan.tests if str(item.get("input", "")).strip()]
        concrete_inputs.extend([sample.input for sample in problem.samples])
        timeout = self.config.verification.high_difficulty_run_timeout_sec if slot.level >= 21 else self.config.verification.run_timeout_sec
        runner = CodeRunner(
            compile_timeout_sec=self.config.verification.compile_timeout_sec,
            run_timeout_sec=timeout,
            max_input_bytes=self.config.verification.max_input_bytes,
            max_tests=count,
        )
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory(prefix="oj-agent-ce-") as tmp:
            binary, compile_result = runner.compile_cpp17(problem.reference_solution_cpp17, Path(tmp))
            if binary is None:
                return RoundResult(round=4, name="Counterexample search", verdict="REVISE", issues=["reference solution does not compile"], data=dump_model(compile_result))
            for i, case_input in enumerate(concrete_inputs[:count], start=1):
                ref = runner.run_binary(binary, case_input)
                if ref.exit_code != 0:
                    issues.append(f"counterexample {i}: reference runtime error")
                    break
                if problem.brute_force_solution_python.strip():
                    brute = runner.run_python(problem.brute_force_solution_python, case_input)
                    if brute.exit_code != 0 or normalize_output(ref.stdout) != normalize_output(brute.stdout):
                        issues.append(f"counterexample {i}: reference/bruteforce mismatch")
                        break
        return RoundResult(
            round=4,
            name="Counterexample search",
            verdict="ACCEPT" if not issues else "REVISE",
            issues=issues,
            data=dump_model(plan),
        )
