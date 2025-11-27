import React, { useState, useRef, useEffect } from 'react';

const AIChatInterface = ({ uploadedData, searchQuery, onNewSearch }) => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'ai',
      content: '안녕하세요! 데이터에 대해 궁금한 것이 있으시면 언제든 물어보세요. 자연어로 질문하시면 분석해드릴게요.',
      timestamp: new Date()
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // 메시지 스크롤
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 초기 검색어가 있으면 환영 메시지 업데이트
  useEffect(() => {
    if (searchQuery && uploadedData) {
      setMessages(prev => [
        ...prev.slice(0, 1),
        {
          id: Date.now(),
          type: 'ai',
          content: `"${searchQuery}"에 대한 분석을 완료했습니다. ${uploadedData.length.toLocaleString()}개의 데이터에서 관련 정보를 찾았어요. 추가로 궁금한 점이 있으시면 언제든 물어보세요!`,
          timestamp: new Date()
        }
      ]);
    }
  }, [searchQuery, uploadedData]);

  // AI 응답 시뮬레이션
  const generateAIResponse = async (userMessage) => {
    // 실제 AI API 연동 지점
    const message = userMessage.toLowerCase();
    
    // 데이터 관련 질문 분석
    if (message.includes('얼마나') || message.includes('몇 개') || message.includes('개수')) {
      return `현재 업로드된 데이터는 총 ${uploadedData?.length || 0}개입니다. 이 중에서 "${userMessage}"와 관련된 항목을 찾아보겠습니다.`;
    }
    
    if (message.includes('평균') || message.includes('average')) {
      return `데이터의 평균값을 계산해보겠습니다. 어떤 필드의 평균을 알고 싶으신가요? 예를 들어 "매출의 평균", "나이의 평균" 등으로 구체적으로 질문해주세요.`;
    }
    
    if (message.includes('최대') || message.includes('최고') || message.includes('max')) {
      return `최대값을 찾아보겠습니다. 구체적인 필드명을 알려주시면 더 정확한 분석을 제공할 수 있어요.`;
    }
    
    if (message.includes('트렌드') || message.includes('변화') || message.includes('추세')) {
      return `트렌드 분석을 위해 시간별 데이터를 확인해보겠습니다. 차트 탭에서 선형 차트를 확인하시면 시간에 따른 변화를 볼 수 있어요.`;
    }
    
    if (message.includes('지역') || message.includes('위치') || message.includes('region')) {
      return `지역별 분석을 진행하겠습니다. 필터 패널에서 특정 지역을 선택하거나, 고급 차트에서 지역별 그룹화를 설정해보세요.`;
    }
    
    if (message.includes('나이') || message.includes('연령') || message.includes('age')) {
      return `연령대별 분석이 필요하시군요. 필터에서 나이 범위를 설정하거나, 연령대별 그룹화 차트를 확인해보세요.`;
    }
    
    if (message.includes('비교') || message.includes('차이') || message.includes('compare')) {
      return `비교 분석을 위해 막대 차트나 테이블 뷰를 추천드립니다. 어떤 항목들을 비교하고 싶으신지 구체적으로 알려주세요.`;
    }
    
    if (message.includes('예측') || message.includes('미래') || message.includes('predict')) {
      return `현재 데이터를 바탕으로 한 예측 분석은 추가 개발이 필요한 기능입니다. 현재는 기존 데이터의 트렌드 분석을 통해 인사이트를 제공할 수 있어요.`;
    }
    
    // 기본 응답
    return `"${userMessage}"에 대해 분석해보겠습니다. 현재 ${uploadedData?.length || 0}개의 데이터를 바탕으로 관련 정보를 찾고 있어요. 더 구체적인 질문을 해주시면 더 정확한 답변을 드릴 수 있습니다.`;
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    const query = inputMessage.trim();
    setInputMessage('');
    setIsLoading(true);

    try {
      // RAG 백엔드 호출
      const response = await fetch('http://localhost:8000/rag/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          session_id: 'popup_chat_session', // 팝업 전용 세션 ID
          mode: 'conv'
        })
      });

      if (!response.ok) throw new Error(`RAG 검색 실패: ${response.status}`);
      const data = await response.json();

      // AI 답변 추가
      const aiMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: data.answer || '답변을 생성할 수 없습니다.',
        timestamp: new Date()
      };
      
      setMessages(prev => [...prev, aiMessage]);
      setIsLoading(false);
      
    } catch (error) {
      console.error('AI 응답 생성 오류:', error);
      
      // 백엔드 연결 실패 시 시뮬레이션 응답 사용
      const aiResponse = await generateAIResponse(query);
      const errorMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: aiResponse,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatTime = (timestamp) => {
    return timestamp.toLocaleTimeString('ko-KR', { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const suggestedQuestions = [
    '데이터의 평균값은 얼마인가요?',
    '가장 높은 값을 가진 항목은?',
    '지역별로 어떤 차이가 있나요?',
    '연령대별 분포는 어떻게 되나요?',
    '최근 트렌드는 어떤가요?'
  ];

  return (
    <div className="flex flex-col h-full bg-transparent">
      {/* 헤더는 팝업에서 처리하므로 제거 */}

      {/* 메시지 영역 */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-transparent">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-2xl ${
              message.type === 'user'
                ? 'bg-purple-600 text-white'
                : 'bg-gray-700 text-gray-100'
            }`}>
              <p className="text-sm">{message.content}</p>
              <p className={`text-xs mt-1 ${
                message.type === 'user' ? 'text-purple-200' : 'text-gray-400'
              }`}>
                {formatTime(message.timestamp)}
              </p>
            </div>
          </div>
        ))}
        
        {/* 로딩 인디케이터 */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-700 text-gray-100 px-4 py-2 rounded-2xl max-w-xs">
              <div className="flex items-center space-x-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
                <span className="text-xs text-gray-400">분석 중...</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* 추천 질문 (메시지가 적을 때만 표시) */}
      {messages.length <= 2 && (
        <div className="px-6 py-4 border-t border-gray-600/50 bg-transparent">
          <p className="text-sm text-gray-400 mb-3">💡 이런 질문을 해보세요:</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {suggestedQuestions.map((question, index) => (
              <button
                key={index}
                onClick={() => setInputMessage(question)}
                className="px-3 py-2 bg-gray-700/50 text-gray-300 rounded-lg text-sm hover:bg-gray-600/50 transition-colors text-left"
              >
                {question}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 입력 영역 */}
      <div className="p-6 border-t border-gray-600/50 bg-transparent">
        <div className="flex items-end space-x-2">
          <div className="flex-1">
            <textarea
              ref={inputRef}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="데이터에 대해 궁금한 점을 물어보세요..."
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm text-gray-100 placeholder-gray-400 resize-none"
              rows="1"
              style={{ minHeight: '40px', maxHeight: '100px' }}
            />
          </div>
          <button
            onClick={handleSendMessage}
            disabled={!inputMessage.trim() || isLoading}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-1"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
            <span className="text-sm">전송</span>
          </button>
        </div>
        
        {/* API 연동 상태 표시 */}
        <div className="mt-2 flex items-center justify-between text-xs text-gray-500">
          <span>🤖 AI 분석 엔진 연동 준비</span>
          <span>Enter로 전송</span>
        </div>
      </div>
    </div>
  );
};

export default AIChatInterface;