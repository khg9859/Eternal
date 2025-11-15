import React from "react";

export default function QuickStats({ query, statistics, demographics, regionDistribution, totalRespondents }) {
  const generateStats = () => {
    console.log('[QuickStats] statistics:', statistics);
    console.log('[QuickStats] demographics:', demographics);
    console.log('[QuickStats] regionDistribution:', regionDistribution);
    
    if (!statistics || statistics.length === 0) {
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

    const topAnswer = statistics[0];
    const totalCount = totalRespondents || statistics.reduce((sum, stat) => sum + stat.count, 0);
    const top3Percentage = statistics.slice(0, 3).reduce((sum, stat) => sum + stat.percentage, 0);
    
    const maxPercentage = Math.max(...statistics.map(s => s.percentage));
    const dominantAnswer = statistics.find(s => s.percentage === maxPercentage);
    
    let ageAnalysis = { value: "분석 중", change: "-", desc: "나이대 데이터를 분석하고 있습니다." };
    if (demographics && Object.keys(demographics).length > 0) {
      const ageGroups = Object.entries(demographics);
      const maxAgeGroup = ageGroups.reduce((max, curr) => curr[1] > max[1] ? curr : max, ageGroups[0]);
      const agePercentage = ((maxAgeGroup[1] / totalCount) * 100).toFixed(1);
      
      ageAnalysis = {
        value: `${maxAgeGroup[0]} 중심`,
        change: `${agePercentage}%`,
        desc: `${maxAgeGroup[0]}가 가장 높은 비율(${agePercentage}%)을 차지하고 있습니다.`
      };
    }
    
    return [
      {
        title: "나이대 통계 분포",
        value: ageAnalysis.value,
        trend: "주요 응답 연령층",
        change: ageAnalysis.change,
        desc: ageAnalysis.desc,
      },
      {
        title: "지역별 응답률 비중",
        value: (() => {
          if (regionDistribution && Object.keys(regionDistribution).length > 0) {
            const regions = Object.entries(regionDistribution);
            const maxRegion = regions.reduce((max, curr) => curr[1] > max[1] ? curr : max, regions[0]);
            return maxRegion[0];
          }
          return "분석 중";
        })(),
        trend: "최다 응답 지역",
        change: (() => {
          if (regionDistribution && Object.keys(regionDistribution).length > 0) {
            const regions = Object.entries(regionDistribution);
            const maxRegion = regions.reduce((max, curr) => curr[1] > max[1] ? curr : max, regions[0]);
            const percentage = ((maxRegion[1] / totalCount) * 100).toFixed(1);
            return `${percentage}%`;
          }
          return "-";
        })(),
        desc: (() => {
          if (regionDistribution && Object.keys(regionDistribution).length > 0) {
            const regions = Object.entries(regionDistribution);
            const maxRegion = regions.reduce((max, curr) => curr[1] > max[1] ? curr : max, regions[0]);
            const percentage = ((maxRegion[1] / totalCount) * 100).toFixed(1);
            return `${maxRegion[0]}가 전체 응답의 ${percentage}%를 차지하는 최다 응답 지역입니다.`;
          }
          return "지역 데이터를 분석하고 있습니다.";
        })(),
      },
      {
        title: "상세 데이터 테이블",
        value: `${totalCount}개 응답자`,
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

  return (
    <section className="mt-10 transition-all duration-500">
      <div className="flex items-center justify-between mb-8">
        <h2 className="text-2xl font-bold bg-gradient-to-r from-gray-900 via-gray-700 to-gray-900 dark:from-gray-100 dark:via-gray-400 dark:to-gray-200 bg-clip-text text-transparent">
          📈 "{query}" 관련된 주요 통계
        </h2>
        <span className="text-gray-500 dark:text-gray-400 text-sm">(AI 기반 요약 데이터)</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
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
              <div className="bg-white/90 dark:bg-[#1E2028]/90 rounded-2xl h-full p-6 backdrop-blur-xl flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-200">
                      {item.title}
                    </h3>
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
                  <p className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                    {item.value}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-300">
                    {item.trend}
                  </p>
                </div>
                <div className="mt-4 border-t border-gray-200 dark:border-gray-700 pt-3">
                  <p className="text-sm text-gray-700 dark:text-gray-200 leading-relaxed">
                    {item.desc}
                  </p>
                </div>
              </div>
              <div className="absolute inset-0 bg-gradient-to-tr from-white/0 via-white/10 to-white/0 
              opacity-0 group-hover:opacity-100 transition-opacity duration-700 rounded-2xl"></div>
            </div>
          ))
        )}
      </div>
    </section>
  );
}
