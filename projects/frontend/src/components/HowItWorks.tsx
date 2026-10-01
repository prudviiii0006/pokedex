import React from 'react';
import { 
  Wallet, 
  ShoppingBag, 
  Swords, 
  ArrowRightLeft
} from 'lucide-react';

export const HowItWorks: React.FC = () => {
  const steps = [
    {
      num: "01",
      title: "CONNECT",
      desc: "Connect your wallet.",
      icon: <Wallet size={22} />,
      color: "var(--accent-cyan)"
    },
    {
      num: "02",
      title: "COLLECT",
      desc: "Discover and own Pokémon.",
      icon: <ShoppingBag size={22} />,
      color: "var(--accent-lime)"
    },
    {
      num: "03",
      title: "PLAY",
      desc: "Battle and evolve.",
      icon: <Swords size={22} />,
      color: "#FF4D2D"
    },
    {
      num: "04",
      title: "TRADE",
      desc: "Exchange Pokémon with collectors.",
      icon: <ArrowRightLeft size={22} />,
      color: "#F59E0B"
    }
  ];

  return (
    <section className="how-it-works-section">
      <div className="editorial-container">
        <div className="section-editorial-header" style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
          <div className="section-label">Simplified Journey</div>
          <h2 className="section-headline">HOW IT WORKS.</h2>
        </div>

        <div className="how-it-works-grid">
          {steps.map((step) => (
            <div key={step.num} className="how-step-card">
              <div className="how-step-top">
                <span className="how-step-num" style={{ color: step.color }}>{step.num}</span>
                <div className="how-step-icon" style={{ color: step.color, background: `${step.color}15` }}>
                  {step.icon}
                </div>
              </div>
              <h3 className="how-step-title">{step.title}</h3>
              <p className="how-step-desc">{step.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
