#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.append('Data/search')
from rag_pipeline import rag_search_pipeline

# 테스트 1: 필터 없이 전체 데이터
print("=" * 70)
print("테스트 1: 헬스하는 사람들 (필터 없음)")
print("=" * 70)
query1 = '헬스하는 사람들의 비율은?'
results1 = rag_search_pipeline(query1, top_k=3, use_gpt_parsing=False)

print('\n상세 결과:')
for i, answer in enumerate(results1[:10], 1):
    print(f'{i}. [응답자 {answer["respondent_id"]}]')
    print(f'   답변: {answer.get("answer_text", answer["answer_value"])}')
    print()

# 테스트 2: 30대 남성 필터
print("\n" + "=" * 70)
print("테스트 2: 30대 남성 필터 적용")
print("=" * 70)
query2 = '헬스하는 30대 남성의 비율은?'
results2 = rag_search_pipeline(query2, top_k=3, use_gpt_parsing=True)

print('\n상세 결과:')
for i, answer in enumerate(results2[:10], 1):
    print(f'{i}. [응답자 {answer["respondent_id"]}]')
    print(f'   답변: {answer.get("answer_text", answer["answer_value"])}')
    print()
