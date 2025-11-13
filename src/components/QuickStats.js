import React, { useState } from "react";

/*
  QuickStats.js
  -------------------------------------------------------
  이 컴포넌트는 “사용자가 입력한 query에 대한 핵심 통계들을
  카드 형태로 빠르게 보여주는 영역”이다.

  구성 요소:
    - 소비 주요 카테고리
    - 평균 이용 빈도
    - 주요 연령대
    - 향후 예측 지표

  현재 상태:
    - 프론트 더미 데이터(dummyStats)를 UI 렌더링하는 구조
    - RAG 백엔드 연동 시 /rag/stats 엔드포인트에서 가져오도록 예정

  RAG 연동 시 데이터 흐름:
  -------------------------------------------------------
  1) ResultsPage → <QuickStats query="질문" />
  2) QuickStats 내부 useEffect에서 POST 요청:
        /rag/stats
        { query: "...사용자 질문..." }
  3) 백엔드에서 패널 데이터 기반 통계 계산 후 JSON으로 반환:
        { stats: [ {...}, {...}, ... ] }
  4) stats 업데이트 후 카드가 자동 렌더링됨

  이점:
    - UI 렌더링 로직과 데이터 분석 로직을 완전히 분리하여 유지보수성 향상
    - 백엔드가 교체되어도 UI 로직은 그대로 재사용 가능
*/

export default function QuickStats({ query }) {
  // -------------------------------------------------------
  // ① 프론트 더미 데이터 (RAG 붙을 때 백엔드 결과로 대체됨)
  // -------------------------------------------------------
  const dummyStats = [
    {
      title: "주요 관심 카테고리",
      value: "식품 · 온라인 쇼핑 · 구독 서비스",
      trend: "소비 트렌드 전환 가속화",
      change: "+8.7%",
      desc: "최근 3개월간 식품·구독형 서비스의 지출 비중이 크게 증가했습니다.",
    },
    {
      title: "평균 이용 빈도",
      value: "월 18회",
      trend: "활동성 상승",
      change: "+2.4%",
      desc: "모바일 결제 사용률 증가와 함께 결제 빈도가 상승하고 있습니다.",
    },
    {
      title: "주요 연령대",
      value: "30대 후반",
      trend: "주요 구매층",
      change: "▲",
      desc: "가전, 패션, 여행 카테고리 중심으로 소비 집중도가 높습니다.",
    },
    {
      title: "향후 예측 지표",
      value: "자동 결제형 서비스 확산",
      trend: "미래 트렌드",
      change: "↑",
      desc: "AI 기반 구독·정기결제 서비스 시장이 빠르게 성장할 것으로 예측됩니다.",
    },
  ];

  // -------------------------------------------------------
  // ② 컴포넌트 상태
  // -------------------------------------------------------
  const [stats, setStats] = useState(dummyStats);
  const [isLoading, setIsLoading] = useState(false);

  /*
  // -------------------------------------------------------
  // ③ RAG 백엔드 연동 코드 (현재는 주석 처리)
  // -------------------------------------------------------
  useEffect(() => {
    const fetchQuickStats = async () => {
      setIsLoading(true);
      try {
        const res = await fetch("http://localhost:8000/rag/stats", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query }),
        });

        const data = await res.json();
        setStats(data.stats || dummyStats);
      } catch (err) {
        console.error("QuickStats 불러오기 실패:", err);
        setStats(dummyStats); // 실패하면 기본값
      } finally {
        setIsLoading(false);
      }
    };

    fetchQuickStats();
  }, [query]);
  */


  // -------------------------------------------------------
  // JSX 렌더링
  // -------------------------------------------------------
  return (
    <section className="mt-10 transition-all duration-500">
      
      {/* 🔹 헤더 영역: "주요 통계" 제목 */}
      <div className="flex items-center justify-between mb-8">
        <h2 className="text-2xl font-bold bg-gradient-to-r from-gray-900 via-gray-700 to-gray-900 dark:from-gray-100 dark:via-gray-400 dark:to-gray-200 bg-clip-text text-transparent">
          📈 "{query}" 관련된 주요 통계
        </h2>
        <span className="text-gray-500 dark:text-gray-400 text-sm">(AI 기반 요약 데이터)</span>
      </div>

      {/* 🔹 카드 리스트 (총 4개) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        
        {/* 로딩 중 화면 */}
        {isLoading ? (
          <div className="col-span-4 text-center py-10 text-gray-500 dark:text-gray-400 animate-pulse">
            분석 중입니다...
          </div>
        ) : (
          stats.map((item, idx) => (
            <div
              key={idx}
              className="group relative p-[2px] rounded-2xl bg-gradient-to-tr from-gray-200 via-gray-300 to-gray-200
              dark:from-gray-700 dark:via-gray-800 dark:to-gray-900
              shadow-[0_0_25px_rgba(0,0,0,0.1)] hover:shadow-[0_0_40px_rgba(0,0,0,0.25)]
              transition-all duration-500"
            >
              {/* 카드 내부 */}
              <div className="bg-white/90 dark:bg-[#1E2028]/90 rounded-2xl h-full p-6 backdrop-blur-xl flex flex-col justify-between">

                {/* 제목 · 변화율 */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-400">
                      {item.title}
                    </h3>

                    {/* 변화율 배지 */}
                    <span
                      className={`text-xs font-bold px-2 py-1 rounded-md ${
                        item.change.includes("+") || item.change.includes("↑")
                          ? "bg-green-100 text-green-600 dark:bg-green-900/40 dark:text-green-400"
                          : "bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-400"
                      }`}
                    >
                      {item.change}
                    </span>
                  </div>

                  {/* 핵심값 */}
                  <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                    {item.value}
                  </p>

                  {/* 트렌드 */}
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {item.trend}
                  </p>
                </div>

                {/* 설명 */}
                <div className="mt-4 border-t border-gray-200 dark:border-gray-700 pt-3">
                  <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                    {item.desc}
                  </p>
                </div>
              </div>

              {/* hover 반짝 효과 */}
              <div className="absolute inset-0 bg-gradient-to-tr from-white/0 via-white/10 to-white/0 
              opacity-0 group-hover:opacity-100 transition-opacity duration-700 rounded-2xl"></div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}