/*import React, { useState } from 'react';
import SearchBox from './components/SearchBox';
import SearchResults from './components/SearchResults';
import Header from './components/Header';
import FileUpload from './components/FileUpload';
import SearchTags from './components/SearchTags';
import Logo from './components/Logo';
import ChatInterface from './components/ChatInterface';
import DataVisualization from './components/DataVisualization';
import FilterPanel from './components/FilterPanel';

function App() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [uploadedData, setUploadedData] = useState(null);
  const [showVisualization, setShowVisualization] = useState(false);
  const [activeFilters, setActiveFilters] = useState({});
  const [interfaceMode, setInterfaceMode] = useState('simple'); // 'simple' or 'chat'

  const handleSearch = async (query) => {
    if (!query.trim()) return;

    setIsLoading(true);
    setSearchQuery(query);

    // 실제 검색 API 호출 로직을 여기에 구현
    // 현재는 더미 데이터로 시뮬레이션
    setTimeout(() => {
      const generateSmartResults = (query) => {
        const keywords = query.toLowerCase();
        const results = [];

        if (keywords.includes('매출') || keywords.includes('판매')) {
          results.push({
            id: 1,
            title: '매출 데이터 분석 결과',
            description: `${query}에 대한 매출 분석을 완료했습니다. 전년 대비 성장률과 주요 트렌드를 확인할 수 있습니다.`,
            data: {
              name: '월별 매출 현황',
              value: 2450000,
              category: '매출',
              trend: '상승',
              period: '2024년 1-10월'
            }
          });
        }

        if (keywords.includes('고객') || keywords.includes('사용자')) {
          results.push({
            id: 2,
            title: '고객 데이터 분석',
            description: `${query}와 관련된 고객 행동 패턴과 선호도 분석 결과입니다.`,
            data: {
              name: '고객 만족도 지수',
              value: 87,
              category: '고객',
              trend: '안정',
              period: '최근 3개월'
            }
          });
        }

        if (keywords.includes('지역') || keywords.includes('위치')) {
          results.push({
            id: 3,
            title: '지역별 성과 분석',
            description: `${query}에 해당하는 지역별 데이터 분포와 성과 지표입니다.`,
            data: {
              name: '서울 지역 성과',
              value: 156,
              category: '지역',
              trend: '상승',
              period: '2024년 Q3'
            }
          });
        }

        // 기본 결과가 없으면 일반적인 결과 제공
        if (results.length === 0) {
          results.push(
            {
              id: 1,
              title: `"${query}" 검색 결과`,
              description: `입력하신 "${query}"와 관련된 데이터를 찾았습니다. 상세한 분석 내용을 확인해보세요.`,
              data: {
                name: '데이터 항목',
                value: Math.floor(Math.random() * 1000) + 100,
                category: '일반',
                trend: Math.random() > 0.5 ? '상승' : '하락',
                period: '최근 데이터'
              }
            },
            {
              id: 2,
              title: '관련 데이터 분석',
              description: `"${query}" 키워드와 연관된 추가 데이터 패턴을 발견했습니다.`,
              data: {
                name: '연관 데이터',
                value: Math.floor(Math.random() * 500) + 50,
                category: '연관',
                trend: '안정',
                period: '지난 주'
              }
            }
          );
        }

        return results;
      };

      const dummyResults = generateSmartResults(query);
      setSearchResults(dummyResults);
      setIsLoading(false);
    }, 1000);
  };

  const handleFileUpload = (data) => {
    setUploadedData(data);
  };

  const handleTagClick = (tagText) => {
    handleSearch(tagText);
  };

  const handleFilterChange = (filters) => {
    setActiveFilters(filters);
    // 필터가 적용된 검색 재실행
    if (searchQuery) {
      handleSearch(searchQuery, filters);
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
    setActiveFilters({});
    setInterfaceMode('simple');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <Header onLogoClick={resetToHome} />

      <main className="flex flex-col items-center justify-center min-h-[calc(100vh-80px)] px-4">
        {// 로고 영역 }
        <div className="mb-12 text-center">
          <div className="cursor-pointer" onClick={resetToHome}>
            <Logo size="large" />
          </div>
          <p className="text-gray-600 text-xl font-light">AI로 데이터를 자연어로 검색하세요</p>
        </div>

        {// 파일 업로드 영역 }
        {!uploadedData && (
          <div className="mb-12 w-full max-w-3xl">
            <FileUpload onFileUpload={handleFileUpload} />
          </div>
        )}

        {// 인터페이스 모드 선택 }
        {uploadedData && (
          <div className="mb-6 flex justify-center">
            <div className="bg-white/80 backdrop-blur-sm rounded-xl p-1 border border-gray-200/50 shadow-lg">
              <button
                onClick={() => setInterfaceMode('simple')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${interfaceMode === 'simple'
                    ? 'bg-gradient-to-r from-google-blue to-google-purple text-white shadow-lg'
                    : 'text-gray-600 hover:text-gray-800'
                  }`}
              >
                🔍 간단 검색
              </button>
              <button
                onClick={() => setInterfaceMode('chat')}
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

        {// 검색 인터페이스 }
        {interfaceMode === 'simple' ? (
          <>
            <div className="w-full max-w-3xl mb-8">
              <SearchBox
                onSearch={handleSearch}
                isLoading={isLoading}
                disabled={!uploadedData}
              />
            </div>

            {// 검색 태그 }
            {uploadedData && searchResults.length === 0 && !isLoading && (
              <SearchTags
                onTagClick={handleTagClick}
                disabled={!uploadedData}
              />
            )}
          </>
        ) : (
          <div className="w-full max-w-4xl mb-8">
            <ChatInterface
              onSearch={handleSearch}
              isLoading={isLoading}
              uploadedData={uploadedData}
            />
          </div>
        )}

        {// 필터 패널 }
        {uploadedData && searchResults.length > 0 && (
          <FilterPanel
            onFilterChange={handleFilterChange}
            uploadedData={uploadedData}
          />
        )}

        {// 시각화 토글 버튼 }
        {searchResults.length > 0 && (
          <div className="mb-6 flex justify-center">
            <button
              onClick={toggleVisualization}
              className="flex items-center px-6 py-3 bg-gradient-to-r from-google-green to-google-blue text-white rounded-xl hover:from-google-green/90 hover:to-google-blue/90 transition-all duration-200 shadow-lg hover:shadow-xl"
            >
              {showVisualization ? '📋 테이블 보기' : '📊 시각화 보기'}
            </button>
          </div>
        )}

        {// 검색 결과 또는 시각화 }
        {searchResults.length > 0 && (
          <div className="w-full max-w-5xl">
            {showVisualization ? (
              <DataVisualization data={searchResults} query={searchQuery} />
            ) : (
              <SearchResults
                results={searchResults}
                query={searchQuery}
                isLoading={isLoading}
              />
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
*/