import React, { useState, useRef, useEffect } from "react";

/*
  AIChatInterface.js
  -------------------------------------------------------
  이 컴포넌트는 “AI 대화형 분석 UI” 를 제공하는 핵심 모듈입니다.

  주요 기능:
  - 사용자 입력 메시지 처리
  - AI 응답 생성 (현재는 프론트 임시 로직 / 향후 LLM API로 교체 예정)
  - 메시지 UI 렌더링
  - 자동 스크롤
  - 챗봇 전체 투명도 조절 기능
  - 부모 컴포넌트로부터 onExit() 전달받아 챗봇 창 닫기

  RAG 백엔드 연동 시 고려사항:
  -------------------------------------------------------
  1) generateAIResponse() 함수는 현재 더미 응답이지만,
     실제로는 FastAPI/Express 서버에 fetch POST 호출로 변경된다.

     예)
       const res = await fetch("/api/chat", {
         method: "POST",
         headers: { "Content-Type": "application/json" },
         body: JSON.stringify({ query: userMessage })
       });
       const data = await res.json();
       return data.answer;

  2) API 출력(JSON 구조)은 다음과 같은 형태가 가장 이상적:
       {
         "answer": "AI의 요약이나 분석 결과",
         "relevant_docs": [...],   ← RAG 기반 참고 문서
         "metadata": {...}         ← 패널 분석 관련 수치
       }

  3) 메시지 배열(messages)은 실제 LLM 챗봇 구현에서도 동일하게 유지 가능.
     (GPT/Claude 메시지 포맷처럼 “role: user/assistant, content: 메시지” 구조와 동일)

  4) 투명도(opacity)는 UI 전용 상태이며 데이터 흐름과는 무관함.
*/

const AIChatInterface = ({ onExit }) => {
  // 대화창 초기 메시지 (AI 환영 메시지 1개)
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: "ai",
      content:
        "안녕하세요! 데이터에 대해 궁금한 것이 있으시면 언제든 물어보세요. 자연어로 질문하시면 분석해드릴게요.",
      timestamp: new Date(),
    },
  ]);

  // 사용자 입력 메시지
  const [inputMessage, setInputMessage] = useState("");

  // AI 응답 대기 상태
  const [isLoading, setIsLoading] = useState(false);

  // 챗봇 전체 투명도 (UI 기능)
  const [opacity, setOpacity] = useState(1.0);

  // 메시지 리스트 끝 위치 (자동 스크롤용)
  const messagesEndRef = useRef(null);

  // 메시지가 추가될 때 자동 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);


  /*
    generateAIResponse()
    -------------------------------------------------------
    - 현재는 프런트엔드에서 임시로 AI처럼 대답해주는 로직
    - 향후엔 반드시 백엔드의 LLM API로 교체됨

    RAG 연결 후 구조 (기본 형태):
      const response = await fetch("/api/chat", { ... });
      const result = await response.json();
      return result.answer;
  */
  const generateAIResponse = async (userMessage) => {
    const message = userMessage.toLowerCase();

    if (message.includes("평균")) return "📊 데이터의 평균값을 계산해보겠습니다.";
    if (message.includes("최대")) return "🔎 최대값을 찾아보겠습니다.";
    if (message.includes("트렌드")) return "📈 시간에 따른 트렌드를 분석해볼게요.";
    if (message.includes("지역")) return "🗺️ 지역별 데이터를 그룹화 중입니다.";

    return `"${userMessage}"에 대한 분석 결과를 준비 중입니다.`;
  };


  /*
    handleSendMessage()
    -------------------------------------------------------
    - 텍스트 필드의 내용을 메시지로 추가
    - generateAIResponse() 실행
    - 이후 AI 메시지를 messages 배열에 추가
    - isLoading으로 로딩 상태 관리

    RAG 연동 시 변경되는 부분:
    - generateAIResponse(userMessage.content)
        → 백엔드 API로 변경
    - 응답은 RAG 파이프라인 결과(answer)로 바로 표시됨.
  */
const handleSendMessage = async () => {
  if (!inputMessage.trim() || isLoading) return;

  const userMessage = {
    id: Date.now(),
    type: "user",
    content: inputMessage.trim(),
    timestamp: new Date(),
  };

  setMessages((prev) => [...prev, userMessage]);
  const query = inputMessage.trim();
  setInputMessage("");
  setIsLoading(true);

  try {
    // ✅ Eternal_SV 백엔드 호출
    const response = await fetch('http://localhost:8000/rag/chatbot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query,
        session_id: 'eternal_fe_session'
      })
    });

    if (!response.ok) throw new Error(`RAG 검색 실패: ${response.status}`);
    const data = await response.json();

    setMessages((prev) => [
      ...prev,
      {
        id: Date.now() + 1,
        type: "ai",
        content: data.answer || '답변을 생성할 수 없습니다.',
        timestamp: new Date(),
      },
    ]);
    
  } catch (error) {
    console.error('AI 응답 생성 오류:', error);
    // Fallback
    const aiResponse = await generateAIResponse(query);
    setMessages((prev) => [...prev, {
      id: Date.now() + 1,
      type: "ai",
      content: aiResponse,
      timestamp: new Date(),
    }]);
  } finally {
    setIsLoading(false);
  }
};

  // Enter키 전송 기능
  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // 시간 표시 포맷
  const formatTime = (t) =>
    t.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" });


  // 추천 질문 목록
  const suggestedQuestions = [
    "데이터의 평균값은 얼마인가요?",
    "가장 높은 값을 가진 항목은?",
    "지역별로 어떤 차이가 있나요?",
    "연령대별 분포는 어떻게 되나요?",
  ];


  return (
    <div
      className="fixed bottom-8 right-8 w-[500px] h-[820px] flex flex-col rounded-2xl overflow-hidden shadow-[0_0_30px_rgba(255,215,0,0.25)] border border-yellow-500/30 z-[9999]"

      /*
        챗봇 전체 UI 투명도 적용 영역
        - 전체 UI 포함(텍스트·버튼 등 모두)
        - opacity는 프로젝트 UI 개성 요소이고 데이터 처리와는 독립적
        - z-[9999]로 최상위 레이어 설정
      */
      style={{
        opacity: opacity,
        transition: "opacity 0.25s ease",
      }}
    >

      {/* ---------------------- 헤더 ---------------------- */}
      <div className="flex items-center justify-between px-5 py-3 bg-gradient-to-r from-amber-400 via-yellow-500 to-orange-400 text-black font-semibold shadow-md">
        <h2 className="text-lg tracking-wide">AI 데이터 사이언스 챗봇</h2>

        {/* 투명도 조절 슬라이더 + 나가기 버튼 */}
        <div className="flex items-center gap-3">

          {/* 슬라이더 */}
          <input
            type="range"
            min="0.3"
            max="1"
            step="0.05"
            value={opacity}
            onChange={(e) => setOpacity(parseFloat(e.target.value))}
            className="w-24 accent-black cursor-pointer"
          />

          {/* 챗봇 닫기 */}
          <button
            onClick={onExit}
            className="text-lg font-medium bg-black/20 px-3 py-1.5 rounded-lg hover:bg-black/40 transition-all duration-200"
          >
            나가기 ✕
          </button>
        </div>
      </div>

      {/* ---------------------- 메시지 리스트 ---------------------- */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gradient-to-b from-black/20 to-black/40 backdrop-blur-md">

        {/* 기존 메시지 렌더링 */}
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex ${m.type === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`px-4 py-2 rounded-2xl text-lg shadow-md ${
                m.type === "user"
                  ? "bg-gradient-to-r from-yellow-400 to-amber-500 text-black font-medium"
                  : "bg-gray-800/80 text-gray-100"
              }`}
            >
              {m.content}
              <p className="text-[12px] text-gray-400 mt-1">
                {formatTime(m.timestamp)}
              </p>
            </div>
          </div>
        ))}

        {/* 로딩 애니메이션 */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-800/70 px-4 py-2 rounded-2xl text-gray-200 animate-pulse">
              <span className="text-xs text-yellow-400">분석 중...</span>
            </div>
          </div>
        )}

        {/* 자동 스크롤 위치 */}
        <div ref={messagesEndRef} />
      </div>

      {/* ---------------------- 추천 질문 영역 ---------------------- */}
      {messages.length <= 2 && (
        <div className="px-4 py-3 border-t border-yellow-500/30 bg-black/30 backdrop-blur-md">
          <p className="text-xs text-yellow-300 mb-2">이런 질문을 해보세요:</p>

          <div className="grid grid-cols-1 gap-2">
            {suggestedQuestions.map((q, i) => (
              <button
                key={i}
                onClick={() => setInputMessage(q)}
                className="text-sm px-3 py-2 bg-gray-700/60 rounded-lg text-gray-200 hover:bg-yellow-500/40 hover:text-black transition-all duration-300"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ---------------------- 하단 입력창 ---------------------- */}
      <div className="p-4 border-t border-yellow-500/30 bg-black/30 backdrop-blur-md">
        <div className="flex items-end space-x-2">

          {/* 텍스트 입력 */}
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="데이터에 대해 궁금한 점을 물어보세요..."
            className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-yellow-400 text-sm text-gray-100 placeholder-gray-500 resize-none transition-all"
            rows="1"
          />

          {/* 전송 버튼 */}
          <button
            onClick={handleSendMessage}
            disabled={!inputMessage.trim() || isLoading}
            className="px-4 py-2 bg-gradient-to-r from-yellow-400 to-amber-500 text-black rounded-lg hover:scale-105 active:scale-95 transition-all duration-200 font-semibold text-sm"
          >
            전송
          </button>
        </div>
      </div>
    </div>
  );
};

export default AIChatInterface;