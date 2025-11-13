import React, { useState } from "react";
import {
  FiDownloadCloud,
  FiImage,
  FiFileText,
  FiChevronLeft,
  FiChevronRight,
} from "react-icons/fi";
import Logo from "./Logo";

export default function SidePanel() {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <aside
      className={`hidden lg:flex flex-col ${
        isOpen ? "w-80 p-6" : "w-16 p-3"
      } bg-gray-50 dark:bg-[#1E2028] border-l border-gray-200 dark:border-gray-700 shadow-inner rounded-l-2xl transition-all duration-500 relative`}
    >
      {/* 🔹 패널 접기/펼치기 버튼 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="absolute -left-4 top-10 bg-white dark:bg-[#252731] border border-gray-300 dark:border-gray-600 rounded-full p-1.5 shadow-md hover:scale-110 transition-all"
      >
        {isOpen ? (
          <FiChevronRight className="text-gray-700 dark:text-gray-300" />
        ) : (
          <FiChevronLeft className="text-gray-700 dark:text-gray-300" />
        )}
      </button>

      {/* 🔹 접힘 상태 (아이콘만) */}
      {!isOpen ? (
        <div className="flex flex-col items-center justify-center text-gray-400 dark:text-gray-500 gap-6 mt-10">
          <FiImage size={20} />
          <FiFileText size={20} />
          <FiDownloadCloud size={20} />
        </div>
      ) : (
        <>
          {/* =======================
              🔸 상단 로고 및 슬로건
              ======================= */}
          <div className="flex flex-col items-center text-center mb-10 mt-4">
            <Logo size="medium" />
            <p className="text-sm mt-3 font-medium text-gray-700 dark:text-gray-300 tracking-wide">
              <span className="bg-gradient-to-r from-blue-500 to-indigo-500 bg-clip-text text-transparent">
                AI 기반 인사이트 엔진
              </span>
            </p>
            <div className="w-20 h-[3px] bg-gradient-to-r from-blue-400 to-indigo-500 dark:from-blue-600 dark:to-indigo-400 rounded-full mt-3"></div>
          </div>

          {/* =======================
              🔸 조회 기간 선택
              ======================= */}
          <section className="mb-10">
            <h3 className="text-base font-bold text-gray-800 dark:text-gray-200 mb-3">
              📅 조회 기간
            </h3>
            <div className="flex items-center bg-gray-100 dark:bg-[#252731] rounded-full p-1 shadow-inner">
              <button className="px-5 py-2 bg-white dark:bg-[#1E2028] text-black dark:text-white rounded-full shadow-sm text-sm font-semibold">
                일간
              </button>
              <button className="px-5 py-2 text-gray-600 dark:text-gray-400 hover:text-black dark:hover:text-white text-sm">
                주간
              </button>
              <button className="px-5 py-2 text-gray-600 dark:text-gray-400 hover:text-black dark:hover:text-white text-sm">
                월간
              </button>
            </div>
          </section>

          {/* =======================
              🔸 데이터 통계
              ======================= */}
          <section className="mb-10">
            <h3 className="text-base font-bold text-gray-800 dark:text-gray-200 mb-3">
              📊 데이터 통계
            </h3>
            <div className="bg-gray-100 dark:bg-[#252731] rounded-xl p-5 space-y-3 text-[15px] text-gray-800 dark:text-gray-200 font-medium">
              <p className="flex justify-between">
                <span>총 데이터</span> <span>5,119</span>
              </p>
              <p className="flex justify-between">
                <span>검색 횟수</span> <span>1</span>
              </p>
              <p className="flex justify-between">
                <span>활성 필터</span> <span>0</span>
              </p>
            </div>
          </section>

          {/* =======================
              🔸 내보내기
              ======================= */}
          <section className="mb-10">
            <h3 className="text-base font-bold text-gray-800 dark:text-gray-200 mb-3">
              📤 내보내기
            </h3>
            <div className="flex flex-col gap-3 text-[15px] font-medium">
              <button className="flex items-center gap-2 px-5 py-3 bg-white dark:bg-[#252731] text-gray-900 dark:text-gray-100 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-[#2C2F3A] transition-all duration-200">
                <FiImage /> 차트 이미지 저장
              </button>
              <button className="flex items-center gap-2 px-5 py-3 bg-white dark:bg-[#252731] text-gray-900 dark:text-gray-100 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-[#2C2F3A] transition-all duration-200">
                <FiFileText /> 결과 PDF 다운로드
              </button>
              <button className="flex items-center gap-2 px-5 py-3 bg-white dark:bg-[#252731] text-gray-900 dark:text-gray-100 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-[#2C2F3A] transition-all duration-200">
                <FiDownloadCloud /> CSV 내보내기
              </button>
            </div>
          </section>

          {/* =======================
              🔸 최근 검색
              ======================= */}
          <section>
            <h3 className="text-base font-bold text-gray-800 dark:text-gray-200 mb-3">
              🕓 최근 검색
            </h3>
            <div className="bg-gray-100 dark:bg-[#252731] rounded-xl p-5 space-y-3 text-[15px] text-gray-700 dark:text-gray-300">
              <p>· 30대 남성 소비 데이터</p>
              <p>· AI 서비스 이용률</p>
              <p>· 지역별 소비 변화</p>
            </div>
          </section>
        </>
      )}
    </aside>
  );
}