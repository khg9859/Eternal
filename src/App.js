import React, { useState } from 'react';
import SearchBox from './components/SearchBox';
import SearchResults from './components/SearchResults';
import FileUpload from './components/FileUpload';
import ChatInterface from './components/ChatInterface';
import FilterPanel from './components/FilterPanel';
import SmartChart from './components/SmartChart';
import DeviceMockup from './components/DeviceMockup';
import DataTable from './components/DataTable';
import AdvancedChart from './components/AdvancedChart';
import AIChatInterface from './components/AIChatInterface';

function App() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [uploadedData, setUploadedData] = useState(null);
  const [showVisualization, setShowVisualization] = useState(false);
  const [showSmartChart, setShowSmartChart] = useState(true); // 기본적으로 차트 우선 표시
  const [activeFilters, setActiveFilters] = useState({});
  const [interfaceMode, setInterfaceMode] = useState('simple'); // 'simple' or 'chat'
  const [currentPage, setCurrentPage] = useState('home'); // 'home' or 'results'
  const [viewMode, setViewMode] = useState('chart'); // 'chart', 'table', 'advanced'
  const [showChatPopup, setShowChatPopup] = useState(false); // AI 채팅 팝업 표시 여부

  const handleSearch = async (query) => {
    if (!query.trim()) return;

    setIsLoading(true);
    setSearchQuery(query);
    
    // 검색 시 결과 페이지로 전환
    setCurrentPage('results');

    // 실제 데이터가 있으면 실제 검색, 없으면 더미 데이터
    setTimeout(() => {
      let results = [];
      
      if (uploadedData && uploadedData.length > 0) {
        // 실제 업로드된 데이터에서 검색
        results = searchInUploadedData(query, uploadedData);
      } else {
        // 더미 데이터 생성
        results = generateSmartResults(query);
      }
      
      setSearchResults(results);
      setIsLoading(false);
    }, 800);
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
      results.push({
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
      });
    }
    
    return results;
  };

  const handleFileUpload = (data) => {
    setUploadedData(data);
    console.log(`📊 ${data.length}개의 데이터 항목이 로드되었습니다.`);
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
    setCurrentPage('home'); // 홈 페이지로 돌아가기
  };

  // 홈 페이지 렌더링
  const renderHomePage = () => (
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
          <div className="w-full max-w-9xl">
            <DeviceMockup type="laptop">
              <div className="w-full max-w-3xl">
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
                      
                      <button
                        onClick={() => setShowChatPopup(true)}
                        disabled={!uploadedData}
                        className="w-full px-6 py-4 bg-gray-800/80 backdrop-blur-sm border border-gray-600/50 rounded-2xl text-left text-gray-400 hover:text-gray-300 hover:border-purple-500/50 transition-all duration-200 flex items-center space-x-4 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <svg className="w-6 h-6 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                        <div className="flex-1">
                          <div className="text-lg font-medium text-gray-300">AI에게 데이터에 대해 질문하세요</div>
                          <div className="text-sm text-gray-500">자연어로 질문하면 AI가 분석해드립니다</div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <span className="text-sm bg-purple-600/20 text-purple-300 px-3 py-1 rounded-full">AI</span>
                          <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        </div>
                      </button>
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
                          🔍 AI Search
                        </button>
                        <button
                          onClick={() => setInterfaceMode('chat')}
                          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                            interfaceMode === 'chat'
                              ? 'bg-gradient-to-r from-purple-600 to-purple-700 text-white shadow-lg'
                              : 'text-gray-300 hover:text-white'
                          }`}
                        >
                          💬  Text Search
                        </button>
                      </div>
                    </div>

                    {/* 검색 인터페이스 */}
                    {interfaceMode === 'simple' ? (
                      <>
                        <div className="mb-6">
                          <button
                            onClick={() => setShowChatPopup(true)}
                            disabled={!uploadedData}
                            className="w-full px-4 py-3 bg-gray-800/80 backdrop-blur-sm border border-gray-600/50 rounded-xl text-left text-gray-400 hover:text-gray-300 hover:border-purple-500/50 transition-all duration-200 flex items-center space-x-3 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                            </svg>
                            <span>AI에게 질문하세요...</span>
                            <div className="ml-auto">
                              <span className="text-xs bg-purple-600/20 text-purple-300 px-2 py-1 rounded">AI</span>
                            </div>
                          </button>
                        </div>

                        {/* 검색 태그 */}
                        {!isLoading && (
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
                      <div className="h-80 overflow-hidden">
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
  );

  // 검색 결과 페이지 렌더링
  const renderResultsPage = () => (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* 상단 네비게이션 */}
      <div className="sticky top-0 z-50 bg-gray-900/80 backdrop-blur-sm border-b border-gray-700/50">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            {/* 로고 및 홈 버튼 */}
            <div className="flex items-center space-x-4">
              <button
                onClick={resetToHome}
                className="text-2xl font-bold bg-gradient-to-r from-purple-400 via-pink-400 to-blue-400 bg-clip-text text-transparent hover:opacity-80 transition-opacity"
              >
                DataSearch
              </button>
              <div className="text-gray-400 text-sm">
                {uploadedData ? `${uploadedData.length.toLocaleString()}개 데이터` : '데이터 없음'}
              </div>
            </div>

            {/* AI 채팅 검색 */}
            <div className="flex-1 max-w-md mx-8">
              <button
                onClick={() => setShowChatPopup(true)}
                className="w-full px-4 py-2 bg-gray-800/80 backdrop-blur-sm border border-gray-600/50 rounded-xl text-left text-gray-400 hover:text-gray-300 hover:border-purple-500/50 transition-all duration-200 flex items-center space-x-3"
              >
                <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <span>AI에게 데이터에 대해 질문하세요...</span>
                <div className="ml-auto flex items-center space-x-1">
                  <span className="text-xs bg-purple-600/20 text-purple-300 px-2 py-1 rounded">AI</span>
                </div>
              </button>
            </div>

            {/* 홈으로 돌아가기 */}
            <button
              onClick={resetToHome}
              className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors border border-gray-600"
            >
              🏠 홈으로
            </button>
          </div>
        </div>
      </div>

      {/* 메인 결과 영역 */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* 검색 쿼리 표시 */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">
            "{searchQuery}" 검색 결과
          </h1>
          <p className="text-gray-400">
            {searchResults.length}개의 결과를 찾았습니다
          </p>
        </div>

        {/* 필터 패널 */}
        <div className="mb-6">
          <FilterPanel 
            onFilterChange={handleFilterChange}
            uploadedData={uploadedData}
            query={searchQuery}
          />
        </div>

        {/* 결과 표시 모드 선택 */}
        <div className="mb-6 flex justify-center">
          <div className="bg-gray-800/80 backdrop-blur-sm rounded-xl p-1 border border-gray-600/50">
            <button
              onClick={() => setViewMode('chart')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                viewMode === 'chart'
                  ? 'bg-gradient-to-r from-purple-600 to-purple-700 text-white shadow-lg'
                  : 'text-gray-300 hover:text-white'
              }`}
            >
              📊 기본 차트
            </button>
            <button
              onClick={() => setViewMode('advanced')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                viewMode === 'advanced'
                  ? 'bg-gradient-to-r from-purple-600 to-purple-700 text-white shadow-lg'
                  : 'text-gray-300 hover:text-white'
              }`}
            >
              📈 고급 차트
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                viewMode === 'table'
                  ? 'bg-gradient-to-r from-purple-600 to-purple-700 text-white shadow-lg'
                  : 'text-gray-300 hover:text-white'
              }`}
            >
              📋 데이터 테이블
            </button>
            <button
              onClick={() => setViewMode('results')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                viewMode === 'results'
                  ? 'bg-gradient-to-r from-purple-600 to-purple-700 text-white shadow-lg'
                  : 'text-gray-300 hover:text-white'
              }`}
            >
              📄 상세 결과
            </button>

          </div>
        </div>

        {/* 검색 결과 컨텐츠 */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* 메인 결과 영역 */}
          <div className="lg:col-span-3">
            <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-600/50 p-6">
              {isLoading ? (
                <div className="flex items-center justify-center h-96">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto mb-4"></div>
                    <p className="text-gray-400">검색 중...</p>
                  </div>
                </div>
              ) : (
                <>
                  {viewMode === 'chart' && (
                    <SmartChart 
                      query={searchQuery} 
                      data={uploadedData}
                      onDataAnalyzed={(result) => {
                        console.log('차트 분석 완료:', result);
                      }}
                    />
                  )}
                  {viewMode === 'advanced' && (
                    <AdvancedChart 
                      data={uploadedData}
                      query={searchQuery}
                      filters={activeFilters}
                    />
                  )}
                  {viewMode === 'table' && (
                    <DataTable 
                      data={uploadedData}
                      query={searchQuery}
                      filters={activeFilters}
                    />
                  )}
                  {viewMode === 'results' && (
                    <SearchResults
                      results={searchResults}
                      query={searchQuery}
                      isLoading={isLoading}
                    />
                  )}

                </>
              )}
            </div>
          </div>



          {/* 사이드바 - 빠른 액션 및 정보 */}
          <div className="space-y-6">
            {/* 빠른 검색 태그 */}
            <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-600/50 p-4">
              <h3 className="text-sm font-semibold text-white mb-3">빠른 검색</h3>
              <div className="flex flex-wrap gap-1.5">
                {[
                  '💰 매출',
                  '👥 고객', 
                  '📊 제품',
                  '📈 트렌드',
                  '🎯 성과',
                  '📅 기간별',
                  '🌍 지역별',
                  '👤 나이별'
                ].map((tag, index) => (
                  <button
                    key={index}
                    onClick={() => handleTagClick(tag.replace(/[💰👥📊📈🎯📅🌍👤]\s/, ''))}
                    className="px-2 py-1 bg-gray-700/50 text-gray-300 rounded text-xs hover:bg-gray-600/50 transition-all duration-200 border border-gray-600/30 hover:border-purple-500/50"
                  >
                    {tag}
                  </button>
                ))}
              </div>
            </div>

            {/* 데이터 통계 */}
            {uploadedData && (
              <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-600/50 p-4">
                <h3 className="text-sm font-semibold text-white mb-3">데이터 통계</h3>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-400">총 데이터:</span>
                    <span className="text-white font-mono">{uploadedData.length.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">검색 결과:</span>
                    <span className="text-green-400 font-mono">{searchResults.length}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">매치율:</span>
                    <span className="text-blue-400 font-mono">
                      {uploadedData.length > 0 ? Math.round((searchResults.length / uploadedData.length) * 100) : 0}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">활성 필터:</span>
                    <span className="text-purple-400 font-mono">{Object.values(activeFilters).filter(v => v && v !== '').length}</span>
                  </div>
                </div>
              </div>
            )}

            {/* 내보내기 옵션 */}
            <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-600/50 p-4">
              <h3 className="text-sm font-semibold text-white mb-3">내보내기</h3>
              <div className="space-y-2">
                <button className="w-full px-3 py-2 bg-gray-700/50 text-gray-300 rounded-lg text-xs hover:bg-gray-600/50 transition-colors">
                  📊 차트 이미지 저장
                </button>
                <button className="w-full px-3 py-2 bg-gray-700/50 text-gray-300 rounded-lg text-xs hover:bg-gray-600/50 transition-colors">
                  📄 결과 PDF 다운로드
                </button>
                <button className="w-full px-3 py-2 bg-gray-700/50 text-gray-300 rounded-lg text-xs hover:bg-gray-600/50 transition-colors">
                  📋 CSV 내보내기
                </button>
              </div>
            </div>

            {/* 최근 검색 */}
            <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-600/50 p-4">
              <h3 className="text-sm font-semibold text-white mb-3">최근 검색</h3>
              <div className="space-y-1">
                {['매출 데이터', '고객 분석', '지역별 성과'].map((recent, index) => (
                  <button
                    key={index}
                    onClick={() => handleSearch(recent)}
                    className="w-full text-left px-2 py-1 text-xs text-gray-400 hover:text-gray-300 hover:bg-gray-700/30 rounded transition-colors"
                  >
                    🔍 {recent}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {currentPage === 'home' ? renderHomePage() : renderResultsPage()}
      
      {/* AI 채팅 팝업 */}
      {showChatPopup && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="relative w-full max-w-4xl h-[80vh] mx-4">
            {/* 팝업 헤더 */}
            <div className="absolute top-0 left-0 right-0 bg-gray-900/95 backdrop-blur-sm border-b border-gray-600/50 rounded-t-xl px-6 py-4 flex items-center justify-between z-10">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-blue-500 rounded-full flex items-center justify-center">
                  <span className="text-white font-bold">AI</span>
                </div>
                <div>
                  <h3 className="text-white font-semibold text-lg">데이터 분석 AI 어시스턴트</h3>
                  <p className="text-sm text-gray-400">
                    {uploadedData ? `${uploadedData.length.toLocaleString()}개 데이터 분석 준비완료` : '데이터를 업로드해주세요'}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowChatPopup(false)}
                className="w-8 h-8 bg-gray-700 hover:bg-gray-600 rounded-full flex items-center justify-center transition-colors"
              >
                <svg className="w-5 h-5 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* 팝업 컨텐츠 */}
            <div className="bg-gray-900/95 backdrop-blur-sm rounded-xl border border-gray-600/50 h-full pt-20">
              <AIChatInterface
                uploadedData={uploadedData}
                searchQuery={searchQuery}
                onNewSearch={(query) => {
                  handleSearch(query);
                  setShowChatPopup(false); // 검색 후 팝업 닫기
                }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;