import React, { useState, useRef, useEffect } from "react";

/*
  AIChatInterface.js
  -------------------------------------------------------
  이 컴포넌트는 “AI 대화형 분석 UI” 를 제공하는 핵심 모듈입니다.
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

  // 🔥 대화 컨텍스트 상태 (후속 질문용)
  // 백엔드 /rag/chat 에서 내려주는 state를 그대로 들고 있다가 다음 요청에 같이 보냄
  const [sessionState, setSessionState] = useState(null);

  // 메시지 리스트 끝 위치 (자동 스크롤용)
  const messagesEndRef = useRef(null);

  // 메시지가 추가될 때 자동 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /*
    generateAIResponse()
    -------------------------------------------------------
    - 백엔드 오류 시 fallback 용 임시 응답
  */
  const generateAIResponse = async (userMessage) => {
    const message = userMessage.toLowerCase();

    if (message.includes("평균")) return "📊 데이터의 평균값을 계산해보겠습니다.";
    if (message.includes("최대")) return "🔎 최대값을 찾아보겠습니다.";
    if (message.includes("트렌드")) return "📈 시간에 따른 트렌드를 분석해볼게요.";
    if (message.includes("지역")) return "🗺️ 지역별 데이터를 그룹화 중입니다.";

    return `"${userMessage}"에 대한 분석 결과를 준비 중입니다. (백엔드 연결 오류로 임시 응답을 보여드려요.)`;
  };

  /*
    handleSendMessage()
    -------------------------------------------------------
    - 텍스트 필드의 내용을 메시지로 추가
    - 백엔드 /rag/chat 호출 (대화형 + 후속 질문 지원)
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
      // ✅ Eternal_SV 백엔드의 대화형 챗봇 엔드포인트 호출
      const response = await fetch("http://localhost:8000/rag/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: query,        // 🔥 ChatRequest.message
          state: sessionState,   // 🔥 이전 턴에서 받은 state (없으면 null)
        }),
      });

      if (!response.ok) {
        throw new Error(`RAG 챗봇 호출 실패: ${response.status}`);
      }

      const data = await response.json();

      // 🔥 백엔드에서 내려준 state를 저장 → 다음 질문 시 그대로 보내기
      if (data.state) {
        setSessionState(data.state);
      }

      // 🔥 대화형으로 재가공된 답변 출력 (chat_with_state → make_chatty_answer 결과)
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          type: "ai",
          content: data.answer || "답변을 생성할 수 없습니다.",
          timestamp: new Date(),
        },
      ]);
    } catch (error) {
      console.error("AI 응답 생성 오류:", error);

      // 🔁 Fallback: 임시 로컬 응답
      const aiResponse = await generateAIResponse(query);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          type: "ai",
          content: aiResponse,
          timestamp: new Date(),
        },
      ]);
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
    "서울 사는 30대 남성은 보통 어떤 직무야?",
    "서울 사는 40대 여성은 OTT 몇 개 정도 쓰고 있어?",
    "경기 거주 20대 여름철 최애 간식은?",
    "20대는 주로 어떤 AI 챗봇을 사용해?",
  ];

  return (
    <div
      className="fixed bottom-8 right-8 w-[500px] h-[820px] flex flex-col rounded-2xl overflow-hidden shadow-[0_0_30px_rgba(255,215,0,0.25)] border border-yellow-500/30 z-[9999]"
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
          <input
            type="range"
            min="0.3"
            max="1"
            step="0.05"
            value={opacity}
            onChange={(e) => setOpacity(parseFloat(e.target.value))}
            className="w-24 accent-black cursor-pointer"
          />
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
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex ${
              m.type === "user" ? "justify-end" : "justify-start"
            }`}
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

        <div ref={messagesEndRef} />
      </div>

      {/* ---------------------- 추천 질문 영역 ---------------------- */}
      {messages.length <= 2 && (
        <div className="px-4 py-3 border-t border-yellow-500/30 bg-black/30 backdrop-blur-md">
          <p className="text-xs text-yellow-300 mb-2">
            이런 질문을 해보세요:
          </p>
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
          <textarea
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="데이터에 대해 궁금한 점을 물어보세요..."
            className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-yellow-400 text-sm text-gray-100 placeholder-gray-500 resize-none transition-all"
            rows="1"
          />
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
