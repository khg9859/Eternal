/** @type {import('tailwindcss').Config} */
module.exports = {
  // 다크모드: class 기반으로 활성화
  darkMode: "class", // ✅ 이 줄 추가가 핵심

  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html",
  ],

  theme: {
    extend: {
      fontFamily: {
        google: ["Product Sans", "Arial", "sans-serif"],
      },

      colors: {
        "google-blue": "#4285f4",
        "google-red": "#ea4335",
        "google-yellow": "#fbbc05",
        "google-green": "#34a853",
        "google-purple": "#9c27b0",
      },

      boxShadow: {
        "3xl": "0 35px 60px -12px rgba(0, 0, 0, 0.25)",
      },

      // 부드러운 색 전환용 (optional)
      transitionProperty: {
        colors: "background-color, border-color, color, fill, stroke",
      },
    },
  },

  plugins: [],
};