import React, { useState, useEffect } from "react";
import {
  FiDownloadCloud,
  FiImage,
  FiFileText,
  FiChevronLeft,
  FiChevronRight,
} from "react-icons/fi";
import Logo from "./Logo";
import html2canvas from "html2canvas";
import jsPDF from "jspdf";

export default function SidePanel({ query, data, dateRange, onDateRangeChange }) {
  const [isOpen, setIsOpen] = useState(true);
  const [recentSearches, setRecentSearches] = useState([]);

  // 최근 검색어 로드 및 저장
  useEffect(() => {
    const saved = localStorage.getItem("recentSearches");
    if (saved) {
      setRecentSearches(JSON.parse(saved));
    }
  }, []);

  useEffect(() => {
    if (query) {
      let searches = JSON.parse(localStorage.getItem("recentSearches") || "[]");
      // 중복 제거 및 최신 검색어를 위로
      searches = searches.filter((s) => s !== query);
      searches.unshift(query);
      // 최대 5개 유지
      if (searches.length > 5) searches.pop();

      localStorage.setItem("recentSearches", JSON.stringify(searches));
      setRecentSearches(searches);
    }
  }, [query]);

  // 이미지 저장 핸들러
  const handleImageExport = async () => {
    const element = document.body; // 전체 페이지 캡처 (또는 특정 영역)
    const canvas = await html2canvas(element);
    const link = document.createElement("a");
    link.download = `report-${query}-${Date.now()}.png`;
    link.href = canvas.toDataURL();
    link.click();
  };

  // PDF 다운로드 핸들러
  const handlePdfExport = async () => {
    const element = document.body;
    const canvas = await html2canvas(element);
    const imgData = canvas.toDataURL("image/png");

    const pdf = new jsPDF("p", "mm", "a4");
    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = (canvas.height * pdfWidth) / canvas.width;

    pdf.addImage(imgData, "PNG", 0, 0, pdfWidth, pdfHeight);
    pdf.save(`report-${query}-${Date.now()}.pdf`);
  };

  // CSV 내보내기 핸들러
  const handleCsvExport = () => {
    if (!data) {
      alert("내보낼 데이터가 없습니다.");
      return;
    }

    // 간단한 CSV 생성 예시 (통계 데이터)
    const headers = ["Category", "Value"];
    const rows = [
      ["Query", query],
      ["Total Respondents", data.total_respondents || 0],
      // 필요한 데이터 추가
    ];

    if (data.statistics) {
      Object.entries(data.statistics).forEach(([key, val]) => {
        rows.push([key, val]);
      });
    }

    let csvContent = "data:text/csv;charset=utf-8,"
      + headers.join(",") + "\n"
      + rows.map(e => e.join(",")).join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `data-${query}-${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // 통계 데이터 (없으면 기본값 0)
  const totalData = data?.total_respondents || 0;
  const searchCount = recentSearches.length; // 예시로 최근 검색어 수 사용
  const activeFilters = 0; // 필터 기능 구현 시 연동

  return (
    <aside
      className={`hidden lg:flex flex-col ${isOpen ? "w-80 p-6" : "w-16 p-3"
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
          <FiImage size={20} onClick={handleImageExport} className="cursor-pointer hover:text-blue-500" title="이미지 저장" />
          <FiFileText size={20} onClick={handlePdfExport} className="cursor-pointer hover:text-blue-500" title="PDF 다운로드" />
          <FiDownloadCloud size={20} onClick={handleCsvExport} className="cursor-pointer hover:text-blue-500" title="CSV 다운로드" />
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
              🔸 데이터 통계
              ======================= */}
          <section className="mb-10">
            <h3 className="text-base font-bold text-gray-800 dark:text-gray-200 mb-3">
              📊 데이터 통계
            </h3>
            <div className="bg-gray-100 dark:bg-[#252731] rounded-xl p-5 space-y-3 text-[15px] text-gray-800 dark:text-gray-200 font-medium">
              <p className="flex justify-between">
                <span>총 데이터</span> <span>{totalData.toLocaleString()}</span>
              </p>
              <p className="flex justify-between">
                <span>검색 횟수</span> <span>{searchCount}</span>
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
              <button
                onClick={handleImageExport}
                className="flex items-center gap-2 px-5 py-3 bg-white dark:bg-[#252731] text-gray-900 dark:text-gray-100 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-[#2C2F3A] transition-all duration-200"
              >
                <FiImage /> 차트 이미지 저장
              </button>
              <button
                onClick={handlePdfExport}
                className="flex items-center gap-2 px-5 py-3 bg-white dark:bg-[#252731] text-gray-900 dark:text-gray-100 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-[#2C2F3A] transition-all duration-200"
              >
                <FiFileText /> 결과 PDF 다운로드
              </button>
              <button
                onClick={handleCsvExport}
                className="flex items-center gap-2 px-5 py-3 bg-white dark:bg-[#252731] text-gray-900 dark:text-gray-100 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-[#2C2F3A] transition-all duration-200"
              >
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
              {recentSearches.length === 0 ? (
                <p className="text-gray-400 text-sm">최근 검색 기록이 없습니다.</p>
              ) : (
                recentSearches.map((term, idx) => (
                  <p key={idx} className="truncate">· {term}</p>
                ))
              )}
            </div>
          </section>
        </>
      )}
    </aside>
  );
}
