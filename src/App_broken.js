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
import HeroSection from './components/HeroSection';
import DeviceMockup from './components/DeviceMockup';

function App() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [uploadedData, setUploadedData] = useState(null);
  const [showVisualization, setShowVisualization] = useState(false);
  const [showSmartChart, setShowSmartChart] = useState(true); // 기본적으로 차트 우선 표시
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
    setShowSmartChart(true);
    setActiveFilters({});
    setInterfaceMode('simple');
  };

  const searchInUploadedData = (query, data) => {
    const keywords = query.toLowerCase().split(' ');
    const matchedItems = [];

    // 최대 10개 결과만 반환 (성능 최적화)
    const maxResults = 10;
    let count = 0;

    for (const item of data) {
      if (count >= maxResults) break;

      // 객체의 모든 값을 문자열로 변환하여 검색
      const itemString = JSON.stringify(item).toLowerCase();

      // 키워드 중 하나라도 매치되면 결과에 포함
      const hasMatch = keywords.some(keyword =>
        itemString.includes(keyword) ||
        Object.values(item).some(value =>
          String(value).toLowerCase().includes(keyword)
        )
      );

      if (hasMatch) {
        // 매치된 필드 찾기
        const matchedFields = Object.entries(item).filter(([key, value]) =>
          keywords.some(keyword =>
            key.toLowerCase().includes(keyword) ||
            String(value).toLowerCase().includes(keyword)
          )
        );

        matchedItems.push({
          id: count + 1,
          title: `데이터 항목 #${count + 1}`,
          description: `"${query}"와 관련된 데이터를 찾았습니다. ${matchedFields.length}개 필드에서 매치되었습니다.`,
          data: {
            name: matchedFields[0] ? `${matchedFields[0][0]}: ${matchedFields[0][1]}` : '데이터 항목',
            value: extractNumericValue(item),
            category: detectCategory(item, keywords),
            trend: Math.random() > 0.5 ? '상승' : '안정',
            period: '업로드된 데이터',
            matchedFields: matchedFields.slice(0, 3), // 최대 3개 필드만 표시
            originalData: item
          }
        });
        count++;
      }
    }

    if (matchedItems.length === 0) {
      return [{
        id: 1,
        title: '검색 결과 없음',
        description: `"${query}"와 일치하는 데이터를 찾을 수 없습니다. 다른 키워드로 시도해보세요.`,
        data: {
          name: '검색 결과 없음',
          value: 0,
          category: '검색',
          trend: '없음',
          period: '현재'
        }
      }];
    }

    return matchedItems;
  };

  const extractNumericValue = (item) => {
    // 객체에서 숫자 값 추출
    for (const value of Object.values(item)) {
      if (typeof value === 'number') return value;
      if (typeof value === 'string') {
        const num = parseFloat(value.replace(/[^\d.-]/g, ''));
        if (!isNaN(num)) return num;
      }
    }
    return Math.floor(Math.random() * 1000);
  };

  const detectCategory = (item, keywords) => {
    const itemString = JSON.stringify(item).toLowerCase();

    if (keywords.some(k => ['매출', '판매', '수익', 'sales', 'revenue'].includes(k)) ||
      itemString.includes('매출') || itemString.includes('sales')) return '매출';
    if (keywords.some(k => ['고객', '사용자', 'customer', 'user'].includes(k)) ||
      itemString.includes('고객') || itemString.includes('customer')) return '고객';
    if (keywords.some(k => ['지역', '위치', 'region', 'location'].includes(k)) ||
      itemString.includes('지역') || itemString.includes('region')) return '지역';

    return '일반';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Header onLogoClick={resetToHome} />

      {/* 메인 컨텐츠 - 항상 히어로 섹션 유지 */}
      <div className="relative min-h-screen flex items-center justify-center overflow-hidden">
        {/* 배경 그라데이션 */}
        <div className="absolute inset-0 bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900"></div>
        
        {/* 배경 패턴 */}
        <div className="absolute inset-0 opacity-10">
          <div className="absolute inset-0" style={{
            backgroundImage: `radial-gradient(circle at 25% 25%, #8b5cf6 0%, transparent 50%),
                             radial-gradient(circle at 75% 75%, #3b82f6 0%, transparent 50%)`
          }}></div>
        </div>
        
        {/* 메인 컨텐츠 */}
        <div className="relative z-10 max-w-7xl mx-auto px-4 py-20">
          <div className="text-center mb-16">
            {/* 메인 타이틀 */}
            <h1 className="text-6xl md:text-7xl font-bold text-white mb-6">
              <span className="bg-gradient-to-r from-purple-400 via-pink-400 to-blue-400 bg-clip-text text-transparent">
                DataSearch
              </span>
            </h1>
            
            {/* 서브 타이틀 */}
            <p className="text-xl md:text-2xl text-gray-300 mb-4 font-light">
              AI로 데이터를 자연어로 검색하세요
            </p>
            
            {/* 설명 */}
            <p className="text-gray-400 text-lg max-w-2xl mx-auto">
              {!uploadedData ? (
                <>
                  CSV, Excel, JSON 파일을 업로드하고 자연어로 질문하면 
                  <br className="hidden md:block" />
                  AI가 자동으로 차트와 인사이트를 생성해드립니다
                </>
              ) : (
                <>
                  {uploadedData.length.toLocaleString()}개의 데이터가 로드되었습니다
                  <br className="hidden md:block" />
                  이제 자연어로 질문해보세요!
                </>
              )}
            </p>
          </div>

          {/* 디바이스 목업 - 항상 표시 */}
          <div className="flex justify-center">
            <div className="w-full max-w-4xl">
              <DeviceMockup type="laptop">
                <div className="w-full max-w-2xl">
                  {!uploadedData ? (
                    /* 파일 업로드 전 - 검색창 + 업로드 */
                    <>
                      <div className="mb-8">
                        <div className="text-center mb-6">
                          <h2 className="text-2xl font-bold text-white mb-2">
                            자연어 데이터 검색
                          </h2>
                          <p className="text-gray-400">
                            먼저 데이터 파일을 업로드하세요
                          </p>
                        </div>
                        
                        <SearchBox 
                          onSearch={handleSearch}
                          isLoading={isLoading}
                          disabled={!uploadedData}
                        />
                      </div>

                      {/* 파일 업로드 */}
                      <div className="mt-8">
                        <FileUpload onFileUpload={handleFileUpload} />
                      </div>
                    </>
                  ) : (
                    /* 파일 업로드 후 - 검색 인터페이스 */
                    <>
                      {/* 인터페이스 모드 선택 */}
                      <div className="mb-6 flex justify-center">
                        <div className="bg-gray-800/80 backdrop-blur-sm rounded-xl p-1 border border-gray-600/50">
                          <button
                            onClick={() => setInterfaceMode('simple')}
                            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                              interfaceMode === 'simple'
                                ? 'bg-gradient-to-r from-purple-600 to-purple-700 text-white shadow-lg'
                                : 'text-gray-300 hover:text-white'
                            }`}
                          >
                            🔍 간단 검색
                          </button>
                          <button
                            onClick={() => setInterfaceMode('chat')}
                            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                              interfaceMode === 'chat'
                                ? 'bg-gradient-to-r from-purple-600 to-purple-700 text-white shadow-lg'
                                : 'text-gray-300 hover:text-white'
                            }`}
                          >
                            💬 대화형 검색
                          </button>
                        </div>
                      </div>

                      {/* 검색 인터페이스 */}
                      {interfaceMode === 'simple' ? (
                        <>
                          <div className="mb-6">
                            <SearchBox
                              onSearch={handleSearch}
                              isLoading={isLoading}
                              disabled={!uploadedData}
                            />
                          </div>

                          {/* 검색 태그 */}
                          {searchResults.length === 0 && !isLoading && (
                            <div className="flex flex-wrap justify-center gap-2">
                              {[
                                '💰 매출 데이터',
                                '👥 고객 정보', 
                                '📊 제품 분석',
                                '📈 트렌드 분석'
                              ].map((tag, index) => (
                                <button
                                  key={index}
                                  onClick={() => handleTagClick(tag.replace(/[💰👥📊📈]\s/, ''))}
                                  className="px-3 py-1.5 bg-gray-800/50 backdrop-blur-sm text-gray-300 rounded-full text-xs hover:bg-gray-700/50 transition-all duration-200 border border-gray-600/30 hover:border-purple-500/50"
                                >
                                  {tag}
                                </button>
                              ))}
                            </div>
                          )}
                        </>
                      ) : (
                        <div className="h-64 overflow-hidden">
                          <ChatInterface
                            onSearch={handleSearch}
                            isLoading={isLoading}
                            uploadedData={uploadedData}
                          />
                        </div>
                      )}
                    </>
                  )}
                </div>
              </DeviceMockup>
            </div>
          </div>
        </div>
      </div>

      {/* 검색 결과 섹션 */}
      {uploadedData && searchQuery && (
        <section className="py-20 px-4 bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
          <div className="max-w-5xl mx-auto">

        {/* 인터페이스 모드 선택 */}
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

        {/* 검색 인터페이스 */}
        {interfaceMode === 'simple' ? (
          <>
            <div className="w-full max-w-3xl mb-8">
              <SearchBox
                onSearch={handleSearch}
                isLoading={isLoading}
                disabled={!uploadedData}
              />
            </div>

            {/* 검색 태그 */}
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

        {/* 필터 패널 */}
        {uploadedData && searchResults.length > 0 && (
          <FilterPanel
            onFilterChange={handleFilterChange}
            uploadedData={uploadedData}
          />
        )}

        {/* 검색 결과 - 스마트 차트 우선 표시 */}
        {uploadedData && searchQuery && (
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
                data={uploadedData}
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
        </section>
      )}
    </div>
  );
}

export default App;