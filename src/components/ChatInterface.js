import React, { useState, useRef, useEffect } from 'react';

const ChatInterface = ({ onSearch, isLoading, chatHistory }) => {
  const [currentQuery, setCurrentQuery] = useState('');
  const [searchHistory, setSearchHistory] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!currentQuery.trim()) return;

    onSearch(currentQuery);
    setSearchHistory(prev => [currentQuery, ...prev.slice(0, 4)]); // 최근 5개만 저장
    setCurrentQuery('');
    setShowSuggestions(false);
  };

  const handleSuggestionClick = (suggestion) => {
    setCurrentQuery(suggestion);
    setShowSuggestions(false);
  };

  const handleQuickReply = (reply) => {
    setCurrentQuery(reply);
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* 채팅 메시지 영역 */}
      {chatHistory.length > 0 && (
        <div className="mb-6 bg-white/80 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200/50 max-h-96 overflow-y-auto">
          <div className="p-6 space-y-4">
            {chatHistory.map((message) => (
              <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-xs lg:max-w-md px-4 py-3 rounded-2xl ${
                  message.role === 'user' 
                    ? 'bg-gradient-to-r from-google-blue to-google-purple text-white' 
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  <p className="text-sm">{message.content}</p>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-gray-100 rounded-2xl px-4 py-3">
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-google-blue border-t-transparent"></div>
                    <span className="text-sm text-gray-600">검색 중...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>
      )}

      {/* 검색 입력창 */}
      <div className="relative">
        <form onSubmit={handleSubmit}>
          <div className={`flex items-center bg-white/90 backdrop-blur-sm border border-gray-200/50 rounded-2xl shadow-2xl transition-all duration-300 hover:border-google-blue/30`}>
            <div className="pl-6 pr-4">
              <svg className={`w-6 h-6 transition-colors duration-200 text-google-blue`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>

            <input
              type="text"
              value={currentQuery}
              onChange={(e) => {
                setCurrentQuery(e.target.value);
                setShowSuggestions(e.target.value.length > 0);
              }}
              placeholder={"데이터에 대해 자연어로 질문하세요..."}
              className="flex-1 py-4 px-2 text-gray-800 bg-transparent border-none outline-none text-lg placeholder-gray-400 font-light"
            />

            <div className="pr-6">
              <button
                type="submit"
                disabled={!currentQuery.trim()}
                className="p-2.5 rounded-xl bg-gradient-to-r from-google-blue to-google-purple hover:from-google-blue/90 hover:to-google-purple/90 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-xl"
              >
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
          </div>
        </form>

        {/* 자동완성 및 검색 히스토리 */}
        {showSuggestions && (
          <div className="absolute top-full left-0 right-0 mt-2 bg-white/95 backdrop-blur-md border border-gray-200/50 rounded-xl shadow-2xl z-10 overflow-hidden">
            {searchHistory.length > 0 && (
              <div className="p-4 border-b border-gray-100">
                <p className="text-xs text-gray-500 mb-2 flex items-center">
                  <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  최근 검색
                </p>
                {searchHistory.map((item, index) => (
                  <button
                    key={index}
                    onClick={() => handleSuggestionClick(item)}
                    className="block w-full text-left px-2 py-1 text-sm text-gray-600 hover:bg-gray-50 rounded transition-colors"
                  >
                    {item}
                  </button>
                ))}
              </div>
            )}
            
            <div className="p-4">
              <p className="text-xs text-gray-500 mb-2">추천 질문</p>
              {['매출이 가장 높은 월은?', '지역별 판매 현황은?', '트렌드 분석 보여줘'].map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="block w-full text-left px-2 py-1 text-sm text-gray-600 hover:bg-gray-50 rounded transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 빠른 응답 버튼 */}
      {chatHistory.length > 0 && !isLoading && (
        <div className="mt-4 flex flex-wrap gap-2 justify-center">
          {['더 자세히', '다른 관점으로', '시각화로 보기', '필터 적용'].map((reply, index) => (
            <button
              key={index}
              onClick={() => handleQuickReply(reply)}
              className="px-4 py-2 bg-white/80 backdrop-blur-sm border border-gray-200/50 rounded-full text-sm text-gray-600 hover:bg-gradient-to-r hover:from-google-blue/10 hover:to-google-purple/10 hover:text-google-blue transition-all duration-200"
            >
              {reply}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default ChatInterface;