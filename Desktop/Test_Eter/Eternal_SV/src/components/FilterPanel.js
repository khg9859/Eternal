import React, { useState, useEffect, useMemo } from 'react';

const FilterPanel = ({ onFilterChange, uploadedData, query }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [filters, setFilters] = useState({
    dateRange: { start: '', end: '' },
    category: '',
    region: '',
    ageRange: { min: '', max: '' },
    valueRange: { min: '', max: '' },
    sortBy: 'date',
    sortOrder: 'desc'
  });

  // 업로드된 데이터에서 동적으로 필터 옵션 추출
  const filterOptions = useMemo(() => {
    if (!uploadedData || uploadedData.length === 0) {
      return {
        categories: ['매출', '마케팅', '제품', '고객', '재무'],
        regions: ['서울', '부산', '대구', '인천', '광주', '대전', '울산'],
        ageGroups: ['10대', '20대', '30대', '40대', '50대', '60대 이상']
      };
    }

    const categories = new Set();
    const regions = new Set();
    const ageGroups = new Set();

    // 샘플 데이터에서 옵션 추출
    uploadedData.slice(0, 100).forEach(item => {
      Object.entries(item).forEach(([key, value]) => {
        const keyLower = key.toLowerCase();
        const valueLower = String(value).toLowerCase();

        // 카테고리 추출
        if (keyLower.includes('category') || keyLower.includes('카테고리') || 
            keyLower.includes('type') || keyLower.includes('분류')) {
          categories.add(String(value));
        }

        // 지역 추출
        if (keyLower.includes('region') || keyLower.includes('지역') || 
            keyLower.includes('city') || keyLower.includes('도시') ||
            keyLower.includes('location') || keyLower.includes('위치')) {
          regions.add(String(value));
        }

        // 나이 그룹 추출
        if (keyLower.includes('age') || keyLower.includes('나이') || 
            keyLower.includes('연령')) {
          if (typeof value === 'number') {
            if (value < 20) ageGroups.add('10대');
            else if (value < 30) ageGroups.add('20대');
            else if (value < 40) ageGroups.add('30대');
            else if (value < 50) ageGroups.add('40대');
            else if (value < 60) ageGroups.add('50대');
            else ageGroups.add('60대 이상');
          } else {
            ageGroups.add(String(value));
          }
        }

        // 일반적인 값들에서 카테고리 추출
        if (typeof value === 'string' && value.length < 20) {
          if (['서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종'].includes(value)) {
            regions.add(value);
          }
          if (['매출', '마케팅', '제품', '고객', '재무', '영업', '개발', '디자인'].includes(value)) {
            categories.add(value);
          }
        }
      });
    });

    return {
      categories: Array.from(categories).slice(0, 10),
      regions: Array.from(regions).slice(0, 15),
      ageGroups: Array.from(ageGroups).slice(0, 8)
    };
  }, [uploadedData]);

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
      ageRange: { min: '', max: '' },
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
    if (filters.ageRange.min || filters.ageRange.max) count++;
    if (filters.valueRange.min || filters.valueRange.max) count++;
    return count;
  };

  // 검색어 기반 스마트 필터 제안
  const getSmartFilterSuggestions = () => {
    if (!query) return [];
    
    const suggestions = [];
    const queryLower = query.toLowerCase();
    
    if (queryLower.includes('나이') || queryLower.includes('연령') || queryLower.includes('age')) {
      suggestions.push({ type: 'ageRange', label: '나이별 필터링', icon: '👥' });
    }
    if (queryLower.includes('지역') || queryLower.includes('위치') || queryLower.includes('region')) {
      suggestions.push({ type: 'region', label: '지역별 필터링', icon: '🌍' });
    }
    if (queryLower.includes('매출') || queryLower.includes('판매') || queryLower.includes('sales')) {
      suggestions.push({ type: 'valueRange', label: '매출 범위 설정', icon: '💰' });
    }
    
    return suggestions;
  };

  return (
    <div className="w-full max-w-5xl mx-auto mb-6">
      {/* 필터 토글 버튼 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full bg-gray-800/80 backdrop-blur-sm border border-gray-600/50 rounded-xl px-6 py-4 hover:bg-gray-700/80 transition-all duration-200 shadow-lg"
      >
        <div className="flex items-center">
          <svg className="w-5 h-5 text-gray-600 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.414A1 1 0 013 6.707V4z" />
          </svg>
          <span className="font-medium text-gray-300">필터 & 정렬</span>
          {getActiveFilterCount() > 0 && (
            <span className="ml-2 px-2 py-1 bg-purple-600 text-white text-xs rounded-full">
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
        <div className="mt-4 bg-gray-800/90 backdrop-blur-sm border border-gray-600/50 rounded-xl p-6 shadow-xl">
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* 날짜 범위 */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                📅 날짜 범위
              </label>
              <div className="space-y-2">
                <input
                  type="date"
                  value={filters.dateRange.start}
                  onChange={(e) => handleFilterChange('dateRange', { ...filters.dateRange, start: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm text-gray-300"
                  placeholder="시작일"
                />
                <input
                  type="date"
                  value={filters.dateRange.end}
                  onChange={(e) => handleFilterChange('dateRange', { ...filters.dateRange, end: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm text-gray-300"
                  placeholder="종료일"
                />
              </div>
            </div>

            {/* 카테고리 */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                🏷️ 카테고리
              </label>
              <select
                value={filters.category}
                onChange={(e) => handleFilterChange('category', e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm text-gray-300"
              >
                <option value="">전체 카테고리</option>
                {filterOptions.categories.map(category => (
                  <option key={category} value={category}>{category}</option>
                ))}
              </select>
            </div>

            {/* 지역 */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                🌍 지역
              </label>
              <select
                value={filters.region}
                onChange={(e) => handleFilterChange('region', e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm text-gray-300"
              >
                <option value="">전체 지역</option>
                {filterOptions.regions.map(region => (
                  <option key={region} value={region}>{region}</option>
                ))}
              </select>
            </div>

            {/* 나이 범위 */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                👥 나이 범위
              </label>
              <div className="space-y-2">
                <input
                  type="number"
                  value={filters.ageRange.min}
                  onChange={(e) => handleFilterChange('ageRange', { ...filters.ageRange, min: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm text-gray-300"
                  placeholder="최소 나이"
                />
                <input
                  type="number"
                  value={filters.ageRange.max}
                  onChange={(e) => handleFilterChange('ageRange', { ...filters.ageRange, max: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm text-gray-300"
                  placeholder="최대 나이"
                />
              </div>
            </div>

            {/* 값 범위 */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                💰 값 범위
              </label>
              <div className="space-y-2">
                <input
                  type="number"
                  value={filters.valueRange.min}
                  onChange={(e) => handleFilterChange('valueRange', { ...filters.valueRange, min: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm text-gray-300"
                  placeholder="최소값"
                />
                <input
                  type="number"
                  value={filters.valueRange.max}
                  onChange={(e) => handleFilterChange('valueRange', { ...filters.valueRange, max: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm text-gray-300"
                  placeholder="최대값"
                />
              </div>
            </div>

            {/* 정렬 기준 */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                📊 정렬 기준
              </label>
              <select
                value={filters.sortBy}
                onChange={(e) => handleFilterChange('sortBy', e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm text-gray-300"
              >
                <option value="date">날짜</option>
                <option value="value">값</option>
                <option value="name">이름</option>
                <option value="category">카테고리</option>
              </select>
            </div>

            {/* 정렬 순서 */}
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                🔄 정렬 순서
              </label>
              <div className="flex space-x-2">
                <button
                  onClick={() => handleFilterChange('sortOrder', 'asc')}
                  className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                    filters.sortOrder === 'asc'
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  오름차순
                </button>
                <button
                  onClick={() => handleFilterChange('sortOrder', 'desc')}
                  className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                    filters.sortOrder === 'desc'
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  내림차순
                </button>
              </div>
            </div>
          </div>

          {/* 스마트 필터 제안 */}
          {getSmartFilterSuggestions().length > 0 && (
            <div className="mt-6 pt-4 border-t border-gray-600">
              <div className="text-sm font-medium text-gray-300 mb-3">💡 검색어 기반 추천 필터</div>
              <div className="flex flex-wrap gap-2">
                {getSmartFilterSuggestions().map((suggestion, index) => (
                  <button
                    key={index}
                    onClick={() => {
                      // 해당 필터 섹션으로 스크롤하거나 자동 설정
                      if (suggestion.type === 'ageRange') {
                        handleFilterChange('ageRange', { min: '20', max: '40' });
                      }
                    }}
                    className="px-3 py-1.5 bg-purple-600/20 text-purple-300 rounded-lg text-xs hover:bg-purple-600/30 transition-colors border border-purple-500/30"
                  >
                    {suggestion.icon} {suggestion.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 액션 버튼 */}
          <div className="flex justify-between items-center mt-6 pt-4 border-t border-gray-600">
            <button
              onClick={resetFilters}
              className="px-4 py-2 text-gray-400 hover:text-gray-300 text-sm font-medium transition-colors"
            >
              필터 초기화
            </button>
            <div className="flex space-x-3">
              <button
                onClick={() => setIsOpen(false)}
                className="px-6 py-2 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 transition-colors text-sm font-medium"
              >
                닫기
              </button>
              <button
                onClick={() => {
                  onFilterChange(filters);
                  setIsOpen(false);
                }}
                className="px-6 py-2 bg-gradient-to-r from-purple-600 to-purple-700 text-white rounded-lg hover:from-purple-600/90 hover:to-purple-700/90 transition-all duration-200 text-sm font-medium shadow-lg"
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