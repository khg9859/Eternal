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

export default function ChartSection({ query, data }) {

  useEffect(() => {
    let ageChart, categoryChart, sentimentTrustChart;
    
    // data가 없으면 차트를 그리지 않음
    if (!data || !data.statistics) {
      return;
    }
    
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
    // ③ 백엔드 데이터를 차트 형식으로 변환
    // -------------------------------------------------------
    // statistics 데이터를 차트용으로 변환
    const statistics = data.statistics || [];
    
    // 지역별 분포 사용 (region_distribution_percent가 있으면 사용, 없으면 statistics 사용)
    const category_ratio = data.region_distribution_percent || {};
    
    // region_distribution_percent가 없으면 statistics의 상위 5개 사용
    if (Object.keys(category_ratio).length === 0) {
      const topAnswers = statistics.slice(0, 5);
      topAnswers.forEach(stat => {
        const shortText = stat.answer_text.length > 20 
          ? stat.answer_text.substring(0, 20) + '...' 
          : stat.answer_text;
        category_ratio[shortText] = stat.percentage;
      });
    }
    
    // 실제 demographics 데이터 사용 (백엔드에서 가져옴)
    // 퍼센트 데이터가 있으면 사용, 없으면 인원수 사용
    const demographics = data.demographics_percent || data.demographics || { "20대": 0, "30대": 0, "40대": 0, "50대": 0 };
    
    // 응답 순위 데이터 (상위 3개) - 실제 항목명 사용
    const topRankings = statistics.slice(0, 3);
    const ranking_data = {};
    topRankings.forEach((stat) => {
      // 항목명이 너무 길면 축약
      const label = stat.answer_text.length > 15 
        ? stat.answer_text.substring(0, 15) + '...' 
        : stat.answer_text;
      ranking_data[label] = stat.percentage;
    });
    
    // 차트 렌더링
    (() => {
      
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
      // ⑤ 지역별 응답 비율 (Doughnut)
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
      // ⑥ 응답 순위 차트 (Bar)
      // -------------------------------------------------------
      sentimentTrustChart = new Chart(document.getElementById("sentimentTrustChart"), {
      type: "bar",
      data: {
        labels: Object.keys(ranking_data),
        datasets: [
          {
            label: "응답 비율 (%)",
            data: Object.values(ranking_data),
            backgroundColor: [palette.primary, palette.secondary, palette.accent],
            borderRadius: 6,
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


    })();

    // -------------------------------------------------------
    // ⑧ cleanup (메모리 누수 방지)
    // -------------------------------------------------------
    return () => {
      if (ageChart) ageChart.destroy();
      if (categoryChart) categoryChart.destroy();
      if (sentimentTrustChart) sentimentTrustChart.destroy();
    };
  }, [data]); // data 변경 시 차트 다시 렌더링


  // -------------------------------------------------------
  // JSX 렌더링
  // -------------------------------------------------------
  return (
    <>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">

        {/* ① 인구통계 막대그래프 */}
        <div className="lg:col-span-2 bg-white/95 dark:bg-[#1E2028] rounded-3xl p-6 border border-gray-200 dark:border-gray-700 shadow-md">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">나이대 통계 분포</h3>
          <div className="h-[380px]"><canvas id="ageChart"></canvas></div>
        </div>

        {/* ② 카테고리 도넛 */}
        <div className="bg-white/95 dark:bg-[#1E2028] rounded-3xl p-6 border border-gray-200 dark:border-gray-700 shadow-md">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">지역별 응답률 비중</h3>
          <div className="h-[380px]"><canvas id="categoryChart"></canvas></div>
        </div>

        {/* ③ 데이터 테이블 */}
        <div className="lg:col-span-2">
          <DataTable query={query} data={data} />
        </div>

        {/* ④ 감정/신뢰 */}
        <div className="bg-white/95 dark:bg-[#1E2028] rounded-3xl p-6 border border-gray-200 dark:border-gray-700 shadow-md">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">응답 순위 및 성별 응답률</h3>
          <div className="h-[380px]"><canvas id="sentimentTrustChart"></canvas></div>
        </div>
      </div>
    </>
  );
}