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
                <div className={`flex items-center w-full mx-auto bg-gray-900/95 backdrop-blur-sm border border-gray-700/50 rounded-2xl shadow-2xl transition-all duration-300 ${disabled ? 'opacity-50' : 'hover:shadow-purple-500/25 hover:shadow-2xl hover:border-purple-500/50'} ${!disabled ? 'shadow-purple-500/20' : ''}`}>
                    {/* 검색 아이콘 */}
                    <div className="pl-6 pr-4">
                        <svg className={`w-6 h-6 transition-colors duration-200 ${disabled ? 'text-gray-500' : 'text-gray-300'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
                        className="flex-1 py-4 px-2 text-white bg-transparent border-none outline-none text-lg placeholder-gray-400 font-light"
                    />

                    {/* AI 아이콘 */}


                    {/* 로딩 스피너 또는 검색 버튼 */}
                    <div className="pr-4">
                        {isLoading ? (
                            <div className="animate-spin rounded-full h-7 w-7 border-2 border-purple-500 border-t-transparent"></div>
                        ) : (
                            <button
                                type="submit"
                                disabled={disabled || !query.trim()}
                                className="p-3 rounded-xl bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-500 hover:to-purple-600 transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed shadow-lg hover:shadow-purple-500/50 hover:shadow-xl"
                            >
                                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                                </svg>
                            </button>
                        )}
                    </div>
                </div>
            </form>

            {/* 검색 제안 (다크 스타일) */}
            {query && !disabled && (
                <div className="absolute top-full left-0 right-0 mt-2 bg-gray-900/95 backdrop-blur-md border border-gray-700/50 rounded-xl shadow-2xl shadow-purple-500/10 z-10 overflow-hidden">
                    <div className="py-2">
                        <div className="px-6 py-3 hover:bg-gray-800/80 cursor-pointer flex items-center transition-colors duration-150">
                            <svg className="w-4 h-4 text-purple-400 mr-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                            <span className="text-gray-300 font-light">{query}</span>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default SearchBox;