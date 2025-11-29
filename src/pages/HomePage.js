import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import Logo from "../components/Logo";
import AIChatInterface from "../components/AIChatInterface";

/*
  HomePage.js
  -----------------------------
  - 메인 화면 구성
  - 사용자에게 자연어 질의(query)를 입력받는 페이지
  - 입력된 query를 ResultsPage로 전달
  - Home 화면에서 바로 AI 챗봇도 열 수 있도록 구성
  - 향후 RAG 백엔드 연동 시 반드시 거쳐가는 “입력 데이터 출발점”

  RAG 백엔드 연동 고려사항
  -----------------------------
  1) 사용자가 입력한 query는 ResultsPage → ChartSection → 백엔드로 전달됨
     => 여기서는 query 상태만 정확히 유지하면 됨.

  2) AIChatInterface의 onNewSearch(newQuery) 기능은
     LLM 질문을 결과 페이지로 넘기는 Infra 역할을 수행할 수 있음.

  3) 홈 화면 자체는 데이터 요청을 하지 않고
     단순히 query 입력 + navigation 역할만 수행한다.
*/

export default function HomePage() {
  // 사용자가 입력하는 자연어 질의 상태
  const [query, setQuery] = useState("");

  // AI 챗봇 UI 오픈 여부
  const [isChatOpen, setIsChatOpen] = useState(false);

  // 페이지 이동을 위한 React Router 훅
  const navigate = useNavigate();

  /*
    검색 실행 핸들러
    -----------------------------
    - 검색창에서 Enter 또는 버튼 클릭 시 실행
    - query가 비어있지 않을 때 결과 페이지로 이동
    - navigate("/results", { state: { query } })
      → ResultsPage에서 location.state.query 로 받는다.

    RAG 연동 포인트:
    - 이 query는 나중에 FastAPI 또는 Express 서버로 전달되어
      임베딩 검색 → 문서 매칭 → 요약/시각화 데이터로 변환됨.
  */
  const handleSearch = (e) => {
    e.preventDefault();
    if (query.trim()) navigate("/results", { state: { query } });
  };

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden text-white">

      {/* 배경 비디오 (홈 화면 비주얼 요소) */}
      <video
        autoPlay
        muted
        loop
        playsInline
        className="absolute inset-0 w-full h-full object-cover opacity-70"
      >
        <source src="/bg.mp4" type="video/mp4" />
      </video>

      {/* 비디오 위 오버레이 (텍스트 가독성 개선) */}
      <div className="absolute inset-0 bg-gradient-to-b from-black/70 via-black/50 to-black/80 backdrop-blur-[2px]" />

      {/* 로고 + 타이틀 영역 */}
      <motion.div
        initial={{ opacity: 0, y: -30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1 }}
        className="relative z-10 flex flex-col items-center mb-12"
      >
        <Logo size="large" />

        {/* 메인 페이지 타이틀 */}
        <h1 className="text-5xl md:text-6xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 via-amber-300 to-yellow-500 drop-shadow-[0_0_25px_rgba(255,215,0,0.4)]">
          Search with AI Insight
        </h1>

        {/* 서브 텍스트 */}
        <p className="text-gray-200 mt-4 text-lg text-center max-w-2xl">
          데이터를 탐색하고 인사이트를 발견하는 여정,{" "}
          <span className="text-yellow-300 font-semibold">ETERNAL</span>과 함께하세요.
        </p>
      </motion.div>

      {/* 검색창 */}
      <motion.form
        onSubmit={handleSearch}
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1, delay: 0.3 }}
        className="relative z-10 w-full max-w-2xl"
      >
        <div className="flex items-center bg-white/10 backdrop-blur-xl border border-yellow-400/40 rounded-2xl px-5 py-4 shadow-[0_0_30px_rgba(255,215,0,0.25)]">

          {/* 검색 아이콘 */}
          <span className="text-yellow-300 text-xl mr-3">🔍</span>

          {/* 입력 필드 */}
          {/*
            이 input에서 입력한 query가
            RAG 백엔드로 전달될 핵심 텍스트임.
          */}
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question..."
            className="w-full bg-transparent outline-none text-gray-100 placeholder-gray-400 text-lg"
          />

          {/* 제출 버튼 */}
          <button
            type="submit"
            className="ml-3 p-3 rounded-xl bg-gradient-to-r from-amber-400 to-yellow-500 hover:scale-105 transition-transform shadow-lg"
          >
            <svg
              className="w-6 h-6 text-black"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 12h14M12 5l7 7-7 7"
              />
            </svg>
          </button>
        </div>
      </motion.form>

      {/* AI 챗봇 열기 버튼 */}
      <motion.button
        onClick={() => setIsChatOpen(true)}
        initial={{ opacity: 0, y: 60 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8 }}
        className="fixed bottom-6 right-6 bg-gradient-to-r from-yellow-400 to-amber-500 p-5 rounded-full shadow-lg hover:shadow-yellow-400/50 hover:scale-110 transition-transform"
      >
        💬
      </motion.button>

      {/* AI 챗봇 UI */}
      {/*
        AIChatInterface 컴포넌트는
        1) 자연어 대화
        2) query 기반 재검색
        3) 추후 백엔드 LLM과 연결되는 핵심 대화 UI
    
        RAG 연동 시:
        - AIChatInterface에서 입력된 메시지를 그대로 백엔드로 POST
        - 응답을 받아서 UI에 표시하는 구조가 될 예정
      */}
      {isChatOpen && (
        <AIChatInterface
          uploadedData={[]} // 향후 CSV/JSON 업로드 데이터 처리 가능
          searchQuery={query}
          onNewSearch={(newQuery) =>
            navigate("/results", { state: { query: newQuery } })
          }
          onExit={() => setIsChatOpen(false)}
        />
      )}
    </div>
  );
}