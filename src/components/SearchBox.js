import React, { useState } from 'react';

const SearchBox = ({ onSearch, isLoading, disabled }) => {
    const [query, setQuery] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (query.trim() && !disabled) {
            onSearch(query);
        }
    };

    const handleInputChange = (e) => {
        setQuery(e.target.value);
    };

    return (
        <div className="relative">
            <form onSubmit={handleSubmit} className="relative">
                <div className={`flex items-center w-full mx-auto bg-white/90 backdrop-blur-sm border border-gray-200/50 rounded-2xl shadow-2xl hover:shadow-3xl transition-all duration-300 ${disabled ? 'opacity-50' : 'hover:border-google-blue/30'}`}>
                    {/* 검색 아이콘 */}
                    <div className="pl-6 pr-4">
                        <svg className={`w-6 h-6 transition-colors duration-200 ${disabled ? 'text-gray-300' : 'text-google-blue'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                    </div>

                    {/* 입력 필드 */}
                    <input
                        type="text"
                        value={query}
                        onChange={handleInputChange}
                        placeholder={disabled ? "먼저 CSV 또는 Excel 파일을 업로드하세요" : "자연어로 데이터를 검색하세요..."}
                        disabled={disabled}
                        className="flex-1 py-4 px-2 text-gray-800 bg-transparent border-none outline-none text-lg placeholder-gray-400 font-light"
                    />

                    {/* AI 아이콘 */}
                    {!disabled && (
                        <div className="px-3">
                            <div className="w-8 h-8 bg-gradient-to-br from-google-blue to-google-purple rounded-lg flex items-center justify-center">
                                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                            </div>
                        </div>
                    )}

                    {/* 로딩 스피너 또는 검색 버튼 */}
                    <div className="pr-6">
                        {isLoading ? (
                            <div className="animate-spin rounded-full h-7 w-7 border-2 border-google-blue border-t-transparent"></div>
                        ) : (
                            <button
                                type="submit"
                                disabled={disabled || !query.trim()}
                                className="p-2.5 rounded-xl bg-gradient-to-r from-google-blue to-google-purple hover:from-google-blue/90 hover:to-google-purple/90 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-200 shadow-lg hover:shadow-xl"
                            >
                                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                                </svg>
                            </button>
                        )}
                    </div>
                </div>
            </form>

            {/* 검색 제안 (구글 스타일) */}
            {query && !disabled && (
                <div className="absolute top-full left-0 right-0 mt-2 bg-white/95 backdrop-blur-md border border-gray-200/50 rounded-xl shadow-2xl z-10 overflow-hidden">
                    <div className="py-2">
                        <div className="px-6 py-3 hover:bg-gray-50/80 cursor-pointer flex items-center transition-colors duration-150">
                            <svg className="w-4 h-4 text-google-blue mr-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                            <span className="text-gray-700 font-light">{query}</span>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default SearchBox;