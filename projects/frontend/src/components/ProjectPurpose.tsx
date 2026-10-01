import React from 'react';
import { 
  Wallet, 
  Swords, 
  ArrowRightLeft 
} from 'lucide-react';

export const ProjectPurpose: React.FC = () => {
  const concepts = [
    {
      title: "OWN",
      desc: "Keep your collection.",
      icon: <Wallet size={22} />,
      color: "var(--accent-lime)"
    },
    {
      title: "PLAY",
      desc: "Use your Pokémon.",
      icon: <Swords size={22} />,
      color: "#FF4D2D"
    },
    {
      title: "TRADE",
      desc: "Exchange them.",
      icon: <ArrowRightLeft size={22} />,
      color: "#F59E0B"
    }
  ];

  return (
    <section id="project-purpose" className="project-purpose-section simplified">
      <div className="editorial-container">
        {/* Simplified Header */}
        <div className="purpose-editorial-header simplified" style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
          <div className="section-label">Core Philosophy</div>
          <h2 className="section-headline">WHY POKÉDEX?</h2>
          
          <div className="purpose-manifesto-hero simplified">
            <h3 className="purpose-statement-headline">
              YOUR COLLECTION.<br />
              <span className="pmh-accent-glow">IN YOUR WALLET.</span>
            </h3>
            <p className="purpose-statement-desc">
              Pokédex explores a simple idea: digital collectibles should belong to the person who collects them.
            </p>
          </div>
        </div>

        {/* 3 Core Concepts Grid */}
        <div className="purpose-concepts-grid">
          {concepts.map((concept) => (
            <div 
              key={concept.title} 
              className="purpose-concept-card"
              style={{ borderTop: `2px solid ${concept.color}` }}
            >
              <div className="pcc-icon" style={{ color: concept.color, background: `${concept.color}15` }}>
                {concept.icon}
              </div>
              <h4 className="pcc-title">{concept.title}</h4>
              <p className="pcc-desc">{concept.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
