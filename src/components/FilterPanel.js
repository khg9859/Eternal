import React, { useState } from 'react';

const FilterPanel = ({ onFilterChange, uploadedData }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [filters, setFilters] = useState({
    dateRange: { start: '', end: '' },
    category: '',
    region: '',
    valueRange: { min: '', max: '' },
    sortBy: 'date',
    sortOrder: 'desc'
  });

  const handleFilterChange = (key, value) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    onFilterChange(newFilters);
  };

  const resetFilters = () => {
    const resetFilters = {
      dateRange: { start: '', end: '' },
      category: '',
      region: '',
      valueRange: { min: '', max: '' },
      sortBy: 'date',
      sortOrder: 'desc'
    };
    setFilters(resetFilters);
    onFilterChange(resetFilters);
  };

  const getActiveFilterCount = () => {
    let count = 0;
    if (filters.dateRange.start || filters.dateRange.end) count++;
    if (filters.category) count++;
    if (filters.region) count++;
    if (filters.valueRange.min || filters.valueRange.max) count++;
    return count;
  };

  return (
    <div className="w-full max-w-5xl mx-auto mb-6">
      {/* 필터 토글 버튼 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full bg-white/80 backdrop-blur-sm border border-gray-200/50 rounded-xl px-6 py-4 hover:bg-gray-50/80 transition-all duration-200 shadow-lg"
      >
        <div className="flex items-center">
          <svg className="w-5 h-5 text-gray-600 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.414A1 1 0 013 6.707V4z" />
          </svg>
          <span className="font-medium text-gray-700">필터 & 정렬</span>
          {getActiveFilterCount() > 0 && (
            <span className="ml-2 px-2 py-1 bg-google-blue text-white text-xs rounded-full">
              {getActiveFilterCount()}
            </span>
          )}
        </div>
        <svg 
          className={`w-5 h-5 text-gray-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* 필터 패널 */}
      {isOpen && (
        <div className="mt-4 bg-white/90 backdrop-blur-sm border border-gray-200/50 rounded-xl p-6 shadow-xl">
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* 날짜 범위 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                📅 날짜 범위
              </label>
              <div className="space-y-2">
                <input
                  type="date"
                  value={filters.dateRange.start}
                  onChange={(e) => handleFilterChange('dateRange', { ...filters.dateRange, start: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-google-blue focus:border-transparent text-sm"
                  placeholder="시작일"
                />
                <input
                  type="date"
                  value={filters.dateRange.end}
                  onChange={(e) => handleFilterChange('dateRange', { ...filters.dateRange, end: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-google-blue focus:border-transparent text-sm"
                  placeholder="종료일"
                />
              </div>
            </div>

            {/* 카테고리 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                🏷️ 카테고리
              </label>
              <select
                value={filters.category}
                onChange={(e) => handleFilterChange('category', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-google-blue focus:border-transparent text-sm"
              >
                <option value="">전체 카테고리</option>
                <option value="sales">매출</option>
                <option value="marketing">마케팅</option>
                <option value="product">제품</option>
                <option value="customer">고객</option>
                <option value="finance">재무</option>
              </select>
            </div>

            {/* 지역 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                🌍 지역
              </label>
              <select
                value={filters.region}
                onChange={(e) => handleFilterChange('region', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-google-blue focus:border-transparent text-sm"
              >
                <option value="">전체 지역</option>
                <option value="seoul">서울</option>
                <option value="busan">부산</option>
                <option value="daegu">대구</option>
                <option value="incheon">인천</option>
                <option value="gwangju">광주</option>
                <option value="daejeon">대전</option>
                <option value="ulsan">울산</option>
              </select>
            </div>

            {/* 값 범위 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                💰 값 범위
              </label>
              <div className="space-y-2">
                <input
                  type="number"
                  value={filters.valueRange.min}
                  onChange={(e) => handleFilterChange('valueRange', { ...filters.valueRange, min: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-google-blue focus:border-transparent text-sm"
                  placeholder="최소값"
                />
                <input
                  type="number"
                  value={filters.valueRange.max}
                  onChange={(e) => handleFilterChange('valueRange', { ...filters.valueRange, max: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-google-blue focus:border-transparent text-sm"
                  placeholder="최대값"
                />
              </div>
            </div>

            {/* 정렬 기준 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                📊 정렬 기준
              </label>
              <select
                value={filters.sortBy}
                onChange={(e) => handleFilterChange('sortBy', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-google-blue focus:border-transparent text-sm"
              >
                <option value="date">날짜</option>
                <option value="value">값</option>
                <option value="name">이름</option>
                <option value="category">카테고리</option>
              </select>
            </div>

            {/* 정렬 순서 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                🔄 정렬 순서
              </label>
              <div className="flex space-x-2">
                <button
                  onClick={() => handleFilterChange('sortOrder', 'asc')}
                  className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                    filters.sortOrder === 'asc'
                      ? 'bg-google-blue text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  오름차순
                </button>
                <button
                  onClick={() => handleFilterChange('sortOrder', 'desc')}
                  className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                    filters.sortOrder === 'desc'
                      ? 'bg-google-blue text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  내림차순
                </button>
              </div>
            </div>
          </div>

          {/* 액션 버튼 */}
          <div className="flex justify-between items-center mt-6 pt-4 border-t border-gray-200">
            <button
              onClick={resetFilters}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 text-sm font-medium transition-colors"
            >
              필터 초기화
            </button>
            <div className="flex space-x-3">
              <button
                onClick={() => setIsOpen(false)}
                className="px-6 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium"
              >
                닫기
              </button>
              <button
                onClick={() => {
                  onFilterChange(filters);
                  setIsOpen(false);
                }}
                className="px-6 py-2 bg-gradient-to-r from-google-blue to-google-purple text-white rounded-lg hover:from-google-blue/90 hover:to-google-purple/90 transition-all duration-200 text-sm font-medium shadow-lg"
              >
                적용
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 활성 필터 표시 */}
      {getActiveFilterCount() > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {filters.category && (
            <span className="inline-flex items-center px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
              카테고리: {filters.category}
              <button 
                onClick={() => handleFilterChange('category', '')}
                className="ml-2 text-blue-500 hover:text-blue-700"
              >
                ×
              </button>
            </span>
          )}
          {filters.region && (
            <span className="inline-flex items-center px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm">
              지역: {filters.region}
              <button 
                onClick={() => handleFilterChange('region', '')}
                className="ml-2 text-green-500 hover:text-green-700"
              >
                ×
              </button>
            </span>
          )}
          {(filters.dateRange.start || filters.dateRange.end) && (
            <span className="inline-flex items-center px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm">
              날짜 필터 적용됨
              <button 
                onClick={() => handleFilterChange('dateRange', { start: '', end: '' })}
                className="ml-2 text-purple-500 hover:text-purple-700"
              >
                ×
              </button>
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default FilterPanel;