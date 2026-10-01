import React, { useState, useRef } from 'react';

export type PokeBallType = 'NORMAL' | 'GOLDEN' | 'BASIC' | 'PREMIUM';
export type PokeBallState = 'idle' | 'hover' | 'shaking' | 'opening' | 'open';

interface PokeBallProps {
  type: PokeBallType;
  size?: number;
  state?: PokeBallState;
  shakeStage?: number; // 0 = idle, 1 = first shake, 2 = second shake, 3 = third shake
  interactive?: boolean;
  onClick?: () => void;
  className?: string;
  showRays?: boolean;
}

export const PokeBall: React.FC<PokeBallProps> = ({
  type,
  size = 180,
  state = 'idle',
  shakeStage = 0,
  interactive = true,
  onClick,
  className = '',
  showRays = false
}) => {
  const isGolden = type === 'GOLDEN' || type === 'PREMIUM';
  const containerRef = useRef<HTMLDivElement>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [isHovered, setIsHovered] = useState(false);

  // Mouse tilt tracking for 3D depth
  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!interactive || state === 'shaking' || state === 'opening' || state === 'open') return;
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width - 0.5) * 2; // -1 to 1
    const y = ((e.clientY - rect.top) / rect.height - 0.5) * 2; // -1 to 1
    setMousePos({ x, y });
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    setMousePos({ x: 0, y: 0 });
  };

  const handleMouseEnter = () => {
    if (interactive) setIsHovered(true);
  };

  // Compute transform based on state and hover
  const getTransform = () => {
    if (state === 'shaking' || state === 'opening') {
      return '';
    }
    if (isHovered && interactive) {
      const tiltX = -mousePos.y * 14;
      const tiltY = mousePos.x * 16;
      const scale = isGolden ? 1.08 : 1.05;
      return `perspective(600px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) scale3d(${scale}, ${scale}, ${scale})`;
    }
    return '';
  };

  return (
    <div
      ref={containerRef}
      className={`pokeball-wrapper ${isGolden ? 'pokeball-premium' : 'pokeball-basic'} state-${state} shake-stage-${shakeStage} ${className}`}
      style={{
        width: `${size}px`,
        height: `${size}px`,
        cursor: onClick ? 'pointer' : 'default'
      }}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={onClick}
    >
      {/* Outer ambient glow / particles */}
      {isGolden && (
        <div className="pokeball-gold-aura">
          <div className="gold-sparkle p1" />
          <div className="gold-sparkle p2" />
          <div className="gold-sparkle p3" />
          <div className="gold-sparkle p4" />
          <div className="gold-sparkle p5" />
          <div className="gold-sparkle p6" />
        </div>
      )}

      {/* Energy Rays on open */}
      {(showRays || state === 'opening' || state === 'open') && (
        <div className={`pokeball-energy-burst ${isGolden ? 'gold-burst' : 'red-white-burst'}`}>
          <div className="burst-ray r1" />
          <div className="burst-ray r2" />
          <div className="burst-ray r3" />
          <div className="burst-ray r4" />
          <div className="burst-ray r5" />
          <div className="burst-ray r6" />
          <div className="burst-core" />
        </div>
      )}

      {/* 3D Ball Container */}
      <div
        className={`pokeball-sphere ${isGolden ? 'gold-sphere' : 'normal-sphere'} ${
          state === 'idle' ? 'animate-float' : ''
        } ${state === 'shaking' ? `animate-shake-${Math.min(3, Math.max(1, shakeStage || 1))}` : ''} ${
          state === 'opening' ? 'animate-ball-open' : ''
        }`}
        style={{
          transform: getTransform(),
          transition: isHovered ? 'transform 0.1s ease-out' : 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)'
        }}
      >
        <svg
          viewBox="0 0 200 200"
          className="pokeball-svg"
          style={{ width: '100%', height: '100%', overflow: 'visible' }}
        >
          <defs>
            {/* ================= NORMAL POKÉ BALL GRADIENTS ================= */}
            {/* Top Red Hemisphere */}
            <radialGradient id="normalTopGrad" cx="35%" cy="30%" r="65%">
              <stop offset="0%" stopColor="#ff4d4d" />
              <stop offset="35%" stopColor="#ee1515" />
              <stop offset="75%" stopColor="#b30000" />
              <stop offset="100%" stopColor="#660000" />
            </radialGradient>

            {/* Bottom White Hemisphere */}
            <radialGradient id="normalBottomGrad" cx="35%" cy="70%" r="65%">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="45%" stopColor="#f0f2f5" />
              <stop offset="80%" stopColor="#c5cbd3" />
              <stop offset="100%" stopColor="#7a8594" />
            </radialGradient>

            {/* ================= GOLDEN POKÉ BALL GRADIENTS ================= */}
            {/* Top Metallic Gold Hemisphere */}
            <radialGradient id="goldTopGrad" cx="30%" cy="25%" r="70%">
              <stop offset="0%" stopColor="#fff9d6" />
              <stop offset="20%" stopColor="#ffd700" />
              <stop offset="50%" stopColor="#d4af37" />
              <stop offset="80%" stopColor="#997a15" />
              <stop offset="100%" stopColor="#4a3b05" />
            </radialGradient>

            {/* Bottom Deep Burnished Gold Hemisphere */}
            <radialGradient id="goldBottomGrad" cx="30%" cy="75%" r="70%">
              <stop offset="0%" stopColor="#f5e18a" />
              <stop offset="35%" stopColor="#c59b27" />
              <stop offset="70%" stopColor="#7c600b" />
              <stop offset="100%" stopColor="#3d2f04" />
            </radialGradient>

            {/* Metallic Gold Sheen Bar */}
            <linearGradient id="goldSheenGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="0.8" />
              <stop offset="30%" stopColor="#ffd700" stopOpacity="0.4" />
              <stop offset="70%" stopColor="#b8860b" stopOpacity="0" />
              <stop offset="100%" stopColor="#ffffff" stopOpacity="0.3" />
            </linearGradient>

            {/* Central Band Gradients */}
            <linearGradient id="bandGradNormal" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#15171c" />
              <stop offset="50%" stopColor="#22252a" />
              <stop offset="100%" stopColor="#0d0e11" />
            </linearGradient>

            <linearGradient id="bandGradGold" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#1a1505" />
              <stop offset="50%" stopColor="#382d0a" />
              <stop offset="100%" stopColor="#120e03" />
            </linearGradient>

            {/* Center Button Rim */}
            <radialGradient id="buttonRimNormal" cx="35%" cy="35%" r="65%">
              <stop offset="0%" stopColor="#e4e8ed" />
              <stop offset="50%" stopColor="#8c96a4" />
              <stop offset="100%" stopColor="#252a30" />
            </radialGradient>

            <radialGradient id="buttonRimGold" cx="35%" cy="35%" r="65%">
              <stop offset="0%" stopColor="#fff6cc" />
              <stop offset="40%" stopColor="#d4af37" />
              <stop offset="85%" stopColor="#7a5f08" />
              <stop offset="100%" stopColor="#2b2002" />
            </radialGradient>

            {/* Center Core Button (illuminated) */}
            <radialGradient id="buttonCenterNormal" cx="40%" cy="35%" r="60%">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="60%" stopColor="#edf1f7" />
              <stop offset="100%" stopColor="#bcc5d1" />
            </radialGradient>

            <radialGradient id="buttonCenterGold" cx="40%" cy="35%" r="60%">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="40%" stopColor="#fff2a8" />
              <stop offset="80%" stopColor="#f0c23a" />
              <stop offset="100%" stopColor="#b38714" />
            </radialGradient>

            {/* Specular Glare */}
            <linearGradient id="specularGlare" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="0.75" />
              <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
            </linearGradient>

            {/* Drop Shadow filter for depth */}
            <filter id="ballShadow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="10" stdDeviation="12" floodColor="#000000" floodOpacity="0.45" />
            </filter>
            
            <filter id="goldGlow" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="8" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* MAIN POKEBALL GROUP */}
          <g filter="url(#ballShadow)" className="pokeball-main-group">
            {/* Upper Hemisphere */}
            <g className="pokeball-upper-hemisphere">
              <path
                d="M 10 100 A 90 90 0 0 1 190 100 Z"
                fill={isGolden ? 'url(#goldTopGrad)' : 'url(#normalTopGrad)'}
              />
              {/* Glossy Specular Highlight Curve */}
              <ellipse
                cx="80"
                cy="45"
                rx="52"
                ry="24"
                transform="rotate(-18 80 45)"
                fill="url(#specularGlare)"
                opacity={isGolden ? '0.85' : '0.6'}
              />
              {/* Secondary delicate specular reflection */}
              <ellipse
                cx="50"
                cy="65"
                rx="16"
                ry="8"
                transform="rotate(-30 50 65)"
                fill="#ffffff"
                opacity={isGolden ? '0.7' : '0.45'}
              />
              {/* Premium engraved filigree arcs (Golden ball only) */}
              {isGolden && (
                <path
                  d="M 35 75 Q 70 30 130 35 Q 165 40 175 75"
                  fill="none"
                  stroke="#fff5a6"
                  strokeWidth="1.5"
                  strokeDasharray="4 3"
                  opacity="0.65"
                />
              )}
            </g>

            {/* Lower Hemisphere */}
            <g className="pokeball-lower-hemisphere">
              <path
                d="M 10 100 A 90 90 0 0 0 190 100 Z"
                fill={isGolden ? 'url(#goldBottomGrad)' : 'url(#normalBottomGrad)'}
              />
              {/* Ambient bottom shadow occlusion */}
              <path
                d="M 20 120 A 85 85 0 0 0 180 120 Z"
                fill={isGolden ? '#291e02' : '#474f5c'}
                opacity={isGolden ? '0.4' : '0.25'}
              />
              {/* Subtle ground reflection bounce on bottom curve */}
              <ellipse
                cx="100"
                cy="175"
                rx="45"
                ry="8"
                fill="#ffffff"
                opacity={isGolden ? '0.25' : '0.2'}
              />
            </g>

            {/* Middle Divider Band */}
            <g className="pokeball-center-band">
              <rect
                x="9.5"
                y="92"
                width="181"
                height="16"
                fill={isGolden ? 'url(#bandGradGold)' : 'url(#bandGradNormal)'}
              />
              {/* Gold Inlay Trim on Band */}
              {isGolden && (
                <>
                  <line x1="10" y1="92" x2="190" y2="92" stroke="#e0b838" strokeWidth="1" opacity="0.8" />
                  <line x1="10" y1="108" x2="190" y2="108" stroke="#e0b838" strokeWidth="1" opacity="0.8" />
                </>
              )}
            </g>

            {/* Outer Center Ring */}
            <circle
              cx="100"
              cy="100"
              r="28"
              fill={isGolden ? '#1c1504' : '#171a1f'}
              stroke={isGolden ? '#f3cf55' : '#2b3038'}
              strokeWidth="1.5"
            />

            {/* Middle Center Bevel Ring */}
            <circle
              cx="100"
              cy="100"
              r="20"
              fill={isGolden ? 'url(#buttonRimGold)' : 'url(#buttonRimNormal)'}
              stroke={isGolden ? '#6b5107' : '#1b1d22'}
              strokeWidth="1"
            />

            {/* Inner Center Core Button */}
            <circle
              cx="100"
              cy="100"
              r="13"
              className={`pokeball-center-button ${state === 'shaking' || state === 'opening' ? 'button-active-pulse' : ''}`}
              fill={isGolden ? 'url(#buttonCenterGold)' : 'url(#buttonCenterNormal)'}
              stroke={isGolden ? '#ffe066' : '#ffffff'}
              strokeWidth="1.5"
            />

            {/* Button Inner Reflection dot */}
            <circle
              cx="97"
              cy="97"
              r="3.5"
              fill="#ffffff"
              opacity="0.9"
            />
          </g>
        </svg>

        {/* Dynamic dynamic metallic sheen sweep (Gold only) */}
        {isGolden && (
          <div className="gold-sheen-sweep" />
        )}
      </div>

      {/* Floating ground shadow */}
      <div
        className={`pokeball-ground-shadow ${isGolden ? 'gold-shadow' : 'normal-shadow'} ${
          state === 'idle' ? 'animate-shadow-pulse' : ''
        }`}
        style={{
          width: `${size * 0.75}px`,
          height: `${size * 0.12}px`
        }}
      />
    </div>
  );
};

export default PokeBall;
