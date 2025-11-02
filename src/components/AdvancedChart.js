import React, { useState, useEffect, useMemo } from 'react';

const AdvancedChart = ({ data, query, filters = {} }) => {
  const [selectedField, setSelectedField] = useState('');
  const [groupBy, setGroupBy] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showAllCharts, setShowAllCharts] = useState(true); // 모든 차트 표시 여부
  const [singleChartType, setSingleChartType] = useState('bar'); // 단일 차트 모드에서의 차트 타입

  // 데이터 분석 및 필드 추출
  const { numericFields, textFields, processedData } = useMemo(() => {
    if (!data || data.length === 0) return { numericFields: [], textFields: [], processedData: [] };

    // 검색어로 필터링
    let filtered = [...data];
    if (query) {
      const keywords = query.toLowerCase().split(' ');
      filtered = filtered.filter(item => {
        const itemString = JSON.stringify(item).toLowerCase();
        return keywords.some(keyword => itemString.includes(keyword));
      });
    }

    // 필드 분석
    const sample = filtered[0] || {};
    const numericFields = [];
    const textFields = [];

    Object.entries(sample).forEach(([key, value]) => {
      if (typeof value === 'number') {
        numericFields.push({ key, label: key.charAt(0).toUpperCase() + key.slice(1) });
      } else if (typeof value === 'string') {
        const numValue = parseFloat(value.replace(/[^\d.-]/g, ''));
        if (!isNaN(numValue)) {
          numericFields.push({ key, label: key.charAt(0).toUpperCase() + key.slice(1) });
        } else {
          textFields.push({ key, label: key.charAt(0).toUpperCase() + key.slice(1) });
        }
      }
    });

    return { numericFields, textFields, processedData: filtered.slice(0, 100) };
  }, [data, query]);

  // 기본 필드 설정
  useEffect(() => {
    if (numericFields.length > 0 && !selectedField) {
      setSelectedField(numericFields[0].key);
    }
    if (textFields.length > 0 && !groupBy) {
      setGroupBy(textFields[0].key);
    }
  }, [numericFields, textFields, selectedField, groupBy]);

  // 차트 데이터 생성 (막대/선형 차트용)
  const chartData = useMemo(() => {
    if (!processedData.length || !selectedField) return [];

    // 막대/선형 차트 데이터
    const groups = {};
    processedData.forEach(item => {
      const groupValue = groupBy ? String(item[groupBy]) : 'All';
      const numValue = typeof item[selectedField] === 'number' 
        ? item[selectedField] 
        : parseFloat(String(item[selectedField]).replace(/[^\d.-]/g, '')) || 0;
      
      if (!groups[groupValue]) {
        groups[groupValue] = { sum: 0, count: 0, values: [] };
      }
      groups[groupValue].sum += numValue;
      groups[groupValue].count += 1;
      groups[groupValue].values.push(numValue);
    });

    const colors = ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#6366f1', '#84cc16'];
    return Object.entries(groups)
      .map(([label, data], index) => ({
        label: label.length > 15 ? label.substring(0, 15) + '...' : label,
        value: Math.round(data.sum / data.count), // 평균값
        sum: data.sum,
        count: data.count,
        color: colors[index % colors.length]
      }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 10);
  }, [processedData, selectedField, groupBy]);

  // 파이 차트 데이터 생성
  const pieChartData = useMemo(() => {
    if (!processedData.length || !selectedField) return [];

    // 그룹별 집계
    const groups = {};
    processedData.forEach(item => {
      const groupValue = groupBy ? String(item[groupBy]) : 'All';
      const numValue = typeof item[selectedField] === 'number' 
        ? item[selectedField] 
        : parseFloat(String(item[selectedField]).replace(/[^\d.-]/g, '')) || 0;
      
      groups[groupValue] = (groups[groupValue] || 0) + numValue;
    });

    const colors = ['#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#6366f1', '#84cc16'];
    return Object.entries(groups)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 8)
      .map(([label, value], index) => ({
        label: label.length > 20 ? label.substring(0, 20) + '...' : label,
        value,
        color: colors[index % colors.length],
        percentage: Math.round((value / Object.values(groups).reduce((a, b) => a + b, 0)) * 100)
      }));
  }, [processedData, selectedField, groupBy]);

  const maxValue = chartData.length > 0 ? Math.max(...chartData.map(d => d.value)) : 0;

  const renderBarChart = () => (
    <div className="space-y-3">
      {chartData.map((item, index) => (
        <div key={index} className="flex items-center space-x-4">
          <div className="w-32 text-sm font-medium text-gray-300 truncate">
            {item.label}
          </div>
          <div className="flex-1">
            <div className="bg-gray-700/50 rounded-full h-8 relative overflow-hidden">
              <div 
                className="h-full rounded-full transition-all duration-1000 ease-out flex items-center justify-end pr-3"
                style={{ 
                  width: `${(item.value / maxValue) * 100}%`,
                  backgroundColor: item.color
                }}
              >
                <span className="text-white text-xs font-semibold">
                  {item.value.toLocaleString()}
                </span>
              </div>
            </div>
          </div>
          <div className="w-16 text-xs text-gray-400 text-right">
            {item.count && `${item.count}개`}
          </div>
        </div>
      ))}
    </div>
  );

  const renderLineChart = () => (
    <div className="h-64 flex items-end justify-between px-4 border-b border-gray-600/50 relative">
      {/* Y축 라벨 */}
      <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-xs text-gray-400 pr-2">
        <span>{maxValue.toLocaleString()}</span>
        <span>{Math.round(maxValue * 0.75).toLocaleString()}</span>
        <span>{Math.round(maxValue * 0.5).toLocaleString()}</span>
        <span>{Math.round(maxValue * 0.25).toLocaleString()}</span>
        <span>0</span>
      </div>
      
      {/* 데이터 포인트 */}
      <div className="flex-1 ml-8 flex items-end justify-between">
        {chartData.map((item, index) => (
          <div key={index} className="flex flex-col items-center group">
            <div className="relative">
              <div 
                className="w-2 rounded-t-lg transition-all duration-1000 ease-out"
                style={{ 
                  height: `${(item.value / maxValue) * 200}px`,
                  backgroundColor: item.color
                }}
              />
              {/* 호버 툴팁 */}
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-gray-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                {item.value.toLocaleString()}
              </div>
            </div>
            <span className="text-xs text-gray-400 mt-2 transform -rotate-45 origin-left w-16 truncate">
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );

  const renderPieChart = () => {
    const total = pieChartData.reduce((sum, item) => sum + item.value, 0);
    let currentAngle = 0;

    return (
      <div className="flex items-center justify-center space-x-8">
        {/* 파이 차트 */}
        <div className="relative">
          <svg width="200" height="200" className="transform -rotate-90">
            {pieChartData.map((item, index) => {
              const percentage = (item.value / total) * 100;
              const angle = (percentage / 100) * 360;
              const startAngle = currentAngle;
              const endAngle = currentAngle + angle;
              
              const x1 = 100 + 80 * Math.cos((startAngle * Math.PI) / 180);
              const y1 = 100 + 80 * Math.sin((startAngle * Math.PI) / 180);
              const x2 = 100 + 80 * Math.cos((endAngle * Math.PI) / 180);
              const y2 = 100 + 80 * Math.sin((endAngle * Math.PI) / 180);
              
              const largeArcFlag = angle > 180 ? 1 : 0;
              
              const pathData = [
                `M 100 100`,
                `L ${x1} ${y1}`,
                `A 80 80 0 ${largeArcFlag} 1 ${x2} ${y2}`,
                'Z'
              ].join(' ');
              
              currentAngle += angle;
              
              return (
                <path
                  key={index}
                  d={pathData}
                  fill={item.color}
                  className="hover:opacity-80 transition-opacity cursor-pointer"
                />
              );
            })}
          </svg>
          
          {/* 중앙 텍스트 */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="text-lg font-bold text-white">{total.toLocaleString()}</div>
              <div className="text-xs text-gray-400">총합</div>
            </div>
          </div>
        </div>

        {/* 범례 */}
        <div className="space-y-2">
          {pieChartData.map((item, index) => (
            <div key={index} className="flex items-center space-x-3">
              <div 
                className="w-4 h-4 rounded"
                style={{ backgroundColor: item.color }}
              />
              <div className="text-sm">
                <div className="text-gray-300 font-medium">{item.label}</div>
                <div className="text-gray-400 text-xs">
                  {item.value.toLocaleString()} ({item.percentage}%)
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // renderChart 함수는 더 이상 필요하지 않음 (각 차트를 직접 렌더링)

  return (
    <div className="space-y-6">
      {/* 차트 설정 */}
      <div className="flex flex-wrap gap-4 p-4 bg-gray-800/30 backdrop-blur-sm rounded-xl border border-gray-600/50">
        {/* 표시 모드 */}
        <div className="flex items-center space-x-2">
          <label className="text-sm font-medium text-gray-300">표시 모드:</label>
          <div className="flex space-x-1">
            <button
              onClick={() => setShowAllCharts(true)}
              className={`px-3 py-1.5 rounded-lg text-sm transition-all duration-200 ${
                showAllCharts
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              📊 모든 차트
            </button>
            <button
              onClick={() => setShowAllCharts(false)}
              className={`px-3 py-1.5 rounded-lg text-sm transition-all duration-200 ${
                !showAllCharts
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              🎯 선택 차트
            </button>
          </div>
        </div>

        {/* 값 필드 선택 */}
        {numericFields.length > 0 && (
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-300">값:</label>
            <select
              value={selectedField}
              onChange={(e) => setSelectedField(e.target.value)}
              className="px-3 py-1.5 bg-gray-700 text-gray-300 rounded-lg text-sm border border-gray-600 focus:border-purple-500 focus:outline-none"
            >
              {numericFields.map(field => (
                <option key={field.key} value={field.key}>{field.label}</option>
              ))}
            </select>
          </div>
        )}

        {/* 그룹 필드 선택 */}
        {textFields.length > 0 && (
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-300">그룹:</label>
            <select
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value)}
              className="px-3 py-1.5 bg-gray-700 text-gray-300 rounded-lg text-sm border border-gray-600 focus:border-purple-500 focus:outline-none"
            >
              <option value="">그룹 없음</option>
              {textFields.map(field => (
                <option key={field.key} value={field.key}>{field.label}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* 차트 영역 */}
      {showAllCharts ? (
        /* 모든 차트 표시 - 스크롤 가능 */
        <div className="space-y-6">
          {/* 막대 차트 */}
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-600/50 p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-semibold text-white flex items-center">
                <span className="mr-2">📊</span>
                막대 차트 - {selectedField && numericFields.find(f => f.key === selectedField)?.label}
              </h3>
              <div className="text-sm text-gray-400">
                {processedData.length}개 데이터 포인트
              </div>
            </div>
            {chartData.length > 0 ? renderBarChart() : (
              <div className="text-center py-12 text-gray-500">
                <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <p>막대 차트를 생성할 수 있는 데이터가 없습니다.</p>
              </div>
            )}
          </div>

          {/* 선형 차트 */}
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-600/50 p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-semibold text-white flex items-center">
                <span className="mr-2">📈</span>
                선형 차트 - {selectedField && numericFields.find(f => f.key === selectedField)?.label}
              </h3>
              <div className="text-sm text-gray-400">
                트렌드 분석
              </div>
            </div>
            {chartData.length > 0 ? renderLineChart() : (
              <div className="text-center py-12 text-gray-500">
                <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
                <p>선형 차트를 생성할 수 있는 데이터가 없습니다.</p>
              </div>
            )}
          </div>

          {/* 파이 차트 */}
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-600/50 p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-semibold text-white flex items-center">
                <span className="mr-2">🥧</span>
                파이 차트 - {selectedField && numericFields.find(f => f.key === selectedField)?.label}
              </h3>
              <div className="text-sm text-gray-400">
                비율 분석
              </div>
            </div>
            {pieChartData.length > 0 ? renderPieChart() : (
              <div className="text-center py-12 text-gray-500">
                <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
                </svg>
                <p>파이 차트를 생성할 수 있는 데이터가 없습니다.</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* 단일 차트 표시 (기존 방식) */
        <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl border border-gray-600/50 p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-semibold text-white flex items-center">
              <span className="mr-2">📊</span>
              {selectedField && numericFields.find(f => f.key === selectedField)?.label} 분석
            </h3>
            <div className="text-sm text-gray-400">
              {processedData.length}개 데이터 포인트
            </div>
          </div>
          
          {/* 차트 타입 선택 (단일 모드에서만) */}
          <div className="mb-4 flex justify-center">
            <div className="flex space-x-1 bg-gray-700/50 rounded-lg p-1">
              {[
                { type: 'bar', icon: '📊', label: '막대' },
                { type: 'line', icon: '📈', label: '선형' },
                { type: 'pie', icon: '🥧', label: '파이' }
              ].map(({ type, icon, label }) => (
                <button
                  key={type}
                  onClick={() => setSingleChartType(type)}
                  className={`px-3 py-1.5 rounded-lg text-sm transition-all duration-200 ${
                    singleChartType === type
                      ? 'bg-purple-600 text-white'
                      : 'bg-gray-600 text-gray-300 hover:bg-gray-500'
                  }`}
                >
                  {icon} {label}
                </button>
              ))}
            </div>
          </div>
          
          {/* 선택된 차트 타입에 따라 렌더링 */}
          {singleChartType === 'bar' && renderBarChart()}
          {singleChartType === 'line' && renderLineChart()}
          {singleChartType === 'pie' && renderPieChart()}
        </div>
      )}

      {/* 통계 요약 */}
      {chartData.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-4 border border-gray-600/50">
            <div className="text-2xl font-bold text-purple-400">{chartData.length}</div>
            <div className="text-sm text-gray-400">카테고리</div>
          </div>
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-4 border border-gray-600/50">
            <div className="text-2xl font-bold text-blue-400">
              {Math.max(...chartData.map(d => d.value)).toLocaleString()}
            </div>
            <div className="text-sm text-gray-400">최대값</div>
          </div>
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-4 border border-gray-600/50">
            <div className="text-2xl font-bold text-green-400">
              {Math.round(chartData.reduce((sum, d) => sum + d.value, 0) / chartData.length).toLocaleString()}
            </div>
            <div className="text-sm text-gray-400">평균값</div>
          </div>
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-4 border border-gray-600/50">
            <div className="text-2xl font-bold text-yellow-400">
              {chartData.reduce((sum, d) => sum + d.value, 0).toLocaleString()}
            </div>
            <div className="text-sm text-gray-400">총합</div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdvancedChart;