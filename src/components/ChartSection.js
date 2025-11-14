import React, { useEffect } from "react";
import Chart from "chart.js/auto";
import DataTable from "./DataTable";

/*
  ChartSection.js
  -------------------------------------------------------
  이 컴포넌트는 “AI 분석 결과를 시각화하는 4개의 차트(막대/도넛/선/복합)”를
  렌더링하는 핵심 UI 컴포넌트이다.

  주요 역할:
  - query(사용자 질문)에 따라 데이터를 받아 시각화
  - 라이트/다크 모드에 따른 팔레트 색상 자동 변경
  - 차트 4종 렌더링:
      ① 인구통계 분포 (Bar)
      ② 카테고리 비중 (Doughnut)
      ③ 월별 트렌드 (Line)
      ④ 감정 & 신뢰도 (Bar + Line)
  - useEffect 내에서 차트 인스턴스 생성 → 컴포넌트 언마운트 시 destroy()

  RAG 백엔드 연동 시 흐름:
  -------------------------------------------------------
  1) ResultsPage.js → <ChartSection query="사용자 질문" />
  2) ChartSection이 API 요청:
        POST /rag/charts
        { query: "사용자 질문" }
  3) 백엔드 LangChain + 벡터DB가 관련 문서를 가져와 패널 통계 분석
  4) 다음 형태로 응답(JSON):
        {
          demographics: {...},
          category_ratio: {...},
          monthly_trend: {...},
          sentiment_score: {...},
          trust_index: [...]
        }
  5) ChartSection은 해당 데이터를 그대로 차트에 반영

  현재는 프론트 더미 데이터로 동작하며,
  RAG 연결 시 `더미 데이터 부분`만 fetch로 교체하면 된다.
*/

export default function ChartSection({ query }) {

  useEffect(() => {
    let ageChart, categoryChart, sentimentTrustChart;
    
    // -------------------------------------------------------
    // ① 라이트/다크 모드 감지 → 팔레트 지정
    // -------------------------------------------------------
    const isDark = document.documentElement.classList.contains("dark");

    const palette = isDark
      ? {
          text: "#FFFFFF",
          grid: "rgba(255,255,255,0.15)",
          border: "#4B5563",
          bg: "#111827",
          primary: "#818CF8",
          secondary: "#A78BFA",
          accent: "#60A5FA",
          positive: "#22C55E",
          neutral: "#EAB308",
          negative: "#EF4444",
        }
      : {
          text: "#1F2937",
          grid: "rgba(0,0,0,0.06)",
          border: "#D1D5DB",
          bg: "#FFFFFF",
          primary: "#6366F1",
          secondary: "#8B5CF6",
          accent: "#3B82F6",
          positive: "rgba(34,197,94,1)",
          neutral: "rgba(250,204,21,1)",
          negative: "rgba(239,68,68,1)",
        };

    // -------------------------------------------------------
    // ② Chart.js 기본 전역 설정
    // -------------------------------------------------------
    Chart.defaults.color = isDark ? "#E5E7EB" : "#1F2937"; // 라이트/다크 모드에 따라 자동 변경
    Chart.defaults.font = {
      family: "'Inter', 'Pretendard', sans-serif",
      size: 14,
      weight: "600",
      lineHeight: 1.5,
    };

    // -------------------------------------------------------
    // ③ 백엔드에서 차트 데이터 가져오기
    // -------------------------------------------------------
    const fetchChartData = async () => {
      try {
        const res = await fetch("http://localhost:8000/rag/charts", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query }),
        });
        
        if (!res.ok) throw new Error('차트 데이터 로드 실패');
        
        const data = await res.json();
        return data;
      } catch (error) {
        console.error('차트 데이터 로드 오류:', error);
        // Fallback 더미 데이터
        return {
          demographics: { "20대": 24, "30대": 41, "40대": 28, "50대": 7 },
          category_ratio: { "식품": 30, "패션": 25, "IT": 20, "여가": 15, "기타": 10 },
          monthly_trend: { "1월": 82, "2월": 90, "3월": 96, "4월": 103, "5월": 115, "6월": 122 },
          sentiment_score: { 긍정: 68, 중립: 22, 부정: 10 },
          trust_index: [84, 86, 87, 89, 90, 92]
        };
      }
    };

    // 비동기 데이터 로드 및 차트 렌더링
    fetchChartData().then(({ demographics, category_ratio, monthly_trend, sentiment_score, trust_index }) => {
      
      // 기존 차트 인스턴스 제거 (중요!)
      const existingAgeChart = Chart.getChart("ageChart");
      if (existingAgeChart) existingAgeChart.destroy();
      
      const existingCategoryChart = Chart.getChart("categoryChart");
      if (existingCategoryChart) existingCategoryChart.destroy();
      
      const existingSentimentChart = Chart.getChart("sentimentTrustChart");
      if (existingSentimentChart) existingSentimentChart.destroy();

      // -------------------------------------------------------
      // ④ 인구통계 차트 (Bar)
      // -------------------------------------------------------
      ageChart = new Chart(document.getElementById("ageChart"), {
      type: "bar",
      data: {
        labels: Object.keys(demographics),
        datasets: [
          {
            label: "참여 비율 (%)",
            data: Object.values(demographics),
            backgroundColor: isDark
              ? [palette.primary, palette.secondary, "#A5B4FC", "#C4B5FD"]
              : ["#6366F1", "#4F46E5", "#8B5CF6", "#A5B4FC"],
            borderRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: palette.grid },
            ticks: { color: isDark ? "#E5E7EB" : "#1F2937", font: { weight: "bold" } },
          },
          x: {
            grid: { color: palette.grid },
            ticks: { color: isDark ? "#E5E7EB" : "#1F2937", font: { weight: "bold" } },
          },
        },
      },
    });


      // -------------------------------------------------------
      // ⑤ 카테고리 비중 (Doughnut)
      // -------------------------------------------------------
      categoryChart = new Chart(document.getElementById("categoryChart"), {
      type: "doughnut",
      data: {
        labels: Object.keys(category_ratio),
        datasets: [
          {
            data: Object.values(category_ratio),
            backgroundColor: isDark
              ? [palette.primary, palette.secondary, "#F472B6", palette.accent, "#34D399"]
              : ["#6366F1", "#8B5CF6", "#EC4899", "#3B82F6", "#10B981"],
            borderWidth: 0,
          },
        ],
      },
      options: {
        cutout: "70%",
        plugins: {
          legend: {
            position: "bottom",
            labels: { 
              color: isDark ? "#E5E7EB" : "#1F2937", 
              font: { size: 14, weight: "600" } 
            },
          },
        },
        maintainAspectRatio: false,
      },
    });


      // -------------------------------------------------------
      // ⑥ 감정·신뢰(Layered Bar + Line)
      // -------------------------------------------------------
      sentimentTrustChart = new Chart(document.getElementById("sentimentTrustChart"), {
      type: "bar",
      data: {
        labels: Object.keys(sentiment_score),
        datasets: [
          {
            label: "감정 비율 (%)",
            data: Object.values(sentiment_score),
            backgroundColor: [palette.positive, palette.neutral, palette.negative],
            borderRadius: 6,
            order: 2,
          },
          {
            label: "AI 신뢰도 (%)",
            data: trust_index.slice(0, 3),
            type: "line",
            borderColor: palette.accent,
            backgroundColor: isDark ? "rgba(59,130,246,0.4)" : "rgba(59,130,246,0.25)",
            fill: false,
            tension: 0.3,
            order: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: palette.text, font: { size: 14, weight: "600" } },
          },
        },
        scales: {
          y: { beginAtZero: true, max: 100, grid: { color: palette.grid }, ticks: { color: isDark ? "#E5E7EB" : "#1F2937", font: { weight: "bold" } } },
          x: { grid: { color: palette.grid }, ticks: { color: isDark ? "#E5E7EB" : "#1F2937", font: { weight: "bold" } } },
        },
      },
    });


    });

    // -------------------------------------------------------
    // ⑧ cleanup (메모리 누수 방지)
    // -------------------------------------------------------
    return () => {
      if (ageChart) ageChart.destroy();
      if (categoryChart) categoryChart.destroy();
      if (sentimentTrustChart) sentimentTrustChart.destroy();
    };
  }, [query]); // query 변경 시 차트 다시 렌더링


  // -------------------------------------------------------
  // JSX 렌더링
  // -------------------------------------------------------
  return (
    <>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">

        {/* ① 인구통계 막대그래프 */}
        <div className="lg:col-span-2 bg-white/95 dark:bg-[#1E2028] rounded-3xl p-6 border border-gray-200 dark:border-gray-700 shadow-md">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">인구통계 분포</h3>
          <div className="h-[380px]"><canvas id="ageChart"></canvas></div>
        </div>

        {/* ② 카테고리 도넛 */}
        <div className="bg-white/95 dark:bg-[#1E2028] rounded-3xl p-6 border border-gray-200 dark:border-gray-700 shadow-md">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">주요 카테고리 비중</h3>
          <div className="h-[380px]"><canvas id="categoryChart"></canvas></div>
        </div>

        {/* ③ 데이터 테이블 */}
        <div className="lg:col-span-2">
          <DataTable query={query} />
        </div>

        {/* ④ 감정/신뢰 */}
        <div className="bg-white/95 dark:bg-[#1E2028] rounded-3xl p-6 border border-gray-200 dark:border-gray-700 shadow-md">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">감정·신뢰 지표</h3>
          <div className="h-[380px]"><canvas id="sentimentTrustChart"></canvas></div>
        </div>
      </div>
    </>
  );
}