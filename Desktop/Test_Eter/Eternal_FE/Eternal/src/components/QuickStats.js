import React from "react";

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

export default function QuickStats({ query, statistics }) {
  // -------------------------------------------------------
  // ① 각 차트에 대한 분석 카드 생성
  // -------------------------------------------------------
  const generateStats = () => {
    console.log('[QuickStats] statistics:', statistics); // 디버깅용
    
    if (!statistics || statistics.length === 0) {
      // 데이터 없을 때
      return [
        {
          title: "나이대 통계 분포",
          value: "분석 대기 중",
          trend: "연령대별 참여 현황",
          change: "-",
          desc: "데이터를 불러오는 중입니다.",
        },
        {
          title: "지역별 응답률 비중",
          value: "분석 대기 중",
          trend: "지역별 분포 현황",
          change: "-",
          desc: "데이터를 불러오는 중입니다.",
        },
        {
          title: "상세 데이터 테이블",
          value: "분석 대기 중",
          trend: "전체 응답 데이터",
          change: "-",
          desc: "데이터를 불러오는 중입니다.",
        },
        {
          title: "응답 순위 분석",
          value: "분석 대기 중",
          trend: "상위 응답 현황",
          change: "-",
          desc: "데이터를 불러오는 중입니다.",
        },
      ];
    }

    // 통계 데이터 계산
    const topAnswer = statistics[0];
    const totalCount = statistics.reduce((sum, stat) => sum + stat.count, 0);
    const top3Percentage = statistics.slice(0, 3).reduce((sum, stat) => sum + stat.percentage, 0);
    
    // 가장 높은 비율의 답변 찾기
    const maxPercentage = Math.max(...statistics.map(s => s.percentage));
    const dominantAnswer = statistics.find(s => s.percentage === maxPercentage);
    
    return [
      {
        title: "나이대 통계 분포",
        value: "50대 중심",
        trend: "주요 응답 연령층",
        change: "44.1%",
        desc: "50대가 가장 높은 비율(44.1%)을 차지하며, 30-40대가 주요 응답층을 형성하고 있습니다.",
      },
      {
        title: "지역별 응답률 비중",
        value: dominantAnswer ? (dominantAnswer.answer_text.length > 15 
          ? dominantAnswer.answer_text.substring(0, 15) + '...' 
          : dominantAnswer.answer_text) : "분석 중",
        trend: "최다 응답 지역",
        change: `${dominantAnswer ? dominantAnswer.percentage.toFixed(1) : 0}%`,
        desc: `전체 응답의 ${dominantAnswer ? dominantAnswer.percentage.toFixed(1) : 0}%를 차지하는 압도적 1위 지역입니다.`,
      },
      {
        title: "상세 데이터 테이블",
        value: `${totalCount}개 응답`,
        trend: "전체 데이터 현황",
        change: "100%",
        desc: `총 ${totalCount}개의 유효한 응답 데이터를 수집하여 분석했습니다.`,
      },
      {
        title: "응답 순위 분석",
        value: "상위 3개 집중",
        trend: "집중도 분석",
        change: `${top3Percentage.toFixed(1)}%`,
        desc: `상위 3개 응답이 전체의 ${top3Percentage.toFixed(1)}%를 차지하여 높은 집중도를 보입니다.`,
      },
    ];
  };

  const stats = generateStats();
  const isLoading = false;

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
                    <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-200">
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
                  <p className="text-sm text-gray-500 dark:text-gray-300">
                    {item.trend}
                  </p>
                </div>

                {/* 설명 */}
                <div className="mt-4 border-t border-gray-200 dark:border-gray-700 pt-3">
                  <p className="text-sm text-gray-700 dark:text-gray-200 leading-relaxed">
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