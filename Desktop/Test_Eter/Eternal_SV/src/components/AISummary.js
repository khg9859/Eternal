import { useState, useEffect } from "react";

export default function AISummary({ query, aiSummary }) {
  const staticSummary = [`"${query}"에 대한 분석 결과를 불러오는 중입니다.`];
  const [summary, setSummary] = useState(staticSummary);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (aiSummary) {
      if (typeof aiSummary === 'string') {
        const sentences = aiSummary.split(/[.!?]\s+/).filter(s => s.trim()).map(s => s.trim() + '.');
        setSummary(sentences.length > 0 ? sentences : [aiSummary]);
      } else if (Array.isArray(aiSummary)) {
        setSummary(aiSummary);
      }
    } else {
      setSummary(staticSummary);
    }
  }, [aiSummary, query]);

  return (
    <div className="relative mb-10 p-[2px] rounded-2xl overflow-hidden bg-gradient-to-r from-blue-400 via-indigo-400 to-sky-500 dark:from-gray-700 dark:via-gray-800 dark:to-gray-900 animate-gradient-x shadow-[0_0_20px_rgba(120,150,255,0.25)] dark:shadow-[0_0_20px_rgba(0,0,0,0.5)]">
      <div className="bg-white/90 dark:bg-[#1E2028]/80 backdrop-blur-2xl rounded-2xl p-8 transition-all duration-300">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-2 h-10 bg-gradient-to-b from-blue-400 to-indigo-500 dark:from-gray-500 dark:to-gray-700 rounded-full" />
          <h3 className="text-2xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-500 via-indigo-500 to-sky-600 dark:from-gray-200 dark:via-gray-300 dark:to-gray-100">
            AI 요약 분석 결과
          </h3>
        </div>

        {isLoading ? (
          <p className="text-gray-600 dark:text-gray-400 animate-pulse">요약 분석 중입니다...</p>
        ) : error ? (
          <p className="text-red-500 text-sm">{error}</p>
        ) : (
          <ul className="space-y-3 text-gray-800 dark:text-gray-100">
            {summary.map((line, i) => (
              <li key={i} className="group relative overflow-hidden px-4 py-2 rounded-xl bg-gray-50 dark:bg-gray-800/60 border border-gray-200 dark:border-gray-700 transition-all duration-500 shadow-sm animate-fadeInUp" style={{ animationDelay: `${i * 0.15}s` }}>
                {line}
              </li>
            ))}
          </ul>
        )}

        <div className="mt-8 h-[2px] bg-gradient-to-r from-transparent via-blue-400/50 to-transparent dark:via-gray-500/40" />
      </div>

      <style jsx>{`
        @keyframes gradient-x {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }
        .animate-gradient-x {
          background-size: 200% 200%;
          animation: gradient-x 6s ease infinite;
        }
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeInUp {
          animation: fadeInUp 0.6s ease forwards;
        }
      `}</style>
    </div>
  );
}
