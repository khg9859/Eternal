import React, { useState, useEffect, useMemo, useRef } from 'react';

const AdvancedChart = ({ query, filters = {} }) => {
  const [selectedField, setSelectedField] = useState('');
  const [groupBy, setGroupBy] = useState('');
  const [apiData, setApiData] = useState([]);
  const [animationTrigger, setAnimationTrigger] = useState(0); // 애니메이션 트리거
  const [isAnimating, setIsAnimating] = useState(false);
  const [showAllCharts, setShowAllCharts] = useState(true); // 모든 차트 표시 여부
  const [singleChartType, setSingleChartType] = useState('bar'); // 단일 차트 타입
  const chartRef = useRef(null);

  // API에서 데이터 가져오기
  useEffect(() => {
    const generateDummyApiData = (query) => {
      const dummyData = [];
      
      for (let i = 0; i < 20; i++) {
        dummyData.push({
          q_title: `${query} 관련 질문 ${i + 1}`,
          codebook_id: `dummy_${i}`,
          answers: [
            { answer: `답변 ${i + 1}-1`, count: Math.floor(Math.random() * 50) + 10 },
            { answer: `답변 ${i + 1}-2`, count: Math.floor(Math.random() * 30) + 5 }
          ]
        });
      }
      
      return dummyData;
    };

    const fetchApiData = async () => {
      try {
        const response = await fetch(`http://localhost:8000/search/questions`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query: query,
            limit: 100
          })
        });
  
        if (response.ok) {
          const data = await response.json();
          setApiData(data.results);
        } else {
          // API 실패 시 더미 데이터 사용
          setApiData(generateDummyApiData(query));
        }
      } catch (error) {
        console.error('API fetch failed:', error);
        setApiData(generateDummyApiData(query));
      }
    };

    if (query) {
      fetchApiData();
    }
  }, [query]);

  // 데이터 분석 및 필드 추출
  const { numericFields, textFields, processedData } = useMemo(() => {
    if (!apiData || apiData.length === 0) return { numericFields: [], textFields: [], processedData: [] };

    // API 데이터를 차트용 데이터로 변환
    let filtered = apiData.map((item, index) => ({
      id: index,
      title: item.q_title,
      category: item.codebook_id.includes('w2_') ? 'Welcome 2nd' : 
                item.codebook_id.includes('qp') ? 'Q-Poll' : 'General',
      answer_count: item.answers ? item.answers.length : 0,
      total_responses: item.answers ? item.answers.reduce((sum, ans) => sum + (ans.count || 0), 0) : 0,
      avg_response: item.answers && item.answers.length > 0 ? 
                   item.answers.reduce((sum, ans) => sum + (ans.count || 0), 0) / item.answers.length : 0
    }));

    // 필드 분석 - API 데이터 구조에 맞게 수정
    const numericFields = [
      { key: 'answer_count', label: '답변 개수' },
      { key: 'total_responses', label: '총 응답 수' },
      { key: 'avg_response', label: '평균 응답 수' }
    ];
    
    const textFields = [
      { key: 'category', label: '카테고리' },
      { key: 'title', label: '질문 제목' }
    ];

    // 더미 필드 추가 (차트 표시용)
    if (filtered.length === 0) {
      for (let i = 0; i < 10; i++) {
        filtered.push({
          id: i,
          title: `${query} 관련 항목 ${i + 1}`,
          category: i % 3 === 0 ? 'Welcome 2nd' : i % 3 === 1 ? 'Q-Poll' : 'General',
          answer_count: Math.floor(Math.random() * 10) + 1,
          total_responses: Math.floor(Math.random() * 100) + 10,
          avg_response: Math.floor(Math.random() * 20) + 5
        });
      }
    }

    return { numericFields, textFields, processedData: filtered.slice(0, 100) };
  }, [apiData, query]);

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

  // 애니메이션 트리거
  useEffect(() => {
    if (chartData.length > 0) {
      setIsAnimating(true);
      setAnimationTrigger(prev => prev + 1);
      
      // 애니메이션 완료 후 상태 리셋
      const timer = setTimeout(() => {
        setIsAnimating(false);
      }, 1500);
      
      return () => clearTimeout(timer);
    }
  }, [chartData.length, selectedField, groupBy]);

  const renderBarChart = () => (
    <div className="space-y-3" ref={chartRef}>
      {chartData.map((item, index) => (
        <div 
          key={`${animationTrigger}-${index}`} 
          className="flex items-center space-x-4 opacity-0 animate-fade-in-up"
          style={{ 
            animationDelay: `${index * 100}ms`,
            animationFillMode: 'forwards'
          }}
        >
          <div className="w-32 text-sm font-medium text-gray-300 truncate">
            {item.label}
          </div>
          <div className="flex-1">
            <div className="bg-gray-700/50 rounded-full h-8 relative overflow-hidden shadow-inner">
              {/* 배경 글로우 효과 */}
              <div 
                className="absolute inset-0 rounded-full opacity-20"
                style={{ 
                  background: `linear-gradient(90deg, transparent, ${item.color})`
                }}
              />
              
              {/* 메인 바 */}
              <div 
                className="h-full rounded-full flex items-center justify-end pr-3 relative overflow-hidden animate-bar-grow shadow-lg"
                style={{ 
                  width: isAnimating ? '0%' : `${(item.value / maxValue) * 100}%`,
                  backgroundColor: item.color,
                  background: `linear-gradient(90deg, ${item.color}dd, ${item.color})`,
                  animationDelay: `${index * 150 + 300}ms`,
                  animationDuration: '1200ms',
                  animationFillMode: 'forwards',
                  boxShadow: `0 0 20px ${item.color}40`
                }}
              >
                {/* 반짝이는 효과 */}
                <div 
                  className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-30 animate-shimmer"
                  style={{ 
                    animationDelay: `${index * 150 + 800}ms`,
                    animationDuration: '2000ms'
                  }}
                />
                
                {/* 값 표시 */}
                <span 
                  className="text-white text-xs font-semibold relative z-10 opacity-0 animate-fade-in"
                  style={{ 
                    animationDelay: `${index * 150 + 1000}ms`,
                    animationFillMode: 'forwards',
                    textShadow: '0 1px 2px rgba(0,0,0,0.5)'
                  }}
                >
                  {item.value.toLocaleString()}
                </span>
              </div>
              
              {/* 펄스 효과 */}
              <div 
                className="absolute inset-0 rounded-full animate-pulse-glow"
                style={{ 
                  backgroundColor: item.color,
                  animationDelay: `${index * 150 + 500}ms`,
                  animationDuration: '1500ms'
                }}
              />
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
        <span className="opacity-0 animate-fade-in" style={{ animationDelay: '200ms', animationFillMode: 'forwards' }}>
          {maxValue.toLocaleString()}
        </span>
        <span className="opacity-0 animate-fade-in" style={{ animationDelay: '300ms', animationFillMode: 'forwards' }}>
          {Math.round(maxValue * 0.75).toLocaleString()}
        </span>
        <span className="opacity-0 animate-fade-in" style={{ animationDelay: '400ms', animationFillMode: 'forwards' }}>
          {Math.round(maxValue * 0.5).toLocaleString()}
        </span>
        <span className="opacity-0 animate-fade-in" style={{ animationDelay: '500ms', animationFillMode: 'forwards' }}>
          {Math.round(maxValue * 0.25).toLocaleString()}
        </span>
        <span className="opacity-0 animate-fade-in" style={{ animationDelay: '600ms', animationFillMode: 'forwards' }}>
          0
        </span>
      </div>
      
      {/* 그리드 라인 */}
      <div className="absolute left-8 right-4 top-0 h-full">
        {[0, 0.25, 0.5, 0.75, 1].map((ratio, index) => (
          <div 
            key={index}
            className="absolute w-full border-t border-gray-600/30 opacity-0 animate-fade-in"
            style={{ 
              bottom: `${ratio * 100}%`,
              animationDelay: `${700 + index * 100}ms`,
              animationFillMode: 'forwards'
            }}
          />
        ))}
      </div>
      
      {/* 데이터 포인트 */}
      <div className="flex-1 ml-8 flex items-end justify-between relative">
        {/* 연결선 */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none">
          <path
            d={`M ${chartData.map((item, index) => 
              `${(index / (chartData.length - 1)) * 100}% ${100 - (item.value / maxValue) * 100}%`
            ).join(' L ')}`}
            stroke="#8b5cf6"
            strokeWidth="2"
            fill="none"
            className="opacity-0 animate-draw-line"
            style={{ 
              animationDelay: '1000ms',
              animationDuration: '2000ms',
              animationFillMode: 'forwards',
              strokeDasharray: '1000',
              strokeDashoffset: '1000'
            }}
          />
        </svg>
        
        {chartData.map((item, index) => (
          <div 
            key={`${animationTrigger}-${index}`} 
            className="flex flex-col items-center group relative"
          >
            <div className="relative">
              {/* 데이터 포인트 */}
              <div 
                className="w-3 h-3 rounded-full border-2 border-white opacity-0 animate-bounce-in"
                style={{ 
                  backgroundColor: item.color,
                  boxShadow: `0 0 15px ${item.color}80`,
                  animationDelay: `${1200 + index * 100}ms`,
                  animationFillMode: 'forwards'
                }}
              />
              
              {/* 세로 바 */}
              <div 
                className="w-2 rounded-t-lg absolute left-1/2 transform -translate-x-1/2 bottom-0 animate-line-grow"
                style={{ 
                  height: isAnimating ? '0px' : `${(item.value / maxValue) * 200}px`,
                  backgroundColor: `${item.color}60`,
                  animationDelay: `${800 + index * 150}ms`,
                  animationDuration: '1000ms',
                  animationFillMode: 'forwards'
                }}
              />
              
              {/* 호버 툴팁 */}
              <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-800/90 backdrop-blur-sm text-white text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-all duration-200 whitespace-nowrap border border-gray-600/50">
                <div className="font-semibold">{item.value.toLocaleString()}</div>
                <div className="text-gray-300 text-xs">{item.label}</div>
                {/* 툴팁 화살표 */}
                <div className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-800/90"></div>
              </div>
            </div>
            
            {/* X축 라벨 */}
            <span 
              className="text-xs text-gray-400 mt-3 transform -rotate-45 origin-left w-16 truncate opacity-0 animate-fade-in"
              style={{ 
                animationDelay: `${1400 + index * 50}ms`,
                animationFillMode: 'forwards'
              }}
            >
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
          {/* 배경 원 */}
          <div className="w-52 h-52 rounded-full bg-gray-700/30 absolute inset-0 animate-pulse-ring" 
               style={{ animationDelay: '200ms' }} />
          
          <svg width="200" height="200" className="transform -rotate-90 relative z-10">
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
                <g key={`${animationTrigger}-${index}`}>
                  {/* 메인 슬라이스 */}
                  <path
                    d={pathData}
                    fill={item.color}
                    className="hover:opacity-80 transition-all duration-300 cursor-pointer animate-pie-slice"
                    style={{ 
                      animationDelay: `${500 + index * 200}ms`,
                      animationDuration: '800ms',
                      animationFillMode: 'forwards',
                      transformOrigin: '100px 100px',
                      filter: `drop-shadow(0 0 8px ${item.color}60)`
                    }}
                    onMouseEnter={(e) => {
                      e.target.style.transform = 'scale(1.05)';
                      e.target.style.filter = `drop-shadow(0 0 15px ${item.color}80)`;
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.transform = 'scale(1)';
                      e.target.style.filter = `drop-shadow(0 0 8px ${item.color}60)`;
                    }}
                  />
                  
                  {/* 글로우 효과 */}
                  <path
                    d={pathData}
                    fill="none"
                    stroke={item.color}
                    strokeWidth="2"
                    className="opacity-50 animate-glow-pulse"
                    style={{ 
                      animationDelay: `${700 + index * 200}ms`,
                      filter: `blur(2px)`
                    }}
                  />
                </g>
              );
            })}
          </svg>
          
          {/* 중앙 텍스트 */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center opacity-0 animate-fade-in" style={{ animationDelay: '1200ms', animationFillMode: 'forwards' }}>
              <div className="text-2xl font-bold text-white animate-count-up">{total.toLocaleString()}</div>
              <div className="text-sm text-gray-400">총합</div>
            </div>
          </div>
          
          {/* 중앙 글로우 */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-20 h-20 rounded-full bg-purple-500/20 animate-pulse-glow" 
                 style={{ animationDelay: '1000ms' }} />
          </div>
        </div>

        {/* 범례 */}
        <div className="space-y-3">
          {pieChartData.map((item, index) => (
            <div 
              key={`${animationTrigger}-${index}`} 
              className="flex items-center space-x-3 opacity-0 animate-slide-in-right"
              style={{ 
                animationDelay: `${800 + index * 150}ms`,
                animationFillMode: 'forwards'
              }}
            >
              <div 
                className="w-4 h-4 rounded shadow-lg animate-bounce-in"
                style={{ 
                  backgroundColor: item.color,
                  boxShadow: `0 0 10px ${item.color}60`,
                  animationDelay: `${900 + index * 150}ms`
                }}
              />
              <div className="text-sm">
                <div className="text-gray-300 font-medium">{item.label}</div>
                <div className="text-gray-400 text-xs">
                  <span className="animate-count-up">{item.value.toLocaleString()}</span> 
                  <span className="ml-1">({item.percentage}%)</span>
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