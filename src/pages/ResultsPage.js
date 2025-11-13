import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { motion } from "framer-motion";

// 결과 페이지를 구성하는 주요 UI 컴포넌트
import DashboardHeader from "../components/DashboardHeader";
import AISummary from "../components/AISummary";
import QuickStats from "../components/QuickStats";
import ChartSection from "../components/ChartSection";
import AIChatInterface from "../components/AIChatInterface";
import SidePanel from "../components/SidePanel";

/*
  ResultsPage.js
  --------------------------------------------------
  이 페이지는 "자연어 기반 분석 결과"를 보여주는 대시보드 페이지입니다.

  HomePage → (사용자가 입력한 query) → ResultsPage

  이 페이지에서 수행하는 기능:
  1) 상단 배경 비디오 + 제목
  2) 대시보드 구성 (요약 / 통계 / 그래프)
  3) 사이드 패널
  4) 다크모드 전환
  5) AI 챗봇 열기

  RAG 백엔드 연동 관점 설명:
  --------------------------------------------------
  - ResultsPage는 "query"를 받아서
      → AISummary(query)
      → QuickStats(query)
      → ChartSection(query)
    이 세 컴포넌트에 각각 넘깁니다.

  - 나중에 백엔드가 구축되면
      AISummary / QuickStats / ChartSection 는
      query를 받아 fetch("/analyze") 같은 API를 호출하도록 변경됩니다.

  - 즉, ResultsPage는 프론트 전체 RAG 데이터 플로우의 중심입니다.
*/

export default function ResultsPage() {
  // 홈으로 이동/다른 페이지 이동을 위해 React Router 사용
  const navigate = useNavigate();

  // HomePage에서 전달된 query 값
  const location = useLocation();
  // 사용자가 입력하지 않았을 경우 기본값 지정
  const query = location.state?.query || "30대 남성의 소비 패턴";

  // UI 상태: 다크모드 여부
  const [darkMode, setDarkMode] = useState(false);

  // AI 챗봇 열기 여부
  const [isChatOpen, setIsChatOpen] = useState(false);

  return (
    // 다크모드 class를 최상위 div에 적용 → Tailwind dark: 제어 가능
    <div className={`${darkMode ? "dark" : ""}`}>
      <div className="relative min-h-screen flex bg-white dark:bg-[#1E2028] text-gray-900 dark:text-gray-100 transition-colors duration-500">

        {/* 왼쪽 메인 콘텐츠 영역 */}
        <div className="flex-1 overflow-y-auto">

          {/* 상단 배경 영상 헤더 */}
          <div className="relative h-[320px] w-full overflow-hidden rounded-b-3xl shadow-lg">

            {/* 배경 비디오 */}
            <video
              autoPlay
              muted
              loop
              playsInline
              className="absolute inset-0 w-full h-full object-cover opacity-70"
            >
              <source src="/bg1.mp4" type="video/mp4" />
            </video>

            {/* 오버레이 → 텍스트 가독성 확보 */}
            <div className="absolute inset-0 bg-black/40 dark:bg-black/50" />

            {/* 상단 타이틀/텍스트 */}
            <div className="absolute inset-0 flex flex-col justify-center items-center text-center text-white">

              {/* 메인 제목 */}
              <motion.h1
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 1 }}
                className="text-3xl font-bold mb-3 drop-shadow-lg"
              >
                AI 인사이트 분석 결과
              </motion.h1>

              {/* 분석 대상 query 표시 */}
              <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5, duration: 1 }}
                className="text-lg font-medium text-gray-100/90 drop-shadow-md"
              >
                “{query}” 분석 리포트
              </motion.p>
            </div>

            {/* 모드 전환 / 홈 버튼 */}
            <div className="absolute top-5 right-5 flex gap-3">

              {/* 다크모드 토글 */}
              <button
                onClick={() => setDarkMode(!darkMode)}
                className="px-4 py-2 bg-white/80 dark:bg-gray-700/80 text-gray-800 dark:text-white rounded-lg text-sm font-medium hover:opacity-80 transition-all backdrop-blur-md"
              >
                {darkMode ? "🌙 다크모드" : "☀️ 라이트모드"}
              </button>

              {/* 홈으로 이동 */}
              <button
                onClick={() => navigate("/")}
                className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white font-semibold rounded-lg transition-all shadow-sm backdrop-blur-md"
              >
                🏠 홈으로
              </button>
            </div>
          </div>

          {/* 메인 분석 콘텐츠 */}
          <div className="p-8">

            {/* 대시보드 헤더 (필요 시 날짜/설명 추가 가능) */}
            <DashboardHeader />

            {/* AI 요약 정보 (RAG 응답 주요 텍스트) */}
            {/*
              RAG 연동 시:
              - 백엔드에서 요약 텍스트를 받아와서 표시하는 역할
              - AISummary(query) 내에서 fetch → 요약 텍스트 렌더링 구조로 변환 가능
            */}
            <AISummary query={query} />

            {/* 간단 통계 UI */}
            <QuickStats query={query} />

            {/* 차트 모음 */}
            {/*
              ChartSection(query):
              - 백엔드가 분석한 원시 데이터/수치 기반으로 그래프를 렌더링할 예정
              - 현재는 더미 데이터 기반 Chart.js
              - RAG/DB 연결 후 분석 결과를 차트에 매핑 예정
            */}
            <ChartSection query={query} />
          </div>
        </div>

        {/* 오른쪽 사이드 패널 */}
        <SidePanel />

        {/* AI 챗봇 인터페이스 */}
        {isChatOpen ? (
          <div className="fixed bottom-8 right-8 z-50">
            <AIChatInterface onExit={() => setIsChatOpen(false)} />
          </div>
        ) : (
          <button
            onClick={() => setIsChatOpen(true)}
            className="fixed bottom-8 right-8 z-50 bg-gradient-to-r from-blue-500 to-indigo-500 text-white font-semibold px-5 py-3 rounded-full shadow-lg hover:scale-105 transition-transform"
          >
            💬 챗봇 열기
          </button>
        )}
      </div>
    </div>
  );
}