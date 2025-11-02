import React, { useState, useEffect } from 'react';

const SmartChart = ({ query, data, onDataAnalyzed }) => {
  const [chartData, setChartData] = useState([]);
  const [chartType, setChartType] = useState('bar');
  const [summary, setSummary] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  useEffect(() => {
    if (query && data && data.length > 0) {
      analyzeAndCreateChart();
    }
  }, [query, data]);

  const analyzeAndCreateChart = async () => {
    setIsAnalyzing(true);
    
    // 검색어 분석
    const keywords = query.toLowerCase().split(' ');
    const analysisResult = await analyzeSearchQuery(keywords, data);
    
    setChartData(analysisResult.chartData);
    setChartType(analysisResult.chartType);
    setSummary(analysisResult.summary);
    setIsAnalyzing(false);
    
    // 부모 컴포넌트에 분석 결과 전달
    onDataAnalyzed && onDataAnalyzed(analysisResult);
  };

  const analyzeSearchQuery = async (keywords, data) => {
    // 1. 숫자 필드 찾기
    const numericFields = findNumericFields(data.slice(0, 100));
    
    // 2. 키워드와 매치되는 데이터 찾기
    const matchedData = findMatchingData(keywords, data, numericFields);
    
    // 3. 차트 타입 결정
    const chartType = determineChartType(query, matchedData);
    
    // 4. 차트 데이터 생성
    const chartData = createChartData(matchedData, chartType);
    
    // 5. 요약 통계 생성
    const summary = generateSummary(chartData, query);
    
    return { chartData, chartType, summary };
  };

  const findNumericFields = (sampleData) => {
    if (!sampleData || sampleData.length === 0) return [];
    
    const numericFields = [];
    const firstItem = sampleData[0];
    
    Object.entries(firstItem).forEach(([key, value]) => {
      if (typeof value === 'number') {
        numericFields.push({ field: key, type: 'number' });
      } else if (typeof value === 'string') {
        const numValue = parseFloat(value.replace(/[^\d.-]/g, ''));
        if (!isNaN(numValue)) {
          numericFields.push({ field: key, type: 'string-number' });
        }
      }
    });
    
    return numericFields;
  };

  const findMatchingData = (keywords, data, numericFields) => {
    const matched = [];
    const maxResults = 50; // 차트용 데이터 포인트
    
    for (let i = 0; i < Math.min(data.length, maxResults * 2); i++) {
      const item = data[i];
      const itemString = JSON.stringify(item).toLowerCase();
      
      // 키워드 매치 확인
      const hasMatch = keywords.some(keyword => 
        itemString.includes(keyword) || 
        Object.entries(item).some(([key, value]) => 
          key.toLowerCase().includes(keyword) || 
          String(value).toLowerCase().includes(keyword)
        )
      );
      
      if (hasMatch && matched.length < maxResults) {
        matched.push(item);
      }
    }
    
    return matched;
  };

  const determineChartType = (query, data) => {
    const queryLower = query.toLowerCase();
    
    if (queryLower.includes('트렌드') || queryLower.includes('변화') || queryLower.includes('월별') || queryLower.includes('시간')) {
      return 'line';
    } else if (queryLower.includes('비율') || queryLower.includes('점유율') || queryLower.includes('분포')) {
      return 'pie';
    } else if (queryLower.includes('비교') || queryLower.includes('순위') || queryLower.includes('top')) {
      return 'bar';
    }
    
    return 'bar'; // 기본값
  };

  const createChartData = (matchedData, chartType) => {
    if (!matchedData || matchedData.length === 0) return [];
    
    const chartPoints = [];
    const colors = ['#4285f4', '#ea4335', '#fbbc05', '#34a853', '#9c27b0', '#ff6d01', '#00bcd4', '#795548'];
    
    matchedData.forEach((item, index) => {
      // 라벨 찾기 (문자열 필드 중 가장 적절한 것)
      let label = `항목 ${index + 1}`;
      for (const [key, value] of Object.entries(item)) {
        if (typeof value === 'string' && value.length > 0 && value.length < 30) {
          label = value;
          break;
        }
      }
      
      // 값 찾기 (숫자 필드 중 가장 적절한 것)
      let value = Math.random() * 100; // 기본값
      for (const [key, val] of Object.entries(item)) {
        if (typeof val === 'number' && val > 0) {
          value = val;
          break;
        } else if (typeof val === 'string') {
          const numVal = parseFloat(val.replace(/[^\d.-]/g, ''));
          if (!isNaN(numVal) && numVal > 0) {
            value = numVal;
            break;
          }
        }
      }
      
      chartPoints.push({
        label: label,
        value: value,
        color: colors[index % colors.length],
        originalData: item
      });
    });
    
    return chartPoints.slice(0, 15); // 최대 15개 포인트
  };

  const generateSummary = (chartData, query) => {
    if (!chartData || chartData.length === 0) return null;
    
    const values = chartData.map(d => d.value);
    const total = values.reduce((a, b) => a + b, 0);
    const average = total / values.length;
    const max = Math.max(...values);
    const min = Math.min(...values);
    
    return {
      query,
      total: total.toLocaleString(),
      average: Math.round(average).toLocaleString(),
      max: max.toLocaleString(),
      min: min.toLocaleString(),
      count: chartData.length,
      topItem: chartData.find(d => d.value === max)?.label || 'N/A'
    };
  };

  const renderChart = () => {
    if (!chartData || chartData.length === 0) {
      return (
        <div className="text-center py-12 text-gray-500">
          <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p>검색 결과에서 차트를 생성할 수 있는 데이터를 찾지 못했습니다.</p>
        </div>
      );
    }

    const maxValue = Math.max(...chartData.map(d => d.value));

    if (chartType === 'bar') {
      return (
        <div className="space-y-4">
          {chartData.map((item, index) => (
            <div key={index} className="flex items-center space-x-4">
              <div className="w-24 text-sm font-medium text-gray-700 truncate">
                {item.label}
              </div>
              <div className="flex-1">
                <div className="bg-gray-200 rounded-full h-8 relative overflow-hidden">
                  <div 
                    className="h-full rounded-full transition-all duration-1000 ease-out flex items-center justify-end pr-2"
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
            </div>
          ))}
        </div>
      );
    }

    if (chartType === 'line') {
      return (
        <div className="h-64 flex items-end justify-between px-4 border-b border-gray-200">
          {chartData.map((item, index) => (
            <div key={index} className="flex flex-col items-center">
              <div 
                className="w-6 rounded-t-lg transition-all duration-1000 ease-out"
                style={{ 
                  height: `${(item.value / maxValue) * 200}px`,
                  backgroundColor: item.color
                }}
              />
              <span className="text-xs text-gray-600 mt-2 transform -rotate-45 origin-left w-16 truncate">
                {item.label}
              </span>
            </div>
          ))}
        </div>
      );
    }

    return renderChart(); // 기본값으로 bar 차트
  };

  if (isAnalyzing) {
    return (
      <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-8 shadow-xl border border-gray-200/50">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-google-blue border-t-transparent mr-3"></div>
          <span className="text-gray-600">데이터를 분석하고 차트를 생성하는 중...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 차트 영역 */}
      <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 shadow-xl border border-gray-200/50">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-semibold text-gray-800 flex items-center">
            <span className="mr-2">📊</span>
            "{query}" 분석 결과
          </h3>
          <div className="flex space-x-2">
            <button
              onClick={() => setChartType('bar')}
              className={`px-3 py-1 rounded-lg text-sm ${chartType === 'bar' ? 'bg-google-blue text-white' : 'bg-gray-100 text-gray-600'}`}
            >
              막대
            </button>
            <button
              onClick={() => setChartType('line')}
              className={`px-3 py-1 rounded-lg text-sm ${chartType === 'line' ? 'bg-google-blue text-white' : 'bg-gray-100 text-gray-600'}`}
            >
              선형
            </button>
          </div>
        </div>
        
        {renderChart()}
      </div>

      {/* 요약 통계 */}
      {summary && (
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-2xl p-6 border border-blue-200/50">
          <h4 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
            <span className="mr-2">📈</span>
            주요 통계
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div className="text-center">
              <div className="text-2xl font-bold text-google-blue">{summary.count}</div>
              <div className="text-gray-600">데이터 포인트</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-google-green">{summary.max}</div>
              <div className="text-gray-600">최대값</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-google-yellow">{summary.average}</div>
              <div className="text-gray-600">평균값</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-google-red">{summary.total}</div>
              <div className="text-gray-600">총합</div>
            </div>
          </div>
          <div className="mt-4 p-3 bg-white/50 rounded-lg">
            <p className="text-gray-700">
              <strong>최고 성과:</strong> {summary.topItem} ({summary.max})
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default SmartChart;