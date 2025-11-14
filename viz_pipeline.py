# viz_pipeline.py
# -----------------------------------------------
# 📊 통계 시각화 전용 파이프라인 (챗봇 아님)
#
# 기능 요약
# 1) 자연어 쿼리 → LLMlangchan.parse_query 로 filters / semantic_query 분리
# 2) semantic_query 임베딩 → codebooks.q_vector 유사도 검색 → codebook_id 상위 1개
# 3) 미리 정의한 STAT_CONFIG 기준으로
#    - top_codebook_id 가 required_codebooks에 포함되는 차트만 활성화
# 4) 활성화된 차트별로 answers + metadata + codebooks 기반 통계 데이터 생성
# 5) "주요 카테고리 비중(category_share)" 결과는 콘솔에 디버그 출력

from typing import Dict, Any, List
import json

from psycopg2.extras import RealDictCursor

# LLMlangchan에서 구현해둔 유틸 재사용
from LLMlangchan import (
    parse_query,      # 자연어 → {filters, semantic_query}
    embed,            # semantic_query 임베딩
    db_conn,          # psycopg2 연결
    build_where,      # filters → WHERE 절
    _attach_human_readable_labels,  # answer_value → 보기 텍스트
    PGVECTOR_OP,
)

# -------------------------------------------------
# 1) 차트 설정 (현재 테스트: 주요 카테고리 비중만)
# -------------------------------------------------
STAT_CONFIG: Dict[str, Dict[str, Any]] = {
    "category_share": {
        "label": "주요 카테고리 비중",
        # 이 리스트 안의 codebook_id 중 하나가 top_codebook_id로 선택되면 차트 활성화
        # 지금은 테스트용으로 w2_Q1만 사용 (결혼여부)
        "required_codebooks": ["w2_Q1"],
    }
}


# -------------------------------------------------
# 2) semantic_query → 관련 codebook_id 1개 찾기
# -------------------------------------------------
def find_relevant_codebook_id(semantic_query: str) -> str:
    """
    semantic_query를 임베딩 후 codebooks.q_vector와 유사도 비교하여
    상위 1개 codebook_id를 반환.
    """
    vec = embed(semantic_query)

    with db_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT codebook_id
            FROM codebooks
            ORDER BY q_vector {PGVECTOR_OP} %s::vector
            LIMIT 1;
            """,
            (vec.tolist(),),
        )
        row = cur.fetchone()

    return row["codebook_id"] if row else None


# -------------------------------------------------
# 3) filters + question_id 기반 answers 조회
# -------------------------------------------------
def fetch_filtered_answers(filters: List[Dict[str, Any]], question_id: str) -> List[Dict[str, Any]]:
    """
    1) filters → metadata WHERE → mb_sn 화이트리스트 추출
    2) answers에서 (question_id = 주어진 question_id) AND (mb_sn ∈ 화이트리스트)
    3) codebooks와 LEFT JOIN해서 codebook_data 함께 가져오기
    4) 객관식 번호를 사람이 읽을 수 있는 라벨(answer_value_text)로 변환
    """
    # 1) filters → metadata WHERE
    where_sql, params = build_where(filters)

    with db_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"SELECT mb_sn FROM metadata{where_sql};", params)
        mb_list = [r["mb_sn"] for r in cur.fetchall()]

    if not mb_list:
        return []

    # 2) answers + codebooks 조인
    with db_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                a.answer_id,
                a.mb_sn,
                a.question_id,
                a.answer_value,
                c.codebook_data
            FROM answers a
            LEFT JOIN codebooks c
                ON a.question_id = c.codebook_id
            WHERE a.question_id = %s
              AND a.mb_sn = ANY(%s);
            """,
            (question_id, mb_list),
        )
        rows = cur.fetchall()

    # 3) 객관식 번호 → 텍스트 라벨 부착 (예: "1" → "미혼")
    rows = _attach_human_readable_labels(rows)

    return rows


# -------------------------------------------------
# 4) 메인 파이프라인: viz_search
# -------------------------------------------------
def viz_search(user_query: str) -> Dict[str, Any]:
    """
    자연어 쿼리를 받아 통계 시각화용 데이터를 반환.

    반환 예:
        변수 = { "w2_Q1": { 
        "q_title": "결혼여부",
        "value_counts": {
            "미혼": 333,
            "기혼": 125,
            "기타(사별/이혼 등)": 3
          }
        "answers": [
             {"answer_id": 1311276,
              "mb_sn": "w209536081994405",
              "question_id": "w2_Q1",
              "answer_value": "1",
              "codebook_data": {
                "answers": [
                  {
                    "qi_val": "1",
                    "qi_title": "미혼"
                  },
                  {
                    "qi_val": "2",
                    "qi_title": "기혼"
                  },
                  {
                    "qi_val": "3",
                    "qi_title": "기타(사별/이혼 등)"
                  }
                ],
                "q_title": "결혼여부",
                "codebook_id": "w2_Q1"
              },
              "answer_value_text": "미혼"
            },
....
]}

}
    """
    # 1) 쿼리 파싱
    parsed = parse_query(user_query)
    parsed_filters: List[Dict[str, Any]] = parsed.get("filters", []) or []
    semantic_query: str = (parsed.get("semantic_query") or "").strip()

    if not semantic_query:
        return {
            "error": "분석 주제가 없습니다. 예: '서울 30대 남성의 OTT 사용 경향'",
            "filters": parsed_filters,
            "semantic_query": semantic_query,
            "active_charts": [],
            "chart_data": {},
        }

    # 2) semantic_query → codebook_id top-1
    matched_question_id = find_relevant_codebook_id(semantic_query)
    if not matched_question_id:
        return {
            "error": "유사한 설문 문항(codebook_id)을 찾을 수 없습니다.",
            "filters": parsed_filters,
            "semantic_query": semantic_query,
            "active_charts": [],
            "chart_data": {},
        }

    # 3) 어떤 차트 활성화할지 결정
    active_charts: List[str] = []
    for chart_key, cfg in STAT_CONFIG.items():
        required = cfg.get("required_codebooks", [])
        if matched_question_id in required:
            active_charts.append(chart_key)

    chart_data: Dict[str, Any] = {}

    # 4) "주요 카테고리 비중" 차트 처리 (지금은 이것만 존재)
    if "category_share" in active_charts:
        cfg = STAT_CONFIG["category_share"]

        # 4-1) answers 데이터 조회
        category_rows = fetch_filtered_answers(parsed_filters, matched_question_id)

        # 4-2) answer_value_text 기준으로 개수 집계
        category_count: Dict[str, int] = {}

        for row in category_rows:
            # _attach_human_readable_labels에서 붙여준 필드를 우선 사용
            label = row.get("answer_value_text") or row.get("answer_value") or "기타"
            category_count[label] = category_count.get(label, 0) + 1

        # 4-3) 최종 chart_data 구조
        category_chart_data = {
            "label": cfg["label"],
            "codebook_id": matched_question_id,
            "answers": category_rows,       # 개별 응답(필요시 프론트에서 재집계 가능)
            "value_counts": category_count, # 라벨별 집계 (디버그/직접 사용 가능)
        }

        chart_data["category_share"] = category_chart_data

          # 4-4) 🔍 디버그 출력
        print("\n==============================")
        print("📊 [DEBUG] 주요 카테고리 비중(category_share) 활성화")
        print("==============================")
        print(f"➡️ 선택된 codebook_id (matched_question_id): {matched_question_id}\n")

        print("📌 [DEBUG] Filters (파싱된 분석 대상 조건):")
        if not parsed_filters:
            print("   - (필터 없음: 전체 응답 대상)")
        else:
            for f in parsed_filters:
                col = f.get("column")
                op = f.get("operator")
                val = f.get("value")
                print(f"   - {col} {op} {val}")

        # 🔻 sample size 3개만 출력하도록 변경
        sample_size = 3
        sample_rows = category_rows[:sample_size]

        print(f"\n📌 [DEBUG] answers raw rows (표본 {sample_size}개만 표시):")
        if not sample_rows:
            print("   - (데이터 없음)")
        else:
            for row in sample_rows:
                print(
                    f"   - mb_sn={row.get('mb_sn')}, "
                    f"question_id={row.get('question_id')}, "
                    f"answer_value={row.get('answer_value')}, "
                    f"answer_value_text={row.get('answer_value_text')}"
                )

        print("\n📌 [DEBUG] 최종 category_share chart_data 구조 (요약):")

        debug_preview = {
            "label": category_chart_data["label"],
            "codebook_id": category_chart_data["codebook_id"],
            "value_counts": category_chart_data["value_counts"],
            # answers 전체 대신, 샘플 3개만
            "answers_sample": category_rows[:3],
        }

        print(json.dumps(debug_preview, ensure_ascii=False, indent=2))
        print("==============================\n")
    # 5) 최종 응답
    return {
        "filters": parsed_filters,
        "semantic_query": semantic_query,
        "top_codebook_id": matched_question_id,
        "active_charts": active_charts,
        "chart_data": chart_data,
    }


# -------------------------------------------------
# 5) 단독 실행 테스트용
# -------------------------------------------------
if __name__ == "__main__":
    test_query = "서울 사는 30대 남성의 결혼 여부 분포 보여줘"
    result = viz_search(test_query)
    print("\n=== viz_search() 결과 요약 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2))
