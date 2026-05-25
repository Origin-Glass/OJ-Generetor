import unittest

from oj_agent.code_runner import CodeRunner
from oj_agent.models import SampleCase


CPP = r"""
#include <bits/stdc++.h>
using namespace std;
int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long a,b;
    if(!(cin>>a>>b)) return 0;
    cout << a+b << "\n";
}
"""

PY = r"""
a,b=map(int,input().split())
print(a+b)
"""

GEN = r"""
import json
print(json.dumps([{"input":"1 2\n"},{"input":"5 7\n"}]))
"""


class CodeRunnerTest(unittest.TestCase):
    def test_validate_cpp_python(self) -> None:
        runner = CodeRunner(max_tests=2)
        result = runner.validate(CPP, PY, GEN, [SampleCase(input="3 4\n", output="7\n")])
        self.assertTrue(result.accepted, result.errors)


if __name__ == "__main__":
    unittest.main()
