
# -*- coding: utf-8 -*-

"""
Metadata 필터링을 위한 SQL WHERE 절 생성기
"""

from collections import defaultdict

def build_metadata_where_clause(filters_list, table_name="metadata"):
    """
    필터 리스트(JSON)를 기반으로 SQL WHERE 절과 파라미터를 생성합니다.
    """
    if not filters_list:
        return "", []

    # 1. 컬럼(column)별로 필터 그룹화
    #    {'region': [...], 'age': [...], 'gender': [...]}
    grouped_filters = defaultdict(list)
    for f in filters_list:
        # 컬럼명에 유효하지 않은 문자가 있는지 간단히 확인 (방어용)
        column_name = f['column']
        if not column_name.isalnum() and '_' not in column_name:
             print(f"Warning: 유효하지 않은 컬럼명 '{column_name}'는 건너뜁니다.")
             continue
        grouped_filters[column_name].append(f)

    all_conditions = []  # 최종 AND로 결합될 조건 그룹
    all_parameters = []  # SQL 파라미터 (순서 중요)

    # SQL Injection을 막기 위한 허용된 연산자 목록 >> 사실 우리 수준에서 보안 신경 안쓰면 더 많은 연산자를 추가해도 됌...
    ALLOWED_OPERATORS = {'=', '!=', 'LIKE', '>', '>=', '<', '<='}

    # 2. 그룹화된 필터 순회 (예: 'region' 그룹, 'age' 그룹)
    for column, filters in grouped_filters.items():
        
        column_conditions = [] # 개별 컬럼 그룹의 조건 (예: 'region LIKE %s')
        
        # 3. 이 그룹 내의 연산자 확인 (AND로 묶을지 OR로 묶을지 결정)
        #    연산자가 모두 'LIKE' 또는 '=' 이면 OR로,
        #    '<' 또는 '>' 같은 범위 연산자가 섞여 있으면 AND로 묶습니다.
        ops_in_group = {f['operator'] for f in filters}
        
        joiner = " AND " # 기본값 (예: age >= 40 AND age < 50)
        
        # 모든 연산자가 '등가/유사' 연산자일 경우 OR로 결합
        if all(op in ['=', '!=', 'LIKE'] for op in ops_in_group):
            joiner = " OR " # 예: region LIKE '서울%' OR region LIKE '경기도%'
            
        # 4. 그룹 내 개별 조건 생성
        for f in filters:
            op = f['operator']
            if op not in ALLOWED_OPERATORS:
                print(f"Warning: 허용되지 않는 연산자 '{op}'는 건너뜁니다.")
                continue
            
            # (예: "age >= %s")
            # 컬럼명은 안전하다고 가정 (위에서 1차 필터링)
            column_conditions.append(f"{column} {op} %s")
            all_parameters.append(f['value'])
        
        if column_conditions:
            # 그룹 내 조건들을 joiner(AND 또는 OR)로 묶음
            # (예: "(age >= %s AND age < %s)")
            all_conditions.append(f"({joiner.join(column_conditions)})")

    # 5. 최종 WHERE 절 생성
    if not all_conditions:
        return "", []

    # (예: "WHERE (region LIKE %s OR region LIKE %s) AND (age >= %s AND age < %s) ...")
    final_where_clause = f"WHERE " + " AND ".join(all_conditions)
    
    return final_where_clause, all_parameters

# --- 스크립트 실행 예제 ---
if __name__ == '__main__':
    # RAG 쿼리 파서(parsing.py)로부터 전달받았다고 가정한 입력값
    query_input = {
  "filters": [
    {
      "column": "region",
      "operator": "LIKE",
      "value": "서울%"
    },
    {
      "column": "age",
      "operator": ">=",
      "value": "30"
    },
    {
      "column": "age",
      "operator": "<",
      "value": "40"
    },
    {
      "column": "gender",
      "operator": "=",
      "value": "남성"
    }
  ],
  "semantic_query": "전문직인 직종"
}


    # 함수 실행
    where_sql, params = build_metadata_where_clause(query_input['filters'])

    print("--- 1. 생성된 SQL WHERE 절 ---")
    print(where_sql)

    print("\n--- 2. 생성된 파라미터 (순서대로) ---")
    print(params)

    print("\n--- 3. RAG 실행기 (예시) ---")
    # RAG 실행기(Executor)는 이 두 값을 조합하여 최종 쿼리를 만듭니다.
    # (예시: 여기서는 응답자 ID(mb_sn)만 가져옵니다)
    
    # 여기서는 metadata 테이블을 필터링하는 부분만 보여줍니다.
    
    final_sql_query = f"SELECT mb_sn FROM metadata {where_sql};"
    
    print(f"생성된 쿼리 (psycopg2용): {final_sql_query}")
    print(f"쿼리 파라미터 (psycopg2용): {params}")

    # --- [수정] 4. 최종 SQL 문 (디버깅용) ---
    print("\n--- 4. 최종 SQL 문 (디버깅용) ---")
    print(f"(주의: 이 쿼리는 디버깅용이며, 실제 실행은 파라미터화된 쿼리를 사용해야 합니다.)")
    
    debug_sql_with_values = final_sql_query
    try:
        # 파라미터를 순서대로 치환합니다.
        # (age >= 40)처럼 숫자형으로 처리되어야 할 값('40')과
        # (region LIKE '서울%')처럼 문자열로 처리되어야 할 값을 구분합니다.
        
        # 임시 리스트를 만들어 파라미터를 하나씩 소비합니다.
        params_copy = list(params)
        
        # 쿼리 문자열에 %s가 남아있는 동안 반복
        while '%s' in debug_sql_with_values:
            if not params_copy:
                break # 파라미터가 더 없으면 중단
            
            p = params_copy.pop(0) # 첫 번째 파라미터 추출
            
            value_to_insert = ""
            # 파라미터가 숫자 형태의 문자열(예: '40')이거나 실제 숫자인지 확인
            is_numeric_like = False
            try:
                # '40'이나 40은 float으로 변환 가능, '서울%'는 불가능
                float(p) 
                is_numeric_like = True
            except (ValueError, TypeError):
                is_numeric_like = False
            
            # LIKE 연산자는 값이 숫자여도 문자열이어야 함
            # 임시로 'age' 컬럼 필터링의 값(숫자)만 따옴표 없이 처리
            # (이 로직은 완벽하지 않으나 디버깅용으로는 충분함)
            
            # '40', '50'은 숫자지만 JSON을 거치며 문자열이 됨
            if str(p).isdigit():
                value_to_insert = str(p)
            else:
                # '서울%', '여성' 등 (SQL 문자열로 감싸기)
                value_to_insert = f"'{str(p)}'"
            
            # %s를 첫 번째 값으로 한 번만 교체
            debug_sql_with_values = debug_sql_with_values.replace("%s", value_to_insert, 1)

        print(debug_sql_with_values)
        
    except Exception as e:
        print(f"디버그 SQL 생성 중 오류 발생: {e}")
        print("(파라미터가 채워지지 않은 쿼리를 출력합니다)")
        print(final_sql_query)


    # (실제 psycopg2 사용 예시)
    # import psycopg2
    # conn = psycopg2.connect(...)
    # cur = conn.cursor()
    # cur.execute(final_sql_query, params)
    # results = cur.fetchall()
    # respondent_ids = [row[0] for row in results]
    # print(f"\n필터링된 응답자 ID: {respondent_ids}")