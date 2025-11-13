import React, { useState, useEffect } from "react";

/*
  AISummary.js
  -----------------------------------------------------------
  이 컴포넌트는 “사용자가 입력한 query에 대해 AI가 요약 분석한 텍스트”를
  화면에 보여주는 영역이다.

  주요 기능:
  - query를 기반으로 생성된 요약문(summary) 표시
  - 로딩 상태 출력
  - 오류 발생 시 fallback 요약문 표시
  - 애니메이션, UI 스타일 적용

  현재 구조는 "프론트 전용 더미 데이터(staticSummary)"를 사용하고 있으며,
  추후 LangChain RAG 백엔드로 교체될 예정.

  RAG 연동 시 흐름:
  -----------------------------------------------------------
  1) ResultsPage → AISummary(query) 전달
  2) AISummary에서 useEffect로 백엔드에 POST 요청:
       POST /rag/summary
       { "query": "사용자 질문" }
  3) 백엔드 RAG 파이프라인이 패널 데이터 기반으로 요약 생성
  4) JSON 반환: { summary: [...] }
  5) summary state 업데이트 후 렌더링

  결론:
  - 이 컴포넌트는 “요약문을 렌더링하는 역할”만 담당하고
    실제 요약 생성은 백엔드가 수행한다.
*/

export default function AISummary({ query }) {
  // 기본 요약문 (프론트 더미)
  const staticSummary = [
    `"${query}"에 대한 소비 패턴 분석 결과, 30대 남성은 주로 온라인 쇼핑과 식품 카테고리 지출 비중이 높습니다.`,
    "평균 결제 금액은 전 세대 대비 약 15% 높고, 주말 결제 비중이 1.4배 높습니다.",
    "모바일 결제 사용률은 약 68%로, 특히 구독형 서비스 이용률이 상승세입니다.",
    "가전·패션·취미 카테고리 지출이 최근 3개월간 20% 이상 증가했습니다.",
    "향후 소비 트렌드는 ‘편리함’ 중심으로, 자동 결제형 서비스가 증가할 것으로 예상됩니다.",
  ];

  // 실제 화면에 표시될 요약문
  const [summary, setSummary] = useState(staticSummary);

  // 로딩 / 에러 상태
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);


  /*
    🧠 [백엔드 RAG 연동 시 사용할 코드]

    useEffect(() => {
      const fetchSummary = async () => {
        setIsLoading(true);
        setError(null);

        try {
          const res = await fetch("http://localhost:8000/rag/summary", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query }),
          });

          if (!res.ok) throw new Error("서버 오류 발생");

          const data = await res.json();

          // data.summary는 문자열 배열 형태여야 함
          setSummary(data.summary || staticSummary);
        } catch (err) {
          console.error("요약 실패:", err);
          setError("AI 요약 데이터를 불러오는 중 오류가 발생했습니다.");
          setSummary(staticSummary); // fallback
        } finally {
          setIsLoading(false);
        }
      };

      fetchSummary();
    }, [query]);

    요약:
    - query가 바뀔 때마다 AI에게 새 요약 요청
    - 성공하면 summary 업데이트
    - 실패하면 staticSummary로 fallback
  */

  return (
    <div
      className="
        relative mb-10 p-[2px] rounded-2xl overflow-hidden
        bg-gradient-to-r from-blue-400 via-indigo-400 to-sky-500
        dark:from-gray-700 dark:via-gray-800 dark:to-gray-900
        animate-gradient-x
        shadow-[0_0_20px_rgba(120,150,255,0.25)]
        dark:shadow-[0_0_20px_rgba(0,0,0,0.5)]
      "
    >
      {/* 내부 Glass Card */}
      <div className="bg-white/90 dark:bg-[#1E2028]/80 backdrop-blur-2xl rounded-2xl p-8 transition-all duration-300">

        {/* 헤더: 타이틀 */}
        <div className="flex items-center gap-3 mb-5">
          <div className="w-2 h-10 bg-gradient-to-b from-blue-400 to-indigo-500 dark:from-gray-500 dark:to-gray-700 rounded-full" />
          <h3 className="text-2xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-500 via-indigo-500 to-sky-600 dark:from-gray-200 dark:via-gray-300 dark:to-gray-100">
            AI 요약 분석 결과
          </h3>
        </div>

        {/* 요약 내용 */}
        {isLoading ? (
          <p className="text-gray-600 dark:text-gray-400 animate-pulse">
            요약 분석 중입니다...
          </p>
        ) : error ? (
          <p className="text-red-500 text-sm">{error}</p>
        ) : (
          <ul className="space-y-3 text-gray-800 dark:text-gray-100">
            {summary.map((line, i) => (
              <li
                key={i}
                className="
                  group relative overflow-hidden px-4 py-2 rounded-xl
                  bg-gray-50 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700
                  transition-all duration-500
                  shadow-sm
                  animate-fadeInUp
                "
                style={{ animationDelay: `${i * 0.15}s` }}
              >
                {line}
              </li>
            ))}
          </ul>
        )}

        {/* 하단 장식 라인 */}
        <div className="mt-8 h-[2px] bg-gradient-to-r from-transparent via-blue-400/50 to-transparent dark:via-gray-500/40" />
      </div>

      {/* 애니메이션 정의 */}
      <style jsx>{`
        @keyframes gradient-x {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }
        .animate-gradient-x {
          background-size: 200% 200%;
          animation: gradient-x 6s ease infinite;
        }

        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeInUp {
          animation: fadeInUp 0.6s ease forwards;
        }
      `}</style>
    </div>
  );
}