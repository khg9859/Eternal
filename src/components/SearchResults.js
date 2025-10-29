import React from 'react';

const SearchResults = ({ results, query, isLoading }) => {
  if (isLoading) {
    return (
      <div className="flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-google-blue"></div>
        <span className="ml-3 text-gray-600">검색 중...</span>
      </div>
    );
  }

  if (!results || results.length === 0) {
    return null;
  }

  return (
    <div className="w-full max-w-4xl mx-auto px-4">
      {/* 검색 정보 */}
      <div className="mb-6 text-sm text-gray-600">
        약 {results.length}개의 결과 (0.42초)
      </div>

      {/* 검색 결과 목록 */}
      <div className="space-y-6">
        {results.map((result, index) => (
          <div key={result.id || index} className="group">
            {/* 결과 헤더 */}
            <div className="mb-2">
              <h3 className="text-xl text-google-blue hover:underline cursor-pointer group-hover:underline">
                {result.title}
              </h3>
              <div className="text-sm text-green-700">
                데이터 레코드 #{result.id}
              </div>
            </div>

            {/* 결과 설명 */}
            <p className="text-gray-700 text-sm leading-relaxed mb-3">
              {result.description}
            </p>

            {/* 데이터 요약 */}
            {result.data && (
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200/50 rounded-xl p-5 text-sm">
                <div className="text-gray-700 mb-4 font-semibold flex items-center">
                  <span className="mr-2">📊</span>
                  데이터 인사이트
                </div>
                <div className="space-y-3 text-gray-700">
                  <div className="flex items-start">
                    <span className="text-blue-500 mr-3 mt-0.5">📋</span>
                    <div>
                      <strong className="text-gray-800">데이터 항목:</strong> {result.data.name || '데이터 항목'}
                      {result.data.period && <span className="text-gray-500 ml-2">({result.data.period})</span>}
                    </div>
                  </div>
                  
                  <div className="flex items-start">
                    <span className="text-green-500 mr-3 mt-0.5">💰</span>
                    <div>
                      <strong className="text-gray-800">측정값:</strong> 
                      <span className="ml-2 font-mono text-lg text-green-600">
                        {typeof result.data.value === 'number' && result.data.value > 1000 
                          ? result.data.value.toLocaleString() 
                          : result.data.value}
                        {result.data.category === '매출' && '원'}
                        {result.data.category === '고객' && '점'}
                      </span>
                    </div>
                  </div>

                  {result.data.trend && (
                    <div className="flex items-start">
                      <span className={`mr-3 mt-0.5 ${
                        result.data.trend === '상승' ? 'text-green-500' : 
                        result.data.trend === '하락' ? 'text-red-500' : 'text-blue-500'
                      }`}>
                        {result.data.trend === '상승' ? '📈' : result.data.trend === '하락' ? '📉' : '📊'}
                      </span>
                      <div>
                        <strong className="text-gray-800">트렌드:</strong> 
                        <span className={`ml-2 px-2 py-1 rounded-full text-xs font-medium ${
                          result.data.trend === '상승' ? 'bg-green-100 text-green-700' :
                          result.data.trend === '하락' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'
                        }`}>
                          {result.data.trend}
                        </span>
                      </div>
                    </div>
                  )}

                  <div className="flex items-start">
                    <span className="text-purple-500 mr-3 mt-0.5">🔍</span>
                    <div>
                      <strong className="text-gray-800">AI 분석:</strong> 
                      <span className="ml-2">
                        {result.data.category === '매출' && result.data.value > 2000000 && 
                          "매출 성과가 목표치를 상회하고 있습니다. 지속적인 성장 추세를 보이고 있어 긍정적입니다."}
                        {result.data.category === '고객' && result.data.value > 80 && 
                          "고객 만족도가 우수한 수준입니다. 현재 서비스 품질을 유지하는 것이 중요합니다."}
                        {result.data.category === '지역' && 
                          "해당 지역의 성과가 전국 평균을 상회하고 있습니다. 지역 특성을 활용한 전략이 효과적입니다."}
                        {(!result.data.category || result.data.category === '일반') && 
                          `현재 수치는 ${result.data.value > 500 ? '높은' : result.data.value > 200 ? '보통' : '낮은'} 수준으로 평가됩니다.`}
                      </span>
                    </div>
                  </div>

                  {result.data.category && (
                    <div className="flex items-start">
                      <span className="text-orange-500 mr-3 mt-0.5">🏷️</span>
                      <div>
                        <strong className="text-gray-800">카테고리:</strong> 
                        <span className="ml-2 px-2 py-1 bg-orange-100 text-orange-700 rounded-full text-xs font-medium">
                          {result.data.category}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* 매치된 필드들 표시 (실제 JSON 데이터용) */}
                  {result.data.matchedFields && result.data.matchedFields.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-gray-200">
                      <div className="text-gray-600 text-xs font-medium mb-2">매치된 데이터 필드:</div>
                      <div className="space-y-1">
                        {result.data.matchedFields.map(([key, value], index) => (
                          <div key={index} className="flex items-start text-xs">
                            <span className="text-blue-500 mr-2">•</span>
                            <span className="font-medium text-gray-700 mr-2">{key}:</span>
                            <span className="text-gray-600 break-all">{String(value).substring(0, 100)}{String(value).length > 100 ? '...' : ''}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 액션 버튼들 */}
            <div className="mt-3 flex space-x-4 text-sm">
              <button className="text-google-blue hover:underline">
                전체 데이터 보기
              </button>
              <button className="text-google-blue hover:underline">
                JSON 다운로드
              </button>
              <button className="text-google-blue hover:underline">
                관련 데이터 찾기
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* 페이지네이션 (구글 스타일) */}
      <div className="flex justify-center mt-12 mb-8">
        <div className="flex items-center space-x-2">
          <button className="px-3 py-2 text-google-blue hover:bg-gray-100 rounded">
            이전
          </button>
          
          <div className="flex space-x-1">
            {[1, 2, 3, 4, 5].map((page) => (
              <button
                key={page}
                className={`w-10 h-10 rounded-full flex items-center justify-center text-sm ${
                  page === 1 
                    ? 'bg-google-blue text-white' 
                    : 'text-google-blue hover:bg-gray-100'
                }`}
              >
                {page}
              </button>
            ))}
          </div>
          
          <button className="px-3 py-2 text-google-blue hover:bg-gray-100 rounded">
            다음
          </button>
        </div>
      </div>
    </div>
  );
};

export default SearchResults;