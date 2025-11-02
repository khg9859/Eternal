import React from 'react';
import DeviceMockup from './DeviceMockup';
import SearchBox from './SearchBox';

const HeroSection = ({ onSearch, isLoading, disabled }) => {
  return (
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
            CSV, Excel, JSON 파일을 업로드하고 자연어로 질문하면 
            <br className="hidden md:block" />
            AI가 자동으로 차트와 인사이트를 생성해드립니다
          </p>
        </div>

        {/* 디바이스 목업 */}
        <div className="flex justify-center">
          <div className="w-full max-w-4xl">
            <DeviceMockup type="laptop">
              <div className="w-full max-w-2xl">
                {/* 목업 내부의 검색창 */}
                <div className="mb-8">
                  <div className="text-center mb-6">
                    <h2 className="text-2xl font-bold text-white mb-2">
                      자연어 데이터 검색
                    </h2>
                    <p className="text-gray-400">
                      "총 매출은 얼마야?" "고객 만족도 트렌드 보여줘"
                    </p>
                  </div>
                  
                  <SearchBox 
                    onSearch={onSearch}
                    isLoading={isLoading}
                    disabled={disabled}
                  />
                </div>

                {/* 예시 검색어 */}
                <div className="flex flex-wrap justify-center gap-2 mt-6">
                  {[
                    '💰 매출 데이터',
                    '👥 고객 정보', 
                    '📊 제품 분석',
                    '📈 트렌드 분석'
                  ].map((tag, index) => (
                    <button
                      key={index}
                      onClick={() => !disabled && onSearch(tag.replace(/[💰👥📊📈]\s/, ''))}
                      className="px-4 py-2 bg-gray-800/50 backdrop-blur-sm text-gray-300 rounded-full text-sm hover:bg-gray-700/50 transition-all duration-200 border border-gray-600/30 hover:border-purple-500/50"
                    >
                      {tag}
                    </button>
                  ))}
                </div>
              </div>
            </DeviceMockup>
          </div>
        </div>

        {/* 특징 섹션 */}
        <div className="mt-20 grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
          <div className="text-center p-6 bg-gray-800/30 backdrop-blur-sm rounded-2xl border border-gray-700/50">
            <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">빠른 검색</h3>
            <p className="text-gray-400 text-sm">자연어로 질문하면 즉시 결과를 확인할 수 있습니다</p>
          </div>

          <div className="text-center p-6 bg-gray-800/30 backdrop-blur-sm rounded-2xl border border-gray-700/50">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">스마트 차트</h3>
            <p className="text-gray-400 text-sm">AI가 자동으로 최적의 차트를 생성해드립니다</p>
          </div>

          <div className="text-center p-6 bg-gray-800/30 backdrop-blur-sm rounded-2xl border border-gray-700/50">
            <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">다양한 형식</h3>
            <p className="text-gray-400 text-sm">CSV, Excel, JSON 파일을 모두 지원합니다</p>
          </div>
        </div>
      </div>

      {/* 스크롤 인디케이터 */}
      <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 animate-bounce">
        <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
        </svg>
      </div>
    </div>
  );
};

export default HeroSection;