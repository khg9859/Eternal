import React, { useState, useMemo } from 'react';

const DataTable = ({ data, query, filters = {} }) => {
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // 데이터 필터링 및 정렬
  const processedData = useMemo(() => {
    if (!data || data.length === 0) return [];

    let filtered = [...data];

    // 검색어 필터링
    if (query) {
      const keywords = query.toLowerCase().split(' ');
      filtered = filtered.filter(item => {
        const itemString = JSON.stringify(item).toLowerCase();
        return keywords.some(keyword => itemString.includes(keyword));
      });
    }

    // 추가 필터 적용
    if (filters.category) {
      filtered = filtered.filter(item => 
        Object.values(item).some(value => 
          String(value).toLowerCase().includes(filters.category.toLowerCase())
        )
      );
    }

    if (filters.region) {
      filtered = filtered.filter(item => 
        Object.values(item).some(value => 
          String(value).toLowerCase().includes(filters.region.toLowerCase())
        )
      );
    }

    // 정렬
    if (sortConfig.key) {
      filtered.sort((a, b) => {
        const aValue = a[sortConfig.key];
        const bValue = b[sortConfig.key];
        
        if (aValue < bValue) {
          return sortConfig.direction === 'asc' ? -1 : 1;
        }
        if (aValue > bValue) {
          return sortConfig.direction === 'asc' ? 1 : -1;
        }
        return 0;
      });
    }

    return filtered;
  }, [data, query, filters, sortConfig]);

  // 페이지네이션
  const totalPages = Math.ceil(processedData.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedData = processedData.slice(startIndex, startIndex + itemsPerPage);

  // 컬럼 정보 추출
  const columns = useMemo(() => {
    if (!processedData || processedData.length === 0) return [];
    
    const firstItem = processedData[0];
    return Object.keys(firstItem).map(key => ({
      key,
      label: key.charAt(0).toUpperCase() + key.slice(1),
      type: typeof firstItem[key] === 'number' ? 'number' : 'text'
    }));
  }, [processedData]);

  const handleSort = (key) => {
    setSortConfig(prevConfig => ({
      key,
      direction: prevConfig.key === key && prevConfig.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  const getSortIcon = (key) => {
    if (sortConfig.key !== key) {
      return (
        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
        </svg>
      );
    }
    
    return sortConfig.direction === 'asc' ? (
      <svg className="w-4 h-4 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" />
      </svg>
    ) : (
      <svg className="w-4 h-4 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h9m5-4v12m0 0l-4-4m4 4l4-4" />
      </svg>
    );
  };

  const formatValue = (value, type) => {
    if (type === 'number' && typeof value === 'number') {
      return value.toLocaleString();
    }
    if (typeof value === 'string' && value.length > 50) {
      return value.substring(0, 50) + '...';
    }
    return String(value);
  };

  const getValueColor = (value, type) => {
    if (type === 'number' && typeof value === 'number') {
      if (value > 1000000) return 'text-green-600 font-semibold';
      if (value > 100000) return 'text-blue-600 font-medium';
      if (value > 10000) return 'text-purple-600';
    }
    return 'text-gray-700';
  };

  if (!processedData || processedData.length === 0) {
    return (
      <div className="text-center py-12">
        <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <p className="text-gray-500">표시할 데이터가 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 테이블 정보 */}
      <div className="flex justify-between items-center">
        <div className="text-sm text-gray-400">
          총 {processedData.length.toLocaleString()}개 항목 중 {startIndex + 1}-{Math.min(startIndex + itemsPerPage, processedData.length)}개 표시
        </div>
        <div className="text-sm text-gray-400">
          페이지 {currentPage} / {totalPages}
        </div>
      </div>

      {/* 테이블 */}
      <div className="overflow-x-auto bg-gray-800/30 backdrop-blur-sm rounded-xl border border-gray-600/50">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-600/50">
              {columns.map((column) => (
                <th
                  key={column.key}
                  className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider cursor-pointer hover:bg-gray-700/50 transition-colors"
                  onClick={() => handleSort(column.key)}
                >
                  <div className="flex items-center space-x-1">
                    <span>{column.label}</span>
                    {getSortIcon(column.key)}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-600/30">
            {paginatedData.map((item, index) => (
              <tr
                key={index}
                className="hover:bg-gray-700/30 transition-colors"
              >
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={`px-4 py-3 text-sm ${getValueColor(item[column.key], column.type)}`}
                  >
                    {formatValue(item[column.key], column.type)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 페이지네이션 */}
      {totalPages > 1 && (
        <div className="flex justify-center items-center space-x-2">
          <button
            onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
            disabled={currentPage === 1}
            className="px-3 py-2 text-sm bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            이전
          </button>
          
          <div className="flex space-x-1">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const pageNum = Math.max(1, Math.min(currentPage - 2 + i, totalPages - 4 + i));
              return (
                <button
                  key={pageNum}
                  onClick={() => setCurrentPage(pageNum)}
                  className={`w-10 h-10 text-sm rounded-lg transition-colors ${
                    currentPage === pageNum
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}
          </div>
          
          <button
            onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
            disabled={currentPage === totalPages}
            className="px-3 py-2 text-sm bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            다음
          </button>
        </div>
      )}

      {/* 통계 요약 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
        {columns.filter(col => col.type === 'number').slice(0, 4).map((column) => {
          const values = processedData.map(item => item[column.key]).filter(val => typeof val === 'number');
          if (values.length === 0) return null;
          
          const sum = values.reduce((a, b) => a + b, 0);
          const avg = sum / values.length;
          const max = Math.max(...values);
          const min = Math.min(...values);
          
          return (
            <div key={column.key} className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-4 border border-gray-600/50">
              <h4 className="text-sm font-medium text-gray-300 mb-2">{column.label}</h4>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-400">평균:</span>
                  <span className="text-white font-mono">{Math.round(avg).toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">최대:</span>
                  <span className="text-green-400 font-mono">{max.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">최소:</span>
                  <span className="text-red-400 font-mono">{min.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">합계:</span>
                  <span className="text-blue-400 font-mono">{sum.toLocaleString()}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default DataTable;