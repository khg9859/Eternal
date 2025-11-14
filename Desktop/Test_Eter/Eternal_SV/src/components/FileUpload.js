import React, { useState, useRef } from 'react';
import * as XLSX from 'xlsx';

const FileUpload = ({ onFileUpload }) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      handleFile(file);
    }
  };

  const handleFile = (file) => {
    const fileName = file.name.toLowerCase();
    const isCSV = fileName.endsWith('.csv');
    const isXLSX = fileName.endsWith('.xlsx') || fileName.endsWith('.xls');
    const isJSON = fileName.endsWith('.json');
    
    if (!isCSV && !isXLSX && !isJSON) {
      setUploadStatus('CSV, Excel 또는 JSON 파일만 업로드 가능합니다.');
      return;
    }

    setUploadStatus('파일을 처리 중입니다...');
    
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        let jsonData = [];
        
        if (isJSON) {
          // JSON 파일 처리
          try {
            const jsonContent = e.target.result;
            const parsedData = JSON.parse(jsonContent);
            
            // 배열인지 확인
            if (Array.isArray(parsedData)) {
              jsonData = parsedData;
            } else if (typeof parsedData === 'object' && parsedData !== null) {
              // 객체인 경우 배열로 변환
              jsonData = [parsedData];
            } else {
              throw new Error('올바른 JSON 형식이 아닙니다.');
            }
          } catch (jsonError) {
            console.error('JSON 파싱 오류:', jsonError);
            setUploadStatus('JSON 파일 형식이 올바르지 않습니다.');
            return;
          }
        } else if (isCSV) {
          // CSV 파일 처리
          const csvData = e.target.result;
          const lines = csvData.split('\n');
          const headers = lines[0].split(',').map(h => h.trim());
          
          for (let i = 1; i < lines.length; i++) {
            if (lines[i].trim()) {
              const values = lines[i].split(',').map(v => v.trim());
              const obj = {};
              headers.forEach((header, index) => {
                obj[header] = values[index] || '';
              });
              jsonData.push(obj);
            }
          }
        } else if (isXLSX) {
          // Excel 파일 처리
          const data = new Uint8Array(e.target.result);
          const workbook = XLSX.read(data, { type: 'array' });
          const sheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[sheetName];
          jsonData = XLSX.utils.sheet_to_json(worksheet);
        }
        
        setUploadStatus(`성공적으로 ${jsonData.length}개의 레코드를 로드했습니다.`);
        onFileUpload(jsonData);
      } catch (error) {
        console.error('파일 처리 오류:', error);
        setUploadStatus('파일 처리 중 오류가 발생했습니다.');
      }
    };
    
    if (isCSV || isJSON) {
      reader.readAsText(file);
    } else {
      reader.readAsArrayBuffer(file);
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="w-full mx-auto">
      <div
        className={`border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-300 backdrop-blur-sm ${
          isDragOver 
            ? 'border-google-blue bg-gradient-to-br from-blue-50/80 to-purple-50/80 shadow-2xl scale-105' 
            : 'border-gray-300/60 hover:border-google-blue/50 hover:bg-gradient-to-br hover:from-blue-50/40 hover:to-purple-50/40 hover:shadow-xl'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls,.json"
          onChange={handleFileSelect}
          className="hidden"
        />
        
        <div className="flex flex-col items-center">
          <div className="w-20 h-20 bg-gradient-to-br from-google-blue to-google-purple rounded-2xl flex items-center justify-center mb-6 shadow-lg">
            <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          
          <h3 className="text-2xl font-light text-gray-800 mb-3">
            데이터 파일을 업로드하세요
          </h3>
          
          <p className="text-gray-500 mb-6 text-lg font-light max-w-md">
            CSV, Excel 또는 JSON 파일을 드래그하거나 클릭하여 선택하세요
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 items-center">
            <button className="px-8 py-3 bg-gradient-to-r from-google-blue to-google-purple text-white rounded-xl hover:from-google-blue/90 hover:to-google-purple/90 transition-all duration-200 shadow-lg hover:shadow-xl font-medium">
              파일 선택
            </button>
            <div className="flex items-center space-x-2 text-sm text-gray-400">
              <span>.csv</span>
              <span>•</span>
              <span>.xlsx</span>
              <span>•</span>
              <span>.xls</span>
              <span>•</span>
              <span className="text-green-500 font-medium">.json</span>
            </div>
          </div>
        </div>
      </div>
      
      {uploadStatus && (
        <div className={`mt-6 p-4 rounded-xl text-center font-medium backdrop-blur-sm ${
          uploadStatus.includes('성공') 
            ? 'bg-green-100/80 text-green-700 border border-green-200/50' 
            : uploadStatus.includes('오류') || uploadStatus.includes('만')
            ? 'bg-red-100/80 text-red-700 border border-red-200/50'
            : 'bg-blue-100/80 text-blue-700 border border-blue-200/50'
        }`}>
          {uploadStatus}
        </div>
      )}
    </div>
  );
};

export default FileUpload;