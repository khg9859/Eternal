import React from 'react';

const Logo = ({ size = 'large' }) => {
  const sizeClasses = {
    small: 'w-32 h-16',
    medium: 'w-48 h-24',
    large: 'w-64 h-32'
  };

  return (
    <div className={`${sizeClasses[size]} mx-auto mb-6`}>
      <svg viewBox="0 0 400 160" className="w-full h-full">
        {/* 배경 그라데이션 */}
        <defs>
          <linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#4285f4" stopOpacity="0.1" />
            <stop offset="50%" stopColor="#ea4335" stopOpacity="0.1" />
            <stop offset="100%" stopColor="#9c27b0" stopOpacity="0.1" />
          </linearGradient>
          
          <linearGradient id="textGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#4285f4" />
            <stop offset="25%" stopColor="#ea4335" />
            <stop offset="50%" stopColor="#fbbc05" />
            <stop offset="75%" stopColor="#34a853" />
            <stop offset="100%" stopColor="#9c27b0" />
          </linearGradient>

          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge> 
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        {/* 배경 원형들 */}
        <circle cx="80" cy="40" r="20" fill="#4285f4" opacity="0.1" />
        <circle cx="320" cy="120" r="25" fill="#ea4335" opacity="0.1" />
        <circle cx="200" cy="30" r="15" fill="#34a853" opacity="0.1" />
        <circle cx="350" cy="50" r="18" fill="#9c27b0" opacity="0.1" />

        {/* 데이터 아이콘들 */}
        <g opacity="0.3">
          {/* 차트 아이콘 */}
          <rect x="30" y="100" width="8" height="30" fill="#4285f4" rx="2" />
          <rect x="42" y="90" width="8" height="40" fill="#ea4335" rx="2" />
          <rect x="54" y="110" width="8" height="20" fill="#34a853" rx="2" />
          
          {/* 검색 아이콘 */}
          <circle cx="340" cy="100" r="12" fill="none" stroke="#9c27b0" strokeWidth="2" />
          <line x1="349" y1="109" x2="360" y2="120" stroke="#9c27b0" strokeWidth="2" strokeLinecap="round" />
        </g>

        {/* 메인 텍스트 */}
        <text x="200" y="90" textAnchor="middle" className="text-4xl font-light" fill="url(#textGradient)" filter="url(#glow)">
          DataSearch
        </text>
        
        {/* 서브 텍스트 */}
        <text x="200" y="115" textAnchor="middle" className="text-sm" fill="#6b7280" opacity="0.8">
          AI-Powered Data Discovery
        </text>

        {/* 장식적인 라인 */}
        <line x1="120" y1="130" x2="280" y2="130" stroke="url(#textGradient)" strokeWidth="2" strokeLinecap="round" opacity="0.6" />
      </svg>
    </div>
  );
};

export default Logo;