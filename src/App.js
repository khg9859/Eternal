import React, { useState } from 'react';
import SearchBox from './components/SearchBox';
import SearchResults from './components/SearchResults';
import Header from './components/Header';
import FileUpload from './components/FileUpload';
import SearchTags from './components/SearchTags';
import Logo from './components/Logo';
import ChatInterface from './components/ChatInterface';
import DataVisualization from './components/DataVisualization';
import FilterPanel from './components/FilterPanel';
import SmartChart from './components/SmartChart';

function App() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [chatHistory, setChatHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showVisualization, setShowVisualization] = useState(false);
  const [showSmartChart, setShowSmartChart] = useState(true); // 기본적으로 차트 우선 표시
  const [activeFilters, setActiveFilters] = useState({});
  const [interfaceMode, setInterfaceMode] = useState('chat'); // 'chat' or 'simple'

  // 간단 검색 핸들러
  const handleSimpleSearch = async (query) => {
    if (!query.trim()) return;

    setIsLoading(true);
    setSearchQuery(query);
    setInterfaceMode('simple');
    setShowSmartChart(false); // 상세 결과 보기로 전환

    try {
      const response = await fetch('http://localhost:5000/api/simple-search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      const results = await response.json();
      setSearchResults(results);
    } catch (error) {
      console.error("Simple search failed:", error);
      setSearchResults([{ id: 'error', title: '검색 실패', description: '서버와 통신 중 오류가 발생했습니다.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTagClick = (tagText) => {
    handleChatSearch(tagText);
  };

  const handleFilterChange = (filters) => {
    setActiveFilters(filters);
    // 필터가 적용된 검색 재실행
    if (searchQuery) {
      // 필터 적용 로직은 백엔드에서 처리해야 합니다.
      // 현재는 간단하게 chatSearch를 다시 호출합니다.
      handleChatSearch(searchQuery, filters);
    }
  };

  const toggleVisualization = () => {
    setShowVisualization(!showVisualization);
  };

  const resetToHome = () => {
    setSearchQuery('');
    setSearchResults([]);
    setIsLoading(false);
    setShowVisualization(false);
    setShowSmartChart(false);
    setActiveFilters({});
    setInterfaceMode('chat');
    setChatHistory([]);
  };

  // 대화형 검색 핸들러
  const handleChatSearch = async (query) => {
    if (!query.trim()) return;

    setIsLoading(true);
    setSearchQuery(query);
    setInterfaceMode('chat');

    const newUserMessage = { id: `user-${Date.now()}`, role: 'user', content: query };
    const updatedHistory = [...chatHistory, newUserMessage];
    setChatHistory(updatedHistory);

    try {
      const response = await fetch('http://localhost:5000/api/chat-search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, history: updatedHistory.slice(0, -1) }), // 마지막 사용자 메시지는 query로 전달되므로 제외
      });
      const result = await response.json();
      setChatHistory(prev => [...prev, result]);
    } catch (error) {
      console.error("Chat search failed:", error);
      setChatHistory(prev => [...prev, { id: 'error', role: 'assistant', type: 'ai', content: '검색 중 오류가 발생했습니다.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <Header onLogoClick={resetToHome} />

      <main className="flex flex-col items-center justify-center min-h-[calc(100vh-80px)] px-4">
        {/* 로고 영역 */}
        <div className="mb-12 text-center">
          <div className="cursor-pointer" onClick={resetToHome}>
            <Logo size="large" />
          </div>
          <p className="text-gray-600 text-xl font-light">AI로 데이터를 자연어로 검색하세요</p>
        </div>

        {/* 인터페이스 모드 선택 */}
        {(
          <div className="mb-6 flex justify-center">
            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-1 border border-gray-200/50 shadow-lg">
              <button
                onClick={() => setInterfaceMode('chat')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${interfaceMode === 'simple'
                  ? 'bg-gradient-to-r from-google-blue to-google-purple text-white shadow-lg'
                  : 'text-gray-600 hover:text-gray-800'
                  }`}
              >
                🔍 간단 검색
              </button>
              <button
                onClick={() => setInterfaceMode('simple')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${interfaceMode === 'chat'
                  ? 'bg-gradient-to-r from-google-blue to-google-purple text-white shadow-lg'
                  : 'text-gray-600 hover:text-gray-800'
                  }`}
              >
                💬 대화형 검색
              </button>
            </div>
          </div>
        )}

        {/* 검색 인터페이스 */}
        {interfaceMode === 'simple' ? (
          <>
            <div className="w-full max-w-3xl mb-8">
              <SearchBox
                onSearch={handleSimpleSearch}
                isLoading={isLoading}
              />
            </div>

            {/* 검색 태그 */}
            {searchResults.length === 0 && !isLoading && (
              <SearchTags
                onTagClick={handleTagClick}
              />
            )}
          </>
        ) : (
          <div className="w-full max-w-4xl mb-8">
            <ChatInterface
              onSearch={handleChatSearch}
              isLoading={isLoading}
              chatHistory={chatHistory}
            />
          </div>
        )}

        {/* 필터 패널 */}
        {searchResults.length > 0 && (
          <FilterPanel
            onFilterChange={handleFilterChange}
          />
        )}

        {/* 검색 결과 - 스마트 차트 우선 표시 */}
        {searchQuery && (
          <div className="w-full max-w-5xl">
            {/* 표시 모드 선택 */}
            <div className="mb-6 flex justify-center">
              <div className="bg-white/80 backdrop-blur-sm rounded-xl p-1 border border-gray-200/50 shadow-lg">
                <button
                  onClick={() => setShowSmartChart(true)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${showSmartChart
                      ? 'bg-gradient-to-r from-google-blue to-google-purple text-white shadow-lg'
                      : 'text-gray-600 hover:text-gray-800'
                    }`}
                >
                  📊 스마트 차트
                </button>
                <button
                  onClick={() => setShowSmartChart(false)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${!showSmartChart
                      ? 'bg-gradient-to-r from-google-blue to-google-purple text-white shadow-lg'
                      : 'text-gray-600 hover:text-gray-800'
                    }`}
                >
                  📋 상세 결과
                </button>
              </div>
            </div>

            {/* 컨텐츠 표시 */}
            {showSmartChart ? (
              <SmartChart
                query={searchQuery}
                data={searchResults.map(r => r.data)} // Pass data from search results
                onDataAnalyzed={(result) => {
                  console.log('차트 분석 완료:', result);
                }}
              />
            ) : (
              <>
                {searchResults.length > 0 && (
                  <SearchResults
                    results={searchResults}
                    query={searchQuery}
                    isLoading={isLoading}
                  />
                )}
              </>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;