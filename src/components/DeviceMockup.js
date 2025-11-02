import React from 'react';

const DeviceMockup = ({ children, type = 'laptop' }) => {
  if (type === 'laptop') {
    return (
      <div className="relative mx-auto">
        {/* 노트북 스크린 */}
        <div className="relative bg-gray-800 rounded-t-3xl p-4 shadow-2xl">
          {/* 상단 바 (카메라, 센서) */}
          <div className="flex justify-center mb-3">
            <div className="w-3 h-3 bg-gray-600 rounded-full"></div>
          </div>
          
          {/* 스크린 영역 */}
          <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-xl overflow-hidden" style={{ aspectRatio: '16/10' , minHeight : '600px', minWidth : '1200px'}}>
            <div className="h-full flex flex-col">
              {/* 브라우저 상단 바 */}
              <div className="bg-gray-700 px-6 py-3 flex items-center space-x-3">
                <div className="flex space-x-2">
                  <div className="w-4 h-4 bg-red-500 rounded-full"></div>
                  <div className="w-4 h-4 bg-yellow-500 rounded-full"></div>
                  <div className="w-4 h-4 bg-green-500 rounded-full"></div>
                </div>
                <div className="flex-1 bg-gray-600 rounded-lg px-4 py-2 ml-6">
                  <span className="text-gray-300 text-sm">Search Servey Result _ Eternal</span>
                </div>
              </div>
              
              {/* 컨텐츠 영역 */}
              <div className="flex-1 p-12 flex items-center justify-center">
                {children}
              </div>
            </div>
          </div>
        </div>
        
        {/* 노트북 베이스 */}
        <div className="bg-gray-700 h-6 rounded-b-3xl shadow-lg relative">
          <div className="absolute inset-x-0 top-2 h-1 bg-gray-600 rounded-full mx-12"></div>
        </div>
      </div>
    );
  }

  if (type === 'tablet') {
    return (
      <div className="relative mx-auto">
        {/* 태블릿 프레임 */}
        <div className="bg-gray-800 rounded-3xl p-4 shadow-2xl" style={{ aspectRatio: '4/3' }}>
          {/* 스크린 영역 */}
          <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-2xl h-full overflow-hidden">
            <div className="h-full flex flex-col">
              {/* 상단 상태바 */}
              <div className="bg-gray-700/50 px-6 py-2 flex justify-between items-center">
                <div className="flex items-center space-x-2">
                  <div className="w-1 h-1 bg-white rounded-full"></div>
                  <div className="w-1 h-1 bg-white rounded-full"></div>
                  <div className="w-1 h-1 bg-white rounded-full"></div>
                </div>
                <span className="text-white text-xs">DataSearch</span>
                <div className="flex items-center space-x-1">
                  <div className="w-4 h-2 border border-white rounded-sm">
                    <div className="w-3 h-1 bg-green-500 rounded-sm"></div>
                  </div>
                </div>
              </div>
              
              {/* 컨텐츠 영역 */}
              <div className="flex-1 p-6 flex items-center justify-center">
                {children}
              </div>
            </div>
          </div>
        </div>
        
        {/* 홈 버튼 */}
        <div className="absolute bottom-2 left-1/2 transform -translate-x-1/2 w-12 h-1 bg-gray-600 rounded-full"></div>
      </div>
    );
  }

  if (type === 'phone') {
    return (
      <div className="relative mx-auto">
        {/* 폰 프레임 */}
        <div className="bg-gray-800 rounded-3xl p-2 shadow-2xl" style={{ aspectRatio: '9/19.5' }}>
          {/* 노치 */}
          <div className="bg-gray-800 h-6 rounded-t-3xl flex justify-center items-center">
            <div className="w-16 h-1 bg-gray-600 rounded-full"></div>
          </div>
          
          {/* 스크린 영역 */}
          <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-2xl h-full overflow-hidden">
            <div className="h-full flex flex-col">
              {/* 상단 상태바 */}
              <div className="px-4 py-2 flex justify-between items-center">
                <span className="text-white text-xs font-medium">9:41</span>
                <div className="flex items-center space-x-1">
                  <div className="w-4 h-2 border border-white rounded-sm">
                    <div className="w-3 h-1 bg-green-500 rounded-sm"></div>
                  </div>
                </div>
              </div>
              
              {/* 컨텐츠 영역 */}
              <div className="flex-1 p-4 flex items-center justify-center">
                {children}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return <div>{children}</div>;
};

export default DeviceMockup;