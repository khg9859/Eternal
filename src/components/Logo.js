import React from "react";

const Logo = ({ size = "large" }) => {
  const sizeClasses = {
    small: "text-3xl",
    medium: "text-5xl",
    large: "text-7xl",
  };

  return (
    <div className="flex justify-center items-center">
      <h1
        className={`${sizeClasses[size]} font-extrabold tracking-widest bg-gradient-to-r from-yellow-400 via-amber-300 to-yellow-500 bg-clip-text text-transparent drop-shadow-[0_0_20px_rgba(255,215,0,0.4)] select-none`}
        style={{
          fontFamily: "'Poppins', 'Pretendard', sans-serif",
          letterSpacing: "0.15em",
        }}
      >
        ETERNAL
      </h1>
    </div>
  );
};

export default Logo;