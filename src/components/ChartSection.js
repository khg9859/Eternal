import React, { useEffect } from "react";
import Chart from "chart.js/auto";
import DataTable from "./DataTable";

export default function ChartSection({ query }) {
  useEffect(() => {
    // 1) 라이트/다크 모드 팔레트
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

    // 2) Chart.js 기본값
    Chart.defaults.color = palette.text;
    Chart.defaults.font = {
      family: "'Inter', 'Pretendard', sans-serif",
      size: 14,
      weight: "600",
      lineHeight: 1.5,
    };

    // ✅ 이미 존재하는 차트가 있으면 먼저 제거
    const destroyIfExists = (canvasIdOrCtx) => {
      const existing = Chart.getChart(canvasIdOrCtx);
      if (existing) existing.destroy();
    };

    let ageChart = null;
    let categoryChart = null;
    let sentimentTrustChart = null;

    async function fetchAndRenderCharts() {
      // 더미 기본값들
      const demographics = { "20대": 24, "30대": 41, "40대": 28, "50대": 7 };
      let categoryRatio = { 식품: 30, 패션: 25, IT: 20, 여가: 15, 기타: 10 };
      const sentiment_score = { 긍정: 68, 중립: 22, 부정: 10 };
      const trust_index = [84, 86, 87, 89, 90, 92];

      // --- /viz 호출 ---
      try {
        const res = await fetch("http://localhost:8000/viz", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query }),
        });
        const data = await res.json();

        if (data.error) {
          console.warn("📊 통계 파이프라인 오류:", data.error);
        } else {
          const active = data.active_charts || [];
          const charts = data.chart_data || {};

          if (active.includes("category_share") && charts.category_share) {
            if (charts.category_share.value_counts) {
              // 백엔드가 집계해서 보낸 경우
              categoryRatio = charts.category_share.value_counts;
            } else {
              // 프론트에서 집계 (fallback)
              const rows = charts.category_share.answers || [];
              const tmp = {};
              rows.forEach((row) => {
                const label = row.answer_value_text || row.answer_value || "기타";
                tmp[label] = (tmp[label] || 0) + 1;
              });
              if (Object.keys(tmp).length > 0) categoryRatio = tmp;
            }
          }
        }
      } catch (err) {
        console.error("📊 /viz API 호출 실패:", err);
      }

      // --- ④ 인구통계 막대 그래프 ---
      const ageCtx = document.getElementById("ageChart");
      if (ageCtx) {
        destroyIfExists(ageCtx); // ✅ 새로 만들기 전에 항상 제거

        ageChart = new Chart(ageCtx, {
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
                ticks: {
                  color: isDark ? "#FFFFFF" : palette.text,
                  font: { weight: "bold" },
                },
              },
              x: {
                ticks: {
                  color: isDark ? "#FFFFFF" : palette.text,
                  font: { weight: "bold" },
                },
              },
            },
          },
        });
      }

      // --- ⑤ 카테고리 비중 도넛 ---
      const categoryCtx = document.getElementById("categoryChart");
      if (categoryCtx) {
        destroyIfExists(categoryCtx); // ✅

        categoryChart = new Chart(categoryCtx, {
          type: "doughnut",
          data: {
            labels: Object.keys(categoryRatio),
            datasets: [
              {
                data: Object.values(categoryRatio),
                backgroundColor: isDark
                  ? [
                      palette.primary,
                      palette.secondary,
                      "#F472B6",
                      palette.accent,
                      "#34D399",
                    ]
                  : [
                      "#6366F1",
                      "#8B5CF6",
                      "#EC4899",
                      "#3B82F6",
                      "#10B981",
                    ],
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
                  color: isDark ? "#FFFFFF" : palette.text,
                  font: { size: 14, weight: "600" },
                },
              },
            },
            maintainAspectRatio: false,
          },
        });
      }

      // --- ⑥ 감정/신뢰 복합 차트 ---
      const sentimentCtx = document.getElementById("sentimentTrustChart");
      if (sentimentCtx) {
        destroyIfExists(sentimentCtx); // ✅

        sentimentTrustChart = new Chart(sentimentCtx, {
          type: "bar",
          data: {
            labels: Object.keys(sentiment_score),
            datasets: [
              {
                label: "감정 비율 (%)",
                data: Object.values(sentiment_score),
                backgroundColor: [
                  palette.positive,
                  palette.neutral,
                  palette.negative,
                ],
                borderRadius: 6,
                order: 2,
              },
              {
                label: "AI 신뢰도 (%)",
                data: trust_index.slice(0, 3),
                type: "line",
                borderColor: palette.accent,
                backgroundColor: isDark
                  ? "rgba(59,130,246,0.4)"
                  : "rgba(59,130,246,0.25)",
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
                labels: {
                  color: isDark ? "#FFFFFF" : palette.text,
                  font: { size: 14, weight: "600" },
                },
              },
            },
            scales: {
              y: {
                beginAtZero: true,
                max: 100,
                grid: { color: palette.grid },
                ticks: { color: isDark ? "#FFFFFF" : palette.text },
              },
              x: {
                ticks: { color: isDark ? "#FFFFFF" : palette.text },
              },
            },
          },
        });
      }
    }

    fetchAndRenderCharts();

    // cleanup: 언마운트 시 안전하게 한 번 더 destroy
    return () => {
      if (ageChart) ageChart.destroy();
      if (categoryChart) categoryChart.destroy();
      if (sentimentTrustChart) sentimentTrustChart.destroy();
    };
  }, [query]);

  // JSX
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
      {/* ① 인구통계 막대그래프 */}
      <div className="lg:col-span-2 bg-white/80 dark:bg-[#1E2028]/90 rounded-3xl p-6 border border-gray-200 dark:border-gray-700 shadow-md">
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">
          인구통계 분포
        </h3>
        <div className="h-[380px]">
          <canvas id="ageChart"></canvas>
        </div>
      </div>

      {/* ② 카테고리 도넛 */}
      <div className="bg-white/80 dark:bg-[#1E2028]/90 rounded-3xl p-6 border border-gray-200 dark:border-gray-700 shadow-md">
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">
          주요 카테고리 비중
        </h3>
        <div className="h-[380px]">
          <canvas id="categoryChart"></canvas>
        </div>
      </div>

      {/* ③ 데이터 테이블 */}
      <div className="lg:col-span-2">
        <DataTable query={query} />
      </div>

      {/* ④ 감정/신뢰 */}
      <div className="bg-white/80 dark:bg-[#1E2028]/90 rounded-3xl p-6 border border-gray-200 dark:border-gray-700 shadow-md">
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-3">
          감정·신뢰 지표
        </h3>
        <div className="h-[380px]">
          <canvas id="sentimentTrustChart"></canvas>
        </div>
      </div>
    </div>
  );
}

