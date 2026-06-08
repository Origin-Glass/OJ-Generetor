from __future__ import annotations

from .models import GeneratedProblem, SampleCase, TaskSlot


def template_problem_for_slot(slot: TaskSlot) -> GeneratedProblem:
    """Return a deterministic low-level problem when LLM generation stalls.

    These templates trade creativity for acceptance throughput: exact slot metadata,
    unambiguous Korean text, small constraints, compiling C++17, executable brute
    force, and hidden tests that cover more than the samples. They are used only as
    a fallback for low levels where repeated LLM candidates fail verification.
    """
    tags = set(slot.tags)
    if "string" in tags or "parsing" in tags:
        return _vowel_code(slot)
    if "sorting" in tags:
        return _middle_station(slot)
    if "greedy" in tags:
        return _best_coupon(slot)
    if "brute force" in tags:
        return _square_counter(slot)
    if "arithmetic" in tags or "math" in tags:
        return _button_gap(slot)
    return _signal_compare(slot)


def _base(slot: TaskSlot, *, title: str, slug: str, statement: str, input_desc: str, output_desc: str,
          constraints: list[str], samples: list[SampleCase], intended: str, proof: str,
          cpp: str, py: str, hidden_inputs: list[str]) -> GeneratedProblem:
    generator_cases = [{"input": case} for case in hidden_inputs]
    hidden = "import json\nprint(json.dumps(" + repr(generator_cases) + ", ensure_ascii=False))\n"
    return GeneratedProblem(
        title=f"{title} {slot.slot_id}",
        slug=f"{slug}-{slot.slot_id.lower()}",
        difficulty_level=slot.level,
        tier=slot.tier,
        tags=slot.tags,
        is_bonus=slot.bonus,
        requires_diagram=False,
        diagram_svg="",
        problem_statement=statement,
        input_description=input_desc,
        output_description=output_desc,
        constraints=constraints,
        samples=samples,
        intended_solution=intended,
        correctness_argument=proof,
        time_complexity="O(N)" if "문자열" in statement or "1부터" in statement else "O(1)",
        memory_complexity="O(1)",
        reference_solution_cpp17=cpp,
        brute_force_solution_python=py,
        hidden_test_generator_python=hidden,
        originality_notes="저난이도 fallback 템플릿에서 슬롯 번호와 조건을 반영해 생성했다.",
        validator_notes="입력 크기가 작고 형식이 명확해 표준 입력 파싱만 확인하면 된다.",
    )


def _signal_compare(slot: TaskSlot) -> GeneratedProblem:
    return _base(
        slot,
        title="신호 세기 비교",
        slug="signal-compare",
        statement="두 관측 장비가 같은 시간에 신호 세기를 하나씩 기록했다. 첫 번째 장비의 값이 더 크면 FIRST, 두 번째 장비의 값이 더 크면 SECOND, 같으면 SAME을 출력하라.",
        input_desc="첫째 줄에 두 관측값 X와 Y가 공백으로 구분되어 주어진다.",
        output_desc="X가 Y보다 크면 FIRST, Y가 X보다 크면 SECOND, 같으면 SAME을 출력한다.",
        constraints=["-1000 <= A, B <= 1000"],
        samples=[SampleCase(input="7 3\n", output="FIRST\n", explanation="7이 3보다 크다."), SampleCase(input="4 4\n", output="SAME\n", explanation="두 값이 같다.")],
        intended="두 관측값을 비교해 세 경우 중 하나를 출력한다.",
        proof="정수의 대소 관계는 X>Y, X<Y, X=Y 중 정확히 하나이므로 조건문이 요구한 답을 유일하게 출력한다.",
        cpp="#include <bits/stdc++.h>\nusing namespace std;\nint main(){ios::sync_with_stdio(false);cin.tie(nullptr);long long X,Y;cin>>X>>Y;if(X>Y) cout<<\"FIRST\\n\";else if(X<Y) cout<<\"SECOND\\n\";else cout<<\"SAME\\n\";return 0;}\n",
        py="X,Y=map(int,input().split())\nprint('FIRST' if X>Y else 'SECOND' if X<Y else 'SAME')\n",
        hidden_inputs=["7 3\n", "2 9\n", "4 4\n", "-5 -2\n"],
    )


def _button_gap(slot: TaskSlot) -> GeneratedProblem:
    return _base(
        slot,
        title="버튼 높이 차이",
        slug="button-gap",
        statement="두 버튼의 높이가 정수로 주어진다. 두 버튼을 같은 높이로 맞추려면 더 낮은 버튼을 몇 칸 올려야 하는지 출력하라.",
        input_desc="첫째 줄에 두 버튼 높이 X와 Y가 공백으로 구분되어 주어진다.",
        output_desc="두 값의 차이의 절댓값을 출력한다.",
        constraints=["0 <= A, B <= 1000000"],
        samples=[SampleCase(input="3 10\n", output="7\n", explanation="3을 7칸 올리면 10이 된다.")],
        intended="두 수의 절댓값 차이를 계산한다.",
        proof="낮은 값에서 높은 값까지 필요한 증가 횟수는 두 값의 차이의 절댓값과 정확히 같다.",
        cpp="#include <bits/stdc++.h>\nusing namespace std;\nint main(){ios::sync_with_stdio(false);cin.tie(nullptr);long long X,Y;cin>>X>>Y;cout<<llabs(X-Y)<<'\\n';return 0;}\n",
        py="X,Y=map(int,input().split())\nprint(abs(X-Y))\n",
        hidden_inputs=["3 10\n", "10 3\n", "0 0\n", "1000000 1\n"],
    )


def _vowel_code(slot: TaskSlot) -> GeneratedProblem:
    return _base(
        slot,
        title="코드 모음 세기",
        slug="code-vowels",
        statement="대문자 알파벳과 숫자로 이루어진 코드 문자열 S가 주어진다. S에 들어 있는 대문자 모음 A, E, I, O, U의 개수를 출력하라.",
        input_desc="첫째 줄에 문자열 S가 주어진다.",
        output_desc="S에 포함된 A, E, I, O, U의 총개수를 출력한다.",
        constraints=["1 <= |S| <= 100", "S는 대문자 알파벳과 숫자로만 이루어진다."],
        samples=[SampleCase(input="A1B2E3\n", output="2\n", explanation="A와 E가 모음이다.")],
        intended="문자열을 한 글자씩 보며 모음 집합에 속하는 글자를 센다.",
        proof="각 문자는 한 번씩 검사되고, 검사 조건은 문제에서 정의한 다섯 모음과 정확히 일치하므로 누적한 개수가 정답이다.",
        cpp="#include <bits/stdc++.h>\nusing namespace std;\nint main(){ios::sync_with_stdio(false);cin.tie(nullptr);string S;cin>>S;int ans=0;for(char c:S) if(string(\"AEIOU\").find(c)!=string::npos) ans++;cout<<ans<<'\\n';return 0;}\n",
        py="S=input().strip()\nprint(sum(c in 'AEIOU' for c in S))\n",
        hidden_inputs=["A1B2E3\n", "XYZ\n", "AEIOU\n", "Q9O8U7\n"],
    )


def _middle_station(slot: TaskSlot) -> GeneratedProblem:
    return _base(
        slot,
        title="가운데 정류장 번호",
        slug="middle-station",
        statement="서로 다른 세 정류장 번호가 주어진다. 번호를 오름차순으로 정렬했을 때 가운데에 오는 번호를 출력하라.",
        input_desc="첫째 줄에 서로 다른 세 정수 A, B, C가 공백으로 구분되어 주어진다.",
        output_desc="세 수 중 두 번째로 작은 수를 출력한다.",
        constraints=["1 <= A, B, C <= 1000", "A, B, C는 서로 다르다."],
        samples=[SampleCase(input="8 3 5\n", output="5\n", explanation="3, 5, 8 순서이므로 가운데 값은 5이다.")],
        intended="세 수를 배열에 넣고 정렬한 뒤 인덱스 1의 값을 출력한다.",
        proof="정렬 후 배열은 오름차순이므로 길이 3 배열의 두 번째 원소가 문제에서 요구한 가운데 번호이다.",
        cpp="#include <bits/stdc++.h>\nusing namespace std;\nint main(){ios::sync_with_stdio(false);cin.tie(nullptr);vector<int> v(3);for(int &x:v) cin>>x;sort(v.begin(),v.end());cout<<v[1]<<'\\n';return 0;}\n",
        py="v=list(map(int,input().split()))\nv.sort()\nprint(v[1])\n",
        hidden_inputs=["8 3 5\n", "1 2 3\n", "1000 4 9\n", "7 11 2\n"],
    )


def _best_coupon(slot: TaskSlot) -> GeneratedProblem:
    return _base(
        slot,
        title="쿠폰 하나 고르기",
        slug="best-coupon",
        statement="가게에는 정가 P원인 물건이 있다. 두 쿠폰은 각각 X원 할인과 Y원 할인을 제공한다. 더 많이 할인되는 쿠폰 하나를 골랐을 때 지불해야 하는 금액을 출력하라. 단, 할인 후 금액은 음수가 되지 않는다.",
        input_desc="첫째 줄에 세 정수 P, X, Y가 공백으로 구분되어 주어진다.",
        output_desc="둘 중 더 큰 할인 금액을 적용한 뒤의 지불 금액을 출력한다.",
        constraints=["0 <= X, Y <= P <= 1000000"],
        samples=[SampleCase(input="100 30 20\n", output="70\n", explanation="30원 할인을 고르는 것이 더 좋다.")],
        intended="두 할인 금액 중 큰 값을 선택해 P에서 뺀다.",
        proof="쿠폰을 하나만 쓸 수 있으므로 지불 금액을 최소화하려면 할인 금액이 큰 쿠폰을 고르는 것이 항상 최적이다.",
        cpp="#include <bits/stdc++.h>\nusing namespace std;\nint main(){ios::sync_with_stdio(false);cin.tie(nullptr);long long P,X,Y;cin>>P>>X>>Y;cout<<P-max(X,Y)<<'\\n';return 0;}\n",
        py="P,X,Y=map(int,input().split())\nprint(P-max(X,Y))\n",
        hidden_inputs=["100 30 20\n", "50 0 50\n", "7 3 3\n", "1000000 1 999999\n"],
    )


def _square_counter(slot: TaskSlot) -> GeneratedProblem:
    return _base(
        slot,
        title="작은 제곱수 세기",
        slug="small-squares",
        statement="정수 N이 주어진다. 1부터 N까지의 정수 x 중에서 x*x가 N 이하인 x의 개수를 직접 세어 출력하라.",
        input_desc="첫째 줄에 정수 N이 주어진다.",
        output_desc="조건을 만족하는 양의 정수 x의 개수를 출력한다.",
        constraints=["1 <= N <= 10000"],
        samples=[SampleCase(input="10\n", output="3\n", explanation="1, 2, 3의 제곱은 10 이하이다.")],
        intended="1부터 N까지 반복하며 x*x <= N인 경우를 센다.",
        proof="반복문은 가능한 모든 양의 정수 후보를 빠짐없이 검사하므로 조건을 만족하는 후보의 수를 정확히 센다.",
        cpp="#include <bits/stdc++.h>\nusing namespace std;\nint main(){ios::sync_with_stdio(false);cin.tie(nullptr);int N;cin>>N;int ans=0;for(int x=1;x<=N;x++) if(x*x<=N) ans++;cout<<ans<<'\\n';return 0;}\n",
        py="N=int(input())\nans=0\nfor x in range(1,N+1):\n    if x*x<=N:\n        ans+=1\nprint(ans)\n",
        hidden_inputs=["1\n", "10\n", "16\n", "9999\n"],
    )
