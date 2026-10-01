import React, { useState, useRef, useEffect } from 'react';
import { 
  Play, 
  Pause, 
  Volume2, 
  VolumeX, 
  Maximize2, 
  RotateCcw, 
  Wallet, 
  ShoppingBag, 
  Sparkles, 
  Swords, 
  Dna, 
  ArrowRightLeft,
  CheckCircle2,
  ShieldCheck
} from 'lucide-react';
import { getPokemonArtworkUrl } from '../services/pokemonService';

export interface DemoStep {
  id: number;
  label: string;
  badge: string;
  description: string;
  subtext: string;
  icon: React.ReactNode;
  bgGradient: string;
  pokemonId?: number;
  pokemonName?: string;
  actionSnippet?: string;
}

const DEMO_STEPS: DemoStep[] = [
  {
    id: 1,
    label: "Connect Wallet",
    badge: "01 CONNECT",
    description: "Connect your self-custody wallet.",
    subtext: "Your wallet holds and secures your Pokémon.",
    icon: <Wallet size={18} />,
    bgGradient: "linear-gradient(135deg, rgba(0, 240, 255, 0.15) 0%, rgba(8, 10, 12, 0.85) 100%)",
    actionSnippet: "pera.connect() → Active"
  },
  {
    id: 2,
    label: "Choose Pack",
    badge: "02 CHOOSE",
    description: "Pick a Poké Ball tier.",
    subtext: "Standard or Golden Poké Ball encounters.",
    icon: <ShoppingBag size={18} />,
    bgGradient: "linear-gradient(135deg, rgba(212, 255, 0, 0.15) 0%, rgba(8, 10, 12, 0.85) 100%)",
    actionSnippet: "Pack: Golden Poké Ball"
  },
  {
    id: 3,
    label: "Confirm Authorization",
    badge: "03 UNLOCK",
    description: "Confirm authorization in your wallet.",
    subtext: "Instant confirmation & verification.",
    icon: <Sparkles size={18} />,
    bgGradient: "linear-gradient(135deg, rgba(255, 184, 0, 0.15) 0%, rgba(8, 10, 12, 0.85) 100%)",
    actionSnippet: "Unlock: 0.50 ALGO"
  },
  {
    id: 4,
    label: "Poké Ball Opens",
    badge: "04 DISCOVER",
    description: "Reveal your Pokémon.",
    subtext: "Capture reveal with energy and silhouette.",
    icon: <Sparkles size={18} />,
    bgGradient: "linear-gradient(135deg, rgba(255, 77, 45, 0.2) 0%, rgba(8, 10, 12, 0.85) 100%)",
    pokemonId: 25,
    pokemonName: "Pikachu #025",
    actionSnippet: "Discover: Pikachu #025"
  },
  {
    id: 5,
    label: "Enters Wallet",
    badge: "05 OWN",
    description: "1-of-1 digital collectible enters your wallet.",
    subtext: "Ownership delivered directly into your custody.",
    icon: <ShieldCheck size={18} />,
    bgGradient: "linear-gradient(135deg, rgba(16, 185, 129, 0.2) 0%, rgba(8, 10, 12, 0.85) 100%)",
    pokemonId: 6,
    pokemonName: "Charizard #006",
    actionSnippet: "Delivered to Wallet"
  },
  {
    id: 6,
    label: "Collection Updates",
    badge: "06 COLLECTION",
    description: "Collection updates automatically.",
    subtext: "Live stats and verified holdings.",
    icon: <CheckCircle2 size={18} />,
    bgGradient: "linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, rgba(8, 10, 12, 0.85) 100%)",
    pokemonId: 448,
    pokemonName: "Lucario #448",
    actionSnippet: "Synchronized: 6 Owned"
  },
  {
    id: 7,
    label: "Tactical Battle",
    badge: "07 BATTLE",
    description: "Enter turn-based arena battles.",
    subtext: "Gain combat XP and level up fighters.",
    icon: <Swords size={18} />,
    bgGradient: "linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(8, 10, 12, 0.85) 100%)",
    pokemonId: 94,
    pokemonName: "Gengar #094",
    actionSnippet: "Victory! +50 XP"
  },
  {
    id: 8,
    label: "Evolution",
    badge: "08 EVOLVE",
    description: "Evolve your Pokémon.",
    subtext: "Unlock apex forms and upgraded stats.",
    icon: <Dna size={18} />,
    bgGradient: "linear-gradient(135deg, rgba(168, 85, 247, 0.2) 0%, rgba(8, 10, 12, 0.85) 100%)",
    pokemonId: 658,
    pokemonName: "Greninja #658",
    actionSnippet: "Evolution: Frogadier → Greninja"
  },
  {
    id: 9,
    label: "P2P Trade",
    badge: "09 TRADE",
    description: "Trade Pokémon with collectors.",
    subtext: "Direct peer-to-peer asset swap.",
    icon: <ArrowRightLeft size={18} />,
    bgGradient: "linear-gradient(135deg, rgba(245, 158, 11, 0.2) 0%, rgba(8, 10, 12, 0.85) 100%)",
    pokemonId: 384,
    pokemonName: "Rayquaza #384",
    actionSnippet: "Trade: Rayquaza ⇄ Mewtwo"
  }
];

export const DemoVideo: React.FC = () => {
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [isMuted, setIsMuted] = useState<boolean>(true);
  const [activeStepIndex, setActiveStepIndex] = useState<number>(0);
  const [playbackProgress, setPlaybackProgress] = useState<number>(0);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Auto-advance through interactive demo steps
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      setActiveStepIndex((prev) => {
        const next = (prev + 1) % DEMO_STEPS.length;
        setPlaybackProgress(((next + 1) / DEMO_STEPS.length) * 100);
        return next;
      });
    }, 3800);

    return () => clearInterval(interval);
  }, [isPlaying]);

  const togglePlay = () => {
    setIsPlaying(!isPlaying);
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play().catch(() => {});
      }
    }
  };

  const toggleMute = () => {
    setIsMuted(!isMuted);
    if (videoRef.current) {
      videoRef.current.muted = !isMuted;
    }
  };

  const handleStepSelect = (index: number) => {
    setActiveStepIndex(index);
    setPlaybackProgress(((index + 1) / DEMO_STEPS.length) * 100);
  };

  const toggleFullscreen = () => {
    if (!containerRef.current) return;
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    } else {
      containerRef.current.requestFullscreen().catch(() => {});
    }
  };

  const currentStep = DEMO_STEPS[activeStepIndex];

  return (
    <section id="demo-video" className="demo-video-section">
      <div className="editorial-container">
        <div className="demo-side-by-side-layout">
          {/* Left Column: Short Project Description (35-40%) */}
          <div className="demo-description-column">
            <div className="section-label">Interactive Showcase</div>
            <h2 className="section-headline">SEE IT IN ACTION.</h2>
            
            <p className="demo-summary-lead">
              Pokédex is a digital Pokémon collecting experience where you can discover Pokémon, keep them in your wallet, battle, evolve and trade your collection.
            </p>

            <div className="demo-flow-subtle">
              <span className="flow-step">CONNECT</span>
              <span className="flow-sep">→</span>
              <span className="flow-step">COLLECT</span>
              <span className="flow-sep">→</span>
              <span className="flow-step">PLAY</span>
              <span className="flow-sep">→</span>
              <span className="flow-step">TRADE</span>
            </div>

            {/* Current Step Status Pill */}
            <div className="demo-current-step-status">
              <div className="dcss-badge">{currentStep.badge}</div>
              <div className="dcss-content">
                <strong>{currentStep.description}</strong>
                <span>{currentStep.subtext}</span>
              </div>
            </div>

            {/* Step Milestones Scrubber */}
            <div className="demo-mini-stepper">
              {DEMO_STEPS.map((step, idx) => (
                <button
                  key={step.id}
                  className={`demo-mini-step-btn ${activeStepIndex === idx ? 'active' : ''}`}
                  onClick={() => handleStepSelect(idx)}
                  title={step.label}
                >
                  <span className="dms-num">0{step.id}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Right Column: Demo Video Player (55-60%, max-width ~700px) */}
          <div className="demo-player-column">
            <div ref={containerRef} className="cinematic-video-player-frame compact">
              {/* Ambient Glow */}
              <div className="video-player-glow" style={{ background: currentStep.bgGradient }} />

              <div className="video-screen-viewport">
                {/* Native HTML5 Video Element with playsInline and muted */}
                <video
                  ref={videoRef}
                  className="native-demo-video"
                  muted={isMuted}
                  autoPlay={isPlaying}
                  loop
                  playsInline
                  poster={getPokemonArtworkUrl(currentStep.pokemonId || 6)}
                  style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: 0.15 }}
                >
                  <source src="/demo_preview.mp4" type="video/mp4" />
                </video>

                {/* Interactive Stage Overlay */}
                <div className="video-stage-canvas" style={{ background: currentStep.bgGradient }}>
                  <div className="video-stage-inner">
                    {/* Top Bar */}
                    <div className="video-stage-top-bar">
                      <span className="demo-step-pill">
                        {currentStep.badge}
                      </span>
                      <div className="demo-live-badge">
                        <span className="pulsing-dot" style={{ background: 'var(--accent-lime)' }} />
                        <span>PREVIEW</span>
                      </div>
                    </div>

                    {/* Center Spotlight */}
                    <div className="video-stage-center-content">
                      {currentStep.pokemonId ? (
                        <div className="demo-artwork-spotlight">
                          <img 
                            src={getPokemonArtworkUrl(currentStep.pokemonId)} 
                            alt={currentStep.pokemonName || "Pokémon"}
                            className="demo-spotlight-img"
                          />
                          <div className="demo-artwork-meta">
                            <h4>{currentStep.pokemonName}</h4>
                          </div>
                        </div>
                      ) : (
                        <div className="demo-icon-spotlight">
                          <div className="demo-icon-halo">
                            {currentStep.icon}
                          </div>
                        </div>
                      )}

                      <div className="demo-step-text-wrap">
                        <h3 className="demo-step-headline">{currentStep.description}</h3>
                        {currentStep.actionSnippet && (
                          <div className="demo-action-snippet">
                            <code>{currentStep.actionSnippet}</code>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Controls Bar */}
                    <div className="video-stage-controls-bar">
                      <div className="video-controls-left">
                        <button 
                          className="video-ctrl-btn play-btn"
                          onClick={togglePlay}
                          aria-label={isPlaying ? "Pause Demo" : "Play Demo"}
                        >
                          {isPlaying ? <Pause size={16} /> : <Play size={16} fill="currentColor" />}
                        </button>
                        <button 
                          className="video-ctrl-btn"
                          onClick={() => handleStepSelect(0)}
                          title="Restart"
                        >
                          <RotateCcw size={14} />
                        </button>
                        <button 
                          className="video-ctrl-btn"
                          onClick={toggleMute}
                          title={isMuted ? "Unmute" : "Mute"}
                        >
                          {isMuted ? <VolumeX size={14} /> : <Volume2 size={14} />}
                        </button>
                        <span className="video-time-indicator">
                          0{activeStepIndex + 1} / 0{DEMO_STEPS.length}
                        </span>
                      </div>

                      {/* Progress Line */}
                      <div className="video-progress-track" onClick={(e) => {
                        const rect = e.currentTarget.getBoundingClientRect();
                        const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
                        const newIdx = Math.min(DEMO_STEPS.length - 1, Math.floor(ratio * DEMO_STEPS.length));
                        handleStepSelect(newIdx);
                      }}>
                        <div className="video-progress-fill" style={{ width: `${playbackProgress}%` }} />
                      </div>

                      <div className="video-controls-right">
                        <button 
                          className="video-ctrl-btn"
                          onClick={toggleFullscreen}
                          title="Fullscreen"
                        >
                          <Maximize2 size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
