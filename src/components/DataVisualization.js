import React, { useState } from 'react';

const DataVisualization = ({ data, query }) => {
  const [viewType, setViewType] = useState('chart');

  // 더미 차트 데이터 생성
  const generateChartData = () => {
    return Array.from({ length: 6 }, (_, i) => ({
      label: `항목 ${i + 1}`,
      value: Math.floor(Math.random() * 100) + 10,
      color: ['#4285f4', '#ea4335', '#fbbc05', '#34a853', '#9c27b0', '#ff6d01'][i]
    }));
  };

  const chartData = generateChartData();
  const maxValue = Math.max(...chartData.map(d => d.value));

  const ViewTypeButton = ({ type, icon, label, active, onClick }) => (
    <button
      onClick={() => onClick(type)}
      className={`flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
        active 
          ? 'bg-gradient-to-r from-google-blue to-google-purple text-white shadow-lg' 
          : 'bg-white/80 text-gray-600 hover:bg-gray-50 border border-gray-200/50'
      }`}
    >
      <span className="mr-2">{icon}</span>
      {label}
    </button>
  );

  const BarChart = () => (
    <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 shadow-xl border border-gray-200/50">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">📊 데이터 분석 결과</h3>
      <div className="space-y-3">
        {chartData.map((item, index) => (
          <div key={index} className="flex items-center">
            <div className="w-20 text-sm text-gray-600 font-medium">{item.label}</div>
            <div className="flex-1 mx-4">
              <div className="bg-gray-200 rounded-full h-6 relative overflow-hidden">
                <div 
                  className="h-full rounded-full transition-all duration-1000 ease-out"
                  style={{ 
                    width: `${(item.value / maxValue) * 100}%`,
                    backgroundColor: item.color
                  }}
                />
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-xs font-semibold text-white drop-shadow">{item.value}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const TrendChart = () => (
    <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 shadow-xl border border-gray-200/50">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">📈 트렌드 분석</h3>
      <div className="h-48 flex items-end justify-between px-4">
        {chartData.map((item, index) => (
          <div key={index} className="flex flex-col items-center">
            <div 
              className="w-8 rounded-t-lg transition-all duration-1000 ease-out"
              style={{ 
                height: `${(item.value / maxValue) * 160}px`,
                backgroundColor: item.color
              }}
            />
            <span className="text-xs text-gray-600 mt-2 transform -rotate-45 origin-left">{item.label}</span>
          </div>
        ))}
      </div>
      <div className="mt-4 flex items-center justify-center space-x-4 text-sm text-gray-600">
        <div className="flex items-center">
          <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
          <span>증가 추세</span>
        </div>
        <div className="flex items-center">
          <div className="w-3 h-3 bg-red-500 rounded-full mr-2"></div>
          <span>감소 추세</span>
        </div>
      </div>
    </div>
  );

  const TableView = () => (
    <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 shadow-xl border border-gray-200/50">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">📋 상세 데이터</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-3 px-4 font-semibold text-gray-700">항목</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-700">값</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-700">비율</th>
              <th className="text-left py-3 px-4 font-semibold text-gray-700">상태</th>
            </tr>
          </thead>
          <tbody>
            {chartData.map((item, index) => (
              <tr key={index} className="border-b border-gray-100 hover:bg-gray-50/50 transition-colors">
                <td className="py-3 px-4 flex items-center">
                  <div 
                    className="w-3 h-3 rounded-full mr-3"
                    style={{ backgroundColor: item.color }}
                  />
                  {item.label}
                </td>
                <td className="py-3 px-4 font-medium">{item.value}</td>
                <td className="py-3 px-4">{((item.value / maxValue) * 100).toFixed(1)}%</td>
                <td className="py-3 px-4">
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    item.value > 50 ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {item.value > 50 ? '높음' : '보통'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  return (
    <div className="w-full max-w-5xl mx-auto mt-8">
      {/* 시각화 타입 선택 */}
      <div className="flex flex-wrap gap-3 mb-6 justify-center">
        <ViewTypeButton 
          type="chart" 
          icon="📊" 
          label="막대 차트" 
          active={viewType === 'chart'} 
          onClick={setViewType} 
        />
        <ViewTypeButton 
          type="trend" 
          icon="📈" 
          label="트렌드" 
          active={viewType === 'trend'} 
          onClick={setViewType} 
        />
        <ViewTypeButton 
          type="table" 
          icon="📋" 
          label="테이블" 
          active={viewType === 'table'} 
          onClick={setViewType} 
        />
      </div>

      {/* 시각화 컨텐츠 */}
      <div className="transition-all duration-300">
        {viewType === 'chart' && <BarChart />}
        {viewType === 'trend' && <TrendChart />}
        {viewType === 'table' && <TableView />}
      </div>

      {/* 인사이트 요약 */}
      <div className="mt-6 bg-gradient-to-r from-blue-50 to-purple-50 rounded-2xl p-6 border border-blue-200/50">
        <h4 className="text-lg font-semibold text-gray-800 mb-3 flex items-center">
          <span className="mr-2">💡</span>
          주요 인사이트
        </h4>
        <div className="grid md:grid-cols-2 gap-4 text-sm text-gray-700">
          <div className="flex items-start">
            <span className="text-green-500 mr-2">▲</span>
            <span>가장 높은 값: <strong>{Math.max(...chartData.map(d => d.value))}</strong></span>
          </div>
          <div className="flex items-start">
            <span className="text-blue-500 mr-2">📊</span>
            <span>평균값: <strong>{Math.round(chartData.reduce((a, b) => a + b.value, 0) / chartData.length)}</strong></span>
          </div>
          <div className="flex items-start">
            <span className="text-purple-500 mr-2">🎯</span>
            <span>총 데이터 포인트: <strong>{chartData.length}개</strong></span>
          </div>
          <div className="flex items-start">
            <span className="text-orange-500 mr-2">📈</span>
            <span>데이터 범위: <strong>{Math.min(...chartData.map(d => d.value))} - {Math.max(...chartData.map(d => d.value))}</strong></span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DataVisualization;