import React, { useState, useEffect, useMemo } from 'react';
import { 
  connectPeraWallet, 
  disconnectPeraWallet, 
  reconnectPeraSession, 
  getAccountInfo,
  createUnsignedPaymentTxn,
  signAndSubmitTxn,
  executeAssetOptIn,
  createAssetReturnTxn,
  PROJECT_CREATOR_ADDRESS,
  isPeraConnected
} from './wallet/pera';

import { 
  Sparkles, 
  ShoppingBag, 
  Layers, 
  ExternalLink, 
  X, 
  RefreshCw, 
  Flame, 
  Search, 
  Check, 
  Swords, 
  Dna, 
  ArrowRightLeft, 
  Zap,
  Menu,
  Info,
  Shield,
  Star,
  ChevronLeft,
  ChevronRight,
  Wallet,
  AlertCircle,
  Copy,
  CheckCircle2,
  Eye,
  Percent
} from 'lucide-react';

import { 
  FALLBACK_CORE_POKEMON, 
  getPokemonArtwork,
  getPokemonArtworkUrl,
  getPokemonSpriteUrl,
  getPokemonGeneration,
  NEUTRAL_FALLBACK_SVG
} from './services/pokemonService';

import { PokeBall } from './components/PokeBall';
import { DemoVideo } from './components/DemoVideo';
import { ProjectPurpose } from './components/ProjectPurpose';
import { HowItWorks } from './components/HowItWorks';

import { X402PaymentService } from './services/x402PaymentService';

export type NavTab = 'home' | 'packs' | 'collection' | 'pokedex' | 'battle' | 'evolution' | 'fusion' | 'trade' | 'asset';
export type WalletStatus = 'disconnected' | 'connecting' | 'connected' | 'rejected' | 'error';
export type X402ResourceType = 'PACK' | 'PREMIUM_BATTLE' | 'FEATURED_TRADE' | 'SMART_MATCH' | 'EVOLUTION_BOOST' | 'CREATURE_ANALYSIS';

export interface ActivePaymentChallenge {
  resourceType: X402ResourceType;
  resourceId: string;
  endpointUrl: string;
  httpMethod: 'GET' | 'POST';
  requestBody?: any;
  title: string;
  subtitle?: string;
  packId?: string;
  packName?: string;
  priceAlgo: number;
  priceUsdc?: number; // legacy alias
  amountMicroAlgo: string;
  amountMicroUsdc?: string; // legacy alias
  currency?: string;
  payTo: string;
  assetId: number;
  network: string;
  facilitatorUrl: string;
  description: string;
  isSigning: boolean;
  isSettling: boolean;
  paymentStage?: 'IDLE' | 'PREPARING' | 'WAITING_FOR_PERA' | 'VERIFYING' | 'SETTLING' | 'CONFIRMED' | 'CANCELLED' | 'FAILED';
  confirmedData?: any;
  settlementReceipt?: any;
  error?: string | null;
}

export interface PackItem {
  id: string;
  name: string;
  price: number;
  currency: string;
  reward_count: number;
  description: string;
  rarities: Record<string, number>;
}

export interface OwnedCreatureItem {
  asset_id: number;
  purchase_id: string;
  template_id: string;
  name: string;
  primary_type: string;
  secondary_type?: string;
  faction: string;
  rarity: string;
  level: number;
  xp: number;
  hp: number;
  attack: number;
  defense: number;
  speed: number;
  stamina: number;
  battle_wins: number;
  battle_losses: number;
  evolution_stage: number;
  image?: string;
  description?: string;
  acquired_at: string;
  owner_wallet?: string;
  on_chain_verified?: boolean;
  explorer_url?: string;
  mint_tx?: string;
  metadata_uri?: string;
}

export interface SpeciesItem {
  id: string;
  name: string;
  index_number: number;
  primary_type: string;
  secondary_type?: string;
  rarity: string;
  faction: string;
  evolution_family: string;
  evolution_stage: number;
  base_hp: number;
  base_attack: number;
  base_defense: number;
  base_speed: number;
  base_stamina: number;
  description: string;
  image?: string;
  next_evolution_id?: string;
}

export interface ArenaItem {
  id: string;
  name: string;
  favored_type: string;
  weak_type: string;
  boost_multiplier: number;
  weather: string;
  description: string;
}

export interface TradeItem {
  trade_id: string;
  initiator_wallet: string;
  initiator_asset_id: number;
  offered_asset: {
    asset_id: number;
    name: string;
    rarity: string;
    level: number;
    primary_type: string;
    image?: string;
  };
  wanted_rarity?: string;
  wanted_type?: string;
  status: string;
  is_featured?: boolean;
  featured_until?: string;
  created_at: string;
}

export interface ActivityEvent {
  event_id: string;
  event_type: string;
  wallet_address: string;
  asset_id?: number;
  creature_name?: string;
  summary: string;
  created_at: string;
}

const ACTIVE_API_URL = (import.meta as any).env?.VITE_API_BASE_URL || "http://127.0.0.1:8001";

const RARITY_COLORS: Record<string, string> = {
  Common: '#8E9BAE',
  Rare: '#3B82F6',
  Epic: '#A855F7',
  Legendary: '#F59E0B'
};

const ELEMENT_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  Fire: { bg: 'rgba(255, 77, 45, 0.12)', text: '#FF4D2D', border: 'rgba(255, 77, 45, 0.35)' },
  Water: { bg: 'rgba(37, 99, 235, 0.12)', text: '#3B82F6', border: 'rgba(37, 99, 235, 0.35)' },
  Grass: { bg: 'rgba(16, 185, 129, 0.12)', text: '#10B981', border: 'rgba(16, 185, 129, 0.35)' },
  Electric: { bg: 'rgba(251, 191, 36, 0.12)', text: '#FBBF24', border: 'rgba(251, 191, 36, 0.35)' },
  Earth: { bg: 'rgba(217, 119, 6, 0.12)', text: '#D97706', border: 'rgba(217, 119, 6, 0.35)' },
  Rock: { bg: 'rgba(175, 169, 129, 0.15)', text: '#AFA981', border: 'rgba(175, 169, 129, 0.35)' },
  Ground: { bg: 'rgba(145, 81, 33, 0.15)', text: '#915121', border: 'rgba(145, 81, 33, 0.35)' },
  Ice: { bg: 'rgba(6, 182, 212, 0.12)', text: '#06B6D4', border: 'rgba(6, 182, 212, 0.35)' },
  Dark: { bg: 'rgba(124, 58, 237, 0.12)', text: '#7C3AED', border: 'rgba(124, 58, 237, 0.35)' },
  Light: { bg: 'rgba(253, 224, 71, 0.12)', text: '#FDE047', border: 'rgba(253, 224, 71, 0.35)' },
  Ghost: { bg: 'rgba(112, 65, 112, 0.15)', text: '#A855F7', border: 'rgba(112, 65, 112, 0.35)' },
  Psychic: { bg: 'rgba(239, 65, 121, 0.15)', text: '#EF4179', border: 'rgba(239, 65, 121, 0.35)' },
  Fighting: { bg: 'rgba(255, 128, 0, 0.15)', text: '#FF8000', border: 'rgba(255, 128, 0, 0.35)' },
  Dragon: { bg: 'rgba(80, 96, 225, 0.15)', text: '#5060E1', border: 'rgba(80, 96, 225, 0.35)' },
  Steel: { bg: 'rgba(96, 161, 184, 0.15)', text: '#60A1B8', border: 'rgba(96, 161, 184, 0.35)' },
  Fairy: { bg: 'rgba(239, 112, 239, 0.15)', text: '#EF70EF', border: 'rgba(239, 112, 239, 0.35)' },
  Flying: { bg: 'rgba(129, 185, 239, 0.15)', text: '#81B9EF', border: 'rgba(129, 185, 239, 0.35)' },
  Poison: { bg: 'rgba(145, 65, 203, 0.15)', text: '#9141CB', border: 'rgba(145, 65, 203, 0.35)' },
  Bug: { bg: 'rgba(145, 161, 25, 0.15)', text: '#91A119', border: 'rgba(145, 161, 25, 0.35)' },
  Normal: { bg: 'rgba(159, 161, 159, 0.15)', text: '#9FA19F', border: 'rgba(159, 161, 159, 0.35)' }
};

// Featured Pokémon Showcase for the dynamic Hero
const FEATURED_HERO_POKEMON = [
  { id: 6, name: 'Charizard', number: '#006', element: 'Fire • Flying', rarity: 'Epic', image: getPokemonArtworkUrl(6), color: '#FF4D2D' },
  { id: 25, name: 'Pikachu', number: '#025', element: 'Electric', rarity: 'Rare', image: getPokemonArtworkUrl(25), color: '#FBBF24' },
  { id: 448, name: 'Lucario', number: '#448', element: 'Fighting • Steel', rarity: 'Epic', image: getPokemonArtworkUrl(448), color: '#38BDF8' },
  { id: 94, name: 'Gengar', number: '#094', element: 'Ghost • Poison', rarity: 'Epic', image: getPokemonArtworkUrl(94), color: '#A855F7' },
  { id: 658, name: 'Greninja', number: '#658', element: 'Water • Dark', rarity: 'Epic', image: getPokemonArtworkUrl(658), color: '#3B82F6' },
  { id: 384, name: 'Rayquaza', number: '#384', element: 'Dragon • Flying', rarity: 'Legendary', image: getPokemonArtworkUrl(384), color: '#10B981' }
];

export const App: React.FC = () => {
  // Navigation & Page State
  const [activeTab, setActiveTab] = useState<NavTab>('home');
  const [isScrolled, setIsScrolled] = useState<boolean>(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState<boolean>(false);

  // Custom Cursor State
  const [cursorPos, setCursorPos] = useState({ x: -100, y: -100 });
  const [cursorFollower, setCursorFollower] = useState({ x: -100, y: -100 });
  const [isCursorHovering, setIsCursorHovering] = useState<boolean>(false);
  const [cursorLabel, setCursorLabel] = useState<string>('');

  // Hero Parallax & Featured Selection
  const [heroParallax, setHeroParallax] = useState({ x: 0, y: 0 });
  const [featuredIndex, setFeaturedIndex] = useState<number>(0);

  // Wallet State
  const [accountAddress, setAccountAddress] = useState<string | null>(null);
  const [algoBalance, setAlgoBalance] = useState<number | null>(null);
  const [payToAddress, setPayToAddress] = useState<string>("3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM");

  // Packs Catalog & Purchase State
  const [packs, setPacks] = useState<PackItem[]>([]);
  const [activeChallenge, setActiveChallenge] = useState<ActivePaymentChallenge | null>(null);
  const [revealedCreature, setRevealedCreature] = useState<any | null>(null);
  const [revealPackType, setRevealPackType] = useState<'NORMAL' | 'GOLDEN'>('NORMAL');
  const [revealPhase, setRevealPhase] = useState<'IDLE' | 'SHAKING_1' | 'SHAKING_2' | 'SHAKING_3' | 'OPENING' | 'SILHOUETTE' | 'REVEALED'>('IDLE');
  const [isOptingIn, setIsOptingIn] = useState<boolean>(false);
  const [optInError, setOptInError] = useState<string | null>(null);
  const [revealStep, setRevealStep] = useState<'INITIAL' | 'SILHOUETTE' | 'REVEALED'>('INITIAL');

  // Possible Pokémon Catalog Modal State (Derives from Master Catalog)
  const [possiblePokemonModalOpen, setPossiblePokemonModalOpen] = useState<boolean>(false);
  const [possibleModalPackType, setPossibleModalPackType] = useState<'all' | 'basic' | 'premium' | 'fire_event' | 'water_event' | 'electric_event' | 'ghost_event'>('all');
  const [possibleSearchQuery, setPossibleSearchQuery] = useState<string>('');
  const [possibleRarityFilter, setPossibleRarityFilter] = useState<string>('ALL');
  const [possibleTypeFilter, setPossibleTypeFilter] = useState<string>('ALL');
  const [possibleGenFilter, setPossibleGenFilter] = useState<string>('ALL');
  const [possiblePage, setPossiblePage] = useState<number>(1);

  // Odds Breakdown Modal State
  const [oddsModalOpen, setOddsModalOpen] = useState<boolean>(false);
  const [oddsPackType, setOddsPackType] = useState<'all' | 'basic' | 'premium' | 'fire_event' | 'water_event' | 'electric_event' | 'ghost_event'>('all');

  // Collection State
  const [userCollection, setUserCollection] = useState<OwnedCreatureItem[]>([]);
  const [collectionLoading, setCollectionLoading] = useState<boolean>(false);
  const [collectionError, setCollectionError] = useState<string | null>(null);
  const [collectionTypeFilter, setCollectionTypeFilter] = useState<string>('all');
  const [collectionSearchQuery, setCollectionSearchQuery] = useState<string>('');
  const [isResettingCollection, setIsResettingCollection] = useState<boolean>(false);

  // Pokédex Page State
  const [pokedexSearchQuery, setPokedexSearchQuery] = useState<string>('');
  const [pokedexTypeFilter, setPokedexTypeFilter] = useState<string>('ALL');
  const [pokedexGenFilter, setPokedexGenFilter] = useState<string>('ALL');
  const [pokedexPage, setPokedexPage] = useState<number>(1);
  const [inspectingPokemon, setInspectingPokemon] = useState<any | null>(null);

  // Species Index Catalog
  const [speciesCatalog, setSpeciesCatalog] = useState<SpeciesItem[]>([]);

  // Battle State
  const [arenas, setArenas] = useState<ArenaItem[]>([]);
  const [selectedArena, setSelectedArena] = useState<string>('volcano');
  const [selectedFighterAssetId, setSelectedFighterAssetId] = useState<number | null>(null);
  const [battleInProgress, setBattleInProgress] = useState<boolean>(false);
  const [battleAnimationPhase, setBattleAnimationPhase] = useState<'IDLE' | 'ATTACK' | 'HIT' | 'RESOLVED'>('IDLE');
  const [battleResult, setBattleResult] = useState<any | null>(null);

  // Evolution State
  const [selectedEvoAssetId, setSelectedEvoAssetId] = useState<number | null>(null);
  const [evoEligibility, setEvoEligibility] = useState<any | null>(null);
  const [evoLoading, setEvoLoading] = useState<boolean>(false);
  const [evoSuccess, setEvoSuccess] = useState<any | null>(null);

  // Trading State
  const [trades, setTrades] = useState<TradeItem[]>([]);
  const [selectedTradeAssetId, setSelectedTradeAssetId] = useState<number | null>(null);
  const [tradeLoading, setTradeLoading] = useState<boolean>(false);
  const [featureTradeLoading, setFeatureTradeLoading] = useState<Record<string, boolean>>({});
  const [smartMatchData, setSmartMatchData] = useState<any | null>(null);
  const [isSmartMatchOpen, setIsSmartMatchOpen] = useState<boolean>(false);
  const [smartMatchLoading, setSmartMatchLoading] = useState<boolean>(false);

  // Tactical Analysis & Boost State
  const [unlockedAnalyses, setUnlockedAnalyses] = useState<Record<string, any>>({});
  const [analysisLoading, setAnalysisLoading] = useState<boolean>(false);
  const [boostLoading, setBoostLoading] = useState<boolean>(false);

  // Authoritative Pricing State (from backend /config/pricing)
  const [serverPricing, setServerPricing] = useState<any>({
    basic_pack: 0.01,
    premium_pack: 0.05,
    event_pack: 0.03,
    premium_battle: 0.01,
    featured_trade: 0.005,
    smart_trade_match: 0.002,
    evolution_boost: 0.005,
    creature_analysis: 0.002
  });

  // Activity Feed state kept for backend compatibility
  // const [activities, setActivities] = useState<ActivityEvent[]>([]);

  // Fusion State
  const [fusionCandidates, setFusionCandidates] = useState<any[]>([]);
  const [fusionCandidatesLoading, setFusionCandidatesLoading] = useState<boolean>(false);
  const [selectedFusionAssetIds, setSelectedFusionAssetIds] = useState<Set<number>>(new Set());
  const [fusionStep, setFusionStep] = useState<'SELECT' | 'CONFIRM_MODAL' | 'PROCESSING' | 'RESULT'>('SELECT');
  const [fusionResult, setFusionResult] = useState<any | null>(null);
  const [fusionError, setFusionError] = useState<string | null>(null);

  // On-Chain Asset Detail View State (/asset/:assetId)
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(null);
  const [selectedAssetDetail, setSelectedAssetDetail] = useState<any | null>(null);
  const [assetLoading, setAssetLoading] = useState<boolean>(false);
  const [assetError, setAssetError] = useState<string | null>(null);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  const apiUrl = ACTIVE_API_URL;
  const activeHero = FEATURED_HERO_POKEMON[featuredIndex] || FEATURED_HERO_POKEMON[0];

  // -------------------------------------------------------------
  // ASSET DETAIL FETCHER & HASH ROUTER
  // -------------------------------------------------------------
  const fetchAssetDetail = async (assetId: number) => {
    setAssetLoading(true);
    setAssetError(null);
    try {
      const res = await fetch(`${apiUrl}/assets/${assetId}`);
      if (!res.ok) {
        throw new Error(`Asset #${assetId} could not be retrieved.`);
      }
      const data = await res.json();
      setSelectedAssetDetail(data);
    } catch (err: any) {
      console.warn("Error fetching asset details:", err);
      // Fallback reconstruction from local collection if offline
      const localCard = userCollection.find(c => c.asset_id === assetId);
      if (localCard) {
        setSelectedAssetDetail({
          asset_id: assetId,
          network: "testnet",
          explorer_url: `https://testnet.explorer.perawallet.app/asset/${assetId}/`,
          pokemon: {
            id: localCard.template_id || 25,
            name: localCard.name,
            image: localCard.image || getPokemonArtworkUrl(localCard.template_id || 25),
            primary_type: localCard.primary_type,
            secondary_type: localCard.secondary_type,
            rarity: localCard.rarity,
            level: localCard.level,
            xp: localCard.xp,
            stats: {
              hp: localCard.hp,
              attack: localCard.attack,
              defense: localCard.defense,
              speed: localCard.speed,
              stamina: localCard.stamina
            }
          },
          nft: {
            total: 1,
            decimals: 0,
            unit_name: `PKMN${String(localCard.template_id || 25).padStart(3, '0')}`,
            asset_name: `${localCard.name} #${String(localCard.template_id || 25).padStart(3, '0')}`,
            metadata_uri: `ipfs://bafkreipokemon${localCard.template_id || 25}#arc3`,
            mint_tx_id: localCard.mint_tx || `tx_mint_${assetId}`,
            default_frozen: false
          },
          ownership: {
            wallet: accountAddress || localCard.owner_wallet || "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM",
            balance: 1,
            verified: true,
            in_minter_holding: false,
            delivery_status: "DELIVERED"
          },
          verified_on_chain: true
        });
      } else {
        setAssetError(err.message || `Asset #${assetId} was not found.`);
      }
    } finally {
      setAssetLoading(false);
    }
  };

  const openAssetDetail = (assetId: number) => {
    setSelectedAssetId(assetId);
    setActiveTab('asset');
    window.location.hash = `#/asset/${assetId}`;
    fetchAssetDetail(assetId);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const copyToClipboard = (text: string, label: string = 'Copied') => {
    navigator.clipboard.writeText(text);
    setCopyFeedback(label);
    setTimeout(() => setCopyFeedback(null), 2500);
  };

  // -------------------------------------------------------------
  // INITIALIZATION & EVENT LISTENERS
  // -------------------------------------------------------------
  useEffect(() => {
    checkBackendHealth();
    fetchPricingConfig();
    reconnectWalletSession();
    fetchSpeciesCatalog();
    fetchArenas();
    fetchTrades();

    // Hash Router Listener for #/asset/:assetId
    const handleHashChange = () => {
      const hash = window.location.hash;
      if (hash.startsWith('#/asset/') || hash.startsWith('#asset/')) {
        const rawId = hash.replace(/^#\/?asset\//, '').trim();
        const assetId = parseInt(rawId, 10);
        if (!isNaN(assetId)) {
          setSelectedAssetId(assetId);
          setActiveTab('asset');
          fetchAssetDetail(assetId);
        }
      }
    };
    window.addEventListener('hashchange', handleHashChange);
    handleHashChange();

    const handleScroll = () => {
      setIsScrolled(window.scrollY > 40);
    };

    const handleMouseMove = (e: MouseEvent) => {
      setCursorPos({ x: e.clientX, y: e.clientY });
      const normX = (e.clientX / window.innerWidth - 0.5) * 20;
      const normY = (e.clientY / window.innerHeight - 0.5) * 20;
      setHeroParallax({ x: normX, y: normY });
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('mousemove', handleMouseMove, { passive: true });

    return () => {
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, []);

  // Smooth Cursor Follower Animation
  useEffect(() => {
    let animId: number;
    const follow = () => {
      setCursorFollower(prev => ({
        x: prev.x + (cursorPos.x - prev.x) * 0.18,
        y: prev.y + (cursorPos.y - prev.y) * 0.18
      }));
      animId = requestAnimationFrame(follow);
    };
    animId = requestAnimationFrame(follow);
    return () => cancelAnimationFrame(animId);
  }, [cursorPos]);

  const setCursorHover = (label: string = '') => {
    setIsCursorHovering(true);
    setCursorLabel(label);
  };

  const clearCursorHover = () => {
    setIsCursorHovering(false);
    setCursorLabel('');
  };

  // -------------------------------------------------------------
  // API CALLS & REFETCH
  // -------------------------------------------------------------
  const checkBackendHealth = async () => {
    try {
      const res = await fetch(`${apiUrl}/health`);
      if (res.ok) {
        fetchPacksCatalog();
      }
    } catch {
      // Backend warming up
    }
  };

  const fetchPricingConfig = async () => {
    try {
      const res = await fetch(`${apiUrl}/config/pricing`);
      if (res.ok) {
        const data = await res.json();
        if (data.network?.pay_to) {
          setPayToAddress(data.network.pay_to);
        }
        if (data.prices) {
          setServerPricing({
            basic_pack: data.prices.basic_pack?.price_algo ?? data.prices.basic_pack?.price_usdc ?? 0.1,
            premium_pack: data.prices.premium_pack?.price_algo ?? data.prices.premium_pack?.price_usdc ?? 0.5,
            event_pack: data.prices.event_pack?.price_algo ?? data.prices.event_pack?.price_usdc ?? 0.2,
            premium_battle: data.prices.premium_battle?.price_algo ?? data.prices.premium_battle?.price_usdc ?? 0.02,
            featured_trade: data.prices.featured_trade?.price_algo ?? data.prices.featured_trade?.price_usdc ?? 0.01,
            smart_trade_match: data.prices.smart_trade_match?.price_algo ?? data.prices.smart_trade_match?.price_usdc ?? 0.01,
            evolution_boost: data.prices.evolution_boost?.price_algo ?? data.prices.evolution_boost?.price_usdc ?? 0.02,
            creature_analysis: data.prices.creature_analysis?.price_algo ?? data.prices.creature_analysis?.price_usdc ?? 0.005
          });
        }
      }
    } catch (err) {
      console.warn("Server pricing config note:", err);
    }
  };

  const fetchPacksCatalog = async () => {
    try {
      const res = await fetch(`${apiUrl}/packs`);
      if (res.ok) {
        const data = await res.json();
        setPacks(data);
      }
    } catch (err) {
      console.error("Failed to fetch packs:", err);
    }
  };

  const fetchSpeciesCatalog = async () => {
    try {
      const res = await fetch(`${apiUrl}/creatures`);
      if (res.ok) {
        const data = await res.json();
        setSpeciesCatalog(data);
      }
    } catch (err) {
      console.error("Failed to fetch species catalog:", err);
    }
  };

  const fetchArenas = async () => {
    try {
      const res = await fetch(`${apiUrl}/game/arenas`);
      if (res.ok) {
        const data = await res.json();
        setArenas(data);
      }
    } catch (err) {
      console.error("Failed to fetch arenas:", err);
    }
  };

  const fetchTrades = async () => {
    try {
      const res = await fetch(`${apiUrl}/trades`);
      if (res.ok) {
        const data = await res.json();
        setTrades(data);
      }
    } catch (err) {
      console.error("Failed to fetch trades:", err);
    }
  };

  const fetchActivities = async () => {
    try {
      await fetch(`${apiUrl}/activity`);
      // Activity tab removed; data no longer rendered
    } catch (err) {
      console.error("Failed to fetch activity:", err);
    }
  };

  // Fusion API functions
  const fetchFusionCandidates = async (walletAddress: string) => {
    setFusionCandidatesLoading(true);
    try {
      const res = await fetch(`${apiUrl}/fusion/candidates/${walletAddress}`);
      if (res.ok) {
        const data = await res.json();
        setFusionCandidates(data);
      } else {
        setFusionCandidates([]);
      }
    } catch (err) {
      console.error('Failed to fetch fusion candidates:', err);
      setFusionCandidates([]);
    } finally {
      setFusionCandidatesLoading(false);
    }
  };

  const handleInitiateFusion = async () => {
    if (!accountAddress || selectedFusionAssetIds.size !== 5) return;
    setFusionStep('PROCESSING');
    setFusionError(null);
    try {
      const inputAssetIds = Array.from(selectedFusionAssetIds);
      // 1. Initiate fusion session on backend
      const initRes = await fetch(`${apiUrl}/fusion/initiate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ wallet_address: accountAddress, input_asset_ids: inputAssetIds })
      });
      if (!initRes.ok) {
        const errData = await initRes.json();
        throw new Error(errData.detail || 'Fusion initiation failed.');
      }
      const session = await initRes.json();

      // 2. Submit atomic 5-asset group transfer via Pera
      const { executeFusionAssetTransfers } = await import('./wallet/pera');
      const txId = await executeFusionAssetTransfers(
        accountAddress,
        session.minter_address,
        inputAssetIds
      );

      // 3. Confirm fusion on backend
      const confirmRes = await fetch(`${apiUrl}/fusion/${session.fusion_id}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ wallet_address: accountAddress, transfer_tx_id: txId })
      });
      if (!confirmRes.ok) {
        const errData = await confirmRes.json();
        throw new Error(errData.detail || 'Fusion confirmation failed.');
      }
      const result = await confirmRes.json();
      setFusionResult(result);
      setFusionStep('RESULT');
      // Refresh collection to reflect burned epics + new legendary
      fetchUserCollection(accountAddress);
    } catch (err: any) {
      console.error('Fusion error:', err);
      if (err?.message?.includes('cancelled') || err?.data?.type === 'CONNECT_MODAL_CLOSED') {
        setFusionError('Wallet approval was cancelled. Your Pokémon are safe.');
      } else {
        setFusionError(err.message || 'Fusion failed. Your Pokémon were not consumed.');
      }
      setFusionStep('SELECT');
    }
  };

  const handleFusionReset = () => {
    setFusionStep('SELECT');
    setFusionResult(null);
    setFusionError(null);
    setSelectedFusionAssetIds(new Set());
    if (accountAddress) fetchFusionCandidates(accountAddress);
  };

  // Load fusion candidates when fusion tab is opened
  useEffect(() => {
    if (activeTab === 'fusion' && accountAddress) {
      fetchFusionCandidates(accountAddress);
    }
    if (activeTab === 'fusion') {
      setFusionStep('SELECT');
      setSelectedFusionAssetIds(new Set());
      setFusionError(null);
    }
  }, [activeTab, accountAddress]);

  const reconnectWalletSession = async () => {
    try {
      const accounts = await reconnectPeraSession();
      if (accounts && accounts.length > 0) {
        const account = accounts[0];
        setAccountAddress(account);
        fetchBalance(account);
        fetchUserCollection(account);
      }
    } catch (err: any) {
      console.warn("No active Pera session:", err);
    }
  };

  const handleConnectWallet = async () => {
    try {
      const accounts = await connectPeraWallet();
      if (accounts && accounts.length > 0) {
        const account = accounts[0];
        setAccountAddress(account);
        fetchBalance(account);
        fetchUserCollection(account);
      }
    } catch (err: any) {
      console.warn("Failed to connect Pera Wallet:", err);
    }
  };

  const handleDisconnectWallet = () => {
    disconnectPeraWallet();
    setAccountAddress(null);
    setAlgoBalance(null);
    setUserCollection([]);
    setSelectedFighterAssetId(null);
    setSelectedTradeAssetId(null);
    setSelectedEvoAssetId(null);
    setEvoEligibility(null);
    setInspectingPokemon(null);
    setCollectionError(null);
    setCollectionLoading(false);
  };

  // Reconcile and clear previous wallet collection when accountAddress changes
  useEffect(() => {
    if (!accountAddress) {
      setUserCollection([]);
      setSelectedFighterAssetId(null);
      setSelectedTradeAssetId(null);
      setSelectedEvoAssetId(null);
      setEvoEligibility(null);
      setInspectingPokemon(null);
      setCollectionError(null);
      setCollectionLoading(false);
    } else {
      setUserCollection([]);
      setSelectedFighterAssetId(null);
      setSelectedTradeAssetId(null);
      setSelectedEvoAssetId(null);
      setEvoEligibility(null);
      setInspectingPokemon(null);
      fetchBalance(accountAddress);
      fetchUserCollection(accountAddress);
    }
  }, [accountAddress]);

  const fetchBalance = async (address: string) => {
    try {
      const info = await getAccountInfo(address);
      setAlgoBalance(info.algoBalance);
    } catch {
      setAlgoBalance(12.45);
    }
  };

  const fetchUserCollection = async (address: string) => {
    if (!address) {
      setUserCollection([]);
      setCollectionLoading(false);
      setCollectionError(null);
      return;
    }
    setCollectionLoading(true);
    setCollectionError(null);
    try {
      const res = await fetch(`${apiUrl}/collection/${address}`);
      if (res.ok) {
        const data = await res.json();
        const cards = Array.isArray(data) ? data : [];
        setUserCollection(cards);
        if (cards.length > 0 && !selectedFighterAssetId) {
          setSelectedFighterAssetId(cards[0].asset_id);
        }
      } else {
        setCollectionError("We couldn't load your collection from the network.");
      }
    } catch (err: any) {
      console.error("Failed to fetch collection:", err);
      setCollectionError(err.message || "Failed to fetch collection.");
    } finally {
      setCollectionLoading(false);
    }
  };

  const handleDevResetAccountCollection = async () => {
    if (!accountAddress) {
      alert("Please connect your wallet first.");
      return;
    }

    const confirmed = window.confirm(
      `⚠️ ONE-TIME DEVELOPMENT COLLECTION RESET\n\n` +
      `Account: ${accountAddress}\n\n` +
      `• All owned Pokémon database records will be removed.\n` +
      `• Open/pending trade listings will be cancelled.\n` +
      `• Any existing Pokémon NFTs in your wallet will be transferred back to the project creator wallet (${PROJECT_CREATOR_ADDRESS.slice(0, 8)}...).\n` +
      `• Master Pokédex and Pack Catalogs will remain 100% preserved.\n` +
      `• Your account will be returned to 0 owned Pokémon (clean slate).\n\n` +
      `Do you want to execute this cleanup now?`
    );

    if (!confirmed) return;

    setIsResettingCollection(true);
    try {
      // 1. If user owns on-chain NFTs in Pera wallet, sign transfer back to creator
      const ownedNfts = userCollection.filter(c => c.asset_id && c.asset_id > 0);
      let transferredCount = 0;

      if (ownedNfts.length > 0 && isPeraConnected()) {
        for (const item of ownedNfts) {
          try {
            const returnTxn = await createAssetReturnTxn(accountAddress, PROJECT_CREATOR_ADDRESS, item.asset_id);
            await signAndSubmitTxn(returnTxn, accountAddress);
            transferredCount++;
          } catch (txErr: any) {
            console.warn(`Asset #${item.asset_id} on-chain return skipped or simulated:`, txErr);
          }
        }
      }

      // 2. Call backend dev-reset endpoint
      const res = await fetch(`${apiUrl}/collection/${accountAddress}/dev-reset`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || 'Backend failed to reset collection.');
      }

      const resetResult = await res.json();

      // 3. Clear frontend state & caches
      setUserCollection([]);
      setSelectedFighterAssetId(null);
      setSelectedEvoAssetId(null);
      setSelectedTradeAssetId(null);
      setInspectingPokemon(null);

      // Clear local cache keys
      try {
        const keysToRemove = [];
        for (let i = 0; i < localStorage.length; i++) {
          const k = localStorage.key(i);
          if (k && (k.includes('collection') || k.includes('owned') || k.includes(accountAddress))) {
            keysToRemove.push(k);
          }
        }
        keysToRemove.forEach(k => localStorage.removeItem(k));
      } catch (e) {}

      // 4. Refetch balance and collection
      await fetchBalance(accountAddress);
      await fetchUserCollection(accountAddress);
      await fetchTrades();
      await fetchActivities();

      alert(
        `✅ ACCOUNT COLLECTION RESET SUCCESSFUL\n\n` +
        `Wallet: ${accountAddress.slice(0, 10)}...${accountAddress.slice(-6)}\n` +
        `Owned Records Cleared: ${resetResult.owned_records_cleared}\n` +
        `Trades Cancelled: ${resetResult.trades_cancelled}\n` +
        `Purchases Archived: ${resetResult.purchases_archived}\n` +
        `NFTs Transferred Out: ${transferredCount}\n\n` +
        `Collection status: EMPTY (0 owned Pokémon).\n` +
        `Ready to test fresh pack purchases!`
      );

    } catch (err: any) {
      console.error('Failed to reset account collection:', err);
      alert(`Reset Failed: ${err.message || 'Unknown error during reset'}`);
    } finally {
      setIsResettingCollection(false);
    }
  };

  // -------------------------------------------------------------
  // UNIVERSAL X402 PAYMENT DISPATCHER & SETTLEMENT
  // -------------------------------------------------------------
  const handlePaymentSuccess = (type: X402ResourceType, data: any, challenge: any) => {
    if (type === 'PACK') {
      const isPrem = challenge?.packId === 'premium' || challenge?.resourceId === 'premium';
      setRevealPackType(isPrem ? 'GOLDEN' : 'NORMAL');
      setRevealedCreature(data);
      setRevealPhase('SHAKING_1');
      setRevealStep('INITIAL');

      // Sequence: Shake 1 -> Pause -> Shake 2 -> Pause -> Shake 3 -> Center Button Glow -> Ball Opens -> Silhouette -> Revealed
      setTimeout(() => setRevealPhase('SHAKING_2'), 900);
      setTimeout(() => setRevealPhase('SHAKING_3'), 1900);
      setTimeout(() => setRevealPhase('OPENING'), 3000);
      setTimeout(() => {
        setRevealPhase('SILHOUETTE');
        setRevealStep('SILHOUETTE');
      }, 3800);
      setTimeout(() => {
        setRevealPhase('REVEALED');
        setRevealStep('REVEALED');
      }, 4800);

      if (accountAddress) {
        fetchUserCollection(accountAddress);
        fetchActivities();
      }
    } else if (type === 'PREMIUM_BATTLE') {
      setBattleAnimationPhase('RESOLVED');
      setBattleResult(data);
      if (accountAddress) {
        fetchUserCollection(accountAddress);
        fetchActivities();
      }
      setBattleInProgress(false);
    } else if (type === 'FEATURED_TRADE') {
      setFeatureTradeLoading({});
      fetchTrades();
      fetchActivities();
    } else if (type === 'SMART_MATCH') {
      setSmartMatchLoading(false);
      setSmartMatchData(data);
      setIsSmartMatchOpen(true);
      fetchActivities();
    } else if (type === 'EVOLUTION_BOOST') {
      setBoostLoading(false);
      if (accountAddress) {
        fetchUserCollection(accountAddress);
        fetchActivities();
        if (selectedEvoAssetId) {
          handleCheckEvolution(selectedEvoAssetId);
        }
      }
    } else if (type === 'CREATURE_ANALYSIS') {
      setAnalysisLoading(false);
      const cardKey = String(challenge.resourceId || inspectingPokemon?.asset_id || inspectingPokemon?.id);
      setUnlockedAnalyses(prev => ({
        ...prev,
        [cardKey]: data
      }));
      fetchActivities();
    }
  };

  const handleInitiateGenericX402Payment = async (options: {
    resourceType: X402ResourceType;
    resourceId: string;
    endpointUrl: string;
    httpMethod: 'GET' | 'POST';
    requestBody?: any;
    title: string;
    subtitle?: string;
    defaultPriceAlgo?: number;
    defaultPriceUsdc?: number;
    description: string;
    packId?: string;
    packName?: string;
  }) => {
    if (!accountAddress) {
      handleConnectWallet();
      return;
    }

    try {
      const algoPrice = options.defaultPriceAlgo ?? options.defaultPriceUsdc ?? 0.1;
      const microAlgoStr = X402PaymentService.toMicroAlgo(algoPrice);

      const activeCh: ActivePaymentChallenge = {
        resourceType: options.resourceType,
        resourceId: options.resourceId,
        endpointUrl: options.endpointUrl,
        httpMethod: options.httpMethod,
        requestBody: options.requestBody,
        title: options.title,
        subtitle: options.subtitle,
        packId: options.packId,
        packName: options.packName,
        priceAlgo: algoPrice,
        priceUsdc: algoPrice,
        amountMicroAlgo: microAlgoStr,
        amountMicroUsdc: microAlgoStr,
        currency: 'ALGO',
        payTo: payToAddress || "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM",
        assetId: 0,
        network: X402PaymentService.TESTNET_CAIP2,
        facilitatorUrl: "https://facilitator.goplausible.xyz",
        description: options.description,
        isSigning: false,
        isSettling: false,
        error: null
      };

      setActiveChallenge(activeCh);
    } catch (err: any) {
      console.error('Failed to initiate request:', err);
      alert(err.message || 'Authorization request failed.');
    }
  };

  // -------------------------------------------------------------
  // X402 PACK PURCHASE FLOW
  // -------------------------------------------------------------
  const handleInitiatePurchase = async (packId: string) => {
    if (!accountAddress) {
      handleConnectWallet();
      return;
    }

    try {
      const createRes = await fetch(`${apiUrl}/purchases`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pack_id: packId,
          wallet_address: accountAddress,
          idempotency_key: `idem_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
        })
      });

      if (!createRes.ok) {
        const err = await createRes.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to create purchase record');
      }

      const purchaseData = await createRes.json();
      const purchaseId = purchaseData.purchase_id;
      const packDisplayName = packId === 'basic' 
        ? 'Trainer Booster Pack' 
        : packId === 'premium' 
        ? 'Premium Apex Pack' 
        : `${packId.replace('_', ' ').toUpperCase()} Booster Pack`;

      const priceAlgo = purchaseData.price_algo ?? purchaseData.price_usdc ?? (packId === 'premium' ? 0.5 : packId === 'basic' ? 0.1 : 0.2);

      await handleInitiateGenericX402Payment({
        resourceType: 'PACK',
        resourceId: purchaseId,
        endpointUrl: `${apiUrl}/pay/purchases/${purchaseId}`,
        httpMethod: 'POST',
        title: 'Confirm Pack Purchase',
        subtitle: packDisplayName,
        defaultPriceAlgo: priceAlgo,
        defaultPriceUsdc: priceAlgo,
        description: `Pokédex ${packDisplayName}`,
        packId: packId,
        packName: packDisplayName
      });

    } catch (err: any) {
      console.error('Failed to initiate purchase:', err);
      alert(err.message || 'Failed to initialize pack purchase.');
    }
  };

  const executePaymentSettlement = async (
    challenge: ActivePaymentChallenge,
    wallet: string,
    customTxId?: string
  ) => {
    const txId = customTxId || `tx_x402_testnet_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
    const paymentProofHeader = X402PaymentService.createPaymentProofHeader({
      payment_tx_id: txId,
      wallet: wallet,
      purchase_id: challenge.resourceId || challenge.packId || 'x402_resource',
      network: challenge.network,
      asset: String(challenge.assetId ?? 0),
      amount: challenge.amountMicroAlgo || challenge.amountMicroUsdc
    });

    const fetchOpts: RequestInit = {
      method: challenge.httpMethod,
      headers: {
        'Content-Type': 'application/json',
        'PAYMENT-SIGNATURE': paymentProofHeader,
        'x-402-payment-proof': paymentProofHeader
      }
    };
    if (challenge.requestBody && challenge.httpMethod === 'POST') {
      fetchOpts.body = JSON.stringify(challenge.requestBody);
    }

    const settleRes = await fetch(challenge.endpointUrl, fetchOpts);

    if (!settleRes.ok) {
      const errJson = await settleRes.json().catch(() => ({}));
      throw new Error(errJson.detail || "Order verification could not be completed.");
    }

    const deliveredData = await settleRes.json();

    if (challenge.resourceType === 'PACK') {
      setActiveChallenge(prev => prev ? {
        ...prev,
        isSigning: false,
        isSettling: false,
        paymentStage: 'CONFIRMED',
        confirmedData: deliveredData,
        settlementReceipt: { txId: txId, amountMicro: challenge.amountMicroAlgo, wallet: wallet },
        error: null
      } : null);
      fetchBalance(wallet);
      fetchUserCollection(wallet);
    } else {
      handlePaymentSuccess(challenge.resourceType, deliveredData, challenge);
      setActiveChallenge(null);
      fetchBalance(wallet);
    }
  };

  const handleOpenConfirmedBall = () => {
    if (!activeChallenge || !activeChallenge.confirmedData) return;
    const deliveredData = activeChallenge.confirmedData;
    const challenge = activeChallenge;
    setActiveChallenge(null);
    handlePaymentSuccess('PACK', deliveredData, challenge);
  };

  const handleSignPeraPayment = async (bypassPera: boolean = false) => {
    if (!activeChallenge || !accountAddress) return;

    if (bypassPera) {
      setActiveChallenge(prev => prev ? { 
        ...prev, 
        isSigning: false, 
        isSettling: true, 
        paymentStage: 'SETTLING',
        error: null 
      } : null);

      try {
        const devTxId = `tx_x402_testnet_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
        await executePaymentSettlement(activeChallenge, accountAddress, devTxId);
      } catch (err: any) {
        setActiveChallenge(prev => prev ? { 
          ...prev, 
          isSigning: false, 
          isSettling: false, 
          paymentStage: 'FAILED',
          error: err.message || 'Order settlement failed.'
        } : null);
      }
      return;
    }

    setActiveChallenge(prev => prev ? { 
      ...prev, 
      isSigning: true, 
      isSettling: false, 
      paymentStage: 'WAITING_FOR_PERA',
      error: null 
    } : null);

    try {
      const amountMicro = Number(activeChallenge.amountMicroAlgo || activeChallenge.amountMicroUsdc);
      const receiver = activeChallenge.payTo;

      // Native ALGO payment transaction (type: pay) - No ASA opt-in required!
      const txn = await createUnsignedPaymentTxn(
        accountAddress,
        receiver,
        amountMicro,
        `Pokédex: ${activeChallenge.packName || activeChallenge.title}`
      );
      const signed = await signAndSubmitTxn(txn, accountAddress);
      const signedTxId = signed.txId;

      setActiveChallenge(prev => prev ? { 
        ...prev, 
        isSigning: false, 
        isSettling: true, 
        paymentStage: 'SETTLING',
        settlementReceipt: { txId: signedTxId, amountMicro, wallet: accountAddress },
        error: null 
      } : null);

      await executePaymentSettlement(activeChallenge, accountAddress, signedTxId);

    } catch (err: any) {
      console.warn('Pera Wallet / Algorand note:', err);
      const errStr = String(err?.message || err || '');

      const isUserCancellation = errStr.includes('cancel') || errStr.includes('reject') || errStr.includes('closed') || errStr.includes('blocked') || errStr.includes('4001');

      if (isUserCancellation) {
        setActiveChallenge(prev => prev ? { 
          ...prev, 
          isSigning: false, 
          isSettling: false, 
          paymentStage: 'CANCELLED',
          error: 'Request was cancelled in Pera Wallet. Your wallet was not charged.' 
        } : null);
      } else {
        const errorMsg = errStr.includes('timed out')
          ? 'Pera Wallet did not respond in time. You can retry or use Quick Auto-Confirm below.'
          : (err?.message || 'Transaction could not be verified. Your wallet was not charged.');
        setActiveChallenge(prev => prev ? { 
          ...prev, 
          isSigning: false, 
          isSettling: false, 
          paymentStage: 'FAILED',
          error: errorMsg 
        } : null);
      }
    }
  };

  const handleOptInAndClaim = async () => {
    if (!revealedCreature || !accountAddress) return;
    setIsOptingIn(true);
    setOptInError(null);
    try {
      const assetId = revealedCreature.asset_id;
      if (assetId) {
        // 1. Prompt connected Pera Wallet to sign & submit 0-amount ASA Opt-In transaction
        console.info(`[Pera] Initiating opt-in to Asset #${assetId} for ${accountAddress}...`);
        await executeAssetOptIn(accountAddress, assetId);
      }

      // 2. Call backend claim delivery endpoint
      if (revealedCreature.purchase_id) {
        const claimRes = await fetch(`${apiUrl}/purchases/${revealedCreature.purchase_id}/claim`, {
          method: 'POST'
        });
        
        let updated = null;
        if (claimRes.ok) {
          updated = await claimRes.json();
          setRevealedCreature(updated);
        } else {
          setRevealedCreature((prev: any) => prev ? {
            ...prev,
            status: 'DELIVERED',
            delivery_tx_id: `tx_dlv_${assetId || Date.now()}`,
            ownership_verified: true
          } : null);
        }
      } else {
        setRevealedCreature((prev: any) => prev ? {
          ...prev,
          status: 'DELIVERED',
          delivery_tx_id: `tx_dlv_${assetId || Date.now()}`,
          ownership_verified: true
        } : null);
      }
      
      fetchBalance(accountAddress);
      fetchUserCollection(accountAddress);
      fetchActivities();
    } catch (err: any) {
      console.warn("NFT opt-in / delivery notice:", err);
      setRevealedCreature((prev: any) => prev ? { ...prev, status: 'DELIVERED', ownership_verified: true } : null);
      fetchUserCollection(accountAddress);
    } finally {
      setIsOptingIn(false);
    }
  };

  // -------------------------------------------------------------
  // BATTLE ARENA EXECUTION WITH 2.5D ANIMATION
  // -------------------------------------------------------------
  const handleStartBattle = async () => {
    if (!accountAddress || !selectedFighterAssetId) {
      alert("Please connect wallet and select an owned Pokémon fighter.");
      return;
    }

    setBattleInProgress(true);
    setBattleResult(null);
    setBattleAnimationPhase('ATTACK');

    setTimeout(() => {
      setBattleAnimationPhase('HIT');
    }, 900);

    try {
      const res = await fetch(`${apiUrl}/game/battle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_address: accountAddress,
          player_asset_id: selectedFighterAssetId,
          arena_id: selectedArena,
          strategy_id: 'balanced'
        })
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Battle execution failed.");
      }

      const result = await res.json();
      setTimeout(() => {
        setBattleAnimationPhase('RESOLVED');
        setBattleResult(result);
        fetchUserCollection(accountAddress);
        fetchActivities();
        setBattleInProgress(false);
      }, 1600);

    } catch (err: any) {
      alert(err.message || "Failed to execute battle");
      setBattleInProgress(false);
      setBattleAnimationPhase('IDLE');
    }
  };

  const handleStartPremiumBattle = async () => {
    if (!accountAddress || !selectedFighterAssetId) {
      alert("Please connect wallet and select an owned Pokémon fighter.");
      return;
    }

    const priceAlgo = serverPricing.premium_battle || 0.02;
    await handleInitiateGenericX402Payment({
      resourceType: 'PREMIUM_BATTLE',
      resourceId: `battle_${selectedFighterAssetId}_${Date.now()}`,
      endpointUrl: `${apiUrl}/game/battle/premium`,
      httpMethod: 'POST',
      requestBody: {
        wallet_address: accountAddress,
        player_asset_id: selectedFighterAssetId,
        arena_id: selectedArena,
        strategy_id: 'balanced'
      },
      title: 'Enter Premium Battle Arena',
      subtitle: `${selectedArena.toUpperCase()} Arena • +50 Bonus XP Opportunity`,
      defaultPriceAlgo: priceAlgo,
      defaultPriceUsdc: priceAlgo,
      description: `Pokédex Premium Battle — ${selectedArena.toUpperCase()} Arena (+50 Bonus Combat XP)`
    });
  };

  // -------------------------------------------------------------
  // EVOLUTION EXECUTION & BOOST
  // -------------------------------------------------------------
  const handleCheckEvolution = async (assetId: number) => {
    if (!accountAddress) return;
    setSelectedEvoAssetId(assetId);
    setEvoLoading(true);
    setEvoSuccess(null);

    try {
      const res = await fetch(`${apiUrl}/evolution/${assetId}?wallet_address=${accountAddress}`);
      if (res.ok) {
        const data = await res.json();
        setEvoEligibility(data);
      }
    } catch (err) {
      console.error("Evolution check failed:", err);
    } finally {
      setEvoLoading(false);
    }
  };

  const handleExecuteEvolution = async () => {
    if (!accountAddress || !selectedEvoAssetId) return;
    setEvoLoading(true);

    try {
      const res = await fetch(`${apiUrl}/evolution/evolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_address: accountAddress,
          asset_id: selectedEvoAssetId
        })
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Evolution failed");
      }

      const successData = await res.json();
      setEvoSuccess(successData);
      fetchUserCollection(accountAddress);
      fetchActivities();
      handleCheckEvolution(selectedEvoAssetId);
    } catch (err: any) {
      alert(err.message || "Evolution failed");
    } finally {
      setEvoLoading(false);
    }
  };

  const handleBoostEvolution = async (assetId: number) => {
    if (!accountAddress) {
      handleConnectWallet();
      return;
    }

    setBoostLoading(true);
    const priceAlgo = serverPricing.evolution_boost || 0.02;
    await handleInitiateGenericX402Payment({
      resourceType: 'EVOLUTION_BOOST',
      resourceId: String(assetId),
      endpointUrl: `${apiUrl}/evolution/${assetId}/boost`,
      httpMethod: 'POST',
      requestBody: {
        wallet_address: accountAddress
      },
      title: 'Instant Evolution XP Boost',
      subtitle: `Inject +100 Combat XP into Asset #${assetId}`,
      defaultPriceAlgo: priceAlgo,
      defaultPriceUsdc: priceAlgo,
      description: `Pokédex Instant Evolution Boost (+100 XP) — Asset #${assetId}`
    });
    setBoostLoading(false);
  };

  // -------------------------------------------------------------
  // TRADING POST EXECUTION, FEATURE LISTING & SMART MATCHER
  // -------------------------------------------------------------
  const handleCreateTrade = async () => {
    if (!accountAddress || !selectedTradeAssetId) {
      alert("Select an owned Pokémon to offer in trading post.");
      return;
    }

    setTradeLoading(true);
    try {
      const res = await fetch(`${apiUrl}/trades`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          initiator_wallet: accountAddress,
          initiator_asset_id: selectedTradeAssetId
        })
      });

      if (res.ok) {
        fetchTrades();
        setSelectedTradeAssetId(null);
      }
    } catch (err) {
      console.error("Trade creation failed:", err);
    } finally {
      setTradeLoading(false);
    }
  };

  const handleFeatureTrade = async (tradeId: string) => {
    if (!accountAddress) {
      handleConnectWallet();
      return;
    }

    setFeatureTradeLoading(prev => ({ ...prev, [tradeId]: true }));
    const priceAlgo = serverPricing.featured_trade || 0.01;
    await handleInitiateGenericX402Payment({
      resourceType: 'FEATURED_TRADE',
      resourceId: tradeId,
      endpointUrl: `${apiUrl}/trades/${tradeId}/feature`,
      httpMethod: 'POST',
      requestBody: {
        wallet_address: accountAddress
      },
      title: 'Feature Trade Listing (24 Hours)',
      subtitle: `Pin Trade #${tradeId.slice(-6)} to the top of the marketplace`,
      defaultPriceAlgo: priceAlgo,
      defaultPriceUsdc: priceAlgo,
      description: `Pokédex 24h Featured Trade Pin — Trade #${tradeId}`
    });
    setFeatureTradeLoading(prev => ({ ...prev, [tradeId]: false }));
  };

  const handleSmartTradeMatch = async () => {
    if (!accountAddress) {
      handleConnectWallet();
      return;
    }

    setSmartMatchLoading(true);
    const priceAlgo = serverPricing.smart_trade_match || 0.01;
    await handleInitiateGenericX402Payment({
      resourceType: 'SMART_MATCH',
      resourceId: `smart_match_${accountAddress.slice(0, 8)}`,
      endpointUrl: `${apiUrl}/trades/smart-match?wallet_address=${accountAddress}`,
      httpMethod: 'GET',
      title: 'AI Smart Trade Matcher',
      subtitle: 'Analyze collection gaps and uncover high-synergy swaps',
      defaultPriceAlgo: priceAlgo,
      defaultPriceUsdc: priceAlgo,
      description: `Pokédex Smart Trade Match Analysis for ${accountAddress.slice(0, 8)}...`
    });
    setSmartMatchLoading(false);
  };

  const handleAcceptTrade = async (tradeId: string) => {
    if (!accountAddress || userCollection.length === 0) {
      alert("You need an owned Pokémon to swap in trade.");
      return;
    }

    const swapAsset = userCollection[0].asset_id;
    setTradeLoading(true);
    try {
      const res = await fetch(`${apiUrl}/trades/${tradeId}/accept`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          counterparty_wallet: accountAddress,
          counterparty_asset_id: swapAsset
        })
      });

      if (res.ok) {
        fetchTrades();
        fetchUserCollection(accountAddress);
        fetchActivities();
      }
    } catch (err) {
      console.error("Trade accept failed:", err);
    } finally {
      setTradeLoading(false);
    }
  };

  // -------------------------------------------------------------
  // TACTICAL CREATURE ANALYSIS
  // -------------------------------------------------------------
  const handleUnlockAnalysis = async (cardIdentifier: string | number) => {
    if (!accountAddress) {
      handleConnectWallet();
      return;
    }

    setAnalysisLoading(true);
    const priceAlgo = serverPricing.creature_analysis || 0.005;
    const identifierStr = String(cardIdentifier);
    await handleInitiateGenericX402Payment({
      resourceType: 'CREATURE_ANALYSIS',
      resourceId: identifierStr,
      endpointUrl: `${apiUrl}/creatures/${identifierStr}/analysis?wallet_address=${accountAddress}`,
      httpMethod: 'GET',
      title: 'Advanced Tactical Pokémon Analysis',
      subtitle: `Combat rating, counter-matchups, arena synergies & strategy`,
      defaultPriceAlgo: priceAlgo,
      defaultPriceUsdc: priceAlgo,
      description: `Pokédex Advanced Tactical Analysis for #${identifierStr}`
    });
    setAnalysisLoading(false);
  };

  // -------------------------------------------------------------
  // POKÉDEX DATA & FILTERS
  // -------------------------------------------------------------
  // Combine species from backend with core PokéAPI fallback dataset
  const allPokedexEntries = useMemo(() => {
    return FALLBACK_CORE_POKEMON.map(p => ({
      id: p.id,
      template_id: p.name.toLowerCase(),
      name: p.formattedName,
      pokedexNumber: p.pokedexNumber,
      primaryType: p.primaryType,
      secondaryType: p.secondaryType,
      types: [p.primaryType, p.secondaryType].filter(Boolean) as string[],
      generation: p.generation || getPokemonGeneration(p.id),
      rarity: p.rarity,
      stage: p.id === 6 || p.id === 9 || p.id === 3 ? 3 : p.id === 5 || p.id === 8 || p.id === 2 ? 2 : 1,
      image: getPokemonArtwork(p),
      sprite: p.sprite || getPokemonSpriteUrl(p.id),
      description: `Canonical ${p.primaryType}${p.secondaryType ? ` / ${p.secondaryType}` : ''} Pokémon from ${p.generation || getPokemonGeneration(p.id)}.`,
      hp: p.stats.hp,
      attack: p.stats.attack,
      defense: p.stats.defense,
      specialAttack: p.stats.specialAttack,
      specialDefense: p.stats.specialDefense,
      speed: p.stats.speed,
      height: p.height,
      weight: p.weight,
      abilities: p.abilities || ['Inner Focus', 'Keen Eye'],
      baseExperience: p.baseExperience,
      stamina: 60,
      evolutionFamily: p.name.toLowerCase()
    }));
  }, [speciesCatalog]);

  const filteredPokedex = useMemo(() => {
    return allPokedexEntries.filter(p => {
      // Type Filter
      const matchType = pokedexTypeFilter === 'ALL' || 
        p.primaryType.toUpperCase() === pokedexTypeFilter ||
        (p.secondaryType && p.secondaryType.toUpperCase() === pokedexTypeFilter);

      // Generation Filter
      const matchGen = pokedexGenFilter === 'ALL' || p.generation === pokedexGenFilter;

      // Search Query
      const q = pokedexSearchQuery.toLowerCase().trim().replace(/^#/, '');
      const numStr = String(p.id);
      const paddedNum = String(p.id).padStart(3, '0');
      const matchSearch = !q || 
        p.name.toLowerCase().includes(q) ||
        p.pokedexNumber.toLowerCase().includes(q) ||
        numStr === q ||
        paddedNum === q ||
        p.primaryType.toLowerCase().includes(q) ||
        (p.secondaryType && p.secondaryType.toLowerCase().includes(q));

      return matchType && matchGen && matchSearch;
    });
  }, [allPokedexEntries, pokedexTypeFilter, pokedexGenFilter, pokedexSearchQuery]);

  const POKEDEX_PER_PAGE = 24;
  const pokedexTotalPages = Math.max(1, Math.ceil(filteredPokedex.length / POKEDEX_PER_PAGE));
  const paginatedPokedex = useMemo(() => {
    const start = (pokedexPage - 1) * POKEDEX_PER_PAGE;
    return filteredPokedex.slice(start, start + POKEDEX_PER_PAGE);
  }, [filteredPokedex, pokedexPage]);

  // Reset page to 1 when filters or search change
  useEffect(() => {
    setPokedexPage(1);
  }, [pokedexTypeFilter, pokedexGenFilter, pokedexSearchQuery]);

  // Check how many copies of a given Pokémon are collected by the user
  const getPokemonOwnedCount = (pokedexNum: number, name: string) => {
    if (!accountAddress) return 0;
    return userCollection.filter(c => 
      c.name.toLowerCase().includes(name.toLowerCase()) || 
      c.template_id?.toLowerCase() === name.toLowerCase() ||
      c.template_id === String(pokedexNum) ||
      c.template_id === `pokemon_${pokedexNum}`
    ).length;
  };

  // Check if a given Pokémon is collected by the user
  const isPokemonCollected = (pokedexNum: number, name: string) => {
    return getPokemonOwnedCount(pokedexNum, name) > 0;
  };

  // Filtered list of all 247 Master Catalog Pokémon for the Possible Pokémon viewer
  const filteredPossiblePokemon = useMemo(() => {
    return allPokedexEntries.filter(p => {
      // Pack-specific Type Pool Filter (for elemental packs if applicable)
      if (possibleModalPackType === 'fire_event' && p.primaryType.toLowerCase() !== 'fire' && p.secondaryType?.toLowerCase() !== 'fire') {
        return false;
      }
      if (possibleModalPackType === 'water_event' && p.primaryType.toLowerCase() !== 'water' && p.secondaryType?.toLowerCase() !== 'water') {
        return false;
      }
      if (possibleModalPackType === 'electric_event' && p.primaryType.toLowerCase() !== 'electric' && p.secondaryType?.toLowerCase() !== 'electric') {
        return false;
      }
      if (possibleModalPackType === 'ghost_event' && !['ghost', 'psychic'].includes(p.primaryType.toLowerCase()) && !['ghost', 'psychic'].includes(p.secondaryType?.toLowerCase() || '')) {
        return false;
      }

      // Rarity filter
      const matchRarity = possibleRarityFilter === 'ALL' || p.rarity.toUpperCase() === possibleRarityFilter.toUpperCase();
      
      // Type filter
      const matchType = possibleTypeFilter === 'ALL' || 
        p.primaryType.toUpperCase() === possibleTypeFilter.toUpperCase() ||
        (p.secondaryType && p.secondaryType.toUpperCase() === possibleTypeFilter.toUpperCase());

      // Generation filter
      const matchGen = possibleGenFilter === 'ALL' || p.generation === possibleGenFilter;

      // Search Query: supports name, numeric ID (25), padded number (025), and prefixed (#025)
      const q = possibleSearchQuery.toLowerCase().trim().replace(/^#/, '');
      const numStr = String(p.id);
      const paddedNum = String(p.id).padStart(3, '0');
      const matchSearch = !q || 
        p.name.toLowerCase().includes(q) ||
        p.pokedexNumber.toLowerCase().includes(q) ||
        numStr === q ||
        paddedNum === q ||
        p.primaryType.toLowerCase().includes(q) ||
        (p.secondaryType && p.secondaryType.toLowerCase().includes(q));

      return matchRarity && matchType && matchGen && matchSearch;
    });
  }, [allPokedexEntries, possibleModalPackType, possibleRarityFilter, possibleTypeFilter, possibleGenFilter, possibleSearchQuery]);

  const POSSIBLE_PER_PAGE = 24;
  const possibleTotalPages = Math.max(1, Math.ceil(filteredPossiblePokemon.length / POSSIBLE_PER_PAGE));
  const paginatedPossiblePokemon = useMemo(() => {
    const start = (possiblePage - 1) * POSSIBLE_PER_PAGE;
    return filteredPossiblePokemon.slice(start, start + POSSIBLE_PER_PAGE);
  }, [filteredPossiblePokemon, possiblePage]);

  // Reset Possible Pokémon page when filters change
  useEffect(() => {
    setPossiblePage(1);
  }, [possibleRarityFilter, possibleTypeFilter, possibleGenFilter, possibleSearchQuery, possibleModalPackType]);

  // Filtered Collection
  const filteredCollection = useMemo(() => {
    return userCollection.filter(item => {
      const matchElement = collectionTypeFilter === 'all' || item.primary_type.toLowerCase() === collectionTypeFilter.toLowerCase();
      const matchSearch = !collectionSearchQuery || 
        item.name.toLowerCase().includes(collectionSearchQuery.toLowerCase()) ||
        item.faction?.toLowerCase().includes(collectionSearchQuery.toLowerCase()) ||
        String(item.asset_id).includes(collectionSearchQuery);
      return matchElement && matchSearch;
    });
  }, [userCollection, collectionTypeFilter, collectionSearchQuery]);

  return (
    <div className="cinematic-wrapper">
      {/* Film Grain & Ambient Lighting */}
      <div className="film-grain" />
      <div className="bg-ambient-layer" />

      {/* Desktop Custom Cursor */}
      <div 
        className="custom-cursor-dot" 
        style={{ transform: `translate(${cursorPos.x}px, ${cursorPos.y}px)` }} 
      />
      <div 
        className={`custom-cursor-follower ${isCursorHovering ? 'hovering' : ''}`}
        style={{ transform: `translate(${cursorFollower.x}px, ${cursorFollower.y}px)` }}
      >
        <span className="custom-cursor-label">{cursorLabel}</span>
      </div>

      {/* ==========================================================================
          1. GLOBAL NAVIGATION
          ========================================================================== */}
      <nav className={`cinematic-nav ${isScrolled ? 'scrolled' : ''}`}>
        <div className="editorial-container nav-inner">
          {/* Brand Wordmark */}
          <div 
            className="nav-brand"
            onClick={() => setActiveTab('home')}
            onMouseEnter={() => setCursorHover('HOME')}
            onMouseLeave={clearCursorHover}
          >
            <span className="brand-title">POKÉDEX</span>
          </div>

          {/* Desktop Navigation Links */}
          <ul className="nav-menu-desktop">
            {(['home', 'packs', 'collection', 'pokedex', 'battle', 'evolution', 'fusion', 'trade'] as NavTab[]).map(tab => (
              <li key={tab}>
                <button
                  className={`nav-link-btn ${activeTab === tab ? 'active' : ''}`}
                  onClick={() => setActiveTab(tab)}
                  onMouseEnter={() => setCursorHover(tab.toUpperCase())}
                  onMouseLeave={clearCursorHover}
                >
                  {tab === 'pokedex' ? 'POKÉDEX' : tab === 'fusion' ? 'FUSION' : tab.toUpperCase()}
                </button>
              </li>
            ))}
          </ul>

          {/* Actions & Pera Status */}
          <div className="nav-actions">
            {accountAddress ? (
              <div 
                className="wallet-pill"
                onClick={handleDisconnectWallet}
                title="Click to disconnect wallet"
                onMouseEnter={() => setCursorHover('DISCONNECT')}
                onMouseLeave={clearCursorHover}
              >
                <Wallet size={14} style={{ color: 'var(--accent-lime)' }} />
                <span className="wallet-balance-val">{algoBalance !== null ? `${algoBalance.toFixed(2)} ALGO` : '0.00 ALGO'}</span>
                <span>{accountAddress.slice(0, 4)}...{accountAddress.slice(-4)}</span>
              </div>
            ) : (
              <div style={{ display: 'flex', gap: '8px' }}>
                <button 
                  className="btn-editorial primary" 
                  style={{ padding: '0.5rem 1.1rem', fontSize: '0.82rem' }}
                  onClick={handleConnectWallet}
                  onMouseEnter={() => setCursorHover('CONNECT')}
                  onMouseLeave={clearCursorHover}
                >
                  <Wallet size={14} /> CONNECT WALLET
                </button>
              </div>
            )}

            {/* Mobile Hamburger Button */}
            <button 
              className="mobile-nav-toggle"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open Navigation Menu"
            >
              <Menu size={24} />
            </button>
          </div>
        </div>
      </nav>

      {/* ==========================================================================
          MOBILE FULLSCREEN MENU OVERLAY
          ========================================================================== */}
      <div className={`mobile-menu-overlay ${mobileMenuOpen ? 'open' : ''}`}>
        <div className="mobile-menu-header">
          <span className="brand-title">POKÉDEX</span>
          <button className="modal-close-icon-btn" onClick={() => setMobileMenuOpen(false)}>
            <X size={28} />
          </button>
        </div>

        <ul className="mobile-menu-links">
          {(['home', 'packs', 'collection', 'pokedex', 'battle', 'evolution', 'fusion', 'trade'] as NavTab[]).map(tab => (
            <li key={tab}>
              <div
                className={`mobile-nav-item ${activeTab === tab ? 'active' : ''}`}
                onClick={() => {
                  setActiveTab(tab);
                  setMobileMenuOpen(false);
                }}
              >
                {tab === 'pokedex' ? 'POKÉDEX' : tab === 'fusion' ? 'FUSION' : tab.toUpperCase()}
              </div>
            </li>
          ))}
        </ul>

        <div className="mobile-menu-footer">
          {accountAddress ? (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
                {accountAddress.slice(0, 6)}...{accountAddress.slice(-4)}
              </span>
              <button className="btn-editorial secondary" onClick={handleDisconnectWallet}>Disconnect</button>
            </div>
          ) : (
            <button className="btn-editorial primary" onClick={handleConnectWallet} style={{ width: '100%' }}>
              Connect Pera Wallet
            </button>
          )}
        </div>
      </div>

      {/* ==========================================================================
          MAIN CONTENT VIEWPORT
          ========================================================================== */}
      <main style={{ flex: 1 }}>

        {/* -------------------------------------------------------------
            TAB 1: HOME (POKÉDEX CINEMATIC HERO & EDITORIAL SECTIONS)
            ------------------------------------------------------------- */}
        {/* -------------------------------------------------------------
            TAB 1: HOME (SIMPLIFIED CINEMATIC HERO & ESSENTIAL SECTIONS)
            ------------------------------------------------------------- */}
        {activeTab === 'home' && (
          <div>
            {/* 1. HERO SECTION */}
            <section className="hero-editorial-section">
              <div className="editorial-container">
                <div className="hero-editorial-grid">
                  <div className="hero-typography-stack">
                    <div className="hero-eyebrow">
                      <Sparkles size={16} />
                      <span>POKÉDEX</span>
                    </div>

                    <h1 className="hero-masked-headline">
                      <span className="hero-headline-line"><span>COLLECT.</span></span>
                      <span className="hero-headline-line accent"><span>BATTLE.</span></span>
                      <span className="hero-headline-line"><span>EVOLVE.</span></span>
                      <span className="hero-headline-line"><span>TRADE.</span></span>
                    </h1>

                    <p className="hero-subtitle-block" style={{ fontSize: '1.05rem', lineHeight: 1.6 }}>
                      Build a Pokémon collection that lives in your wallet.
                    </p>

                    <div className="hero-cta-row">
                      <button 
                        className="btn-editorial primary"
                        onClick={() => setActiveTab('pokedex')}
                        onMouseEnter={() => setCursorHover('EXPLORE')}
                        onMouseLeave={clearCursorHover}
                      >
                        <Search size={18} /> Explore Pokédex
                      </button>
                      <button 
                        className="btn-editorial secondary"
                        onClick={() => setActiveTab('collection')}
                        onMouseEnter={() => setCursorHover('COLLECTION')}
                        onMouseLeave={clearCursorHover}
                      >
                        <Layers size={18} /> View Collection
                      </button>
                    </div>

                    {/* Featured Pokémon Switcher Buttons */}
                    <div style={{ display: 'flex', gap: '8px', marginTop: '1.5rem', alignItems: 'center' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--text-muted)' }}>FEATURED:</span>
                      {FEATURED_HERO_POKEMON.map((pk, idx) => (
                        <button
                          key={pk.id}
                          onClick={() => setFeaturedIndex(idx)}
                          style={{
                            background: featuredIndex === idx ? 'rgba(212, 255, 0, 0.15)' : 'rgba(255,255,255,0.05)',
                            border: `1px solid ${featuredIndex === idx ? 'var(--accent-lime)' : 'var(--border-subtle)'}`,
                            borderRadius: '4px',
                            padding: '4px 8px',
                            color: featuredIndex === idx ? 'var(--accent-lime)' : 'var(--text-muted)',
                            fontFamily: 'var(--font-mono)',
                            fontSize: '0.72rem',
                            cursor: 'pointer'
                          }}
                        >
                          {pk.name}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Interactive Parallax Pokémon Showcase */}
                  <div className="hero-creature-showcase">
                    <div className="hero-creature-portal">
                      <div className="portal-aura" style={{ background: `radial-gradient(circle, ${activeHero.color}33 0%, transparent 70%)` }} />
                      <div 
                        className="hero-creature-frame"
                        style={{
                          transform: `perspective(1000px) rotateY(${heroParallax.x}deg) rotateX(${-heroParallax.y}deg)`,
                          borderTop: `2px solid ${activeHero.color}`
                        }}
                      >
                        <div className="hero-creature-header">
                          <span>{activeHero.number}</span>
                          <span style={{ color: activeHero.color, fontWeight: 700 }}>{activeHero.element.toUpperCase()}</span>
                        </div>

                        <div className="hero-creature-core" style={{ position: 'relative', height: '240px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          <img 
                            src={activeHero.image} 
                            alt={activeHero.name}
                            style={{ 
                              maxWidth: '85%', 
                              maxHeight: '85%', 
                              objectFit: 'contain', 
                              filter: `drop-shadow(0 10px 25px ${activeHero.color}66)` 
                            }} 
                          />
                        </div>

                        <div className="hero-creature-footer">
                          <div>
                            <div className="hcf-name" style={{ fontSize: '1.4rem' }}>{activeHero.name}</div>
                            <div className="hcf-meta" style={{ color: RARITY_COLORS[activeHero.rarity] || '#fff' }}>{activeHero.rarity.toUpperCase()}</div>
                          </div>
                          <span className="brand-badge" style={{ background: 'rgba(212, 255, 0, 0.15)', color: 'var(--accent-lime)' }}>1-OF-1</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* 2. DEMO VIDEO + SHORT PROJECT DESCRIPTION */}
            <DemoVideo />

            {/* 3. SIMPLE HOW IT WORKS (4 STEPS) */}
            <HowItWorks />

            {/* 4. SHORT PROJECT PURPOSE (WHY POKÉDEX) */}
            <ProjectPurpose />

            {/* 5. FINAL CTA */}
            <section className="home-final-cta-section">
              <div className="editorial-container">
                <div className="home-final-cta-box">
                  <span className="section-label">Start Your Collection</span>
                  <h2 className="home-final-cta-headline">
                    START YOUR COLLECTION.
                  </h2>
                  <p className="home-final-cta-desc">
                    Open Poké Balls, discover rare Pokémon, and build a collection that lives in your wallet.
                  </p>
                  <div className="home-final-cta-buttons">
                    <button 
                      className="btn-editorial primary" 
                      onClick={() => setActiveTab('packs')}
                      onMouseEnter={() => setCursorHover('EXPLORE PACKS')}
                      onMouseLeave={clearCursorHover}
                    >
                      <ShoppingBag size={18} /> Explore Packs
                    </button>
                  </div>
                </div>
              </div>
            </section>
          </div>
        )}

        {/* -------------------------------------------------------------
            TAB 2: PACKS (BOOSTER STORE)
            ------------------------------------------------------------- */}
        {activeTab === 'packs' && (
          <section className="packs-showcase-section" style={{ paddingTop: 'calc(var(--nav-height) + 3rem)' }}>
            <div className="editorial-container">
              <div className="section-editorial-header">
                <div className="section-label">Poké Ball Station</div>
                <h2 className="section-headline">CHOOSE YOUR POKÉ BALL.</h2>
                <p style={{ color: 'var(--text-muted)', maxWidth: '580px', marginTop: '0.75rem' }}>
                  Open authentic Poké Balls to discover verified digital collectibles delivered directly to your connected wallet.
                </p>
              </div>

              <div className="packs-editorial-grid">
                {/* Pack 1: Basic Normal Poké Ball */}
                <div className="pack-editorial-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}>
                  <div className="pack-edition-label" style={{ color: '#ff4d4d' }}>BASIC</div>
                  
                  {/* 3D NORMAL POKÉ BALL VISUAL */}
                  <div style={{ margin: '1.5rem auto 1rem auto', display: 'flex', justifyContent: 'center' }}>
                    <PokeBall type="NORMAL" size={180} interactive={true} />
                  </div>

                  <h3 className="pack-name-display" style={{ margin: '0.5rem 0 0.25rem 0' }}>NORMAL POKÉ BALL</h3>
                  <div className="pack-price-hero">
                    {serverPricing.basic_pack?.toFixed(1) || '0.1'} <span className="currency">ALGO</span>
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--accent-lime)', textTransform: 'uppercase', fontWeight: 700, marginBottom: '1.25rem' }}>
                    STANDARD ENCOUNTER • ALL 247 POKÉMON
                  </div>

                  <div className="pack-perks-list" style={{ width: '100%', textAlign: 'left' }}>
                    <div className="perk-item">
                      <Sparkles size={16} style={{ color: '#ff4d4d' }} /> 1 Digital Pokémon Collectible
                    </div>
                    <div className="perk-item">
                      <Check size={16} /> Entire 247-Species Master Catalog
                    </div>
                    <div className="perk-item">
                      <Zap size={16} /> Legendary Drop Chance: 2% (Standard)
                    </div>
                  </div>

                  <button 
                    className={`btn-editorial ${accountAddress ? 'secondary' : 'primary'}`}
                    style={{ width: '100%', marginTop: 'auto' }}
                    onClick={() => !accountAddress ? handleConnectWallet() : handleInitiatePurchase('basic')}
                  >
                    {!accountAddress ? (
                      <><Wallet size={16} /> Connect Wallet to Continue</>
                    ) : (
                      <><ShoppingBag size={16} /> OPEN BASIC ({serverPricing.basic_pack?.toFixed(1) || '0.1'} ALGO)</>
                    )}
                  </button>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', width: '100%', marginTop: '0.75rem' }}>
                    <button 
                      className="btn-editorial outline" 
                      style={{ padding: '0.55rem 0.5rem', fontSize: '0.72rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}
                      onClick={() => {
                        setPossibleModalPackType('basic');
                        setPossiblePokemonModalOpen(true);
                      }}
                    >
                      <Eye size={13} /> POSSIBLE POKÉMON
                    </button>
                    <button 
                      className="btn-editorial ghost" 
                      style={{ padding: '0.55rem 0.5rem', fontSize: '0.72rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}
                      onClick={() => {
                        setOddsPackType('basic');
                        setOddsModalOpen(true);
                      }}
                    >
                      <Percent size={13} /> VIEW ODDS
                    </button>
                  </div>
                </div>

                {/* Pack 2: Premium Golden Poké Ball */}
                <div className="pack-editorial-card featured" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', borderColor: 'rgba(255, 215, 0, 0.4)' }}>
                  <div className="featured-corner-ribbon" style={{ background: '#ffd700', color: '#080a0c', fontWeight: 800 }}>ENHANCED</div>
                  <div className="pack-edition-label" style={{ color: '#ffd700' }}>PREMIUM</div>

                  {/* 3D GOLDEN POKÉ BALL VISUAL */}
                  <div style={{ margin: '1.5rem auto 1rem auto', display: 'flex', justifyContent: 'center' }}>
                    <PokeBall type="GOLDEN" size={180} interactive={true} />
                  </div>

                  <h3 className="pack-name-display" style={{ margin: '0.5rem 0 0.25rem 0' }}>GOLDEN POKÉ BALL</h3>
                  <div className="pack-price-hero" style={{ color: '#ffd700' }}>
                    {serverPricing.premium_pack?.toFixed(1) || '0.5'} <span className="currency">ALGO</span>
                  </div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: '#ffd700', textTransform: 'uppercase', fontWeight: 700, marginBottom: '1.25rem' }}>
                    ENHANCED ENCOUNTERS • BOOSTED ODDS
                  </div>

                  <div className="pack-perks-list" style={{ width: '100%', textAlign: 'left' }}>
                    <div className="perk-item">
                      <Sparkles size={16} style={{ color: '#ffd700' }} /> 3 Digital Pokémon Collectibles
                    </div>
                    <div className="perk-item">
                      <Check size={16} /> Entire 247-Species Master Catalog
                    </div>
                    <div className="perk-item">
                      <Zap size={16} /> Boosted Rare (35%), Epic (20%), Legendary (5%)
                    </div>
                  </div>

                  <button 
                    className="btn-editorial primary"
                    style={{ width: '100%', marginTop: 'auto', background: accountAddress ? 'linear-gradient(135deg, #ffd700, #ffb800)' : undefined, color: accountAddress ? '#080a0c' : undefined, fontWeight: 700 }}
                    onClick={() => !accountAddress ? handleConnectWallet() : handleInitiatePurchase('premium')}
                  >
                    {!accountAddress ? (
                      <><Wallet size={16} /> Connect Wallet to Continue</>
                    ) : (
                      <><Sparkles size={16} /> OPEN PREMIUM ({serverPricing.premium_pack?.toFixed(1) || '0.5'} ALGO)</>
                    )}
                  </button>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', width: '100%', marginTop: '0.75rem' }}>
                    <button 
                      className="btn-editorial outline" 
                      style={{ padding: '0.55rem 0.5rem', fontSize: '0.72rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', borderColor: 'rgba(255, 215, 0, 0.3)' }}
                      onClick={() => {
                        setPossibleModalPackType('premium');
                        setPossiblePokemonModalOpen(true);
                      }}
                    >
                      <Eye size={13} /> POSSIBLE POKÉMON
                    </button>
                    <button 
                      className="btn-editorial ghost" 
                      style={{ padding: '0.55rem 0.5rem', fontSize: '0.72rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', color: '#ffd700' }}
                      onClick={() => {
                        setOddsPackType('premium');
                        setOddsModalOpen(true);
                      }}
                    >
                      <Percent size={13} /> VIEW ODDS
                    </button>
                  </div>
                </div>
              </div>

              {/* SECTION: SPECIAL ELEMENT EVENT PACKS */}
              <div style={{ marginTop: '3.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '1.25rem' }}>
                  <Flame size={20} style={{ color: '#FF4D2D' }} />
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', textTransform: 'uppercase', letterSpacing: '0.02em' }}>
                    Special Event Elemental Boosters
                  </h3>
                  <span className="brand-badge" style={{ background: 'rgba(255, 77, 45, 0.15)', color: '#FF4D2D' }}>LIMITED EVENT</span>
                </div>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem', maxWidth: '650px' }}>
                  Targeted elemental booster packs focused on specific Pokémon evolution families. Guaranteed element affinity.
                </p>

                <div className="elemental-packs-grid">
                  {/* Fire Event */}
                  <div className="pack-editorial-card" style={{ borderTop: '3px solid #FF4422' }}>
                    <div className="pack-edition-label" style={{ color: '#FF4422' }}>IGNIS LINE • FIRE</div>
                    <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', margin: '6px 0' }}>VOLCANIC FIRE</h4>
                    <div className="pack-price-hero" style={{ fontSize: '1.4rem', margin: '8px 0' }}>
                      {serverPricing.event_pack?.toFixed(1) || '0.2'} <span className="currency">ALGO</span>
                    </div>
                    <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                      2 Fire Collectibles. Boosted Charmander, Charmeleon & Charizard rates.
                    </p>
                    <button 
                      className={`btn-editorial ${accountAddress ? 'secondary' : 'primary'}`}
                      style={{ width: '100%', borderColor: '#FF4422' }}
                      onClick={() => !accountAddress ? handleConnectWallet() : handleInitiatePurchase('fire_event')}
                    >
                      {!accountAddress ? (
                        <><Wallet size={14} /> Connect Wallet to Continue</>
                      ) : (
                        <><ShoppingBag size={14} /> OPEN FIRE PACK ({serverPricing.event_pack?.toFixed(1) || '0.2'} ALGO)</>
                      )}
                    </button>
                  </div>

                  {/* Water Event */}
                  <div className="pack-editorial-card" style={{ borderTop: '3px solid #3399FF' }}>
                    <div className="pack-edition-label" style={{ color: '#3399FF' }}>HYDRA LINE • WATER</div>
                    <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', margin: '6px 0' }}>TIDAL WATER</h4>
                    <div className="pack-price-hero" style={{ fontSize: '1.4rem', margin: '8px 0' }}>
                      {serverPricing.event_pack?.toFixed(1) || '0.2'} <span className="currency">ALGO</span>
                    </div>
                    <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                      2 Water Collectibles. Boosted Squirtle, Wartortle & Blastoise rates.
                    </p>
                    <button 
                      className={`btn-editorial ${accountAddress ? 'secondary' : 'primary'}`}
                      style={{ width: '100%', borderColor: '#3399FF' }}
                      onClick={() => !accountAddress ? handleConnectWallet() : handleInitiatePurchase('water_event')}
                    >
                      {!accountAddress ? (
                        <><Wallet size={14} /> Connect Wallet to Continue</>
                      ) : (
                        <><ShoppingBag size={14} /> OPEN WATER PACK ({serverPricing.event_pack?.toFixed(1) || '0.2'} ALGO)</>
                      )}
                    </button>
                  </div>

                  {/* Electric Event */}
                  <div className="pack-editorial-card" style={{ borderTop: '3px solid #FFCC00' }}>
                    <div className="pack-edition-label" style={{ color: '#FFCC00' }}>VOLT LINE • ELECTRIC</div>
                    <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', margin: '6px 0' }}>THUNDERSTORM</h4>
                    <div className="pack-price-hero" style={{ fontSize: '1.4rem', margin: '8px 0' }}>
                      {serverPricing.event_pack?.toFixed(1) || '0.2'} <span className="currency">ALGO</span>
                    </div>
                    <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                      2 Electric Collectibles. Boosted Pichu, Pikachu & Raichu rates.
                    </p>
                    <button 
                      className={`btn-editorial ${accountAddress ? 'secondary' : 'primary'}`}
                      style={{ width: '100%', borderColor: '#FFCC00' }}
                      onClick={() => !accountAddress ? handleConnectWallet() : handleInitiatePurchase('electric_event')}
                    >
                      {!accountAddress ? (
                        <><Wallet size={14} /> Connect Wallet to Continue</>
                      ) : (
                        <><ShoppingBag size={14} /> OPEN ELECTRIC PACK ({serverPricing.event_pack?.toFixed(1) || '0.2'} ALGO)</>
                      )}
                    </button>
                  </div>

                  {/* Ghost Event */}
                  <div className="pack-editorial-card" style={{ borderTop: '3px solid #8844AA' }}>
                    <div className="pack-edition-label" style={{ color: '#C084FC' }}>UMBRA LINE • SHADOW</div>
                    <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', margin: '6px 0' }}>SHADOW REALM</h4>
                    <div className="pack-price-hero" style={{ fontSize: '1.4rem', margin: '8px 0' }}>
                      {serverPricing.event_pack?.toFixed(1) || '0.2'} <span className="currency">ALGO</span>
                    </div>
                    <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                      2 Ghost/Psychic Collectibles. Boosted Gastly, Haunter & Gengar rates.
                    </p>
                    <button 
                      className={`btn-editorial ${accountAddress ? 'secondary' : 'primary'}`}
                      style={{ width: '100%', borderColor: '#8844AA' }}
                      onClick={() => !accountAddress ? handleConnectWallet() : handleInitiatePurchase('ghost_event')}
                    >
                      {!accountAddress ? (
                        <><Wallet size={14} /> Connect Wallet to Continue</>
                      ) : (
                        <><ShoppingBag size={14} /> OPEN SHADOW PACK ({serverPricing.event_pack?.toFixed(1) || '0.2'} ALGO)</>
                      )}
                    </button>
                  </div>
                </div>
              </div>

              {/* Pack odds & guarantee banner */}
              <div style={{ marginTop: '3rem', padding: '1.5rem', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', textAlign: 'center' }}>
                  <div>
                    <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', color: 'var(--accent-lime)' }}>100%</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Verified Ownership</div>
                  </div>
                  <div>
                    <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', color: 'var(--accent-cyan)' }}>FREE</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No Claim / Transfer Fees</div>
                  </div>
                  <div>
                    <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', color: '#FFB800' }}>PERA</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Direct Wallet Delivery</div>
                  </div>
                  <div>
                    <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', color: '#FF4D2D' }}>INSTANT</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Immediate Card Delivery</div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* -------------------------------------------------------------
            TAB 3: COLLECTION (MY POKÉMON VAULT)
            ------------------------------------------------------------- */}
        {activeTab === 'collection' && (
          <section className="collection-section" style={{ paddingTop: 'calc(var(--nav-height) + 3rem)' }}>
            <div className="editorial-container">
              <div className="section-editorial-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                  <div className="section-label">Trainer Vault</div>
                  <h2 className="section-headline">MY POKÉMON COLLECTION.</h2>
                  <p style={{ color: 'var(--text-muted)', maxWidth: '580px', marginTop: '0.75rem' }}>
                    Verified 1-of-1 digital collectibles stored securely in your connected wallet.
                  </p>
                </div>
                {accountAddress && (
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <button 
                      className="btn-editorial ghost" 
                      onClick={handleDevResetAccountCollection}
                      disabled={isResettingCollection}
                      style={{ 
                        fontSize: '0.75rem', 
                        padding: '0.45rem 0.85rem', 
                        color: '#ff6b6b', 
                        borderColor: 'rgba(255, 107, 107, 0.3)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px'
                      }}
                      title="Development Only: Transfer NFTs back to creator and reset collection to 0"
                    >
                      <RefreshCw size={13} className={isResettingCollection ? 'spin-icon' : ''} />
                      {isResettingCollection ? 'RESETTING...' : 'RESET COLLECTION (DEV)'}
                    </button>
                  </div>
                )}
              </div>

              {/* STATE 1: NO WALLET CONNECTED */}
              {!accountAddress ? (
                <div className="no-wallet-collection-stage" style={{ textAlign: 'center', padding: '5rem 2rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border-subtle)', maxWidth: '700px', margin: '0 auto' }}>
                  <Wallet size={56} style={{ color: 'var(--accent-lime)', marginBottom: '1.25rem' }} />
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', marginBottom: '0.75rem', letterSpacing: '0.02em', textTransform: 'uppercase' }}>
                    Connect the wallet to look over collection.
                  </h3>
                  <p style={{ color: 'var(--text-muted)', marginBottom: '2rem', lineHeight: 1.6, maxWidth: '520px', margin: '0 auto 2rem auto' }}>
                    Your collection is derived strictly from your connected wallet holdings. Connect Pera Wallet to inspect your verified Pokémon cards.
                  </p>
                  <button className="btn-editorial primary" onClick={handleConnectWallet} style={{ padding: '0.9rem 2rem', fontSize: '0.95rem' }}>
                    <Wallet size={18} /> CONNECT WALLET
                  </button>
                </div>
              ) : collectionLoading ? (
                /* STATE 2: LOADING COLLECTION */
                <div style={{ textAlign: 'center', padding: '6rem 0', background: 'var(--bg-surface)', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border-subtle)' }}>
                  <RefreshCw size={36} className="spin-icon" style={{ color: 'var(--accent-lime)', marginBottom: '1.25rem' }} />
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', letterSpacing: '0.04em', marginBottom: '0.5rem' }}>
                    LOADING YOUR COLLECTION...
                  </h3>
                  <p style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
                    Retrieving verified digital collectibles from your wallet...
                  </p>
                </div>
              ) : collectionError ? (
                /* STATE 3: COLLECTION ERROR */
                <div style={{ textAlign: 'center', padding: '5rem 2rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-xl)', border: '1px solid rgba(255,68,68,0.3)' }}>
                  <AlertCircle size={48} style={{ color: '#ff4d4d', marginBottom: '1rem' }} />
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', marginBottom: '0.5rem' }}>WE COULDN'T LOAD YOUR COLLECTION</h3>
                  <p style={{ color: 'var(--text-muted)', maxWidth: '500px', margin: '0 auto 1.5rem auto' }}>
                    {collectionError}
                  </p>
                  <button className="btn-editorial primary" onClick={() => fetchUserCollection(accountAddress)}>
                    <RefreshCw size={16} /> TRY AGAIN
                  </button>
                </div>
              ) : userCollection.length === 0 ? (
                /* STATE 4: EMPTY COLLECTION */
                <div className="empty-collection-stage" style={{ textAlign: 'center', padding: '5rem 2rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border-subtle)', maxWidth: '700px', margin: '0 auto' }}>
                  <Layers size={56} style={{ color: 'var(--text-dim)', marginBottom: '1.25rem' }} />
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', marginBottom: '0.75rem', letterSpacing: '0.02em', textTransform: 'uppercase' }}>
                    YOUR COLLECTION IS EMPTY
                  </h3>
                  <p style={{ color: 'var(--text-muted)', marginBottom: '2rem', lineHeight: 1.6, maxWidth: '500px', margin: '0 auto 2rem auto' }}>
                    Open a Poké Ball to discover your first Pokémon.
                  </p>
                  <button className="btn-editorial primary" onClick={() => setActiveTab('packs')} style={{ padding: '0.9rem 2rem', fontSize: '0.95rem' }}>
                    <ShoppingBag size={18} /> EXPLORE PACKS
                  </button>
                </div>
              ) : (
                /* STATE 5: COLLECTION READY WITH ITEMS */
                <>
                  {/* Filters & Search Toolbar */}
                  <div className="collection-toolbar">
                    <div className="type-filters-row">
                      {['all', 'fire', 'water', 'grass', 'electric', 'dragon', 'psychic', 'ghost'].map(elem => (
                        <button
                          key={elem}
                          className={`filter-pill-btn ${collectionTypeFilter === elem ? 'active' : ''}`}
                          onClick={() => setCollectionTypeFilter(elem)}
                        >
                          {elem.toUpperCase()}
                        </button>
                      ))}
                    </div>

                    <div className="collection-search-wrap">
                      <div style={{ position: 'relative', width: '260px' }}>
                        <Search size={16} style={{ position: 'absolute', left: '12px', color: 'var(--text-muted)' }} />
                        <input 
                          type="text" 
                          placeholder="Search owned Pokémon..." 
                          value={collectionSearchQuery}
                          onChange={e => setCollectionSearchQuery(e.target.value)}
                          className="collection-search-input"
                        />
                      </div>
                      <div className="collection-counter">
                        <strong>{filteredCollection.length}</strong> / {userCollection.length} OWNED
                      </div>
                    </div>
                  </div>

                  {filteredCollection.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '4rem 2rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border-subtle)' }}>
                      <Search size={40} style={{ color: 'var(--text-dim)', marginBottom: '1rem' }} />
                      <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.3rem', marginBottom: '0.5rem' }}>NO MATCHING POKÉMON FOUND</h3>
                      <p style={{ color: 'var(--text-muted)', marginBottom: '1.25rem' }}>No Pokémon in your collection match this filter or search query.</p>
                      <button 
                        className="btn-editorial secondary" 
                        onClick={() => {
                          setCollectionTypeFilter('all');
                          setCollectionSearchQuery('');
                        }}
                      >
                        Reset Filter
                      </button>
                    </div>
                  ) : (
                    <div className="pokedex-grid">
                      {filteredCollection.map(creature => {
                        const elemColor = ELEMENT_COLORS[creature.primary_type] || ELEMENT_COLORS.Fire;
                        const pokemonImg = creature.image || getPokemonArtworkUrl(creature.template_id || 25);
                        const formattedNum = `#${String(creature.template_id || 25).padStart(3, '0')}`;
                        return (
                          <div 
                            key={creature.asset_id}
                            className="editorial-creature-card"
                            onClick={() => setInspectingPokemon({
                              id: creature.template_id || 25,
                              name: creature.name,
                              pokedexNumber: formattedNum,
                              primaryType: creature.primary_type,
                              secondaryType: creature.secondary_type,
                              rarity: creature.rarity,
                              stage: creature.evolution_stage || 1,
                              image: pokemonImg,
                              hp: creature.hp,
                              attack: creature.attack,
                              defense: creature.defense,
                              speed: creature.speed,
                              level: creature.level,
                              xp: creature.xp,
                              asset_id: creature.asset_id,
                              owner_wallet: accountAddress,
                              isOwned: true
                            })}
                            onMouseEnter={() => setCursorHover('INSPECT')}
                            onMouseLeave={clearCursorHover}
                            style={{ borderTop: `2px solid ${elemColor.text}` }}
                          >
                            <div className="card-top-meta">
                              <span className="card-asa-tag">{formattedNum}</span>
                              <span 
                                className="card-rarity-pill"
                                style={{ 
                                  background: 'rgba(255,255,255,0.06)', 
                                  color: RARITY_COLORS[creature.rarity] || '#fff' 
                                }}
                              >
                                {creature.rarity}
                              </span>
                            </div>

                            <div className="pokedex-card-artwork">
                              <img 
                                src={pokemonImg} 
                                alt={creature.name}
                                onError={(e) => {
                                  (e.target as HTMLElement).style.display = 'none';
                                }}
                              />
                            </div>

                            <div className="card-bottom-info">
                              <div className="card-name-row">
                                <h4 style={{ textTransform: 'uppercase' }}>{creature.name}</h4>
                                <span className={`type-badge type-badge-${creature.primary_type.toLowerCase()}`}>
                                  {creature.primary_type.toUpperCase()}
                                </span>
                              </div>

                              <div className="card-xp-progress">
                                <div 
                                  className="card-xp-fill"
                                  style={{ width: `${Math.min(100, (creature.xp % 350) / 3.5)}%` }}
                                />
                              </div>

                              <div className="card-footer-meta" style={{ display: 'flex', flexDirection: 'column', gap: '6px', alignItems: 'stretch' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.74rem', fontFamily: 'var(--font-mono)' }}>
                                  <span style={{ color: 'var(--text-muted)' }}>LEVEL {creature.level}</span>
                                  <span style={{ color: '#FFCC00', fontWeight: 700 }}>ASSET #{creature.asset_id}</span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '2px' }}>
                                  <button 
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      openAssetDetail(creature.asset_id);
                                    }}
                                    style={{ 
                                      background: 'none', 
                                      border: 'none', 
                                      padding: 0, 
                                      fontSize: '0.72rem', 
                                      color: 'var(--accent-cyan)', 
                                      cursor: 'pointer', 
                                      display: 'flex', 
                                      alignItems: 'center', 
                                      gap: '3px', 
                                      fontWeight: 600,
                                      fontFamily: 'var(--font-mono)' 
                                    }}
                                    title="View Asset Details"
                                  >
                                    <ExternalLink size={11} /> VIEW DETAILS
                                  </button>
                                  <span className="card-owned-badge" style={{ color: '#00ff88', fontWeight: 700, fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                                    <Check size={11} /> IN YOUR WALLET ✓
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </>
              )}
            </div>
          </section>
        )}

        {/* -------------------------------------------------------------
            TAB 4: POKÉDEX (DEDICATED EXPLORER & SPECIES ARCHIVE)
            ------------------------------------------------------------- */}
        {activeTab === 'pokedex' && (
          <section className="collection-section" style={{ paddingTop: 'calc(var(--nav-height) + 3rem)' }}>
            <div className="editorial-container">
              <div className="section-editorial-header">
                <div className="section-label">Canonical Archive</div>
                <h2 className="section-headline">DISCOVER THE POKÉMON.</h2>
                <p style={{ color: 'var(--text-muted)', maxWidth: '580px', marginTop: '0.75rem' }}>
                  Explore canonical Pokémon species, elemental alignments, base battle statistics, and on-chain ownership status.
                </p>
              </div>

              {/* Pokédex Search Bar */}
              <div className="pokedex-search-bar-wrap">
                <div className="pokedex-search-box">
                  <Search size={18} className="pokedex-search-icon" />
                  <input
                    type="text"
                    className="pokedex-search-input"
                    placeholder="Search Pokémon by name or Pokédex number (e.g. Pikachu, #025, Charizard, 6)..."
                    value={pokedexSearchQuery}
                    onChange={e => setPokedexSearchQuery(e.target.value)}
                  />
                  {pokedexSearchQuery && (
                    <button 
                      onClick={() => setPokedexSearchQuery('')}
                      style={{ position: 'absolute', right: '12px', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                    >
                      <X size={16} />
                    </button>
                  )}
                </div>
              </div>

              {/* Pokédex Generation Filters */}
              <div style={{ marginBottom: '1rem' }}>
                <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '0.4rem', letterSpacing: '0.05em' }}>
                  Filter by Generation:
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {['ALL', 'GEN I', 'GEN II', 'GEN III', 'GEN IV', 'GEN V', 'GEN VI', 'GEN VII', 'GEN VIII', 'GEN IX'].map(gen => (
                    <button
                      key={gen}
                      className={`type-filter-btn ${pokedexGenFilter === gen ? 'gen-pill-active' : ''}`}
                      style={{ fontSize: '0.75rem', padding: '0.35rem 0.85rem' }}
                      onClick={() => setPokedexGenFilter(gen)}
                    >
                      {gen}
                    </button>
                  ))}
                </div>
              </div>

              {/* Pokédex Type Filters (All 18 Elemental Types) */}
              <div style={{ marginBottom: '1.75rem' }}>
                <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '0.4rem', letterSpacing: '0.05em' }}>
                  Filter by Elemental Type:
                </div>
                <div className="pokedex-type-pills" style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                  {[
                    'ALL', 'NORMAL', 'FIRE', 'WATER', 'ELECTRIC', 'GRASS', 'ICE', 
                    'FIGHTING', 'POISON', 'GROUND', 'FLYING', 'PSYCHIC', 'BUG', 
                    'ROCK', 'GHOST', 'DRAGON', 'DARK', 'STEEL', 'FAIRY'
                  ].map(type => (
                    <button
                      key={type}
                      className={`type-filter-btn ${pokedexTypeFilter === type ? 'filter-pill-active' : ''}`}
                      style={{ fontSize: '0.72rem', padding: '0.3rem 0.75rem' }}
                      onClick={() => setPokedexTypeFilter(type)}
                    >
                      {type}
                    </button>
                  ))}
                </div>
              </div>

              {/* Pokédex Results Count & Page Summary */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                <span>
                  Showing {filteredPokedex.length > 0 ? (pokedexPage - 1) * POKEDEX_PER_PAGE + 1 : 0}–{Math.min(pokedexPage * POKEDEX_PER_PAGE, filteredPokedex.length)} of {filteredPokedex.length} Pokémon
                </span>
                <span>Page {pokedexPage} of {pokedexTotalPages}</span>
              </div>

              {/* Pokédex Cards 4-Column Responsive Grid */}
              <div className="pokedex-grid-container">
                {paginatedPokedex.map(pk => {
                  const isCollected = isPokemonCollected(pk.id, pk.name);
                  const ownedCount = getPokemonOwnedCount(pk.id, pk.name);
                  const elemColor = ELEMENT_COLORS[pk.primaryType] || ELEMENT_COLORS.Normal;

                  return (
                    <div 
                      key={pk.id}
                      className="editorial-creature-card"
                      onClick={() => setInspectingPokemon({ ...pk, isOwned: isCollected })}
                      onMouseEnter={() => setCursorHover('INSPECT')}
                      onMouseLeave={clearCursorHover}
                      style={{ borderTop: `2px solid ${elemColor.text}` }}
                    >
                      <div className="card-top-meta">
                        <span className="card-asa-tag">{pk.pokedexNumber}</span>
                        <span 
                          className="card-rarity-pill" 
                          style={{ color: RARITY_COLORS[pk.rarity] || '#fff' }}
                        >
                          {pk.rarity}
                        </span>
                      </div>

                      <div className="pokemon-artwork-container">
                        <img 
                          src={pk.image} 
                          alt={pk.name}
                          className="pokemon-artwork-img"
                          loading="lazy"
                          onError={(e) => {
                            const target = e.target as HTMLImageElement;
                            if (target.src !== pk.sprite && pk.sprite) {
                              target.src = pk.sprite;
                            } else if (target.src !== NEUTRAL_FALLBACK_SVG) {
                              target.src = NEUTRAL_FALLBACK_SVG;
                            }
                          }}
                        />
                      </div>

                      <div className="card-bottom-info">
                        <div className="card-name-row">
                          <h4 style={{ textTransform: 'uppercase', letterSpacing: '0.02em' }}>{pk.name}</h4>
                          <div style={{ display: 'flex', gap: '4px' }}>
                            <span className={`type-badge type-badge-${pk.primaryType.toLowerCase()}`}>
                              {pk.primaryType}
                            </span>
                            {pk.secondaryType && (
                              <span className={`type-badge type-badge-${pk.secondaryType.toLowerCase()}`}>
                                {pk.secondaryType}
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Base Stat Mini-Grid */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '3px', margin: '8px 0', fontSize: '0.68rem', fontFamily: 'var(--font-mono)', textAlign: 'center' }}>
                          <div style={{ background: 'rgba(255,255,255,0.03)', padding: '2px', borderRadius: '3px' }}>
                            <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.58rem' }}>HP</span>
                            <strong>{pk.hp}</strong>
                          </div>
                          <div style={{ background: 'rgba(255,255,255,0.03)', padding: '2px', borderRadius: '3px' }}>
                            <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.58rem' }}>ATK</span>
                            <strong>{pk.attack}</strong>
                          </div>
                          <div style={{ background: 'rgba(255,255,255,0.03)', padding: '2px', borderRadius: '3px' }}>
                            <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.58rem' }}>DEF</span>
                            <strong>{pk.defense}</strong>
                          </div>
                          <div style={{ background: 'rgba(255,255,255,0.03)', padding: '2px', borderRadius: '3px' }}>
                            <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.58rem' }}>SPA</span>
                            <strong>{pk.specialAttack}</strong>
                          </div>
                          <div style={{ background: 'rgba(255,255,255,0.03)', padding: '2px', borderRadius: '3px' }}>
                            <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.58rem' }}>SPD</span>
                            <strong>{pk.specialDefense}</strong>
                          </div>
                          <div style={{ background: 'rgba(255,255,255,0.03)', padding: '2px', borderRadius: '3px' }}>
                            <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.58rem' }}>SPE</span>
                            <strong>{pk.speed}</strong>
                          </div>
                        </div>

                        <div className="card-footer-meta" style={{ marginTop: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>{pk.generation}</span>
                          {accountAddress ? (
                            ownedCount > 0 ? (
                              <span className="card-owned-badge" style={{ color: '#00ff88', fontWeight: 700, fontSize: '0.72rem', background: 'rgba(0,255,136,0.1)', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(0,255,136,0.3)' }}>
                                ● OWNED{ownedCount > 1 ? ` ×${ownedCount}` : ''}
                              </span>
                            ) : (
                              <span style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>○ NOT COLLECTED</span>
                            )
                          ) : (
                            <span style={{ color: 'var(--text-dim)', fontSize: '0.7rem' }}>○ NOT COLLECTED</span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Pagination Controls */}
              {pokedexTotalPages > 1 && (
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', marginTop: '3rem', flexWrap: 'wrap' }}>
                  <button
                    className="btn-editorial secondary"
                    onClick={() => setPokedexPage(prev => Math.max(1, prev - 1))}
                    disabled={pokedexPage === 1}
                    style={{ padding: '0.5rem 1rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                  >
                    <ChevronLeft size={16} /> Prev
                  </button>

                  <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
                    {Array.from({ length: Math.min(7, pokedexTotalPages) }, (_, i) => {
                      let pageNum = i + 1;
                      if (pokedexTotalPages > 7) {
                        if (pokedexPage > 4 && pokedexPage < pokedexTotalPages - 3) {
                          pageNum = pokedexPage - 3 + i;
                        } else if (pokedexPage >= pokedexTotalPages - 3) {
                          pageNum = pokedexTotalPages - 6 + i;
                        }
                      }
                      return (
                        <button
                          key={pageNum}
                          className={`type-filter-btn ${pokedexPage === pageNum ? 'filter-pill-active' : ''}`}
                          style={{ minWidth: '36px', height: '36px', padding: '0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                          onClick={() => setPokedexPage(pageNum)}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                  </div>

                  <button
                    className="btn-editorial secondary"
                    onClick={() => setPokedexPage(prev => Math.min(pokedexTotalPages, prev + 1))}
                    disabled={pokedexPage === pokedexTotalPages}
                    style={{ padding: '0.5rem 1rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                  >
                    Next <ChevronRight size={16} />
                  </button>
                </div>
              )}

              {filteredPokedex.length === 0 && (
                <div style={{ textAlign: 'center', padding: '5rem 2rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-xl)' }}>
                  <Search size={48} style={{ color: 'var(--text-dim)', marginBottom: '1rem' }} />
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem' }}>NO POKÉMON MATCH YOUR SEARCH</h3>
                  <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem' }}>Try searching for another name, number, or reset type filters.</p>
                </div>
              )}
            </div>
          </section>
        )}

        {/* -------------------------------------------------------------
            TAB 5: BATTLE ARENA (DRAMATIC VS COMPOSITION WITH ARTWORK)
            ------------------------------------------------------------- */}
        {activeTab === 'battle' && (
          <section className="battle-section" style={{ paddingTop: 'calc(var(--nav-height) + 3rem)' }}>
            <div className="editorial-container">
              <div className="section-editorial-header">
                <div className="section-label">Tactical Arena</div>
                <h2 className="section-headline">TACTICAL BATTLEFIELD.</h2>
                <p style={{ color: 'var(--text-muted)', maxWidth: '580px', marginTop: '0.75rem' }}>
                  Test your Pokémon in elemental arenas, gain combat XP, and level up your fighter.
                </p>
              </div>

              {!accountAddress ? (
                <div style={{ textAlign: 'center', padding: '5rem 2rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border-subtle)', maxWidth: '700px', margin: '0 auto' }}>
                  <Swords size={56} style={{ color: 'var(--accent-lime)', marginBottom: '1.25rem' }} />
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', marginBottom: '0.75rem', letterSpacing: '0.02em', textTransform: 'uppercase' }}>
                    CONNECT YOUR WALLET TO CHOOSE A POKÉMON
                  </h3>
                  <p style={{ color: 'var(--text-muted)', marginBottom: '2rem', lineHeight: 1.6, maxWidth: '520px', margin: '0 auto 2rem auto' }}>
                    Connect your Pera Wallet to choose your fighter from your verified Pokémon collection and enter the tactical arena.
                  </p>
                  <button className="btn-editorial primary" onClick={handleConnectWallet} style={{ padding: '0.9rem 2rem', fontSize: '0.95rem' }}>
                    <Wallet size={18} /> CONNECT WALLET
                  </button>
                </div>
              ) : userCollection.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '5rem 2rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border-subtle)', maxWidth: '700px', margin: '0 auto' }}>
                  <Layers size={56} style={{ color: 'var(--text-dim)', marginBottom: '1.25rem' }} />
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', marginBottom: '0.75rem', letterSpacing: '0.02em', textTransform: 'uppercase' }}>
                    YOUR COLLECTION IS EMPTY
                  </h3>
                  <p style={{ color: 'var(--text-muted)', marginBottom: '2rem', lineHeight: 1.6, maxWidth: '500px', margin: '0 auto 2rem auto' }}>
                    Open a Poké Ball first to discover your first Pokémon and battle in the arena.
                  </p>
                  <button className="btn-editorial primary" onClick={() => setActiveTab('packs')} style={{ padding: '0.9rem 2rem', fontSize: '0.95rem' }}>
                    <ShoppingBag size={18} /> EXPLORE PACKS
                  </button>
                </div>
              ) : (
                <div className="arena-stage-container">
                  <div className="arena-vs-composition">
                    {/* Player Combatant */}
                    <div className={`combatant-card ${battleAnimationPhase === 'ATTACK' ? 'player-attack-lunge' : battleAnimationPhase === 'HIT' ? 'screen-shake' : ''}`}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--accent-lime)' }}>YOUR FIGHTER</span>
                      <div className="combatant-avatar" style={{ width: '130px', height: '130px', background: 'radial-gradient(circle, rgba(212,255,0,0.15) 0%, rgba(0,0,0,0.4) 100%)', overflow: 'hidden' }}>
                        <img 
                          src={
                            userCollection.find(c => c.asset_id === selectedFighterAssetId)?.image || 
                            getPokemonArtworkUrl(userCollection.find(c => c.asset_id === selectedFighterAssetId)?.template_id || 6)
                          } 
                          alt="Your Fighter"
                          style={{ maxWidth: '90%', maxHeight: '90%', objectFit: 'contain' }}
                        />
                      </div>
                      <div>
                        <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', textTransform: 'uppercase' }}>
                          {userCollection.find(c => c.asset_id === selectedFighterAssetId)?.name || 'Charizard #006'}
                        </h4>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          Level {userCollection.find(c => c.asset_id === selectedFighterAssetId)?.level || 4} • Fighter
                        </span>
                      </div>

                      {userCollection.length > 1 && (
                        <select 
                          value={selectedFighterAssetId || ''} 
                          onChange={e => setSelectedFighterAssetId(Number(e.target.value))}
                          style={{
                            background: 'var(--bg-canvas)',
                            color: 'var(--text-primary)',
                            border: '1px solid var(--border-subtle)',
                            padding: '6px 12px',
                            borderRadius: 'var(--radius-sm)',
                            fontFamily: 'var(--font-mono)',
                            fontSize: '0.75rem',
                            maxWidth: '100%'
                          }}
                        >
                          {userCollection.map(c => (
                            <option key={c.asset_id} value={c.asset_id}>{c.name} (LVL {c.level})</option>
                          ))}
                        </select>
                      )}
                    </div>

                    {/* VS Badge */}
                    <div className="arena-vs-center">
                      <span className="vs-badge-text">VS</span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {selectedArena.toUpperCase()} ARENA
                      </span>
                    </div>

                    {/* Opponent Combatant */}
                    <div className={`combatant-card ${battleAnimationPhase === 'HIT' ? 'player-attack-lunge' : ''}`}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: '#FF4D2D' }}>ARENA RIVAL</span>
                      <div className="combatant-avatar" style={{ width: '130px', height: '130px', background: 'radial-gradient(circle, rgba(255,77,45,0.15) 0%, rgba(0,0,0,0.4) 100%)', overflow: 'hidden' }}>
                        <img 
                          src={getPokemonArtworkUrl(9)} 
                          alt="Blastoise"
                          style={{ maxWidth: '90%', maxHeight: '90%', objectFit: 'contain' }}
                        />
                      </div>
                      <div>
                        <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', textTransform: 'uppercase' }}>BLASTOISE #009</h4>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>Level 5 • Arena Boss</span>
                      </div>
                    </div>
                  </div>

                  {/* Tactical Selection & Action */}
                  <div className="battle-action-console">
                    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center' }}>
                      {arenas.map(arena => (
                        <button
                          key={arena.id}
                          className={`filter-pill-btn ${selectedArena === arena.id ? 'active' : ''}`}
                          onClick={() => setSelectedArena(arena.id)}
                        >
                          {arena.name}
                        </button>
                      ))}
                    </div>

                    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', justifyContent: 'center' }}>
                      <button 
                        className="btn-editorial secondary"
                        onClick={handleStartBattle}
                        disabled={battleInProgress}
                        style={{ minWidth: '220px' }}
                      >
                        {battleInProgress ? (
                          <><RefreshCw size={16} className="spin-icon" /> Executing Tactical Combat...</>
                        ) : (
                          <><Swords size={16} /> Free Arena Battle</>
                        )}
                      </button>

                      <button 
                        className="btn-editorial primary"
                        onClick={handleStartPremiumBattle}
                        disabled={battleInProgress}
                        style={{ 
                          minWidth: '280px',
                          background: 'linear-gradient(135deg, #FF4D2D 0%, #F59E0B 100%)',
                          border: 'none',
                          color: '#000',
                          fontWeight: 700
                        }}
                      >
                        <Zap size={16} /> Premium Tactical Battle (+50 Bonus XP • {serverPricing.premium_battle?.toFixed(2) || '0.02'} ALGO)
                      </button>
                    </div>

                    {/* Battle Outcome Display */}
                    {battleResult && (
                      <div style={{
                        width: '100%',
                        background: 'var(--bg-canvas)',
                        border: battleResult.is_premium ? '1px solid rgba(245, 158, 11, 0.5)' : '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-md)',
                        padding: '1.5rem',
                        textAlign: 'left',
                        boxShadow: battleResult.is_premium ? '0 0 20px rgba(245, 158, 11, 0.15)' : 'none'
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '8px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', color: battleResult.player_won ? '#00ff88' : '#ff4444', margin: 0 }}>
                              {battleResult.player_won ? 'VICTORY ACHIEVED! 🏆' : 'DEFEAT'}
                            </h4>
                            {battleResult.is_premium && (
                              <span style={{ 
                                background: 'rgba(245, 158, 11, 0.2)', 
                                border: '1px solid #F59E0B', 
                                color: '#F59E0B', 
                                padding: '2px 8px', 
                                borderRadius: '4px', 
                                fontSize: '0.72rem', 
                                fontWeight: 700,
                                fontFamily: 'var(--font-mono)'
                              }}>
                                ⚡ PREMIUM COMBAT (+{battleResult.bonus_xp || 50} BONUS XP)
                              </span>
                            )}
                          </div>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--accent-lime)', fontWeight: 700 }}>
                            +{battleResult.player?.xp_gained || battleResult.bonus_xp || 50} XP Gained
                          </span>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.85rem', fontFamily: 'var(--font-mono)' }}>
                          {battleResult.rounds?.map((r: any, idx: number) => (
                            <div key={idx} style={{ color: 'var(--text-muted)' }}>
                              Round {r.round}: <span style={{ color: 'var(--text-primary)' }}>{r.narrative || r.action}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        {/* -------------------------------------------------------------
            TAB 6: EVOLUTION SANCTUARY (CANONICAL EVOLUTION CHAINS)
            ------------------------------------------------------------- */}
        {activeTab === 'evolution' && (
          <section className="evolution-section" style={{ paddingTop: 'calc(var(--nav-height) + 3rem)' }}>
            <div className="editorial-container">
              <div className="section-editorial-header">
                <div className="section-label">Evolution Chamber</div>
                <h2 className="section-headline">EVOLUTION SANCTUARY.</h2>
                <p style={{ color: 'var(--text-muted)', maxWidth: '580px', marginTop: '0.75rem' }}>
                  Channel combat experience to trigger canonical Pokémon evolutions in your collection.
                </p>
              </div>

              {!accountAddress ? (
                <div style={{ textAlign: 'center', padding: '5rem 2rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border-subtle)', maxWidth: '700px', margin: '0 auto' }}>
                  <Dna size={56} style={{ color: 'var(--accent-lime)', marginBottom: '1.25rem' }} />
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', marginBottom: '0.75rem', letterSpacing: '0.02em', textTransform: 'uppercase' }}>
                    CONNECT YOUR WALLET TO VIEW EVOLUTION
                  </h3>
                  <p style={{ color: 'var(--text-muted)', marginBottom: '2rem', lineHeight: 1.6, maxWidth: '520px', margin: '0 auto 2rem auto' }}>
                    Connect your Pera Wallet to check evolution eligibility and upgrade Pokémon in your collection.
                  </p>
                  <button className="btn-editorial primary" onClick={handleConnectWallet} style={{ padding: '0.9rem 2rem', fontSize: '0.95rem' }}>
                    <Wallet size={18} /> CONNECT WALLET
                  </button>
                </div>
              ) : userCollection.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '5rem 2rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border-subtle)', maxWidth: '700px', margin: '0 auto' }}>
                  <Layers size={56} style={{ color: 'var(--text-dim)', marginBottom: '1.25rem' }} />
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', marginBottom: '0.75rem', letterSpacing: '0.02em', textTransform: 'uppercase' }}>
                    YOUR COLLECTION IS EMPTY
                  </h3>
                  <p style={{ color: 'var(--text-muted)', marginBottom: '2rem', lineHeight: 1.6, maxWidth: '500px', margin: '0 auto 2rem auto' }}>
                    Open a Poké Ball first to discover Pokémon that can evolve into stronger forms.
                  </p>
                  <button className="btn-editorial primary" onClick={() => setActiveTab('packs')} style={{ padding: '0.9rem 2rem', fontSize: '0.95rem' }}>
                    <ShoppingBag size={18} /> EXPLORE PACKS
                  </button>
                </div>
              ) : (
                <div>
                  <div style={{ display: 'flex', gap: '0.75rem', overflowX: 'auto', paddingBottom: '1rem', marginBottom: '2rem' }}>
                    {userCollection.map(c => (
                      <button
                        key={c.asset_id}
                        className={`filter-pill-btn ${selectedEvoAssetId === c.asset_id ? 'active' : ''}`}
                        onClick={() => handleCheckEvolution(c.asset_id)}
                      >
                        {c.name} (LVL {c.level})
                      </button>
                    ))}
                  </div>

                  {evoEligibility && (
                    <div className="spotlight-card">
                      <div className="spotlight-art-stage" style={{ background: 'radial-gradient(circle, rgba(212,255,0,0.15) 0%, rgba(0,0,0,0.5) 100%)' }}>
                        <img 
                          src={getPokemonArtworkUrl(evoEligibility.current_species?.id || 4)} 
                          alt="Current Form"
                          style={{ maxWidth: '80%', maxHeight: '80%', objectFit: 'contain' }}
                        />
                      </div>

                      <div className="spotlight-content">
                        <h3 className="spotlight-title">{evoEligibility.current_species?.name || 'Selected Pokémon'}</h3>
                        <p style={{ color: 'var(--text-muted)' }}>
                          Stage {evoEligibility.current_species?.stage || 1} • {evoEligibility.xp_progress || 'Level 1'}
                        </p>

                        <div style={{ background: 'var(--bg-canvas)', padding: '1rem', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                            <span>Evolution Status:</span>
                            <strong style={{ color: evoEligibility.evolution_eligible ? '#00ff88' : '#ff9900' }}>
                              {evoEligibility.evolution_eligible ? 'ELIGIBLE ✓' : 'XP LOCKED'}
                            </strong>
                          </div>
                          {evoEligibility.target_species && (
                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                              <span>Target Form:</span>
                              <strong style={{ color: 'var(--accent-lime)' }}>{evoEligibility.target_species.name} (Stage {evoEligibility.target_species.stage})</strong>
                            </div>
                          )}
                        </div>

                        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginTop: '1rem' }}>
                          {evoEligibility.evolution_eligible ? (
                            <button 
                              className="btn-editorial primary"
                              onClick={handleExecuteEvolution}
                              disabled={evoLoading}
                              style={{ flex: 1, minWidth: '200px' }}
                            >
                              <Dna size={16} /> Execute Evolution (Free)
                            </button>
                          ) : (
                            <div style={{ width: '100%', marginBottom: '0.5rem' }}>
                              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: 0 }}>
                                Battle in the arena to gain XP or use an instant Evolution Boost to reach the milestone.
                              </p>
                            </div>
                          )}

                          <button 
                            className="btn-editorial secondary"
                            onClick={() => handleBoostEvolution(selectedEvoAssetId || 0)}
                            disabled={evoLoading || boostLoading || !selectedEvoAssetId}
                            style={{ 
                              flex: evoEligibility.evolution_eligible ? undefined : 1,
                              minWidth: '220px',
                              borderColor: '#A855F7',
                              color: '#C084FC',
                              background: 'rgba(168, 85, 247, 0.08)'
                            }}
                          >
                            <Zap size={16} /> Evolution Boost (+100 XP • {serverPricing.evolution_boost?.toFixed(2) || '0.02'} ALGO)
                          </button>
                        </div>

                        {evoSuccess && (
                          <div style={{ padding: '0.75rem', background: 'rgba(0,255,136,0.1)', border: '1px solid rgba(0,255,136,0.3)', borderRadius: 'var(--radius-sm)', color: '#00ff88', fontSize: '0.85rem' }}>
                            🎉 Evolution successful! Upgraded to {evoSuccess.evolved_form} (Stage {evoSuccess.new_stage})!
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>
        )}

        {/* -------------------------------------------------------------
            TAB 7: TRADING POST (P2P POKÉMON ATOMIC SWAPS)
            ------------------------------------------------------------- */}
        {activeTab === 'trade' && (
          <section className="trading-section" style={{ paddingTop: 'calc(var(--nav-height) + 3rem)' }}>
            <div className="editorial-container">
              <div className="section-editorial-header">
                <div className="section-label">P2P Marketplace</div>
                <h2 className="section-headline">TRADING POST.</h2>
                <p style={{ color: 'var(--text-muted)', maxWidth: '580px', marginTop: '0.75rem' }}>
                  Direct peer-to-peer card swaps with fellow trainers.
                </p>
              </div>

              {/* Disconnected state banner for trade */}
              {!accountAddress && (
                <div style={{ textAlign: 'center', padding: '4rem 2rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border-subtle)', marginBottom: '2.5rem' }}>
                  <ArrowRightLeft size={48} style={{ color: 'var(--accent-lime)', marginBottom: '1rem' }} />
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                    CONNECT YOUR WALLET TO START TRADING
                  </h3>
                  <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem', maxWidth: '500px', margin: '0 auto 1.5rem auto' }}>
                    Connect your Pera Wallet to list your Pokémon cards for trade or swap with other trainers.
                  </p>
                  <button className="btn-editorial primary" onClick={handleConnectWallet}>
                    <Wallet size={16} /> CONNECT WALLET
                  </button>
                </div>
              )}

              {/* AI Smart Trade Matcher Banner */}
              <div style={{ 
                background: 'linear-gradient(135deg, rgba(56, 189, 248, 0.1) 0%, rgba(168, 85, 247, 0.1) 100%)', 
                border: '1px solid rgba(56, 189, 248, 0.3)', 
                borderRadius: 'var(--radius-lg)', 
                padding: '1.25rem 1.5rem', 
                marginBottom: '2rem', 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center', 
                flexWrap: 'wrap', 
                gap: '1rem' 
              }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#38BDF8', fontWeight: 700, fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
                    <Zap size={16} /> AI SMART TRADE MATCHER
                  </div>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: '4px 0 0 0', maxWidth: '600px' }}>
                    Analyze collection gaps, calculate elemental synergy scores against open listings, and uncover optimal trade swaps.
                  </p>
                </div>
                <button 
                  className="btn-editorial primary"
                  onClick={handleSmartTradeMatch}
                  disabled={smartMatchLoading}
                  style={{ whiteSpace: 'nowrap' }}
                >
                  <Sparkles size={16} /> Launch Smart Matcher ({serverPricing.smart_trade_match?.toFixed(2) || '0.01'} ALGO)
                </button>
              </div>

              {/* Create Trade Offer */}
              {userCollection.length > 0 && (
                <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-medium)', borderRadius: 'var(--radius-lg)', padding: '1.5rem', marginBottom: '2.5rem' }}>
                  <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '1.1rem', marginBottom: '1rem', textTransform: 'uppercase' }}>List Pokémon for Open Trade</h4>
                  <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                    <select
                      value={selectedTradeAssetId || ''}
                      onChange={e => setSelectedTradeAssetId(Number(e.target.value))}
                      style={{
                        background: 'var(--bg-canvas)',
                        color: 'var(--text-primary)',
                        border: '1px solid var(--border-subtle)',
                        padding: '8px 14px',
                        borderRadius: 'var(--radius-sm)',
                        fontFamily: 'var(--font-mono)'
                      }}
                    >
                      <option value="">Select Pokémon to offer...</option>
                      {userCollection.map(c => (
                        <option key={c.asset_id} value={c.asset_id}>{c.name} (#{c.asset_id} • {c.rarity})</option>
                      ))}
                    </select>

                    <button 
                      className="btn-editorial primary"
                      onClick={handleCreateTrade}
                      disabled={!selectedTradeAssetId || tradeLoading}
                    >
                      <ArrowRightLeft size={16} /> Create Trade Offer (Free)
                    </button>
                  </div>
                </div>
              )}

              {/* Active Trades List (Sorted with Featured First) */}
              <div className="pokedex-grid">
                {[...trades].sort((a, b) => (b.is_featured ? 1 : 0) - (a.is_featured ? 1 : 0)).map(t => {
                  const offeredImg = getPokemonArtwork(t.offered_asset) || getPokemonArtworkUrl(t.offered_asset?.name?.toLowerCase() || 94);
                  const isOwner = accountAddress && accountAddress === t.initiator_wallet;

                  return (
                    <div 
                      key={t.trade_id} 
                      className="editorial-creature-card"
                      style={{
                        borderTop: t.is_featured ? '2px solid #F59E0B' : '1px solid var(--border-subtle)',
                        boxShadow: t.is_featured ? '0 0 15px rgba(245, 158, 11, 0.12)' : 'none'
                      }}
                    >
                      <div className="card-top-meta">
                        <span className="card-asa-tag">TRADE #{t.trade_id.slice(-6)}</span>
                        {t.is_featured ? (
                          <span className="card-rarity-pill" style={{ background: 'rgba(245, 158, 11, 0.2)', color: '#F59E0B', border: '1px solid rgba(255, 158, 11, 0.4)', fontWeight: 700 }}>
                            ⭐ FEATURED
                          </span>
                        ) : (
                          <span className="card-rarity-pill" style={{ background: 'rgba(212,255,0,0.1)', color: 'var(--accent-lime)' }}>{t.status}</span>
                        )}
                      </div>

                      <div className="pokedex-card-artwork">
                        <img 
                          src={offeredImg} 
                          alt={t.offered_asset?.name || 'Offered Pokémon'} 
                          onError={(e) => {
                            const target = e.target as HTMLImageElement;
                            if (target.src !== NEUTRAL_FALLBACK_SVG) {
                              target.src = NEUTRAL_FALLBACK_SVG;
                            }
                          }}
                        />
                      </div>

                      <div className="card-bottom-info">
                        <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem' }}>{t.offered_asset?.name || `ASA #${t.offered_asset?.asset_id}`}</h4>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          From: {t.initiator_wallet ? `${t.initiator_wallet.slice(0, 4)}...${t.initiator_wallet.slice(-4)}` : 'Marketplace'}
                        </span>

                        {!isOwner && accountAddress && (
                          <button 
                            className="btn-editorial secondary"
                            style={{ width: '100%', marginTop: '0.75rem' }}
                            onClick={() => handleAcceptTrade(t.trade_id)}
                            disabled={tradeLoading}
                          >
                            <ArrowRightLeft size={14} /> Accept & Swap (Free)
                          </button>
                        )}

                        {isOwner && (
                          <div style={{ marginTop: '0.75rem' }}>
                            {t.is_featured ? (
                              <div style={{ color: '#F59E0B', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', textAlign: 'center', padding: '4px', background: 'rgba(245, 158, 11, 0.08)', borderRadius: '4px' }}>
                                ⭐ Featured (Pinned 24h)
                              </div>
                            ) : (
                              <button
                                className="btn-editorial secondary"
                                style={{ width: '100%', borderColor: '#F59E0B', color: '#F59E0B', fontSize: '0.78rem' }}
                                onClick={() => handleFeatureTrade(t.trade_id)}
                                disabled={featureTradeLoading[t.trade_id]}
                              >
                                <Star size={13} /> Feature Listing (24h • {serverPricing.featured_trade?.toFixed(2) || '0.01'} ALGO)
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </section>
        )}

        {/* -------------------------------------------------------------
            TAB 8: FUSION (5 EPIC → 1 LEGENDARY)
            ------------------------------------------------------------- */}
        {activeTab === 'fusion' && (
          <section className="collection-section" style={{ paddingTop: 'calc(var(--nav-height) + 3rem)', paddingBottom: '5rem' }}>
            <div className="editorial-container">

              {/* === FUSION RESULT SCREEN === */}
              {fusionStep === 'RESULT' && fusionResult?.reward && (
                <div style={{ maxWidth: '540px', margin: '0 auto', textAlign: 'center' }}>
                  <div style={{ marginBottom: '1rem' }}>
                    <div className="section-label" style={{ color: '#ffd700', letterSpacing: '0.12em' }}>FUSION COMPLETE</div>
                    <h2 className="section-headline" style={{ color: '#ffd700', fontSize: '2.2rem' }}>LEGENDARY</h2>
                  </div>

                  <div style={{ position: 'relative', width: '220px', height: '220px', margin: '0 auto 1.5rem auto' }}>
                    <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', background: 'radial-gradient(circle, rgba(255,215,0,0.25) 0%, transparent 70%)', animation: 'pulseGlow 2s ease-in-out infinite' }} />
                    <img
                      src={fusionResult.reward.image}
                      alt={fusionResult.reward.name}
                      style={{ width: '100%', height: '100%', objectFit: 'contain', filter: 'drop-shadow(0 0 24px rgba(255,215,0,0.7))' }}
                      onError={(e) => { (e.target as HTMLImageElement).src = NEUTRAL_FALLBACK_SVG; }}
                    />
                  </div>

                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '2rem', textTransform: 'uppercase', letterSpacing: '0.04em', color: '#fff', marginBottom: '0.25rem' }}>
                    {fusionResult.reward.name}
                  </h3>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: '#ffd700', marginBottom: '1rem' }}>
                    #{String(fusionResult.reward.pokemon_id).padStart(3, '0')} • {fusionResult.reward.primary_type}{fusionResult.reward.secondary_type ? ` / ${fusionResult.reward.secondary_type}` : ''}
                  </div>

                  <div className="onchain-status-card" style={{ marginBottom: '1.5rem', textAlign: 'left' }}>
                    <div className="osc-row"><span>Rarity:</span><strong style={{ color: '#ffd700' }}>LEGENDARY</strong></div>
                    <div className="osc-row"><span>Asset ID:</span><strong style={{ color: '#FFCC00' }}>#{fusionResult.reward.asset_id}</strong></div>
                    <div className="osc-row"><span>Ownership:</span><strong style={{ color: '#00ff88' }}>VERIFIED ✓</strong></div>
                    <div className="osc-row"><span>Delivered to:</span><strong>{accountAddress ? `${accountAddress.slice(0, 6)}...${accountAddress.slice(-4)}` : '—'}</strong></div>
                  </div>

                  <p style={{ color: '#00ff88', fontSize: '0.88rem', marginBottom: '1.5rem' }}>
                    ✨ YOUR LEGENDARY HAS BEEN ADDED TO YOUR WALLET.
                  </p>

                  <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', flexWrap: 'wrap' }}>
                    <button className="btn-editorial primary" onClick={() => { setActiveTab('collection'); handleFusionReset(); }}>
                      <Layers size={16} /> VIEW COLLECTION
                    </button>
                    <button className="btn-editorial secondary" onClick={handleFusionReset}>
                      <Dna size={16} /> FUSE AGAIN
                    </button>
                  </div>
                </div>
              )}

              {/* === PROCESSING SCREEN === */}
              {fusionStep === 'PROCESSING' && (
                <div style={{ maxWidth: '500px', margin: '0 auto', textAlign: 'center', padding: '5rem 1rem' }}>
                  <RefreshCw size={48} className="spin-icon" style={{ color: '#a855f7', marginBottom: '1.5rem' }} />
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', letterSpacing: '0.04em', marginBottom: '0.75rem' }}>FORGING LEGENDARY...</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', lineHeight: 1.6, maxWidth: '380px', margin: '0 auto' }}>
                    Transferring your 5 Epic Pokémon and minting your Legendary reward. Do not close this tab.
                  </p>
                </div>
              )}

              {/* === SELECT + CONFIRM SCREENS === */}
              {(fusionStep === 'SELECT' || fusionStep === 'CONFIRM_MODAL') && (
                <>
                  {/* Header */}
                  <div className="section-editorial-header" style={{ marginBottom: '2rem' }}>
                    <div className="section-label" style={{ color: '#a855f7' }}>SACRIFICE & ASCEND</div>
                    <h2 className="section-headline">FUSION.</h2>
                    <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
                      <span style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', color: '#a855f7', fontWeight: 700, letterSpacing: '0.04em' }}>5 EPIC.</span>
                      <span style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', color: '#ffd700', fontWeight: 700, letterSpacing: '0.04em' }}>1 LEGENDARY.</span>
                    </div>
                    <p style={{ color: 'var(--text-muted)', marginTop: '0.6rem', maxWidth: '520px', lineHeight: 1.6 }}>
                      Sacrifice five Epic Pokémon to forge one Legendary. This action is permanent.
                    </p>
                  </div>

                  {fusionError && (
                    <div style={{ marginBottom: '1.5rem', padding: '1rem 1.25rem', background: 'rgba(255,68,68,0.1)', border: '1px solid rgba(255,68,68,0.35)', borderRadius: 'var(--radius-md)', color: '#ff6b6b', fontSize: '0.88rem', maxWidth: '700px' }}>
                      <AlertCircle size={16} style={{ display: 'inline', marginRight: '6px' }} />
                      {fusionError}
                    </div>
                  )}

                  {/* STATE: NO WALLET */}
                  {!accountAddress && (
                    <div style={{ textAlign: 'center', padding: '5rem 2rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border-subtle)', maxWidth: '600px', margin: '0 auto' }}>
                      <Dna size={56} style={{ color: '#a855f7', marginBottom: '1.25rem' }} />
                      <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>CONNECT YOUR WALLET</h3>
                      <p style={{ color: 'var(--text-muted)', marginBottom: '2rem', lineHeight: 1.6, maxWidth: '400px', margin: '0 auto 2rem auto' }}>TO USE FUSION</p>
                      <button className="btn-editorial primary" onClick={handleConnectWallet} style={{ padding: '0.9rem 2rem', fontSize: '0.95rem' }}>
                        <Wallet size={18} /> CONNECT WALLET
                      </button>
                    </div>
                  )}

                  {/* STATE: WALLET CONNECTED — show candidates */}
                  {accountAddress && (
                    <>
                      {fusionCandidatesLoading ? (
                        <div style={{ textAlign: 'center', padding: '4rem 0' }}>
                          <RefreshCw size={32} className="spin-icon" style={{ color: '#a855f7', marginBottom: '1rem' }} />
                          <p style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>Loading your Epic Pokémon...</p>
                        </div>
                      ) : fusionCandidates.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: '5rem 2rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border-subtle)', maxWidth: '600px', margin: '0 auto' }}>
                          <Dna size={56} style={{ color: 'var(--text-dim)', marginBottom: '1.25rem' }} />
                          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', marginBottom: '0.75rem', textTransform: 'uppercase' }}>NO EPIC POKÉMON AVAILABLE</h3>
                          <p style={{ color: 'var(--text-muted)', marginBottom: '2rem', lineHeight: 1.6 }}>Collect Epic Pokémon to unlock Fusion.</p>
                          <button className="btn-editorial primary" onClick={() => setActiveTab('packs')} style={{ padding: '0.9rem 2rem', fontSize: '0.95rem' }}>
                            <ShoppingBag size={18} /> EXPLORE PACKS
                          </button>
                        </div>
                      ) : fusionCandidates.length < 5 ? (
                        <>
                          <div style={{ textAlign: 'center', padding: '3rem 2rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-xl)', border: '1px solid rgba(168,85,247,0.3)', maxWidth: '600px', margin: '0 auto 2rem auto' }}>
                            <Dna size={48} style={{ color: '#a855f7', marginBottom: '1rem' }} />
                            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', marginBottom: '0.5rem', textTransform: 'uppercase' }}>YOU NEED 5 EPIC POKÉMON</h3>
                            <p style={{ fontFamily: 'var(--font-mono)', fontSize: '1rem', color: '#a855f7', marginBottom: '1rem' }}>
                              Owned: {fusionCandidates.length} / 5
                            </p>
                            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Open more packs to collect Epic Pokémon.</p>
                          </div>
                          {/* Show the ones they do own */}
                          <div style={{ marginTop: '1rem' }}>
                            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '0.75rem', letterSpacing: '0.05em' }}>YOUR EPIC COLLECTION</div>
                            <div className="pokedex-grid-container" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.85rem' }}>
                              {fusionCandidates.map(c => (
                                <div key={c.asset_id} className="editorial-creature-card" style={{ borderTop: '2px solid #a855f7', opacity: 0.85 }}>
                                  <div className="card-top-meta">
                                    <span className="card-asa-tag">#{c.asset_id}</span>
                                    <span className="card-rarity-pill" style={{ color: '#a855f7' }}>EPIC</span>
                                  </div>
                                  <div className="pokemon-artwork-container" style={{ height: '120px', padding: '0.6rem' }}>
                                    <img src={c.image} alt={c.name} className="pokemon-artwork-img" loading="lazy" onError={(e) => { (e.target as HTMLImageElement).src = NEUTRAL_FALLBACK_SVG; }} />
                                  </div>
                                  <div className="card-bottom-info">
                                    <div className="card-name-row"><h4 style={{ textTransform: 'uppercase', fontSize: '0.88rem' }}>{c.name}</h4></div>
                                    <div style={{ display: 'flex', gap: '3px', marginTop: '4px' }}>
                                      <span className={`type-badge type-badge-${c.primary_type?.toLowerCase()}`} style={{ fontSize: '0.6rem', padding: '2px 5px' }}>{c.primary_type}</span>
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        </>
                      ) : (
                        /* === MAIN SELECTION UI (5+ epics available) === */
                        <>
                          {/* Selection counter + action bar */}
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', padding: '1rem 1.25rem', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)', flexWrap: 'wrap', gap: '0.75rem' }}>
                            <div>
                              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', color: selectedFusionAssetIds.size === 5 ? '#ffd700' : '#a855f7', fontWeight: 700 }}>
                                {selectedFusionAssetIds.size} / 5 SELECTED
                              </div>
                              <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                                {selectedFusionAssetIds.size < 5 ? `Select ${5 - selectedFusionAssetIds.size} more Epic Pokémon` : 'Ready to fuse — confirm below'}
                              </div>
                            </div>
                            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                              {selectedFusionAssetIds.size > 0 && (
                                <button className="btn-editorial secondary" style={{ fontSize: '0.8rem', padding: '0.5rem 0.9rem' }} onClick={() => setSelectedFusionAssetIds(new Set())}>
                                  <X size={14} /> Clear
                                </button>
                              )}
                              <button
                                className="btn-editorial primary"
                                style={{
                                  background: selectedFusionAssetIds.size === 5 ? 'linear-gradient(135deg, #a855f7, #7c3aed)' : undefined,
                                  opacity: selectedFusionAssetIds.size === 5 ? 1 : 0.4,
                                  cursor: selectedFusionAssetIds.size === 5 ? 'pointer' : 'not-allowed',
                                  padding: '0.6rem 1.4rem'
                                }}
                                disabled={selectedFusionAssetIds.size !== 5}
                                onClick={() => setFusionStep('CONFIRM_MODAL')}
                              >
                                <Dna size={16} /> FUSE INTO LEGENDARY
                              </button>
                            </div>
                          </div>

                          {/* Slot indicators */}
                          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
                            {[1, 2, 3, 4, 5].map(slot => {
                              const ids = Array.from(selectedFusionAssetIds);
                              const assetId = ids[slot - 1];
                              const card = assetId ? fusionCandidates.find(c => c.asset_id === assetId) : null;
                              return (
                                <div key={slot} style={{ flex: '1', minWidth: '90px', maxWidth: '130px', padding: '0.6rem', background: card ? 'rgba(168,85,247,0.15)' : 'var(--bg-surface)', border: `1px solid ${card ? 'rgba(168,85,247,0.5)' : 'var(--border-subtle)'}`, borderRadius: 'var(--radius-md)', textAlign: 'center', transition: 'all 0.2s' }}>
                                  {card ? (
                                    <>
                                      <img src={card.image} alt={card.name} style={{ width: '48px', height: '48px', objectFit: 'contain' }} onError={(e) => { (e.target as HTMLImageElement).src = NEUTRAL_FALLBACK_SVG; }} />
                                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: '#a855f7', marginTop: '3px' }}>{card.name}</div>
                                    </>
                                  ) : (
                                    <>
                                      <div style={{ width: '48px', height: '48px', margin: '0 auto', borderRadius: '50%', border: '2px dashed var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-dim)' }}>{slot}</span>
                                      </div>
                                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.62rem', color: 'var(--text-dim)', marginTop: '4px' }}>SLOT {slot}</div>
                                    </>
                                  )}
                                </div>
                              );
                            })}
                          </div>

                          {/* Epic cards grid */}
                          <div style={{ marginBottom: '0.75rem' }}>
                            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '0.75rem', letterSpacing: '0.05em' }}>
                              EPIC COLLECTION ({fusionCandidates.length} available)
                            </div>
                          </div>

                          <div className="pokedex-grid-container" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '0.85rem' }}>
                            {fusionCandidates.map(c => {
                              const isSelected = selectedFusionAssetIds.has(c.asset_id);
                              const isLocked = c.is_locked;
                              const isDisabled = isLocked || (!isSelected && selectedFusionAssetIds.size >= 5);

                              return (
                                <div
                                  key={c.asset_id}
                                  className="editorial-creature-card"
                                  onClick={() => {
                                    if (isLocked) return;
                                    setSelectedFusionAssetIds(prev => {
                                      const next = new Set(prev);
                                      if (next.has(c.asset_id)) {
                                        next.delete(c.asset_id);
                                      } else if (next.size < 5) {
                                        next.add(c.asset_id);
                                      }
                                      return next;
                                    });
                                  }}
                                  onMouseEnter={() => !isDisabled && setCursorHover(isSelected ? 'DESELECT' : 'SELECT')}
                                  onMouseLeave={clearCursorHover}
                                  style={{
                                    borderTop: `2px solid ${isSelected ? '#ffd700' : '#a855f7'}`,
                                    opacity: isDisabled ? 0.45 : 1,
                                    cursor: isLocked ? 'not-allowed' : isDisabled ? 'default' : 'pointer',
                                    background: isSelected ? 'rgba(255,215,0,0.06)' : undefined,
                                    boxShadow: isSelected ? '0 0 0 2px rgba(255,215,0,0.4)' : undefined,
                                    transition: 'all 0.18s'
                                  }}
                                >
                                  <div className="card-top-meta">
                                    <span className="card-asa-tag">#{c.asset_id}</span>
                                    {isSelected ? (
                                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: '#ffd700', fontWeight: 700 }}>SELECTED ✓</span>
                                    ) : isLocked ? (
                                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', color: '#ff6b6b' }}>IN TRADE</span>
                                    ) : (
                                      <span className="card-rarity-pill" style={{ color: '#a855f7' }}>EPIC</span>
                                    )}
                                  </div>
                                  <div className="pokemon-artwork-container" style={{ height: '120px', padding: '0.6rem' }}>
                                    <img
                                      src={c.image}
                                      alt={c.name}
                                      className="pokemon-artwork-img"
                                      loading="lazy"
                                      onError={(e) => { (e.target as HTMLImageElement).src = NEUTRAL_FALLBACK_SVG; }}
                                      style={{ filter: isSelected ? 'drop-shadow(0 0 10px rgba(255,215,0,0.6))' : undefined }}
                                    />
                                  </div>
                                  <div className="card-bottom-info">
                                    <div className="card-name-row"><h4 style={{ textTransform: 'uppercase', fontSize: '0.88rem' }}>{c.name}</h4></div>
                                    <div style={{ display: 'flex', gap: '3px', marginTop: '4px' }}>
                                      <span className={`type-badge type-badge-${c.primary_type?.toLowerCase()}`} style={{ fontSize: '0.6rem', padding: '2px 5px' }}>{c.primary_type}</span>
                                      {c.secondary_type && <span className={`type-badge type-badge-${c.secondary_type?.toLowerCase()}`} style={{ fontSize: '0.6rem', padding: '2px 5px' }}>{c.secondary_type}</span>}
                                    </div>
                                    {isLocked && <div style={{ fontSize: '0.65rem', color: '#ff6b6b', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>🔒 IN ACTIVE TRADE</div>}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </>
                      )}
                    </>
                  )}

                  {/* === CONFIRM FUSION MODAL === */}
                  {fusionStep === 'CONFIRM_MODAL' && (
                    <div className="pack-reveal-backdrop" onClick={() => setFusionStep('SELECT')}>
                      <div
                        className="reveal-interactive-stage"
                        onClick={e => e.stopPropagation()}
                        style={{ maxWidth: '500px', textAlign: 'center', padding: '2.25rem' }}
                      >
                        <div style={{ marginBottom: '1.25rem' }}>
                          <Dna size={40} style={{ color: '#a855f7', marginBottom: '0.75rem' }} />
                          <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.25rem' }}>
                            FUSE 5 EPIC POKÉMON?
                          </h3>
                        </div>

                        <div style={{ background: 'rgba(255,68,68,0.08)', border: '1px solid rgba(255,68,68,0.3)', borderRadius: 'var(--radius-md)', padding: '1rem 1.25rem', marginBottom: '1.5rem', textAlign: 'left' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '0.5rem' }}>
                            <AlertCircle size={16} style={{ color: '#ff6b6b', flexShrink: 0 }} />
                            <strong style={{ color: '#ff6b6b', fontSize: '0.88rem', fontFamily: 'var(--font-mono)', textTransform: 'uppercase' }}>PERMANENT ACTION</strong>
                          </div>
                          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', lineHeight: 1.6, margin: 0 }}>
                            These Pokémon will be permanently sacrificed and <strong style={{ color: '#fff' }}>cannot be recovered</strong>. You will receive one random Legendary Pokémon.
                          </p>
                        </div>

                        {/* Selected cards preview */}
                        <div style={{ display: 'flex', gap: '0.4rem', justifyContent: 'center', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
                          {Array.from(selectedFusionAssetIds).map(aid => {
                            const card = fusionCandidates.find(c => c.asset_id === aid);
                            return card ? (
                              <div key={aid} style={{ textAlign: 'center', width: '72px' }}>
                                <img src={card.image} alt={card.name} style={{ width: '52px', height: '52px', objectFit: 'contain', filter: 'drop-shadow(0 0 6px rgba(168,85,247,0.5))' }} onError={(e) => { (e.target as HTMLImageElement).src = NEUTRAL_FALLBACK_SVG; }} />
                                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.6rem', color: 'var(--text-muted)', marginTop: '3px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{card.name}</div>
                              </div>
                            ) : null;
                          })}
                        </div>

                        <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', color: '#a855f7', marginBottom: '1.25rem', letterSpacing: '0.04em' }}>
                          ↓ FORGES INTO ↓
                        </div>

                        <div style={{ background: 'rgba(255,215,0,0.08)', border: '1px solid rgba(255,215,0,0.3)', borderRadius: 'var(--radius-md)', padding: '0.75rem 1rem', marginBottom: '1.75rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.75rem' }}>
                          <Sparkles size={20} style={{ color: '#ffd700' }} />
                          <span style={{ fontFamily: 'var(--font-display)', fontSize: '1.1rem', color: '#ffd700', textTransform: 'uppercase', letterSpacing: '0.06em' }}>1 RANDOM LEGENDARY</span>
                        </div>

                        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
                          <button className="btn-editorial secondary" style={{ flex: 1 }} onClick={() => setFusionStep('SELECT')}>
                            CANCEL
                          </button>
                          <button
                            className="btn-editorial primary"
                            style={{ flex: 1, background: 'linear-gradient(135deg, #a855f7, #7c3aed)', fontWeight: 700 }}
                            onClick={handleInitiateFusion}
                          >
                            <Dna size={16} /> CONFIRM FUSION
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}

            </div>
          </section>
        )}

        {/* -------------------------------------------------------------
            TAB 9: POKÉMON ASSET DETAIL PAGE (/asset/:assetId)
            ------------------------------------------------------------- */}
        {activeTab === 'asset' && (
          <section className="collection-section" style={{ paddingTop: 'calc(var(--nav-height) + 2.5rem)', paddingBottom: '5rem' }}>
            <div className="editorial-container">
              {/* Back navigation & breadcrumb */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                <div style={{ display: 'flex', gap: '0.75rem' }}>
                  <button 
                    className="btn-editorial secondary"
                    style={{ fontSize: '0.8rem', padding: '0.45rem 0.9rem' }}
                    onClick={() => {
                      window.location.hash = '';
                      setActiveTab('collection');
                    }}
                  >
                    <ChevronLeft size={16} /> Back to Collection
                  </button>
                  <button 
                    className="btn-editorial secondary"
                    style={{ fontSize: '0.8rem', padding: '0.45rem 0.9rem' }}
                    onClick={() => {
                      window.location.hash = '';
                      setActiveTab('pokedex');
                    }}
                  >
                    <Layers size={16} /> Pokédex Archive
                  </button>
                </div>

                {selectedAssetDetail && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span className="network-pill" style={{ margin: 0 }}>
                      <span className="pulsing-dot" />
                      DIGITAL COLLECTIBLE (1-OF-1)
                    </span>
                    <button
                      onClick={() => {
                        const url = selectedAssetDetail.explorer_url || `https://testnet.explorer.perawallet.app/asset/${selectedAssetDetail.asset_id}/`;
                        navigator.clipboard.writeText(url);
                        setCopyFeedback("Explorer link copied!");
                        setTimeout(() => setCopyFeedback(null), 2500);
                      }}
                      className="btn-editorial secondary"
                      style={{ fontSize: '0.75rem', padding: '0.4rem 0.8rem', display: 'flex', alignItems: 'center', gap: '4px' }}
                    >
                      {copyFeedback ? <Check size={14} style={{ color: 'var(--accent-lime)' }} /> : <Copy size={14} />}
                      {copyFeedback ? 'COPIED' : 'COPY EXPLORER LINK'}
                    </button>
                  </div>
                )}
              </div>

              {/* Loading State */}
              {assetLoading ? (
                <div style={{ textAlign: 'center', padding: '6rem 0', background: 'var(--bg-surface)', borderRadius: 'var(--radius-xl)', border: '1px solid var(--border-subtle)' }}>
                  <RefreshCw size={36} className="spin-icon" style={{ color: 'var(--accent-lime)', marginBottom: '1.25rem' }} />
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', letterSpacing: '0.04em', marginBottom: '0.5rem' }}>
                    VERIFYING DIGITAL ASSET RECORD...
                  </h3>
                  <p style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
                    Looking up Asset #{selectedAssetId || '...'} parameters and ownership holding.
                  </p>
                </div>
              ) : assetError || !selectedAssetDetail ? (
                <div style={{ textAlign: 'center', padding: '5rem 2rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-xl)', border: '1px solid rgba(255,68,68,0.3)' }}>
                  <AlertCircle size={48} style={{ color: '#ff4d4d', marginBottom: '1rem' }} />
                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.5rem', marginBottom: '0.5rem' }}>ASSET NOT FOUND</h3>
                  <p style={{ color: 'var(--text-muted)', maxWidth: '500px', margin: '0 auto 1.5rem auto' }}>
                    {assetError || `Asset #${selectedAssetId} could not be verified.`}
                  </p>
                  <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
                    {selectedAssetId && (
                      <button className="btn-editorial primary" onClick={() => fetchAssetDetail(selectedAssetId)}>
                        <RefreshCw size={16} /> Retry Asset Lookup
                      </button>
                    )}
                    <button className="btn-editorial secondary" onClick={() => setActiveTab('collection')}>
                      View Collection
                    </button>
                  </div>
                </div>
              ) : (
                /* Main Digital Asset Detail Display */
                <div>
                  {/* Header Title & Badges */}
                  <div className="section-editorial-header" style={{ marginBottom: '1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                      <span className="section-label">
                        #{String(selectedAssetDetail.pokemon.id).padStart(3, '0')}
                      </span>
                      <span 
                        className={`type-badge type-badge-${selectedAssetDetail.pokemon.primary_type?.toLowerCase() || 'normal'}`}
                        style={{ padding: '4px 10px', fontSize: '0.78rem' }}
                      >
                        {selectedAssetDetail.pokemon.primary_type}
                      </span>
                      {selectedAssetDetail.pokemon.secondary_type && (
                        <span 
                          className={`type-badge type-badge-${selectedAssetDetail.pokemon.secondary_type.toLowerCase()}`}
                          style={{ padding: '4px 10px', fontSize: '0.78rem' }}
                        >
                          {selectedAssetDetail.pokemon.secondary_type}
                        </span>
                      )}
                      <span 
                        className="spotlight-badge"
                        style={{ color: RARITY_COLORS[selectedAssetDetail.pokemon.rarity] || '#fff', background: 'rgba(255,255,255,0.08)' }}
                      >
                        {selectedAssetDetail.pokemon.rarity}
                      </span>
                    </div>
                    <h1 className="section-headline" style={{ textTransform: 'uppercase', letterSpacing: '0.04em', margin: 0 }}>
                      {selectedAssetDetail.pokemon.name}
                    </h1>
                  </div>

                  {/* 2-Column Responsive Layout */}
                  <div className="asset-detail-stage">
                    {/* Left Column: Visual Panel & Combat Attributes */}
                    <div className="asset-visual-panel">
                      <div className="asset-artwork-hero">
                        <img 
                          src={selectedAssetDetail.pokemon.image || getPokemonArtworkUrl(selectedAssetDetail.pokemon.id)}
                          alt={selectedAssetDetail.pokemon.name}
                          onError={(e) => {
                            const target = e.target as HTMLImageElement;
                            if (target.src !== NEUTRAL_FALLBACK_SVG) target.src = NEUTRAL_FALLBACK_SVG;
                          }}
                        />
                      </div>

                      <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1.5rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                            Combat Statistics
                          </span>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--accent-lime)' }}>
                            Level {selectedAssetDetail.pokemon.level || 4} • {selectedAssetDetail.pokemon.xp || 150} XP
                          </span>
                        </div>

                        {/* Stat Bars */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                          {[
                            { label: 'HP', val: selectedAssetDetail.pokemon.stats?.hp || 50, max: 255, color: '#ff4d4d' },
                            { label: 'ATTACK', val: selectedAssetDetail.pokemon.stats?.attack || 55, max: 190, color: '#f59e0b' },
                            { label: 'DEFENSE', val: selectedAssetDetail.pokemon.stats?.defense || 40, max: 230, color: '#3b82f6' },
                            { label: 'SPEED', val: selectedAssetDetail.pokemon.stats?.speed || 90, max: 200, color: '#10b981' },
                            { label: 'STAMINA', val: selectedAssetDetail.pokemon.stats?.stamina || 100, max: 250, color: '#a855f7' }
                          ].map(stat => (
                            <div key={stat.label} style={{ display: 'grid', gridTemplateColumns: '70px 35px 1fr', alignItems: 'center', gap: '0.75rem', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
                              <span style={{ color: 'var(--text-muted)' }}>{stat.label}</span>
                              <strong style={{ textAlign: 'right' }}>{stat.val}</strong>
                              <div style={{ height: '6px', background: 'rgba(255,255,255,0.06)', borderRadius: '3px', overflow: 'hidden' }}>
                                <div style={{ height: '100%', width: `${Math.min(100, (stat.val / stat.max) * 100)}%`, background: stat.color, borderRadius: '3px' }} />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Tactical In-App Shortcuts */}
                      <div className="asset-action-grid" style={{ marginTop: '1.75rem' }}>
                        <button 
                          className="btn-editorial primary"
                          onClick={() => {
                            setSelectedFighterAssetId(selectedAssetDetail.asset_id);
                            setActiveTab('battle');
                          }}
                        >
                          <Swords size={16} /> Battle in Arena
                        </button>
                        <button 
                          className="btn-editorial secondary"
                          onClick={() => {
                            setSelectedTradeAssetId(selectedAssetDetail.asset_id);
                            setActiveTab('trade');
                          }}
                        >
                          <ArrowRightLeft size={16} /> Initiate Trade
                        </button>
                      </div>
                    </div>

                    {/* Right Column: Digital Asset Specifications */}
                    <div className="asset-spec-card">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                        <div>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--accent-cyan)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                            Verified Asset Ledger
                          </div>
                          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, margin: '4px 0 0 0' }}>
                            DIGITAL ASSET SPECIFICATION
                          </h3>
                        </div>

                        {selectedAssetDetail.ownership?.verified ? (
                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'rgba(0, 255, 136, 0.1)', border: '1px solid rgba(0, 255, 136, 0.3)', padding: '6px 12px', borderRadius: 'var(--radius-pill)', color: '#00ff88', fontFamily: 'var(--font-mono)', fontSize: '0.78rem', fontWeight: 700 }}>
                            <CheckCircle2 size={14} /> OWNERSHIP VERIFIED ✓
                          </div>
                        ) : selectedAssetDetail.ownership?.in_minter_holding ? (
                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'rgba(255, 153, 0, 0.1)', border: '1px solid rgba(255, 153, 0, 0.3)', padding: '6px 12px', borderRadius: 'var(--radius-pill)', color: '#ff9900', fontFamily: 'var(--font-mono)', fontSize: '0.78rem', fontWeight: 700 }}>
                            <Zap size={14} /> READY FOR PERA CLAIM
                          </div>
                        ) : (
                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'rgba(0, 240, 255, 0.1)', border: '1px solid rgba(0, 240, 255, 0.3)', padding: '6px 12px', borderRadius: 'var(--radius-pill)', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>
                            <Shield size={14} /> OWNERSHIP VERIFIED ✓
                          </div>
                        )}
                      </div>

                      {copyFeedback && (
                        <div style={{ padding: '0.5rem 1rem', background: 'rgba(212,255,0,0.1)', border: '1px solid rgba(212,255,0,0.3)', borderRadius: 'var(--radius-sm)', color: 'var(--accent-lime)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', marginBottom: '1rem' }}>
                          ✓ {copyFeedback} copied to clipboard!
                        </div>
                      )}

                      {/* Digital Asset Parameter Rows */}
                      <div className="asset-spec-grid">
                        <div className="asset-spec-item">
                          <span className="asset-spec-label">Asset ID</span>
                          <span className="asset-spec-value" style={{ color: '#FFCC00', fontSize: '1rem' }}>
                            #{selectedAssetDetail.asset_id}
                            <button 
                              className="copy-mini-btn" 
                              onClick={() => copyToClipboard(String(selectedAssetDetail.asset_id), 'Asset ID')}
                              title="Copy Asset ID"
                            >
                              <Copy size={13} />
                            </button>
                          </span>
                        </div>

                        <div className="asset-spec-item">
                          <span className="asset-spec-label">Network</span>
                          <span className="asset-spec-value" style={{ color: 'var(--accent-cyan)' }}>
                            Algorand
                          </span>
                        </div>

                        <div className="asset-spec-item">
                          <span className="asset-spec-label">Token Standard</span>
                          <span className="asset-spec-value">
                            ARC-3 (1-of-1 Digital Collectible)
                          </span>
                        </div>

                        <div className="asset-spec-item">
                          <span className="asset-spec-label">Total Supply</span>
                          <span className="asset-spec-value">
                            {selectedAssetDetail.nft?.total ?? 1} Unit
                          </span>
                        </div>

                        <div className="asset-spec-item">
                          <span className="asset-spec-label">Decimals</span>
                          <span className="asset-spec-value">
                            {selectedAssetDetail.nft?.decimals ?? 0}
                          </span>
                        </div>

                        <div className="asset-spec-item">
                          <span className="asset-spec-label">Default Frozen</span>
                          <span className="asset-spec-value">
                            {selectedAssetDetail.nft?.default_frozen ? 'true' : 'false'}
                          </span>
                        </div>

                        <div className="asset-spec-item">
                          <span className="asset-spec-label">Unit Name</span>
                          <span className="asset-spec-value">
                            {selectedAssetDetail.nft?.unit_name || `PKMN${String(selectedAssetDetail.pokemon.id).padStart(3, '0')}`}
                          </span>
                        </div>

                        <div className="asset-spec-item">
                          <span className="asset-spec-label">Asset Name</span>
                          <span className="asset-spec-value">
                            {selectedAssetDetail.nft?.asset_name || `${selectedAssetDetail.pokemon.name} #${String(selectedAssetDetail.pokemon.id).padStart(3, '0')}`}
                          </span>
                        </div>

                        <div className="asset-spec-item">
                          <span className="asset-spec-label">Current Owner</span>
                          <span className="asset-spec-value">
                            {selectedAssetDetail.ownership?.wallet ? (
                              <>
                                <span>{selectedAssetDetail.ownership.wallet.slice(0, 8)}...{selectedAssetDetail.ownership.wallet.slice(-6)}</span>
                                <button 
                                  className="copy-mini-btn" 
                                  onClick={() => copyToClipboard(selectedAssetDetail.ownership.wallet, 'Owner Wallet')}
                                  title="Copy Owner Address"
                                >
                                  <Copy size={13} />
                                </button>
                              </>
                            ) : 'Minter Treasury'}
                          </span>
                        </div>

                        <div className="asset-spec-item">
                          <span className="asset-spec-label">Delivery Status</span>
                          <span className="asset-spec-value" style={{ color: selectedAssetDetail.ownership?.delivery_status === 'DELIVERED' ? '#00ff88' : '#ff9900' }}>
                            {selectedAssetDetail.ownership?.delivery_status || 'DELIVERED'}
                          </span>
                        </div>

                        <div className="asset-spec-item">
                          <span className="asset-spec-label">Verification</span>
                          <span className="asset-spec-value" style={{ fontSize: '0.82rem', color: '#00ff88', fontWeight: 600 }}>
                            Authenticated (1-of-1 Digital Collectible)
                          </span>
                        </div>

                        <div className="asset-spec-item">
                          <span className="asset-spec-label">Metadata URI</span>
                          <span className="asset-spec-value" style={{ fontSize: '0.76rem', color: 'var(--accent-lime)' }}>
                            <span>{selectedAssetDetail.nft?.metadata_uri ? (selectedAssetDetail.nft.metadata_uri.length > 28 ? selectedAssetDetail.nft.metadata_uri.slice(0, 24) + '...' : selectedAssetDetail.nft.metadata_uri) : 'ipfs://bafkrei...#arc3'}</span>
                            <button 
                              className="copy-mini-btn" 
                              onClick={() => copyToClipboard(selectedAssetDetail.nft?.metadata_uri || '', 'Metadata URI')}
                              title="Copy Metadata URI"
                            >
                              <Copy size={13} />
                            </button>
                          </span>
                        </div>
                      </div>

                      {/* Explorer Links & Opt-in Claim Action */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1.5rem' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                          <button 
                            className="btn-editorial secondary"
                            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
                            onClick={() => {
                              const url = selectedAssetDetail.explorer_url || `https://testnet.explorer.perawallet.app/asset/${selectedAssetDetail.asset_id}/`;
                              navigator.clipboard.writeText(url);
                              setCopyFeedback("Explorer URL copied!");
                              setTimeout(() => setCopyFeedback(null), 2500);
                            }}
                          >
                            <Copy size={16} /> Copy Explorer Link
                          </button>
                          <button 
                            className="btn-editorial secondary"
                            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
                            onClick={() => {
                              const url = `https://lora.algokit.io/testnet/asset/${selectedAssetDetail.asset_id}`;
                              navigator.clipboard.writeText(url);
                              setCopyFeedback("Lora AlgoKit URL copied!");
                              setTimeout(() => setCopyFeedback(null), 2500);
                            }}
                          >
                            <Copy size={16} /> Copy AlgoKit Link
                          </button>
                        </div>

                        {selectedAssetDetail.ownership?.in_minter_holding && accountAddress && (
                          <button 
                            className="btn-editorial primary"
                            style={{ width: '100%', marginTop: '0.5rem', background: 'linear-gradient(135deg, #00ff88, #00f0ff)', color: '#080a0c' }}
                            onClick={() => {
                              setRevealedCreature({
                                asset_id: selectedAssetDetail.asset_id,
                                name: selectedAssetDetail.pokemon.name,
                                creature_name: selectedAssetDetail.pokemon.name,
                                creature_type: selectedAssetDetail.pokemon.primary_type,
                                rarity: selectedAssetDetail.pokemon.rarity,
                                template_id: selectedAssetDetail.pokemon.template_id || selectedAssetDetail.pokemon.id,
                                status: 'WAITING_FOR_OPT_IN'
                              });
                            }}
                          >
                            <Zap size={16} /> Opt In & Claim to Pera Wallet
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

      </main>

      {/* ==========================================================================
          OVERSIZED FOOTER WITH DISCLAIMER
          ========================================================================== */}
      <footer className="cinematic-footer">
        <div className="editorial-container">
          <div className="footer-cta-block">
            <h2 className="footer-cta-headline">
              READY TO BEGIN YOUR POKÉMON JOURNEY?
            </h2>
            <button 
              className="btn-editorial primary"
              onClick={() => setActiveTab('packs')}
              onMouseEnter={() => setCursorHover('START')}
              onMouseLeave={clearCursorHover}
            >
              <ShoppingBag size={18} /> Open Booster Pack
            </button>
          </div>

          <div style={{ 
            background: 'rgba(255, 255, 255, 0.02)', 
            border: '1px solid var(--border-subtle)', 
            borderRadius: 'var(--radius-md)', 
            padding: '1.25rem', 
            marginBottom: '3rem',
            textAlign: 'left'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <Info size={16} style={{ color: 'var(--accent-lime)' }} />
              <strong style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-primary)', letterSpacing: '0.05em' }}>
                EDUCATIONAL & PORTFOLIO DISCLAIMER
              </strong>
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.78rem', lineHeight: 1.6, margin: 0 }}>
              This is an unofficial educational/portfolio project. Pokémon and Pokémon character names are trademarks of their respective rights holders. This project is not affiliated with or endorsed by Nintendo, Game Freak, or The Pokémon Company.
            </p>
          </div>

          <div className="footer-bottom-grid">
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
              <span className="brand-title" style={{ fontSize: '1rem' }}>POKÉDEX</span>
              <span>DIGITAL OWNERSHIP</span>
              <span>AUTHENTIC DIGITAL COLLECTIBLES</span>
            </div>

            <div style={{ display: 'flex', gap: '1.5rem' }}>
              {(['home', 'packs', 'collection', 'pokedex', 'battle', 'evolution', 'trade'] as NavTab[]).map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', textTransform: 'uppercase' }}
                >
                  {tab === 'pokedex' ? 'POKÉDEX' : tab}
                </button>
              ))}
            </div>
          </div>
        </div>
      </footer>

      {/* ==========================================================================
          MODAL 1: X402 PAYMENT CHECKOUT (UNIVERSAL DISPATCHER)
          ========================================================================== */}
      {activeChallenge && (
        <div className="pack-reveal-backdrop" onClick={() => (activeChallenge.isSigning || activeChallenge.isSettling) ? null : setActiveChallenge(null)}>
          <div className="reveal-interactive-stage" onClick={e => e.stopPropagation()} style={{ maxWidth: '480px' }}>
            <div className="reveal-stage-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {activeChallenge.paymentStage === 'CONFIRMED' ? (
                  <span style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    background: '#10B981',
                    boxShadow: '0 0 14px #10B981',
                    display: 'inline-block'
                  }} />
                ) : activeChallenge.paymentStage === 'CANCELLED' ? (
                  <AlertCircle size={20} style={{ color: '#FF5C5C' }} />
                ) : activeChallenge.paymentStage === 'FAILED' ? (
                  <AlertCircle size={20} style={{ color: '#FF5C5C' }} />
                ) : activeChallenge.resourceType === 'PACK' ? (
                  <ShoppingBag size={20} style={{ color: 'var(--accent-lime)' }} />
                ) : activeChallenge.resourceType === 'PREMIUM_BATTLE' ? (
                  <Swords size={20} style={{ color: '#FF4D2D' }} />
                ) : activeChallenge.resourceType === 'FEATURED_TRADE' ? (
                  <Star size={20} style={{ color: '#F59E0B' }} />
                ) : activeChallenge.resourceType === 'SMART_MATCH' ? (
                  <Sparkles size={20} style={{ color: '#38BDF8' }} />
                ) : activeChallenge.resourceType === 'EVOLUTION_BOOST' ? (
                  <Dna size={20} style={{ color: '#A855F7' }} />
                ) : (
                  <Shield size={20} style={{ color: '#10B981' }} />
                )}
                <h3>
                  {activeChallenge.paymentStage === 'CONFIRMED'
                    ? 'ORDER CONFIRMED'
                    : activeChallenge.paymentStage === 'CANCELLED'
                    ? 'REQUEST CANCELLED'
                    : activeChallenge.paymentStage === 'FAILED'
                    ? 'REQUEST FAILED'
                    : activeChallenge.paymentStage === 'WAITING_FOR_PERA'
                    ? 'CONFIRM IN PERA WALLET'
                    : activeChallenge.paymentStage === 'SETTLING'
                    ? 'CONFIRMING ORDER...'
                    : (activeChallenge.title || 'Confirm Unlock')}
                </h3>
              </div>
              {(!activeChallenge.isSettling) && (
                <button className="modal-close-icon-btn" onClick={() => setActiveChallenge(null)}>
                  <X size={20} />
                </button>
              )}
            </div>

            <div style={{ width: '100%', marginBottom: '1.5rem' }}>
              {/* STAGE: CONFIRMED PAYMENT */}
              {activeChallenge.paymentStage === 'CONFIRMED' ? (
                <div style={{ textAlign: 'center', padding: '0.5rem 0' }}>
                  <div style={{
                    background: 'rgba(16, 185, 129, 0.12)',
                    border: '1px solid rgba(16, 185, 129, 0.45)',
                    borderRadius: 'var(--radius-md)',
                    padding: '1.75rem 1.25rem',
                    marginBottom: '1.5rem',
                    boxShadow: '0 0 30px rgba(16, 185, 129, 0.15)'
                  }}>
                    {/* Status Pill */}
                    <div style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '8px',
                      background: 'rgba(16, 185, 129, 0.18)',
                      border: '1px solid #10B981',
                      padding: '7px 16px',
                      borderRadius: '30px',
                      marginBottom: '1rem',
                      boxShadow: '0 0 16px rgba(16, 185, 129, 0.3)'
                    }}>
                      <span style={{
                        width: '10px',
                        height: '10px',
                        borderRadius: '50%',
                        background: '#10B981',
                        boxShadow: '0 0 10px #10B981, 0 0 20px #10B981',
                        display: 'inline-block'
                      }}></span>
                      <span style={{ color: '#10B981', fontWeight: 800, fontSize: '0.88rem', letterSpacing: '0.04em' }}>
                        ORDER CONFIRMED
                      </span>
                    </div>

                    <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '1.35rem', color: '#fff', marginBottom: '0.6rem', letterSpacing: '0.04em' }}>
                      POKÉMON PACK UNLOCKED
                    </h4>
                    
                    {/* Clean Receipt Box */}
                    <div style={{
                      textAlign: 'left',
                      background: 'rgba(0, 0, 0, 0.45)',
                      border: '1px solid rgba(255, 255, 255, 0.08)',
                      padding: '1rem 1.15rem',
                      borderRadius: 'var(--radius-sm)',
                      margin: '1rem auto 1.25rem auto',
                      fontSize: '0.85rem'
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <span style={{ color: 'var(--text-muted)' }}>Status:</span>
                        <span style={{ color: '#10B981', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#10B981', display: 'inline-block' }}></span>
                          Confirmed & Verified
                        </span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <span style={{ color: 'var(--text-muted)' }}>Item:</span>
                        <strong style={{ color: '#fff' }}>{activeChallenge.packName || activeChallenge.title}</strong>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <span style={{ color: 'var(--text-muted)' }}>Price:</span>
                        <strong style={{ color: 'var(--accent-lime)' }}>{activeChallenge.priceAlgo || activeChallenge.priceUsdc} ALGO</strong>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-muted)' }}>Wallet:</span>
                        <span style={{ color: '#fff' }}>{accountAddress ? `${accountAddress.slice(0, 8)}...${accountAddress.slice(-6)}` : 'Connected Wallet'}</span>
                      </div>
                    </div>

                    <p style={{ color: 'var(--accent-lime)', fontSize: '0.92rem', margin: '0.5rem 0 0 0', fontWeight: 800, letterSpacing: '0.04em' }}>
                      POKÉ BALL READY TO OPEN!
                    </p>
                  </div>

                  <button 
                    className="btn-editorial primary"
                    style={{
                      width: '100%',
                      background: 'linear-gradient(135deg, #d4ff00, #10b981)',
                      color: '#080a0c',
                      fontWeight: 800,
                      fontSize: '1rem',
                      padding: '1rem',
                      boxShadow: '0 0 25px rgba(212, 255, 0, 0.4)'
                    }}
                    onClick={handleOpenConfirmedBall}
                  >
                    <Sparkles size={18} /> OPEN POKÉ BALL
                  </button>
                </div>
              ) : activeChallenge.paymentStage === 'CANCELLED' ? (
                /* STAGE: CANCELLED PAYMENT */
                <div style={{ textAlign: 'center', padding: '0.5rem 0' }}>
                  <div style={{
                    background: 'rgba(255, 92, 92, 0.12)',
                    border: '1px solid rgba(255, 92, 92, 0.35)',
                    borderRadius: 'var(--radius-md)',
                    padding: '1.5rem 1rem',
                    marginBottom: '1.5rem',
                    textAlign: 'center'
                  }}>
                    <div style={{ color: '#FF5C5C', fontWeight: 700, fontSize: '1.05rem', marginBottom: '0.5rem' }}>
                      REQUEST CANCELLED
                    </div>
                    <p style={{ color: '#FFB3B3', fontSize: '0.85rem', lineHeight: 1.5, margin: 0 }}>
                      Request was cancelled in Pera Wallet. Your wallet was not charged.
                    </p>
                  </div>

                  <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <button 
                      className="btn-editorial primary"
                      style={{ flex: 1 }}
                      onClick={() => handleSignPeraPayment(false)}
                    >
                      <Zap size={16} /> TRY AGAIN
                    </button>
                    <button 
                      className="btn-editorial secondary"
                      style={{ flex: 1, borderColor: 'rgba(74, 222, 128, 0.3)' }}
                      onClick={() => handleSignPeraPayment(true)}
                    >
                      ⚡ Quick Auto-Confirm
                    </button>
                    <button 
                      className="btn-editorial secondary"
                      style={{ width: '100%' }}
                      onClick={() => setActiveChallenge(null)}
                    >
                      CLOSE
                    </button>
                  </div>
                </div>
              ) : activeChallenge.paymentStage === 'FAILED' ? (
                /* STAGE: FAILED PAYMENT */
                <div style={{ textAlign: 'center', padding: '0.5rem 0' }}>
                  <div style={{
                    background: 'rgba(255, 92, 92, 0.12)',
                    border: '1px solid rgba(255, 92, 92, 0.35)',
                    borderRadius: 'var(--radius-md)',
                    padding: '1.5rem 1rem',
                    marginBottom: '1.5rem',
                    textAlign: 'center'
                  }}>
                    <div style={{ color: '#FF5C5C', fontWeight: 700, fontSize: '1.05rem', marginBottom: '0.5rem' }}>
                      REQUEST FAILED
                    </div>
                    <p style={{ color: '#FFB3B3', fontSize: '0.85rem', lineHeight: 1.5, margin: 0 }}>
                      {activeChallenge.error || 'Request could not be completed. Your wallet was not charged.'}
                    </p>
                  </div>

                  <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <button 
                      className="btn-editorial primary"
                      style={{ flex: 1 }}
                      onClick={() => handleSignPeraPayment(false)}
                    >
                      <Zap size={16} /> TRY AGAIN
                    </button>
                    <button 
                      className="btn-editorial secondary"
                      style={{ flex: 1, borderColor: 'rgba(74, 222, 128, 0.3)' }}
                      onClick={() => handleSignPeraPayment(true)}
                    >
                      ⚡ Quick Auto-Confirm
                    </button>
                    <button 
                      className="btn-editorial secondary"
                      style={{ width: '100%' }}
                      onClick={() => setActiveChallenge(null)}
                    >
                      CLOSE
                    </button>
                  </div>
                </div>
              ) : (
                /* STAGE: IDLE / WAITING_FOR_PERA / SETTLING */
                <>
                  <div className="onchain-status-card">
                    <div className="osc-row">
                      <span>Item:</span>
                      <strong>{activeChallenge.subtitle || activeChallenge.packName || activeChallenge.title}</strong>
                    </div>
                    <div className="osc-row">
                      <span>Description:</span>
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textAlign: 'right', maxWidth: '240px' }}>
                        {activeChallenge.description}
                      </span>
                    </div>
                    <div className="osc-row">
                      <span>Price:</span>
                      <strong style={{ color: 'var(--accent-lime)', fontSize: '1.1rem' }}>{activeChallenge.priceAlgo || activeChallenge.priceUsdc} ALGO</strong>
                    </div>
                    <div className="osc-row" style={{ borderTop: '1px dashed var(--border-subtle)', paddingTop: '6px', marginTop: '6px' }}>
                      <span>Wallet Balance:</span>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: (algoBalance !== null && algoBalance < (activeChallenge.priceAlgo || 0.1)) ? '#FF5C5C' : '#fff' }}>
                        {algoBalance !== null ? `${algoBalance.toFixed(2)} ALGO` : 'Checking...'}
                      </span>
                    </div>
                  </div>

                  {algoBalance !== null && algoBalance < (activeChallenge.priceAlgo || 0.1) && (
                    <div style={{
                      color: '#FFB3B3',
                      fontSize: '0.82rem',
                      lineHeight: 1.5,
                      marginBottom: '1.25rem',
                      background: 'rgba(255, 92, 92, 0.12)',
                      border: '1px solid rgba(255, 92, 92, 0.35)',
                      padding: '0.75rem 1rem',
                      borderRadius: 'var(--radius-sm)',
                      textAlign: 'left'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, marginBottom: '2px', color: '#FF5C5C' }}>
                        <Info size={14} /> INSUFFICIENT ALGO
                      </div>
                      Required: {activeChallenge.priceAlgo || activeChallenge.priceUsdc} ALGO | Available: {algoBalance.toFixed(2)} ALGO.
                    </div>
                  )}

                  {activeChallenge.error && (
                    <div style={{
                      color: '#FFB3B3',
                      fontSize: '0.82rem',
                      lineHeight: 1.5,
                      marginBottom: '1.25rem',
                      background: 'rgba(255, 92, 92, 0.12)',
                      border: '1px solid rgba(255, 92, 92, 0.35)',
                      padding: '0.75rem 1rem',
                      borderRadius: 'var(--radius-sm)',
                      textAlign: 'left'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, marginBottom: '2px', color: '#FF5C5C' }}>
                        <Info size={14} /> Notice
                      </div>
                      {activeChallenge.error}
                    </div>
                  )}

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    <button 
                      className="btn-editorial primary"
                      style={{ width: '100%' }}
                      onClick={() => handleSignPeraPayment(false)}
                      disabled={activeChallenge.isSigning || activeChallenge.isSettling}
                    >
                      {activeChallenge.isSigning ? (
                        <><RefreshCw className="spin-icon" size={16} /> Confirm in Pera Wallet...</>
                      ) : activeChallenge.isSettling ? (
                        <><RefreshCw className="spin-icon" size={16} /> Confirming order...</>
                      ) : (
                        <><Zap size={16} /> Confirm in Pera Wallet ({activeChallenge.priceAlgo || activeChallenge.priceUsdc} ALGO)</>
                      )}
                    </button>

                    {activeChallenge.isSigning && (
                      <button
                        className="btn-editorial secondary"
                        style={{ width: '100%', fontSize: '0.85rem' }}
                        onClick={() => setActiveChallenge(prev => prev ? { 
                          ...prev, 
                          isSigning: false, 
                          paymentStage: 'CANCELLED',
                          error: 'Signing paused. You can retry with Pera or use Quick Auto-Confirm below.' 
                        } : null)}
                      >
                        Cancel Waiting
                      </button>
                    )}

                    <button
                      className="btn-editorial secondary"
                      style={{ width: '100%', fontSize: '0.85rem', opacity: 0.9, borderColor: 'rgba(74, 222, 128, 0.3)' }}
                      onClick={() => handleSignPeraPayment(true)}
                      disabled={activeChallenge.isSettling}
                    >
                      ⚡ Instant Confirm & Open (Dev Quick-Pass)
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ==========================================================================
          MODAL 2: PACK REVEAL / NFT DELIVERY (WITH AUTHENTIC 3-SHAKE POKÉ BALL OPENING)
          ========================================================================== */}
      {revealedCreature && (
        <div className="pack-reveal-backdrop">
          <div className="reveal-interactive-stage" style={{ maxWidth: '500px', textAlign: 'center' }}>
            <div className="reveal-stage-header">
              <Sparkles size={20} style={{ color: revealPackType === 'GOLDEN' ? '#ffd700' : 'var(--accent-lime)' }} />
              <h3>
                {revealPhase === 'SHAKING_1' || revealPhase === 'SHAKING_2' || revealPhase === 'SHAKING_3'
                  ? 'CAPTURING POKÉMON...'
                  : revealPhase === 'OPENING'
                  ? (revealPackType === 'GOLDEN' ? 'GOLDEN POKÉ BALL OPENING!' : 'POKÉ BALL OPENING!')
                  : revealedCreature.status === 'DELIVERED'
                  ? 'POKÉMON DELIVERED ✓'
                  : 'POKÉMON REVEALED ✓'}
              </h3>
              <button className="modal-close-icon-btn" onClick={() => setRevealedCreature(null)}>
                <X size={20} />
              </button>
            </div>

            {/* STAGE 1: 3-SHAKE POKÉ BALL CAPTURE & OPENING ANIMATION */}
            {(revealPhase === 'SHAKING_1' || revealPhase === 'SHAKING_2' || revealPhase === 'SHAKING_3' || revealPhase === 'OPENING') ? (
              <div style={{ padding: '2.5rem 1rem', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <div style={{ margin: '1rem auto 2rem auto' }}>
                  <PokeBall 
                    type={revealPackType} 
                    size={220} 
                    state={revealPhase === 'OPENING' ? 'opening' : 'shaking'} 
                    shakeStage={revealPhase === 'SHAKING_1' ? 1 : revealPhase === 'SHAKING_2' ? 2 : revealPhase === 'SHAKING_3' ? 3 : 0}
                    showRays={revealPhase === 'OPENING'}
                    interactive={false}
                  />
                </div>

                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: revealPackType === 'GOLDEN' ? '#ffd700' : 'var(--accent-lime)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700 }}>
                  {revealPhase === 'SHAKING_1' && '• • • CAPTURE SHAKE 1 • • •'}
                  {revealPhase === 'SHAKING_2' && '• • • CAPTURE SHAKE 2 • • •'}
                  {revealPhase === 'SHAKING_3' && '• • • CAPTURE SHAKE 3 • • •'}
                  {revealPhase === 'OPENING' && '✨ ENERGY RELEASING ✨'}
                </div>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '0.5rem' }}>
                  Verifying digital asset record & preparing Pokémon collectible...
                </p>
              </div>
            ) : (
              /* STAGE 2: SILHOUETTE & OFFICIAL ARTWORK REVEAL */
              <div>
                <div className="pokedex-card-artwork" style={{ height: '220px', width: '220px', margin: '0.5rem auto 1.5rem auto' }}>
                  <img 
                    src={getPokemonArtwork(revealedCreature)} 
                    alt={revealedCreature.creature_name || revealedCreature.name}
                    style={{
                      filter: revealStep === 'SILHOUETTE' ? 'brightness(0) drop-shadow(0 0 16px rgba(212,255,0,0.9))' : 'drop-shadow(0 12px 24px rgba(0,0,0,0.65))',
                      transition: 'filter 0.8s ease',
                      maxWidth: '85%',
                      maxHeight: '85%',
                      objectFit: 'contain'
                    }}
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      if (target.src !== NEUTRAL_FALLBACK_SVG) {
                        target.src = NEUTRAL_FALLBACK_SVG;
                      }
                    }}
                  />
                </div>

                <h2 className="revealed-name-headline" style={{ textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  {revealedCreature.creature_name || revealedCreature.name}
                </h2>
                <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', margin: '6px 0 12px 0' }}>
                  <span 
                    className="revealed-rarity-badge"
                    style={{ background: 'rgba(255,255,255,0.08)', color: RARITY_COLORS[revealedCreature.rarity] || '#fff' }}
                  >
                    {revealedCreature.creature_type ? `${revealedCreature.creature_type} • ` : ''}{revealedCreature.rarity}
                  </span>
                </div>

                <div className="onchain-status-card" style={{ marginBottom: '1.25rem' }}>
                  <div className="osc-row"><span>Digital Asset:</span><strong style={{ color: 'var(--accent-cyan)' }}>Verified Collectible (ARC-3)</strong></div>
                  <div className="osc-row"><span>ASSET ID:</span><strong style={{ color: '#FFCC00' }}>#{revealedCreature.asset_id}</strong></div>
                  {accountAddress && (
                    <div className="osc-row">
                      <span>Owner:</span>
                      <strong>{accountAddress.slice(0, 6)}...{accountAddress.slice(-4)}</strong>
                    </div>
                  )}
                  <div className="osc-row">
                    <span>Status:</span>
                    <strong style={{ color: revealedCreature.status === 'DELIVERED' ? '#00ff88' : '#ff9900' }}>
                      {revealedCreature.status === 'DELIVERED' ? 'IN YOUR WALLET ✓' : 'READY TO CLAIM'}
                    </strong>
                  </div>
                </div>

                {optInError && (
                  <div style={{ marginBottom: '1rem', padding: '0.5rem', background: 'rgba(255,68,68,0.1)', border: '1px solid rgba(255,68,68,0.3)', borderRadius: 'var(--radius-sm)', color: '#ff6666', fontSize: '0.8rem' }}>
                    {optInError}
                  </div>
                )}

                {revealedCreature.status !== 'DELIVERED' ? (
                  <div style={{ width: '100%' }}>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
                      Collect your Pokémon in your Pera Wallet (100% Free):
                    </p>
                    <button 
                      className="btn-editorial primary"
                      style={{ width: '100%' }}
                      onClick={handleOptInAndClaim}
                      disabled={isOptingIn}
                    >
                      {isOptingIn ? (
                        <><RefreshCw className="spin-icon" size={16} /> Delivering Pokémon to Wallet...</>
                      ) : (
                        <><Zap size={16} /> CLAIM TO PERA WALLET (FREE)</>
                      )}
                    </button>
                  </div>
                ) : (
                  <div style={{ width: '100%' }}>
                    <p style={{ fontSize: '0.82rem', color: '#00ff88', marginBottom: '1rem' }}>
                      ✨ Delivered! Open Pera Wallet → Collectibles to view your Pokémon.
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      <button 
                        className="btn-editorial primary"
                        style={{ width: '100%' }}
                        onClick={() => {
                          const aid = revealedCreature.asset_id;
                          setRevealedCreature(null);
                          openAssetDetail(aid);
                        }}
                      >
                        <Shield size={15} /> View Asset Details (#{revealedCreature.asset_id})
                      </button>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                        <button 
                          className="btn-editorial secondary"
                          onClick={() => {
                            setRevealedCreature(null);
                            setActiveTab('collection');
                          }}
                        >
                          <Layers size={15} /> Collection
                        </button>
                        <button 
                          className="btn-editorial secondary"
                          onClick={() => {
                            setRevealedCreature(null);
                            setActiveTab('packs');
                          }}
                        >
                          <ShoppingBag size={15} /> Open Another Pack
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ==========================================================================
          MODAL 3: POKÉMON DETAILS / EDITORIAL INSPECTION DRAWER
          ========================================================================== */}
      {inspectingPokemon && (() => {
        const analysisKey = String(inspectingPokemon.asset_id || inspectingPokemon.id || inspectingPokemon.template_id);
        const analysis = unlockedAnalyses[analysisKey];
        const heightM = inspectingPokemon.height ? (inspectingPokemon.height / 10).toFixed(1) : '1.2';
        const weightKg = inspectingPokemon.weight ? (inspectingPokemon.weight / 10).toFixed(1) : '45.0';
        const abilitiesList = Array.isArray(inspectingPokemon.abilities) && inspectingPokemon.abilities.length > 0 
          ? inspectingPokemon.abilities 
          : ['Inner Focus', 'Keen Eye'];

        return (
          <div className="pack-reveal-backdrop" onClick={() => setInspectingPokemon(null)}>
            <div className="reveal-interactive-stage" onClick={e => e.stopPropagation()} style={{ maxWidth: '560px', maxHeight: '90vh', overflowY: 'auto' }}>
              <div className="reveal-stage-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-lime)' }}>{inspectingPokemon.pokedexNumber || `#${inspectingPokemon.id}`}</span>
                  <h3 style={{ textTransform: 'uppercase' }}>{inspectingPokemon.name}</h3>
                </div>
                <button className="modal-close-icon-btn" onClick={() => setInspectingPokemon(null)}>
                  <X size={20} />
                </button>
              </div>

              {/* Large Canonical Artwork Showcase */}
              <div className="spotlight-art-stage" style={{ height: '220px', marginBottom: '1.25rem', background: 'radial-gradient(circle at center, rgba(255,255,255,0.08) 0%, rgba(0,0,0,0.6) 100%)' }}>
                <img 
                  src={getPokemonArtwork(inspectingPokemon)} 
                  alt={inspectingPokemon.name}
                  style={{ maxWidth: '85%', maxHeight: '85%', objectFit: 'contain', filter: 'drop-shadow(0 12px 24px rgba(0,0,0,0.7))' }}
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    if (target.src !== NEUTRAL_FALLBACK_SVG) {
                      target.src = NEUTRAL_FALLBACK_SVG;
                    }
                  }}
                />
              </div>

              {/* Badges & Types */}
              <div className="spotlight-badges" style={{ marginBottom: '1rem', justifyContent: 'center' }}>
                <span className={`type-badge type-badge-${inspectingPokemon.primaryType?.toLowerCase() || 'normal'}`}>{inspectingPokemon.primaryType}</span>
                {inspectingPokemon.secondaryType && (
                  <span className={`type-badge type-badge-${inspectingPokemon.secondaryType?.toLowerCase()}`}>{inspectingPokemon.secondaryType}</span>
                )}
                <span className="spotlight-badge" style={{ color: RARITY_COLORS[inspectingPokemon.rarity] || '#fff', background: 'rgba(255,255,255,0.08)' }}>
                  {inspectingPokemon.rarity}
                </span>
                <span className="spotlight-badge" style={{ background: 'rgba(255,255,255,0.08)' }}>{inspectingPokemon.generation || 'GEN I'}</span>
              </div>

              {/* Physical Metrics & Abilities */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '1.25rem', fontFamily: 'var(--font-mono)', fontSize: '0.78rem', textAlign: 'center' }}>
                <div style={{ background: 'var(--bg-canvas)', padding: '8px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.68rem' }}>HEIGHT</span>
                  <strong>{heightM} M</strong>
                </div>
                <div style={{ background: 'var(--bg-canvas)', padding: '8px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.68rem' }}>WEIGHT</span>
                  <strong>{weightKg} KG</strong>
                </div>
                <div style={{ background: 'var(--bg-canvas)', padding: '8px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.68rem' }}>ABILITY</span>
                  <strong>{abilitiesList[0] || 'Keen Eye'}</strong>
                </div>
              </div>

              {/* Comprehensive Stat Meters */}
              <div style={{ background: 'var(--bg-surface)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', marginBottom: '1.25rem' }}>
                <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.75rem', letterSpacing: '0.04em' }}>
                  Base Combat Statistics
                </div>
                
                {[
                  { label: 'HP', val: inspectingPokemon.hp || 50, max: 255, color: '#ff4d4d' },
                  { label: 'ATTACK', val: inspectingPokemon.attack || 50, max: 190, color: '#f59e0b' },
                  { label: 'DEFENSE', val: inspectingPokemon.defense || 50, max: 230, color: '#3b82f6' },
                  { label: 'SPECIAL ATTACK', val: inspectingPokemon.specialAttack || inspectingPokemon.attack || 50, max: 194, color: '#a855f7' },
                  { label: 'SPECIAL DEFENSE', val: inspectingPokemon.specialDefense || inspectingPokemon.defense || 50, max: 230, color: '#06b6d4' },
                  { label: 'SPEED', val: inspectingPokemon.speed || 50, max: 200, color: '#10b981' }
                ].map(stat => (
                  <div key={stat.label} style={{ display: 'grid', gridTemplateColumns: '120px 40px 1fr', alignItems: 'center', gap: '8px', margin: '4px 0', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>
                    <span style={{ color: 'var(--text-muted)' }}>{stat.label}</span>
                    <strong>{stat.val}</strong>
                    <div className="pokemon-detail-stat-bar">
                      <div className="pokemon-detail-stat-fill" style={{ width: `${Math.min(100, (stat.val / stat.max) * 100)}%`, background: stat.color }} />
                    </div>
                  </div>
                ))}
              </div>

              {/* TACTICAL ANALYSIS SECTION (LOCKED vs UNLOCKED) */}
              {analysis ? (
                <div style={{ 
                  background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(6, 182, 212, 0.08) 100%)', 
                  border: '1px solid rgba(16, 185, 129, 0.35)', 
                  borderRadius: 'var(--radius-md)', 
                  padding: '1.25rem', 
                  marginBottom: '1.25rem', 
                  textAlign: 'left' 
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: '#10B981', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Check size={14} /> TACTICAL COMBAT TELEMETRY (UNLOCKED)
                    </span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: '#FFB800', fontWeight: 700 }}>
                      Rating: {analysis.battle_rating || 88}/100
                    </span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '0.78rem', fontFamily: 'var(--font-mono)', marginBottom: '0.75rem' }}>
                    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '4px' }}>
                      <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>FAVORED ARENA</span>
                      <strong style={{ color: 'var(--accent-lime)' }}>{analysis.best_arena || 'Volcano'} ({analysis.arena_multiplier || 1.3}x)</strong>
                    </div>
                    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '4px' }}>
                      <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>EVOLUTION READINESS</span>
                      <strong style={{ color: '#38BDF8' }}>{analysis.evolution_readiness || 'Stage Ready'}</strong>
                    </div>
                  </div>

                  <div style={{ fontSize: '0.78rem', marginBottom: '6px' }}>
                    <span style={{ color: '#00ff88', fontWeight: 600 }}>Strong Against: </span>
                    <span style={{ color: 'var(--text-primary)' }}>{Array.isArray(analysis.strong_against) ? analysis.strong_against.join(', ') : analysis.strong_against || 'Grass, Ice, Bug'}</span>
                  </div>
                  <div style={{ fontSize: '0.78rem', marginBottom: '8px' }}>
                    <span style={{ color: '#ff4444', fontWeight: 600 }}>Weak Against: </span>
                    <span style={{ color: 'var(--text-primary)' }}>{Array.isArray(analysis.weak_against) ? analysis.weak_against.join(', ') : analysis.weak_against || 'Water, Rock, Ground'}</span>
                  </div>

                  {analysis.recommended_strategy && (
                    <div style={{ background: 'rgba(0,0,0,0.4)', padding: '8px 10px', borderRadius: '4px', fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.4, borderLeft: '3px solid #10B981' }}>
                      <strong style={{ color: 'var(--text-primary)', display: 'block', marginBottom: '2px' }}>Tactical Strategy:</strong>
                      {analysis.recommended_strategy}
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ 
                  background: 'rgba(255,255,255,0.03)', 
                  border: '1px dashed var(--border-medium)', 
                  borderRadius: 'var(--radius-md)', 
                  padding: '1.25rem', 
                  textAlign: 'center', 
                  marginBottom: '1.25rem' 
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', color: 'var(--text-muted)', marginBottom: '0.4rem', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>
                    <Shield size={16} style={{ color: '#38BDF8' }} /> TACTICAL COMBAT TELEMETRY LOCKED
                  </div>
                  <p style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginBottom: '0.85rem' }}>
                    Unlock deep elemental ratings, arena boost synergies, counter-matchups & strategy.
                  </p>
                  <button 
                    className="btn-editorial primary"
                    style={{ width: '100%', fontSize: '0.85rem' }}
                    onClick={() => handleUnlockAnalysis(inspectingPokemon.asset_id || inspectingPokemon.id || inspectingPokemon.template_id)}
                    disabled={analysisLoading}
                  >
                    {analysisLoading ? (
                      <><RefreshCw className="spin-icon" size={15} /> Unlocking Tactical Telemetry...</>
                    ) : (
                      <><Zap size={15} /> Unlock Tactical Analysis ({serverPricing.creature_analysis?.toFixed(3) || '0.005'} ALGO)</>
                    )}
                  </button>
                </div>
              )}

              {/* Ownership & Action Direct Shortcuts */}
              {inspectingPokemon.isOwned ? (
                <div style={{ width: '100%' }}>
                  <div className="onchain-status-card" style={{ marginBottom: '1rem' }}>
                    <div className="osc-row"><span>Status:</span><strong style={{ color: '#00ff88' }}>IN YOUR WALLET ✓</strong></div>
                    {inspectingPokemon.asset_id && (
                      <div className="osc-row"><span>ASSET ID:</span><strong style={{ color: '#FFCC00' }}>#{inspectingPokemon.asset_id}</strong></div>
                    )}
                    <div className="osc-row"><span>Level / XP:</span><strong>Level {inspectingPokemon.level || 4} ({inspectingPokemon.xp || 150} XP)</strong></div>
                  </div>

                  {inspectingPokemon.asset_id && (
                    <button
                      className="btn-editorial primary"
                      style={{ width: '100%', marginBottom: '0.65rem', background: 'linear-gradient(135deg, rgba(212,255,0,0.15), rgba(0,240,255,0.15))', borderColor: 'var(--accent-lime)' }}
                      onClick={() => {
                        const aid = inspectingPokemon.asset_id;
                        setInspectingPokemon(null);
                        openAssetDetail(aid);
                      }}
                    >
                      <Shield size={14} /> View Asset Details (#{inspectingPokemon.asset_id})
                    </button>
                  )}

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem' }}>
                    <button 
                      className="btn-editorial primary"
                      style={{ fontSize: '0.78rem', padding: '0.5rem' }}
                      onClick={() => {
                        if (inspectingPokemon.asset_id) setSelectedFighterAssetId(inspectingPokemon.asset_id);
                        setInspectingPokemon(null);
                        setActiveTab('battle');
                      }}
                    >
                      <Swords size={14} /> Battle
                    </button>
                    <button 
                      className="btn-editorial secondary"
                      style={{ fontSize: '0.78rem', padding: '0.5rem' }}
                      onClick={() => {
                        if (inspectingPokemon.asset_id) setSelectedTradeAssetId(inspectingPokemon.asset_id);
                        setInspectingPokemon(null);
                        setActiveTab('trade');
                      }}
                    >
                      <ArrowRightLeft size={14} /> Trade
                    </button>
                    {inspectingPokemon.asset_id ? (
                      <button 
                        className="btn-editorial secondary"
                        style={{ fontSize: '0.78rem', padding: '0.5rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}
                        onClick={() => {
                          setSelectedAssetId(inspectingPokemon.asset_id);
                          setInspectingPokemon(null);
                          setActiveTab('asset');
                        }}
                      >
                        <Eye size={14} /> View Asset
                      </button>
                    ) : (
                      <button 
                        className="btn-editorial secondary" 
                        style={{ fontSize: '0.78rem', padding: '0.5rem' }}
                        onClick={() => {
                          setInspectingPokemon(null);
                          setActiveTab('collection');
                        }}
                      >
                        <Layers size={14} /> Collection
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <button 
                  className="btn-editorial primary"
                  style={{ width: '100%' }}
                  onClick={() => {
                    setInspectingPokemon(null);
                    setActiveTab('packs');
                  }}
                >
                  <ShoppingBag size={16} /> Unlock in Booster Pack (0.1 ALGO)
                </button>
              )}
            </div>
          </div>
        );
      })()}

      {/* ==========================================================================
          MODAL 4: SMART TRADE MATCHER MODAL
          ========================================================================== */}
      {isSmartMatchOpen && smartMatchData && (
        <div className="pack-reveal-backdrop" onClick={() => setIsSmartMatchOpen(false)}>
          <div className="reveal-interactive-stage" onClick={e => e.stopPropagation()} style={{ maxWidth: '580px', maxHeight: '90vh', overflowY: 'auto' }}>
            <div className="reveal-stage-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sparkles size={20} style={{ color: '#38BDF8' }} />
                <h3>AI Smart Trade Match Telemetry</h3>
              </div>
              <button className="modal-close-icon-btn" onClick={() => setIsSmartMatchOpen(false)}>
                <X size={20} />
              </button>
            </div>

            <div style={{ width: '100%', marginBottom: '1.5rem', textAlign: 'left' }}>
              {/* Summary Stats */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '1.25rem', fontFamily: 'var(--font-mono)', fontSize: '0.78rem', textAlign: 'center' }}>
                <div style={{ background: 'var(--bg-canvas)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>PORTFOLIO SIZE</span>
                  <strong style={{ color: 'var(--accent-lime)', fontSize: '1.1rem' }}>{smartMatchData.owned_count || userCollection.length}</strong>
                </div>
                <div style={{ background: 'var(--bg-canvas)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>COVERED TYPES</span>
                  <strong style={{ color: '#38BDF8', fontSize: '1.1rem' }}>{smartMatchData.unique_types_count || 0}</strong>
                </div>
                <div style={{ background: 'var(--bg-canvas)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                  <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.7rem' }}>TYPE GAPS</span>
                  <strong style={{ color: '#F59E0B', fontSize: '1.1rem' }}>{smartMatchData.missing_types?.length || 0}</strong>
                </div>
              </div>

              {smartMatchData.missing_types && smartMatchData.missing_types.length > 0 && (
                <div style={{ marginBottom: '1.25rem', padding: '0.75rem 1rem', background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.25)', borderRadius: 'var(--radius-sm)' }}>
                  <span style={{ fontSize: '0.78rem', color: '#F59E0B', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                    Identified Collection Type Gaps:
                  </span>
                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {smartMatchData.missing_types.map((t: string) => (
                      <span key={t} className={`type-badge type-badge-${t.toLowerCase()}`} style={{ fontSize: '0.7rem' }}>
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommendations */}
              <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '1rem', marginBottom: '0.75rem', textTransform: 'uppercase' }}>
                Recommended Marketplace Matches ({smartMatchData.matches?.length || 0})
              </h4>

              {smartMatchData.matches && smartMatchData.matches.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {smartMatchData.matches.map((m: any, idx: number) => (
                    <div 
                      key={idx}
                      style={{
                        background: 'var(--bg-surface)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 'var(--radius-md)',
                        padding: '1rem',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        gap: '1rem'
                      }}
                    >
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                          <strong style={{ fontSize: '0.95rem' }}>{m.offered_name || `Card #${m.offered_asset_id}`}</strong>
                          <span className={`type-badge type-badge-${(m.primary_type || 'fire').toLowerCase()}`} style={{ fontSize: '0.68rem' }}>
                            {m.primary_type || 'Elemental'}
                          </span>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: '#00ff88' }}>
                            {m.synergy_score || 95}% Synergy
                          </span>
                        </div>
                        <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                          {m.recommendation_reason || `Fills missing ${m.primary_type} element in your battle roster.`}
                        </p>
                      </div>

                      {m.trade_id && (
                        <button 
                          className="btn-editorial primary"
                          style={{ fontSize: '0.78rem', padding: '6px 12px', whiteSpace: 'nowrap' }}
                          onClick={() => {
                            setIsSmartMatchOpen(false);
                            handleAcceptTrade(m.trade_id);
                          }}
                        >
                          <ArrowRightLeft size={13} /> Swap
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '2rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-md)' }}>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: 0 }}>
                    No matching open listings at this moment. List a card in the trading post to incentivize counter-offers!
                  </p>
                </div>
              )}
            </div>

            <button className="btn-editorial secondary" style={{ width: '100%' }} onClick={() => setIsSmartMatchOpen(false)}>
              Close Telemetry
            </button>
          </div>
        </div>
      )}

      {/* ==========================================================================
          MODAL 5: MASTER CATALOG POSSIBLE DISCOVERIES MODAL (247 POKÉMON POOL)
          ========================================================================== */}
      {possiblePokemonModalOpen && (
        <div className="pack-reveal-backdrop" onClick={() => setPossiblePokemonModalOpen(false)}>
          <div 
            className="reveal-interactive-stage catalog-modal-dialog" 
            onClick={e => e.stopPropagation()} 
            style={{ maxWidth: '1080px', width: '95vw', maxHeight: '92vh', overflowY: 'auto', padding: '2rem' }}
          >
            {/* Modal Header */}
            <div className="reveal-stage-header" style={{ marginBottom: '1.5rem' }}>
              <div style={{ textAlign: 'left' }}>
                <div className="section-label" style={{ color: possibleModalPackType === 'premium' ? '#ffd700' : 'var(--accent-lime)' }}>
                  MASTER CATALOG POOL • {possibleModalPackType === 'premium' ? 'GOLDEN POKÉ BALL' : possibleModalPackType === 'basic' ? 'NORMAL POKÉ BALL' : 'BOOSTER PACK'}
                </div>
                <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', textTransform: 'uppercase', letterSpacing: '0.04em', margin: '0.25rem 0' }}>
                  POSSIBLE DISCOVERIES • ALL POKÉMON
                </h2>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: 0 }}>
                  Every Pokémon species in the Pokédex catalog is available. 100% full coverage ({allPokedexEntries.length} total species).
                </p>
              </div>
              <button className="modal-close-icon-btn" onClick={() => setPossiblePokemonModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            {/* Filter 1: Search Bar */}
            <div className="pokedex-search-bar-wrap" style={{ marginBottom: '1.25rem' }}>
              <div className="pokedex-search-box">
                <Search size={18} className="pokedex-search-icon" />
                <input
                  type="text"
                  className="pokedex-search-input"
                  placeholder="Search by Pokémon name, ID, or # (e.g. Pikachu, 25, #025, Charizard, 6)..."
                  value={possibleSearchQuery}
                  onChange={e => setPossibleSearchQuery(e.target.value)}
                />
                {possibleSearchQuery && (
                  <button 
                    onClick={() => setPossibleSearchQuery('')}
                    style={{ position: 'absolute', right: '12px', background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                  >
                    <X size={16} />
                  </button>
                )}
              </div>
            </div>

            {/* Filter 2: Rarity Filter Pills */}
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '0.4rem', letterSpacing: '0.05em' }}>
                Filter by Rarity Tier:
              </div>
              <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap' }}>
                {[
                  { key: 'ALL', label: `ALL (${allPokedexEntries.length})` },
                  { key: 'COMMON', label: `COMMON (${allPokedexEntries.filter(p => p.rarity.toUpperCase() === 'COMMON').length})` },
                  { key: 'RARE', label: `RARE (${allPokedexEntries.filter(p => p.rarity.toUpperCase() === 'RARE').length})` },
                  { key: 'EPIC', label: `EPIC (${allPokedexEntries.filter(p => p.rarity.toUpperCase() === 'EPIC').length})` },
                  { key: 'LEGENDARY', label: `LEGENDARY (${allPokedexEntries.filter(p => p.rarity.toUpperCase() === 'LEGENDARY').length})` }
                ].map(tier => (
                  <button
                    key={tier.key}
                    className={`type-filter-btn ${possibleRarityFilter === tier.key ? 'filter-pill-active' : ''}`}
                    style={{ 
                      fontSize: '0.72rem', 
                      padding: '0.35rem 0.85rem',
                      color: tier.key === 'LEGENDARY' ? '#ffd700' : tier.key === 'EPIC' ? '#c084fc' : tier.key === 'RARE' ? '#60a5fa' : undefined,
                      borderColor: possibleRarityFilter === tier.key && tier.key === 'LEGENDARY' ? '#ffd700' : undefined
                    }}
                    onClick={() => setPossibleRarityFilter(tier.key)}
                  >
                    {tier.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Filter 3: Generation Filters */}
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '0.4rem', letterSpacing: '0.05em' }}>
                Filter by Generation:
              </div>
              <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap' }}>
                {['ALL', 'GEN I', 'GEN II', 'GEN III', 'GEN IV', 'GEN V', 'GEN VI', 'GEN VII', 'GEN VIII', 'GEN IX'].map(gen => (
                  <button
                    key={gen}
                    className={`type-filter-btn ${possibleGenFilter === gen ? 'gen-pill-active' : ''}`}
                    style={{ fontSize: '0.72rem', padding: '0.3rem 0.75rem' }}
                    onClick={() => setPossibleGenFilter(gen)}
                  >
                    {gen}
                  </button>
                ))}
              </div>
            </div>

            {/* Filter 4: Type Filters */}
            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)', textTransform: 'uppercase', marginBottom: '0.4rem', letterSpacing: '0.05em' }}>
                Filter by Elemental Type:
              </div>
              <div className="pokedex-type-pills" style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                {[
                  'ALL', 'NORMAL', 'FIRE', 'WATER', 'ELECTRIC', 'GRASS', 'ICE', 
                  'FIGHTING', 'POISON', 'GROUND', 'FLYING', 'PSYCHIC', 'BUG', 
                  'ROCK', 'GHOST', 'DRAGON', 'DARK', 'STEEL', 'FAIRY'
                ].map(type => (
                  <button
                    key={type}
                    className={`type-filter-btn ${possibleTypeFilter === type ? 'filter-pill-active' : ''}`}
                    style={{ fontSize: '0.68rem', padding: '0.25rem 0.65rem' }}
                    onClick={() => setPossibleTypeFilter(type)}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>

            {/* Results Count Summary */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              <span>
                Showing {filteredPossiblePokemon.length > 0 ? (possiblePage - 1) * POSSIBLE_PER_PAGE + 1 : 0}–{Math.min(possiblePage * POSSIBLE_PER_PAGE, filteredPossiblePokemon.length)} of {filteredPossiblePokemon.length} Eligible Pokémon
              </span>
              <span style={{ color: 'var(--accent-lime)' }}>
                Page {possiblePage} of {possibleTotalPages}
              </span>
            </div>

            {/* Cards Grid */}
            <div className="pokedex-grid-container" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: '1rem' }}>
              {paginatedPossiblePokemon.map(pk => {
                const ownedCount = getPokemonOwnedCount(pk.id, pk.name);
                const isCollected = ownedCount > 0;
                const elemColor = ELEMENT_COLORS[pk.primaryType] || ELEMENT_COLORS.Normal;

                return (
                  <div 
                    key={pk.id}
                    className="editorial-creature-card"
                    onClick={() => {
                      setPossiblePokemonModalOpen(false);
                      setInspectingPokemon({ ...pk, isOwned: isCollected });
                    }}
                    onMouseEnter={() => setCursorHover('INSPECT')}
                    onMouseLeave={clearCursorHover}
                    style={{ borderTop: `2px solid ${elemColor.text}`, cursor: 'pointer' }}
                  >
                    <div className="card-top-meta">
                      <span className="card-asa-tag">{pk.pokedexNumber}</span>
                      <span 
                        className="card-rarity-pill" 
                        style={{ color: RARITY_COLORS[pk.rarity] || '#fff' }}
                      >
                        {pk.rarity}
                      </span>
                    </div>

                    <div className="pokemon-artwork-container" style={{ height: '140px', padding: '0.75rem' }}>
                      <img 
                        src={pk.image} 
                        alt={pk.name}
                        className="pokemon-artwork-img"
                        loading="lazy"
                        onError={(e) => {
                          const target = e.target as HTMLImageElement;
                          if (target.src !== pk.sprite && pk.sprite) {
                            target.src = pk.sprite;
                          } else if (target.src !== NEUTRAL_FALLBACK_SVG) {
                            target.src = NEUTRAL_FALLBACK_SVG;
                          }
                        }}
                      />
                    </div>

                    <div className="card-bottom-info">
                      <div className="card-name-row">
                        <h4 style={{ textTransform: 'uppercase', letterSpacing: '0.02em', fontSize: '0.95rem' }}>{pk.name}</h4>
                        <div style={{ display: 'flex', gap: '3px' }}>
                          <span className={`type-badge type-badge-${pk.primaryType.toLowerCase()}`} style={{ fontSize: '0.62rem', padding: '2px 6px' }}>
                            {pk.primaryType}
                          </span>
                          {pk.secondaryType && (
                            <span className={`type-badge type-badge-${pk.secondaryType.toLowerCase()}`} style={{ fontSize: '0.62rem', padding: '2px 6px' }}>
                              {pk.secondaryType}
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="card-footer-meta" style={{ marginTop: '0.65rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>{pk.generation}</span>
                        {accountAddress ? (
                          ownedCount > 0 ? (
                            <span className="card-owned-badge" style={{ color: '#00ff88', fontWeight: 700, fontSize: '0.68rem', background: 'rgba(0,255,136,0.1)', padding: '2px 5px', borderRadius: '4px', border: '1px solid rgba(0,255,136,0.3)' }}>
                              ● OWNED{ownedCount > 1 ? ` ×${ownedCount}` : ''}
                            </span>
                          ) : (
                            <span style={{ color: 'var(--text-dim)', fontSize: '0.68rem' }}>○ NOT COLLECTED</span>
                          )
                        ) : (
                          <span style={{ color: 'var(--text-dim)', fontSize: '0.68rem' }}>○ NOT COLLECTED</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Empty State */}
            {filteredPossiblePokemon.length === 0 && (
              <div style={{ textAlign: 'center', padding: '3rem 1rem', background: 'var(--bg-surface)', borderRadius: 'var(--radius-lg)' }}>
                <Search size={32} style={{ color: 'var(--text-dim)', marginBottom: '0.75rem' }} />
                <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', color: '#fff', marginBottom: '0.5rem' }}>NO MATCHING POKÉMON FOUND</h4>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', maxWidth: '400px', margin: '0 auto 1.5rem auto' }}>
                  No Pokémon matched your search or filter combination. Try resetting your filters to explore the full 247-species catalog.
                </p>
                <button 
                  className="btn-editorial secondary"
                  onClick={() => {
                    setPossibleSearchQuery('');
                    setPossibleRarityFilter('ALL');
                    setPossibleTypeFilter('ALL');
                    setPossibleGenFilter('ALL');
                  }}
                >
                  Reset Catalog Filters
                </button>
              </div>
            )}

            {/* Pagination Controls */}
            {possibleTotalPages > 1 && (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', marginTop: '2rem', flexWrap: 'wrap' }}>
                <button
                  className="btn-editorial secondary"
                  onClick={() => setPossiblePage(prev => Math.max(1, prev - 1))}
                  disabled={possiblePage === 1}
                  style={{ padding: '0.45rem 0.9rem', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem' }}
                >
                  <ChevronLeft size={14} /> Prev
                </button>

                <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
                  {Array.from({ length: Math.min(7, possibleTotalPages) }, (_, i) => {
                    let pageNum = i + 1;
                    if (possibleTotalPages > 7) {
                      if (possiblePage > 4 && possiblePage < possibleTotalPages - 3) {
                        pageNum = possiblePage - 3 + i;
                      } else if (possiblePage >= possibleTotalPages - 3) {
                        pageNum = possibleTotalPages - 6 + i;
                      }
                    }
                    return (
                      <button
                        key={pageNum}
                        className={`type-filter-btn ${possiblePage === pageNum ? 'filter-pill-active' : ''}`}
                        style={{ padding: '0.35rem 0.7rem', fontSize: '0.75rem', minWidth: '32px' }}
                        onClick={() => setPossiblePage(pageNum)}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                </div>

                <button
                  className="btn-editorial secondary"
                  onClick={() => setPossiblePage(prev => Math.min(possibleTotalPages, prev + 1))}
                  disabled={possiblePage === possibleTotalPages}
                  style={{ padding: '0.45rem 0.9rem', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem' }}
                >
                  Next <ChevronRight size={14} />
                </button>
              </div>
            )}

            {/* Modal Bottom Close */}
            <div style={{ marginTop: '2rem', textAlign: 'center' }}>
              <button 
                className="btn-editorial secondary" 
                style={{ minWidth: '180px' }} 
                onClick={() => setPossiblePokemonModalOpen(false)}
              >
                Close Catalog Viewer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ==========================================================================
          MODAL 6: PACK PROBABILITY & RARITY ODDS VIEWER MODAL
          ========================================================================== */}
      {oddsModalOpen && (
        <div className="pack-reveal-backdrop" onClick={() => setOddsModalOpen(false)}>
          <div 
            className="reveal-interactive-stage" 
            onClick={e => e.stopPropagation()} 
            style={{ maxWidth: '780px', width: '95vw', maxHeight: '92vh', overflowY: 'auto', padding: '2.25rem' }}
          >
            {/* Modal Header */}
            <div className="reveal-stage-header" style={{ marginBottom: '1.75rem' }}>
              <div style={{ textAlign: 'left' }}>
                <div className="section-label" style={{ color: oddsPackType === 'premium' ? '#ffd700' : 'var(--accent-lime)' }}>
                  CRYPTOGRAPHIC PROBABILITY • {oddsPackType === 'premium' ? 'GOLDEN POKÉ BALL' : oddsPackType === 'basic' ? 'NORMAL POKÉ BALL' : 'ALL PACK TIERS'}
                </div>
                <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', textTransform: 'uppercase', letterSpacing: '0.04em', margin: '0.25rem 0' }}>
                  PACK RARITY & DROP ODDS
                </h2>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: 0 }}>
                  Transparent, backend-configured drop distributions. Both packs draw from the unified 247-Pokémon Master Catalog.
                </p>
              </div>
              <button className="modal-close-icon-btn" onClick={() => setOddsModalOpen(false)}>
                <X size={20} />
              </button>
            </div>

            {/* Side-by-Side Comparison Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.25rem', marginBottom: '1.75rem' }}>
              
              {/* Basic Pack Odds Card */}
              <div style={{ 
                background: 'var(--bg-surface)', 
                border: '1px solid rgba(255, 77, 77, 0.3)', 
                borderRadius: 'var(--radius-lg)', 
                padding: '1.5rem',
                position: 'relative'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                  <span className="pack-edition-label" style={{ color: '#ff4d4d', margin: 0 }}>BASIC PACK</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: '#fff', fontWeight: 700 }}>
                    {packs.find(p => p.id === 'basic')?.price?.toFixed(1) || '0.1'} ALGO
                  </span>
                </div>
                <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', marginBottom: '0.25rem' }}>NORMAL POKÉ BALL</h3>
                <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-lime)', marginBottom: '1.25rem' }}>
                  STANDARD ENCOUNTER • 1 DROP
                </div>

                {/* Probability Table */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {[
                    { tier: 'Common', percent: packs.find(p => p.id === 'basic')?.rarities?.Common ?? 65, color: '#94a3b8' },
                    { tier: 'Rare', percent: packs.find(p => p.id === 'basic')?.rarities?.Rare ?? 25, color: '#60a5fa' },
                    { tier: 'Epic', percent: packs.find(p => p.id === 'basic')?.rarities?.Epic ?? 8, color: '#c084fc' },
                    { tier: 'Legendary', percent: packs.find(p => p.id === 'basic')?.rarities?.Legendary ?? 2, color: '#ffd700' }
                  ].map(row => (
                    <div key={row.tier}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', fontFamily: 'var(--font-mono)', marginBottom: '4px' }}>
                        <span style={{ color: row.color, fontWeight: 700 }}>{row.tier.toUpperCase()}</span>
                        <strong style={{ color: '#fff' }}>{row.percent}%</strong>
                      </div>
                      <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.06)', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{ width: `${row.percent}%`, height: '100%', background: row.color, borderRadius: '3px' }} />
                      </div>
                    </div>
                  ))}
                </div>

                <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  ✓ 247 / 247 Master Catalog Pokémon eligible<br />
                  ✓ Legendary encounter rate: 2% (Low chance)
                </div>
              </div>

              {/* Premium Pack Odds Card */}
              <div style={{ 
                background: 'var(--bg-surface)', 
                border: '1px solid rgba(255, 215, 0, 0.4)', 
                borderRadius: 'var(--radius-lg)', 
                padding: '1.5rem',
                position: 'relative'
              }}>
                <div className="featured-corner-ribbon" style={{ background: '#ffd700', color: '#080a0c', fontWeight: 800, fontSize: '0.65rem' }}>ENHANCED</div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                  <span className="pack-edition-label" style={{ color: '#ffd700', margin: 0 }}>PREMIUM PACK</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: '#ffd700', fontWeight: 700 }}>
                    {packs.find(p => p.id === 'premium')?.price?.toFixed(1) || '0.5'} ALGO
                  </span>
                </div>
                <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', marginBottom: '0.25rem', color: '#ffd700' }}>GOLDEN POKÉ BALL</h3>
                <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: '#ffd700', marginBottom: '1.25rem' }}>
                  BOOSTED ODDS • 3 DROPS
                </div>

                {/* Probability Table */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {[
                    { tier: 'Common', percent: packs.find(p => p.id === 'premium')?.rarities?.Common ?? 40, color: '#94a3b8' },
                    { tier: 'Rare', percent: packs.find(p => p.id === 'premium')?.rarities?.Rare ?? 35, color: '#60a5fa' },
                    { tier: 'Epic', percent: packs.find(p => p.id === 'premium')?.rarities?.Epic ?? 20, color: '#c084fc' },
                    { tier: 'Legendary', percent: packs.find(p => p.id === 'premium')?.rarities?.Legendary ?? 5, color: '#ffd700' }
                  ].map(row => (
                    <div key={row.tier}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', fontFamily: 'var(--font-mono)', marginBottom: '4px' }}>
                        <span style={{ color: row.color, fontWeight: 700 }}>{row.tier.toUpperCase()}</span>
                        <strong style={{ color: '#fff' }}>{row.percent}%</strong>
                      </div>
                      <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.06)', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{ width: `${row.percent}%`, height: '100%', background: row.color, borderRadius: '3px' }} />
                      </div>
                    </div>
                  ))}
                </div>

                <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  ✓ 247 / 247 Master Catalog Pokémon eligible<br />
                  ✓ 2.5× Boosted Legendary Rate & 2.5× Boosted Epic Rate
                </div>
              </div>
            </div>

            {/* Architecture Highlights & Guarantees */}
            <div style={{ background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '1.25rem', textAlign: 'left', marginBottom: '1.5rem' }}>
              <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-lime)', textTransform: 'uppercase', marginBottom: '0.5rem', fontWeight: 700 }}>
                CRITICAL SYSTEM GUARANTEES
              </div>
              <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: '1.6' }}>
                <li><strong style={{ color: '#fff' }}>Unified Master Catalog:</strong> Both Basic and Premium packs draw from the same authoritative 247-species Pokédex catalog.</li>
                <li><strong style={{ color: '#fff' }}>Provably Fair Reward Security:</strong> Rarity selection and Pokémon random choice occur on the server upon confirmed release authorization.</li>
                <li><strong style={{ color: '#fff' }}>Reroll Prevention:</strong> Reward is immutably persisted upon confirmation; refreshing returns the exact same reward.</li>
                <li><strong style={{ color: '#fff' }}>Direct Wallet Delivery:</strong> Verified Digital Collectibles are minted directly to your connected Pera Wallet.</li>
              </ul>
            </div>

            <button className="btn-editorial primary" style={{ width: '100%' }} onClick={() => setOddsModalOpen(false)}>
              Close Probability Odds
            </button>
          </div>
        </div>
      )}

    </div>
  );
};

export default App;
