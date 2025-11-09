import React, { useState, useRef, useEffect } from 'react';

const ChatInterface = ({ onSearch, isLoading }) => {
  const [currentQuery, setCurrentQuery] = useState('');
  const [searchHistory, setSearchHistory] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!currentQuery.trim() || isLoading) return;

    setSearchHistory(prev => [currentQuery, ...prev.slice(0, 4)]); // 최근 5개만 저장
    
    const query = currentQuery;
    setCurrentQuery('');
    setShowSuggestions(false);

    onSearch(query);
  };

  const handleSuggestionClick = (suggestion) => {
    setCurrentQuery(suggestion);
    setShowSuggestions(false);
  };

  return (
    <div className="w-full max-w-4xl mx-auto">

      {/* 검색 입력창 - 카카오톡 스타일 */}
      <div className="relative">
        <form onSubmit={handleSubmit}>
          <div className="flex items-center bg-white rounded-lg shadow-sm">
            <input
              type="text"
              value={currentQuery}
              onChange={(e) => {
                setCurrentQuery(e.target.value);
                setShowSuggestions(e.target.value.length > 0);
              }}
              placeholder="메시지를 입력하세요..."
              disabled={isLoading}
              className="flex-1 py-3 px-4 text-[#3C1E1E] bg-transparent border-none outline-none placeholder-gray-400"
            />

            <div className="pr-2">
              <button
                type="submit"
                disabled={!currentQuery.trim() || isLoading}
                className="p-2 rounded-full bg-[#FFE812] hover:bg-[#FFD700] transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <svg className="w-5 h-5 text-[#3C1E1E]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
          </div>
        </form>

        {/* 자동완성 및 검색 히스토리 - 카카오톡 스타일 */}
        {showSuggestions && (
          <div className="absolute bottom-full left-0 right-0 mb-2 bg-white rounded-lg shadow-lg z-10 overflow-hidden border border-gray-200">
            {searchHistory.length > 0 && (
              <div className="p-3 border-b border-gray-200">
                <p className="text-xs text-gray-500 mb-2 flex items-center font-medium">
                  <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  최근 검색
                </p>
                {searchHistory.map((item, index) => (
                  <button
                    key={index}
                    onClick={() => handleSuggestionClick(item)}
                    className="block w-full text-left px-2 py-1.5 text-sm text-[#3C1E1E] hover:bg-gray-100 rounded transition-colors"
                  >
                    {item}
                  </button>
                ))}
              </div>
            )}
            
            <div className="p-3">
              <p className="text-xs text-gray-500 mb-2 font-medium">추천 질문</p>
              {['매출이 가장 높은 월은?', '지역별 판매 현황은?', '트렌드 분석 보여줘'].map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="block w-full text-left px-2 py-1.5 text-sm text-[#3C1E1E] hover:bg-gray-100 rounded transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

    </div>
  );
};

export default ChatInterface;