import React from 'react';

const SearchTags = ({ onTagClick, disabled }) => {
  const popularTags = [
    { text: '매출 데이터', icon: '💰' },
    { text: '고객 정보', icon: '👥' },
    { text: '제품 분석', icon: '📊' },
    { text: '월별 통계', icon: '📅' },
    { text: '지역별 현황', icon: '🌍' },
    { text: '성과 지표', icon: '📈' },
    { text: '재고 현황', icon: '📦' },
    { text: '트렌드 분석', icon: '📉' }
  ];

  return (
    <div className="w-full max-w-5xl mx-auto mt-8 mb-12">
      <div className="text-center mb-6">
        <p className="text-gray-500 text-sm font-light flex items-center justify-center">
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
          </svg>
          인기 검색어
        </p>
      </div>
      
      <div className="flex flex-wrap justify-center gap-3 px-4">
        {popularTags.map((tag, index) => (
          <button
            key={index}
            onClick={() => !disabled && onTagClick(tag.text)}
            disabled={disabled}
            className={`group inline-flex items-center px-5 py-2.5 rounded-full text-sm font-medium transition-all duration-300 ${
              disabled 
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed' 
                : 'bg-white/80 backdrop-blur-sm text-gray-700 hover:bg-gradient-to-r hover:from-google-blue/10 hover:to-google-purple/10 hover:text-google-blue hover:shadow-xl hover:scale-105 border border-gray-200/50 hover:border-google-blue/30 shadow-sm'
            }`}
          >
            <span className="mr-2 text-base group-hover:scale-110 transition-transform duration-200">{tag.icon}</span>
            <span className="whitespace-nowrap">{tag.text}</span>
          </button>
        ))}
      </div>
      
      <div className="text-center mt-6">
        <p className="text-xs text-gray-400 font-light">
          태그를 클릭하여 빠른 검색을 시작하세요
        </p>
      </div>
    </div>
  );
};

export default SearchTags;