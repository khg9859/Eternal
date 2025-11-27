import React from "react";

export default function DashboardHeader() {
  return (
    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 mb-10">
      {/* 🔹 왼쪽 섹션: 프로젝트 소개 */}
      <div>
        <div className="flex items-center gap-3 mb-2">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            에테르넬 x PMI 실시간 인사이트 분석
          </h2>
          <span className="px-3 py-1 bg-blue-500/10 text-blue-600 dark:text-blue-400 text-sm font-medium rounded-full">
            실시간
          </span>
        </div>

        <p className="text-gray-600 dark:text-gray-400 max-w-2xl leading-relaxed">
          한성대학교 기업연계 SW캡스톤 프로젝트{" "}
          <span className="font-semibold text-blue-600 dark:text-blue-400">에테르넬(ETERNAL)</span>은
          <span className="font-medium text-gray-800 dark:text-gray-200">
            {" "}
            자연어 질의 기반 데이터 분석 플랫폼
          </span>
          입니다. 사용자가 자연어로 질문하면 AI가 데이터를 분석하여
          관련 통계, 트렌드, 인사이트를 시각화해줍니다.
        </p>

        <p className="text-gray-600 dark:text-gray-400 mt-3">
          본 페이지는{" "}
          <span className="font-semibold text-indigo-600 dark:text-indigo-400">
            PMI(피엠아이)
          </span>{" "}
          기업의 패널 데이터를 기반으로 시장·소비자 행동 변화를
          실시간으로 분석하는 대시보드입니다.
        </p>
      </div>
    </div>
  );
}