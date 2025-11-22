# tests/test_parse_query.py
import json
from pathlib import Path

from search.parsing import parse_query_with_gpt

BASE_DIR = Path(__file__).resolve().parent
CASES_PATH = BASE_DIR / "query_parsing_cases.json"


def filter_matches_expectation(filters, expected_spec) -> bool:
    """
    filters: parse_query_with_gpt 결과 filters (list[dict])
    expected_spec: {"column": "...", "operator": "...", "value_contains_any": [...]}
    """
    col = expected_spec.get("column")
    op = expected_spec.get("operator")
    value_candidates = expected_spec.get("value_contains_any") or []

    for f in filters:
        if not isinstance(f, dict):
            continue
        if col and f.get("column") != col:
            continue
        if op and f.get("operator") != op:
            continue

        if value_candidates:
            v = str(f.get("value") or "")
            if any(vc in v for vc in value_candidates):
                return True
        else:
            # 컬럼/연산자만 맞으면 OK
            return True

    return False


def run_tests():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    total = len(cases)
    passed = 0

    for case in cases:
        cid = case.get("id")
        query = case["query"]
        desc = case.get("description", "")

        print(f"\n=== [{cid}] {desc} ===")
        print(f"질문: {query}")

        parsed = parse_query_with_gpt(query)
        filters = parsed.get("filters", []) or []
        semantic_query = parsed.get("semantic_query", "") or ""

        print("  - filters:", filters)
        print("  - semantic_query:", semantic_query)

        ok = True

        # 1) semantic_query에 특정 키워드 포함 여부
        expected_sem = case.get("expected_semantic_contains") or []
        for kw in expected_sem:
            if kw not in semantic_query:
                print(f"  [FAIL] semantic_query 에 '{kw}' 가 없음")
                ok = False

        # 2) filters에 특정 컬럼/값 포함 여부
        expected_filters_specs = case.get("expected_filters_contains") or []
        for spec in expected_filters_specs:
            if not filter_matches_expectation(filters, spec):
                print(f"  [FAIL] filters 에 {spec} 에 해당하는 항목이 없음")
                ok = False

        if ok:
            print("  [OK] ✅ 통과")
            passed += 1
        else:
            print("  [NG] ❌ 실패")

    print(f"\n요약: {passed}/{total} 케이스 통과")


if __name__ == "__main__":
    run_tests()
