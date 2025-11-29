import React, { useState, useEffect } from "react";

/*
  DataTable.js
  -------------------------------------------------------
  차트 데이터의 원본을 테이블 형태로 보여주는 컴포넌트
  
  주요 기능:
  - 검색 기능
  - 페이지네이션
  - 정렬 기능
  - 다크모드 지원
  
  RAG 연동 시:
  - POST /rag/table_data
  - { query: "사용자 질문" }
  - 응답: { data: [...] }
*/

// ✅ 응답자 ID 블라인드 처리 함수
function maskRespondentId(id) {
  if (!id || typeof id !== "string") return "";

  // 길이가 6 이하라면 전체 마스킹
  if (id.length <= 6) return "••••••";

  const start = id.slice(0, 4);     // 앞 4글자
  const end = id.slice(-2);         // 뒤 2글자
  const masked = "•".repeat(id.length - 6); // 중간 블라인드

  return `${start}${masked}${end}`;
}

export default function DataTable({ query, data }) {
  const [tableData, setTableData] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [sortConfig, setSortConfig] = useState({ key: null, direction: "asc" });
  const itemsPerPage = 10;

  useEffect(() => {
    if (data && data.answer_data) {
      // 백엔드 데이터를 테이블 형식으로 변환
      const formattedData = data.answer_data.map((item, index) => ({
        id: item.answer_id || index + 1,
        category: item.q_title || "기타",
        answer: item.answer_text || item.answer_value,
        
        // ✅ 응답자 ID 마스킹 적용
        respondent_id: maskRespondentId(item.respondent_id),

        question_id: item.question_id,
      }));
      setTableData(formattedData);
    }
  }, [data]);

  // 검색 필터링
  const filteredData = tableData.filter((item) =>
    Object.values(item).some((val) =>
      String(val).toLowerCase().includes(searchTerm.toLowerCase())
    )
  );

  // 정렬
  const sortedData = [...filteredData].sort((a, b) => {
    if (!sortConfig.key) return 0;

    const aVal = a[sortConfig.key];
    const bVal = b[sortConfig.key];

    if (aVal < bVal) return sortConfig.direction === "asc" ? -1 : 1;
    if (aVal > bVal) return sortConfig.direction === "asc" ? 1 : -1;
    return 0;
  });

  // 페이지네이션
  const totalPages = Math.ceil(sortedData.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedData = sortedData.slice(startIndex, startIndex + itemsPerPage);

  // 정렬 핸들러
  const handleSort = (key) => {
    setSortConfig({
      key,
      direction: sortConfig.key === key && sortConfig.direction === "asc" ? "desc" : "asc",
    });
  };

  return (
    <div className="mt-10 bg-white/80 dark:bg-[#1E2028]/90 rounded-3xl p-6 border border-gray-200 dark:border-gray-700 shadow-md">
      
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-2xl font-bold text-gray-900 dark:text-white">
           데이터 테이블
        </h3>
      </div>

      {/* 검색창 */}
      <div className="mb-4">
        <input
          type="text"
          placeholder="검색..."
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            setCurrentPage(1);
          }}
          className="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 
          bg-white dark:bg-[#2A2D3A] text-gray-900 dark:text-white
          focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>

      {/* 테이블 */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b-2 border-gray-200 dark:border-gray-700">
              <th
                onClick={() => handleSort("id")}
                className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-200 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                ID {sortConfig.key === "id" && (sortConfig.direction === "asc" ? "↑" : "↓")}
              </th>
              <th
                onClick={() => handleSort("category")}
                className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-200 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                질문 {sortConfig.key === "category" && (sortConfig.direction === "asc" ? "↑" : "↓")}
              </th>
              <th
                onClick={() => handleSort("answer")}
                className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-200 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                답변 {sortConfig.key === "answer" && (sortConfig.direction === "asc" ? "↑" : "↓")}
              </th>
              <th
                onClick={() => handleSort("respondent_id")}
                className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-200 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                응답자 ID {sortConfig.key === "respondent_id" && (sortConfig.direction === "asc" ? "↑" : "↓")}
              </th>
              <th
                onClick={() => handleSort("question_id")}
                className="px-4 py-3 text-left text-sm font-semibold text-gray-700 dark:text-gray-200 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
              >
                질문 ID {sortConfig.key === "question_id" && (sortConfig.direction === "asc" ? "↑" : "↓")}
              </th>
            </tr>
          </thead>
          <tbody>
            {paginatedData.map((row, idx) => (
              <tr
                key={row.id}
                className={`border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors ${
                  idx % 2 === 0 ? "bg-gray-50/50 dark:bg-gray-900/30" : ""
                }`}
              >
                <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">{row.id}</td>
                <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">{row.category}</td>
                <td className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">{row.answer}</td>

                {/* ✅ 마스킹된 응답자 ID 표시 */}
                <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400 text-xs">
                  {row.respondent_id}
                </td>

                <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400 text-xs">{row.question_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 페이지네이션 */}
      <div className="flex items-center justify-between mt-6">
        <button
          onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
          disabled={currentPage === 1}
          className="px-4 py-2 rounded-lg bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200
          disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
        >
          이전
        </button>

        <span className="text-sm text-gray-600 dark:text-gray-300">
          {currentPage} / {totalPages}
        </span>

        <button
          onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
          disabled={currentPage === totalPages}
          className="px-4 py-2 rounded-lg bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200
          disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
        >
          다음
        </button>
      </div>
    </div>
  );
}

