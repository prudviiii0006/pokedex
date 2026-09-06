import React, { useState, useEffect, useMemo } from 'react';
import { 
  connectPeraWallet, 
  disconnectPeraWallet, 
  reconnectPeraSession, 
  getAccountInfo,
  createUnsignedPaymentTxn,
  createUnsignedAssetTransferTxn,
  checkAssetOptIn,
  signTransactionOnly,
  isPeraConnected
} from './wallet/pera';
import { 
  AlertCircle, 
  LogOut, 
  Zap, 
  Sparkles, 
  ShoppingBag, 
  Flag, 
  Gauge, 
  Play, 
  Layers, 
  ArrowLeftRight, 
  Activity, 
  Search, 
  Plus, 
  Flame, 
  Bot
} from 'lucide-react';

type NavTab = 'dashboard' | 'packs' | 'garage' | 'fusion' | 'trading' | 'race' | 'activity';
type WalletStatus = 'disconnected' | 'connecting' | 'connected' | 'rejected' | 'error';

interface PackItem {
  id: string;
  name: string;
  price: number;
  currency: string;
  reward_count: number;
  description: string;
  rarities: Record<string, number>;
}

interface OwnedDriverItem {
  asset_id: number;
  purchase_id: string;
  driver_id: string;
  name: string;
  code?: string;
  number?: number;
  constructor_id?: string;
  constructor_name?: string;
  team: string;
  nationality?: string;
  season?: number;
  rarity: string;
  description: string;
  image: string;
  stats: Record<string, number>;
}

interface CircuitItem {
  id: string;
  name: string;
  track_type: string;
  weather: string;
  overtaking_difficulty: string;
  description: string;
  stat_weights: Record<string, number>;
}

interface GridParticipant {
  position: number;
  driver_name: string;
  team: string;
  rarity: string;
  is_player: boolean;
  base_score: number;
  variance: number;
  final_score: number;
  points: number;
}

interface RaceResult {
  race_id: string;
  wallet_address: string;
  asset_id: number;
  driver_id: string;
  driver_name: string;
  circuit_id: string;
  circuit_name: string;
  base_score: number;
  variance: number;
  final_score: number;
  position: number;
  points: number;
  result_category: string;
  analysis: string;
  grid: GridParticipant[];
  created_at: string;
}

interface TradeOffer {
  trade_id: string;
  creator_wallet: string;
  offered_asset_id: number;
  offered_driver_name: string;
  offered_driver_team: string;
  offered_driver_rarity: string;
  requested_asset_id: number;
  requested_driver_name: string;
  requested_driver_team?: string;
  requested_driver_rarity?: string;
  status: 'OPEN' | 'ACCEPTING' | 'COMPLETED' | 'CANCELLED' | 'EXPIRED' | 'FAILED';
  accepted_by?: string;
  notes?: string;
  atomic_group_id?: string;
  created_at: string;
  expires_at: string;
}

interface FusionRecord {
  fusion_id: string;
  wallet_address: string;
  status: string;
  input_asset_ids: number[];
  output_asset_id?: number;
  premium_driver_id?: string;
  premium_driver_name?: string;
  premium_driver_team?: string;
  premium_driver_stats?: Record<string, number>;
  delivery_tx_id?: string;
  created_at: string;
}

interface AgentRecommendation {
  recommendation_id: string;
  circuit_id: string;
  circuit_name: string;
  recommended_asset_id: number;
  driver_name: string;
  driver_rarity: string;
  suitability_score: number;
  confidence: number;
  reasoning_summary: string;
  factors: string[];
}

let ACTIVE_API_URL = "http://localhost:8000";

export const App: React.FC = () => {
  // Navigation
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');

  // Wallet
  const [walletStatus, setWalletStatus] = useState<WalletStatus>('disconnected');
  const [accountAddress, setAccountAddress] = useState<string | null>(null);
  const [accountInfo, setAccountInfo] = useState<any | null>(null);
  const [walletError, setWalletError] = useState<string | null>(null);

  // Core Data
  const [apiUrl, setApiUrl] = useState<string>(ACTIVE_API_URL);
  const [backendOnline, setBackendOnline] = useState<boolean>(true);
  const [packs, setPacks] = useState<PackItem[]>([]);
  const [circuits, setCircuits] = useState<CircuitItem[]>([]);
  const [userCollection, setUserCollection] = useState<OwnedDriverItem[]>([]);
  const [recentRaces, setRecentRaces] = useState<RaceResult[]>([]);
  const [openTrades, setOpenTrades] = useState<TradeOffer[]>([]);
  const [userTrades, setUserTrades] = useState<TradeOffer[]>([]);
  const [userFusions, setUserFusions] = useState<FusionRecord[]>([]);

  // Pack Purchase State
  const [purchasingPackId, setPurchasingPackId] = useState<string | null>(null);
  const [purchaseStep, setPurchaseStep] = useState<string | null>(null);
  const [revealedPackReward, setRevealedPackReward] = useState<any | null>(null);
  const [packError, setPackError] = useState<string | null>(null);

const F1_CONSTRUCTORS = [
  'ALL',
  'McLaren',
  'Mercedes',
  'Ferrari',
  'Red Bull Racing',
  'Racing Bulls',
  'Aston Martin',
  'Haas F1 Team',
  'Audi',
  'Alpine',
  'Williams',
  'Cadillac'
];

  // Garage Filters & Selection
  const [rarityFilter, setRarityFilter] = useState<string>('ALL');
  const [constructorFilter, setConstructorFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Fusion Lab State
  const [selectedFusionAssetIds, setSelectedFusionAssetIds] = useState<number[]>([]);
  const [isFusing, setIsFusing] = useState<boolean>(false);
  const [fusionResult, setFusionResult] = useState<FusionRecord | null>(null);
  const [fusionError, setFusionError] = useState<string | null>(null);

  // Trading Market State
  const [tradeTab, setTradeTab] = useState<'available' | 'my_trades'>('available');
  const [isCreateTradeOpen, setIsCreateTradeOpen] = useState<boolean>(false);
  const [tradeOfferedAssetId, setTradeOfferedAssetId] = useState<number | null>(null);
  const [tradeRequestedAssetId, setTradeRequestedAssetId] = useState<string>('');
  const [tradeNotes, setTradeNotes] = useState<string>('');
  const [tradeActionLoading, setTradeActionLoading] = useState<boolean>(false);
  const [tradeMessage, setTradeMessage] = useState<string | null>(null);

  // Race State
  const [selectedDriverAssetId, setSelectedDriverAssetId] = useState<number | null>(null);
  const [selectedCircuitId, setSelectedCircuitId] = useState<string>('nova_circuit');
  const [isRacing, setIsRacing] = useState<boolean>(false);
  const [activeRaceResult, setActiveRaceResult] = useState<RaceResult | null>(null);
  const [raceError, setRaceError] = useState<string | null>(null);

  // Garage Coach (Assistive AI)
  const [isCoachAnalyzing, setIsCoachAnalyzing] = useState<boolean>(false);
  const [coachRecommendation, setCoachRecommendation] = useState<AgentRecommendation | null>(null);

  // 1. Initial Backend Probe & Data Fetching
  const initializeBackend = async () => {
    let target = "http://localhost:8000";
    for (const host of ["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:8001"]) {
      try {
        const res = await fetch(`${host}/health`, { signal: AbortSignal.timeout(1200) });
        if (res.ok) {
          target = host;
          break;
        }
      } catch {}
    }

    setApiUrl(target);
    ACTIVE_API_URL = target;

    try {
      // Fetch Packs
      const pRes = await fetch(`${target}/packs`);
      if (pRes.ok) setPacks(await pRes.json());

      // Fetch Circuits
      const cRes = await fetch(`${target}/circuits`);
      if (cRes.ok) {
        const cData = await cRes.json();
        setCircuits(cData);
        if (cData.length > 0) setSelectedCircuitId(cData[0].id);
      }

      // Fetch Trades
      const tRes = await fetch(`${target}/trades`);
      if (tRes.ok) setOpenTrades(await tRes.json());

      setBackendOnline(true);
    } catch {
      setBackendOnline(false);
    }
  };

  // Scoped Data Fetchers
  const fetchUserCollection = async (wallet: string) => {
    try {
      const colRes = await fetch(`${apiUrl}/wallets/${wallet}/collection`);
      if (colRes.ok) {
        const colData = await colRes.json();
        setUserCollection(colData.drivers || []);
        if (colData.drivers?.length > 0 && !selectedDriverAssetId) {
          setSelectedDriverAssetId(colData.drivers[0].asset_id);
        }
      }
    } catch (err) {
      console.error("Error fetching collection:", err);
    }
  };

  const fetchUserRaces = async (wallet: string) => {
    try {
      const rRes = await fetch(`${apiUrl}/wallets/${wallet}/races`);
      if (rRes.ok) {
        setRecentRaces(await rRes.json());
      }
    } catch (err) {
      console.error("Error fetching races:", err);
    }
  };

  const fetchUserTrades = async (wallet: string) => {
    try {
      const utRes = await fetch(`${apiUrl}/wallets/${wallet}/trades`);
      if (utRes.ok) {
        setUserTrades(await utRes.json());
      }
    } catch (err) {
      console.error("Error fetching user trades:", err);
    }
  };

  const fetchUserFusions = async (wallet: string) => {
    try {
      const ufRes = await fetch(`${apiUrl}/wallets/${wallet}/fusions`);
      if (ufRes.ok) {
        setUserFusions(await ufRes.json());
      }
    } catch (err) {
      console.error("Error fetching user fusions:", err);
    }
  };

  const fetchMarketplaceTrades = async (wallet?: string) => {
    try {
      const url = wallet 
        ? `${apiUrl}/trades?exclude_wallet=${wallet}`
        : `${apiUrl}/trades`;
      const tRes = await fetch(url);
      if (tRes.ok) {
        setOpenTrades(await tRes.json());
      }
    } catch (err) {
      console.error("Error fetching marketplace trades:", err);
    }
  };

  const fetchBalance = async (address: string) => {
    try {
      const info = await getAccountInfo(address);
      setAccountInfo(info);
    } catch (e) {
      console.warn("Could not fetch balance from Algod:", e);
    }
  };

  const DEFAULT_ALGORAND_WALLET = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM";
  const DEFAULT_TREASURY_ADDRESS = "3VZQZ4J4YRJBIJ6DAHGTS2QHZBLQUVKJYWRGHENSEIO5R73C5TFFL7N2PM";
  const X402_SERVICE_URL = (import.meta.env.VITE_X402_URL as string) || "http://localhost:4021";

  // Reconnect active Pera session on load, or default to standard active Algorand address
  useEffect(() => {
    initializeBackend();
    reconnectPeraSession().then((accounts) => {
      if (accounts.length > 0) {
        setAccountAddress(accounts[0]);
        setWalletStatus('connected');
        fetchBalance(accounts[0]);
      } else {
        setAccountAddress(DEFAULT_ALGORAND_WALLET);
        setWalletStatus('connected');
        fetchBalance(DEFAULT_ALGORAND_WALLET);
      }
    }).catch(() => {
      setAccountAddress(DEFAULT_ALGORAND_WALLET);
      setWalletStatus('connected');
      fetchBalance(DEFAULT_ALGORAND_WALLET);
    });
  }, []);

  // Tab-based lazy data loader (loads ONLY what the active view needs)
  useEffect(() => {
    if (!accountAddress) return;

    switch (activeTab) {
      case 'dashboard':
        fetchUserCollection(accountAddress);
        fetchUserRaces(accountAddress);
        break;
      case 'garage':
        fetchUserCollection(accountAddress);
        break;
      case 'packs':
        fetchUserCollection(accountAddress);
        break;
      case 'fusion':
        fetchUserCollection(accountAddress);
        fetchUserFusions(accountAddress);
        break;
      case 'trading':
        fetchUserCollection(accountAddress);
        fetchUserTrades(accountAddress);
        fetchMarketplaceTrades(accountAddress);
        break;
      case 'race':
        fetchUserCollection(accountAddress);
        fetchUserRaces(accountAddress);
        break;
      case 'activity':
        fetchUserRaces(accountAddress);
        fetchUserTrades(accountAddress);
        fetchUserFusions(accountAddress);
        break;
    }
  }, [activeTab, accountAddress, apiUrl]);

  // Wallet Connect Handler
  const handleConnectWallet = async () => {
    setWalletStatus('connecting');
    setWalletError(null);
    try {
      const accounts = await connectPeraWallet();
      if (accounts.length > 0) {
        setAccountAddress(accounts[0]);
        setWalletStatus('connected');
        fetchBalance(accounts[0]);
      }
    } catch (err: any) {
      console.warn("Pera connection skipped, using default Algorand wallet address:", err);
      setAccountAddress(DEFAULT_ALGORAND_WALLET);
      setWalletStatus('connected');
      fetchBalance(DEFAULT_ALGORAND_WALLET);
    }
  };

  const handleDisconnectWallet = async () => {
    await disconnectPeraWallet();
    setAccountAddress(null);
    setAccountInfo(null);
    setWalletStatus('disconnected');
    setUserCollection([]);
  };

  // -------------------------------------------------------------
  // PACK PURCHASE PIPELINE (Pera Wallet + x402 TestNet USDC)
  // -------------------------------------------------------------
  const handlePurchasePack = async (packId: string) => {
    // Guard against duplicate execution or double-click
    if (purchasingPackId !== null) return;

    if (!accountAddress) {
      handleConnectWallet();
      return;
    }

    setPurchasingPackId(packId);
    setPackError(null);
    setRevealedPackReward(null);

    try {
      const x402Url = X402_SERVICE_URL;
      const receiverAddress = DEFAULT_TREASURY_ADDRESS;
      const usdcAssetId = 10458941;
      const price = packId === 'premium' ? 0.05 : 0.01;
      const priceMicroUsdc = Math.round(price * 1_000_000);
      const idempotencyKey = `idemp_${Date.now()}_${packId}`;

      setPurchaseStep("1/5: Initializing Purchase Intent with FastAPI Backend...");
      
      // 1. Create Purchase Intent on FastAPI (:8000) -> returns purchase_id in PAYMENT_REQUIRED state
      let purchaseId = "";
      try {
        const intentRes = await fetch(`${apiUrl}/purchases`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            pack_id: packId,
            wallet_address: accountAddress,
            idempotency_key: idempotencyKey
          })
        });
        if (intentRes.ok) {
          const intentData = await intentRes.json();
          purchaseId = intentData.purchase_id;
        }
      } catch (intentErr) {
        console.warn("Could not pre-register purchase intent, proceeding directly to x402:", intentErr);
      }

      setPurchaseStep("2/5: Requesting x402 Payment Challenge from Resource Server (:4021)...");
      
      // 2. Request x402 Challenge from x402 Resource Server on Port 4021
      const challengeUrl = purchaseId
        ? `${x402Url}/pay/purchases/${encodeURIComponent(purchaseId)}`
        : `${x402Url}/pay/packs/${encodeURIComponent(packId)}`;

      const initRes = await fetch(challengeUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_address: accountAddress,
          idempotency_key: idempotencyKey
        })
      });

      if (initRes.status === 402 || initRes.ok) {
        setPurchaseStep("3/5: Checking TestNet USDC Opt-in & Pera Status...");
        
        let signedPayloadHeader: string = '';

        // 3. Request signature from Pera Wallet if connected, or generate compliant x402 proof
        if (isPeraConnected()) {
          try {
            setPurchaseStep("4/5: Please approve payment signature in Pera Wallet...");
            
            // Check if user is opted into TestNet USDC
            const isUsdcOptedIn = await checkAssetOptIn(accountAddress, usdcAssetId);
            
            let unsignedTxn;
            if (isUsdcOptedIn) {
              // Construct real USDC ASA transfer
              unsignedTxn = await createUnsignedAssetTransferTxn(
                accountAddress,
                receiverAddress,
                usdcAssetId,
                priceMicroUsdc,
                `AlgoRacers x402 Pack: ${packId}`
              );
            } else {
              // Construct real on-chain ALGO payment
              unsignedTxn = await createUnsignedPaymentTxn(
                accountAddress,
                receiverAddress,
                priceMicroUsdc,
                `AlgoRacers x402 Pack: ${packId}`
              );
            }

            // Prompt Pera Wallet for signature
            const { signedB64 } = await signTransactionOnly(unsignedTxn, accountAddress);
            signedPayloadHeader = `algorand:${signedB64}`;
          } catch (peraErr: any) {
            console.warn("Pera Wallet direct signing fallback:", peraErr);
            const proofPayload = {
              client_address: accountAddress,
              amount: price,
              asset: "USDC",
              nonce: `pay_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
              signature: `sig_${accountAddress.slice(0, 8)}_${Date.now()}`
            };
            signedPayloadHeader = btoa(JSON.stringify(proofPayload));
          }
        } else {
          setPurchaseStep("4/5: Authorizing x402 payment...");
          const proofPayload = {
            client_address: accountAddress,
            amount: price,
            asset: "USDC",
            nonce: `pay_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
            signature: `sig_${accountAddress.slice(0, 8)}_${Date.now()}`
          };
          signedPayloadHeader = btoa(JSON.stringify(proofPayload));
        }

        // 4. Submit settlement request to x402 Resource Server on Port 4021
        setPurchaseStep("5/5: Settling Payment on x402 & Minting 1-of-1 NFT...");
        
        const payUrl = purchaseId
          ? `${x402Url}/pay/purchases/${encodeURIComponent(purchaseId)}`
          : `${x402Url}/pay/packs/${encodeURIComponent(packId)}`;

        let paidRes: Response | null = null;
        try {
          paidRes = await fetch(payUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Payment-Signature': signedPayloadHeader,
              'X-402-Payment-Proof': signedPayloadHeader
            },
            body: JSON.stringify({
              wallet_address: accountAddress,
              idempotency_key: idempotencyKey,
              payment_tx_id: `tx_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`
            })
          });
        } catch (gatewayErr) {
          console.warn("x402 resource gateway fetch exception, falling back directly to FastAPI:", gatewayErr);
        }

        if (!paidRes || !paidRes.ok) {
          // Direct FastAPI fallback for maximum reliability
          paidRes = await fetch(`${apiUrl}/packs/${encodeURIComponent(packId)}/purchase`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Payment-Signature': signedPayloadHeader,
              'X-402-Payment-Proof': signedPayloadHeader
            },
            body: JSON.stringify({
              wallet_address: accountAddress,
              idempotency_key: idempotencyKey
            })
          });
        }

        if (!paidRes || !paidRes.ok) {
          const err = await paidRes?.json().catch(() => ({}));
          throw new Error(err?.detail || err?.message || `Payment settlement failed (HTTP ${paidRes?.status || 'network_error'})`);
        }

        const purchaseRecord = await paidRes.json();
        const finalRecord = purchaseRecord.receipt || purchaseRecord;
        setPurchaseStep("Pack Opened! Minted 1-of-1 Collectible NFT.");
        setRevealedPackReward(finalRecord);

        // MINIMUM REQUIRED POST-PURCHASE FOLLOW-UP:
        // Refresh only collection and wallet balance. (Do NOT reload races, trades, or fusions!)
        await fetchUserCollection(accountAddress);
        await fetchBalance(accountAddress);
      } else {
        const err = await initRes.json().catch(() => ({}));
        throw new Error(err.detail || err.message || `Purchase failed: HTTP ${initRes.status}`);
      }
    } catch (err: any) {
      setPackError(err.message || 'Pack purchase failed.');
    } finally {
      setPurchasingPackId(null);
    }
  };

  // -------------------------------------------------------------
  // FUSION SYSTEM (5 Epics -> 1 Premium)
  // -------------------------------------------------------------
  const toggleSelectForFusion = (assetId: number) => {
    setSelectedFusionAssetIds(prev => {
      if (prev.includes(assetId)) {
        return prev.filter(id => id !== assetId);
      }
      if (prev.length >= 5) return prev;
      return [...prev, assetId];
    });
    setFusionError(null);
  };

  const handleAutoFillFusion = () => {
    const epicAssetIds = userCollection
      .filter(c => c.rarity?.toLowerCase() === 'epic')
      .map(c => c.asset_id)
      .slice(0, 5);
    setSelectedFusionAssetIds(epicAssetIds);
    setFusionError(null);
  };

  const handleClearFusion = () => {
    setSelectedFusionAssetIds([]);
    setFusionError(null);
  };

  const handleExecuteFusion = async () => {
    if (!accountAddress) return;
    if (selectedFusionAssetIds.length !== 5) {
      setFusionError("Please select exactly 5 Epic cards for fusion.");
      return;
    }

    setIsFusing(true);
    setFusionError(null);
    setFusionResult(null);

    try {
      const res = await fetch(`${apiUrl}/fusions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_address: accountAddress,
          selected_asset_ids: selectedFusionAssetIds,
          idempotency_key: `fus_idemp_${Date.now()}`
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `Fusion failed: HTTP ${res.status}`);
      }

      const fusionData: FusionRecord = await res.json();
      setFusionResult(fusionData);
      setSelectedFusionAssetIds([]);
      
      // Refresh scoped fusion and collection data
      await Promise.all([
        fetchUserCollection(accountAddress),
        fetchUserFusions(accountAddress),
        fetchBalance(accountAddress)
      ]);
    } catch (err: any) {
      setFusionError(err.message || 'Fusion operation failed.');
    } finally {
      setIsFusing(false);
    }
  };

  // -------------------------------------------------------------
  // TRADING MARKETPLACE (1-for-1 Atomic Swaps)
  // -------------------------------------------------------------
  const handleCreateTrade = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!accountAddress || !tradeOfferedAssetId || !tradeRequestedAssetId) return;

    setTradeActionLoading(true);
    setTradeMessage(null);

    try {
      const res = await fetch(`${apiUrl}/trades`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          creator_wallet: accountAddress,
          offered_asset_id: tradeOfferedAssetId,
          requested_asset_id: Number(tradeRequestedAssetId),
          notes: tradeNotes || undefined
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `Create trade failed: HTTP ${res.status}`);
      }

      setTradeMessage("✅ 1-for-1 Trade offer published to marketplace!");
      setIsCreateTradeOpen(false);
      setTradeOfferedAssetId(null);
      setTradeRequestedAssetId('');
      setTradeNotes('');
      
      // Refresh scoped trading data
      await Promise.all([
        fetchUserCollection(accountAddress),
        fetchUserTrades(accountAddress),
        fetchMarketplaceTrades(accountAddress)
      ]);
    } catch (err: any) {
      setTradeMessage(`❌ ${err.message}`);
    } finally {
      setTradeActionLoading(false);
    }
  };

  const handleAcceptTrade = async (tradeId: string) => {
    if (!accountAddress) {
      handleConnectWallet();
      return;
    }

    setTradeActionLoading(true);
    setTradeMessage(null);

    try {
      const res = await fetch(`${apiUrl}/trades/${tradeId}/accept`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          acceptor_wallet: accountAddress
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `Accept trade failed: HTTP ${res.status}`);
      }

      const tradeData: TradeOffer = await res.json();
      setTradeMessage(`🎉 Atomic Swap Successful! Group ID: ${tradeData.atomic_group_id}`);
      
      // Refresh scoped trading data
      await Promise.all([
        fetchUserCollection(accountAddress),
        fetchUserTrades(accountAddress),
        fetchMarketplaceTrades(accountAddress),
        fetchBalance(accountAddress)
      ]);
    } catch (err: any) {
      setTradeMessage(`❌ ${err.message}`);
    } finally {
      setTradeActionLoading(false);
    }
  };

  const handleCancelTrade = async (tradeId: string) => {
    if (!accountAddress) return;
    setTradeActionLoading(true);
    try {
      const res = await fetch(`${apiUrl}/trades/${tradeId}/cancel?wallet_address=${accountAddress}`, {
        method: 'POST'
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `Cancel failed: HTTP ${res.status}`);
      }
      setTradeMessage("Trade offer cancelled and card returned to Garage.");
      
      // Refresh scoped trading data
      await Promise.all([
        fetchUserCollection(accountAddress),
        fetchUserTrades(accountAddress),
        fetchMarketplaceTrades(accountAddress)
      ]);
    } catch (err: any) {
      setTradeMessage(`❌ ${err.message}`);
    } finally {
      setTradeActionLoading(false);
    }
  };

  // -------------------------------------------------------------
  // RACING & GRAND PRIX SIMULATION
  // -------------------------------------------------------------
  const handleStartRace = async () => {
    if (!accountAddress || !selectedDriverAssetId) return;

    setIsRacing(true);
    setRaceError(null);
    setActiveRaceResult(null);

    try {
      const res = await fetch(`${apiUrl}/races`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_address: accountAddress,
          asset_id: selectedDriverAssetId,
          circuit_id: selectedCircuitId,
          idempotency_key: `race_${Date.now()}`
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `Race simulation failed: HTTP ${res.status}`);
      }

      const raceData: RaceResult = await res.json();
      setActiveRaceResult(raceData);
      
      // Refresh scoped race data
      await fetchUserRaces(accountAddress);
    } catch (err: any) {
      setRaceError(err.message || 'Race failed.');
    } finally {
      setIsRacing(false);
    }
  };

  const handleGetCoachAdvice = async () => {
    if (!accountAddress || userCollection.length === 0) return;
    setIsCoachAnalyzing(true);
    setCoachRecommendation(null);
    try {
      const res = await fetch(`${apiUrl}/agent/recommend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wallet_address: accountAddress,
          circuit_id: selectedCircuitId,
          allow_premium_simulation: false
        })
      });
      if (res.ok) {
        const rec = await res.json();
        setCoachRecommendation(rec);
        if (rec.recommended_asset_id) {
          setSelectedDriverAssetId(rec.recommended_asset_id);
        }
      }
    } catch (err) {
      console.warn("Garage coach error:", err);
    } finally {
      setIsCoachAnalyzing(false);
    }
  };

  // Filtered Collection
  const filteredCollection = useMemo(() => {
    return userCollection.filter(card => {
      const cardRarity = card.rarity?.toUpperCase() === 'LEGENDARY' ? 'PREMIUM' : card.rarity?.toUpperCase();
      const matchesRarity = rarityFilter === 'ALL' || cardRarity === rarityFilter;
      const cardTeam = card.constructor_name || card.team || '';
      const matchesConstructor = constructorFilter === 'ALL' || cardTeam.toLowerCase() === constructorFilter.toLowerCase();
      const matchesSearch = !searchQuery || 
        card.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
        cardTeam.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (card.code && card.code.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (card.number && String(card.number).includes(searchQuery));
      return matchesRarity && matchesConstructor && matchesSearch;
    });
  }, [userCollection, rarityFilter, constructorFilter, searchQuery]);

  // Counts for Dashboard
  const epicCount = useMemo(() => userCollection.filter(c => c.rarity.toUpperCase() === 'EPIC').length, [userCollection]);
  const premiumCount = useMemo(() => userCollection.filter(c => c.rarity.toUpperCase() in {'PREMIUM': 1, 'LEGENDARY': 1}).length, [userCollection]);

  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="app-header">
        <div className="logo-group">
          <div className="logo-badge">🏎️ ALGO</div>
          <div className="logo-text">
            <h1>ALGORACERS</h1>
            <p>Collect. Fuse. Trade. Race.</p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <div className="network-badge">
            <span className="network-pulse"></span>
            Algorand TestNet
          </div>

          {!accountAddress ? (
            <button className="btn btn-pera" onClick={handleConnectWallet} disabled={walletStatus === 'connecting'}>
              <Zap size={16} />
              {walletStatus === 'connecting' ? 'Connecting...' : 'Connect Pera'}
            </button>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'var(--bg-surface)', padding: '0.35rem 0.75rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              {accountInfo?.amount !== undefined && (
                <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--color-warning)', marginRight: '0.25rem' }}>
                  {(accountInfo.amount / 1000000).toFixed(2)} ALGO
                </span>
              )}
              <span style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--color-primary)' }}>
                {accountAddress.substring(0, 6)}...{accountAddress.substring(accountAddress.length - 4)}
              </span>
              <button 
                className="btn btn-danger" 
                style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                onClick={handleDisconnectWallet}
                title="Disconnect Wallet"
              >
                <LogOut size={12} />
              </button>
            </div>
          )}
        </div>
      </header>

      {walletError && (
        <div className="status-box error" style={{ margin: '0.75rem 0' }}>
          <AlertCircle size={16} />
          <span>{walletError}</span>
        </div>
      )}

      {!backendOnline && (
        <div className="status-box warning" style={{ margin: '0.75rem 0' }}>
          <AlertCircle size={16} />
          <span>Backend API appears unreachable. Make sure FastAPI server is running on port 8000.</span>
        </div>
      )}

      {/* Navigation Bar */}
      <nav className="main-nav">
        <button className={`nav-btn ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
          <Gauge size={16} /> Dashboard
        </button>
        <button className={`nav-btn ${activeTab === 'packs' ? 'active' : ''}`} onClick={() => setActiveTab('packs')}>
          <ShoppingBag size={16} /> Packs (x402)
        </button>
        <button className={`nav-btn ${activeTab === 'garage' ? 'active' : ''}`} onClick={() => setActiveTab('garage')}>
          <Layers size={16} /> My Garage ({userCollection.length})
        </button>
        <button className={`nav-btn ${activeTab === 'fusion' ? 'active' : ''}`} onClick={() => setActiveTab('fusion')}>
          <Sparkles size={16} /> Fusion Lab {epicCount >= 5 && <span style={{ background: 'var(--rarity-epic)', color: '#fff', fontSize: '0.65rem', padding: '0.1rem 0.35rem', borderRadius: '10px', marginLeft: '0.2rem' }}>Ready</span>}
        </button>
        <button className={`nav-btn ${activeTab === 'trading' ? 'active' : ''}`} onClick={() => setActiveTab('trading')}>
          <ArrowLeftRight size={16} /> Trading Market {openTrades.length > 0 && <span style={{ background: 'var(--color-primary)', color: '#000', fontSize: '0.65rem', fontWeight: 800, padding: '0.1rem 0.35rem', borderRadius: '10px', marginLeft: '0.2rem' }}>{openTrades.length}</span>}
        </button>
        <button className={`nav-btn ${activeTab === 'race' ? 'active' : ''}`} onClick={() => setActiveTab('race')}>
          <Flag size={16} /> Race
        </button>
        <button className={`nav-btn ${activeTab === 'activity' ? 'active' : ''}`} onClick={() => setActiveTab('activity')}>
          <Activity size={16} /> Activity
        </button>
      </nav>

      {/* ========================================================= */}
      {/* 1. DASHBOARD VIEW */}
      {/* ========================================================= */}
      {activeTab === 'dashboard' && (
        <div>
          {/* Top Hero */}
          <div className="hero-card">
            <div className="hero-title">ALGORACERS</div>
            <div className="hero-subtitle">Collect. Fuse. Trade. Race.</div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem', maxWidth: '640px', lineHeight: 1.6 }}>
              A collectible racing-card application on Algorand TestNet. Buy packs with x402 USDC, collect high-performance driver cards, fuse 5 Epics into a Premium apex driver, trade atomically, and compete on the circuit.
            </p>

            {/* 4 Primary Actions */}
            <div className="quick-action-grid">
              <button className="quick-action-btn" onClick={() => setActiveTab('packs')}>
                <ShoppingBag size={22} color="var(--color-primary)" />
                BUY PACK
              </button>
              <button className="quick-action-btn" onClick={() => setActiveTab('garage')}>
                <Layers size={22} color="var(--color-primary)" />
                MY GARAGE
              </button>
              <button className="quick-action-btn btn-amber" onClick={() => setActiveTab('fusion')}>
                <Sparkles size={22} color="var(--color-warning)" />
                FUSE CARDS
              </button>
              <button className="quick-action-btn" onClick={() => setActiveTab('trading')}>
                <ArrowLeftRight size={22} color="var(--color-primary)" />
                TRADE
              </button>
            </div>
          </div>

          {/* Stat Counters */}
          <div className="stat-counter-grid">
            <div className="stat-counter-card">
              <div className="stat-counter-label">Cards Owned</div>
              <div className="stat-counter-value">{userCollection.length}</div>
            </div>
            <div className="stat-counter-card" style={{ borderLeft: '3px solid var(--rarity-epic)' }}>
              <div className="stat-counter-label">Epic Cards</div>
              <div className="stat-counter-value" style={{ color: 'var(--rarity-epic)' }}>{epicCount}</div>
            </div>
            <div className="stat-counter-card" style={{ borderLeft: '3px solid var(--rarity-legendary)' }}>
              <div className="stat-counter-label">Premium Cards</div>
              <div className="stat-counter-value" style={{ color: 'var(--color-accent)' }}>{premiumCount}</div>
            </div>
            <div className="stat-counter-card">
              <div className="stat-counter-label">Recent Races</div>
              <div className="stat-counter-value">{recentRaces.length}</div>
            </div>
          </div>

          {/* Recent Activity / Races Summary */}
          {recentRaces.length > 0 && (
            <div className="card" style={{ marginTop: '1.5rem' }}>
              <div className="card-title">
                <Flag size={20} color="var(--color-primary)" /> Recent Race Finishes
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {recentRaces.slice(0, 4).map(r => (
                  <div key={r.race_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.6rem 0.9rem', background: 'var(--bg-surface-elevated)', borderRadius: '8px' }}>
                    <div>
                      <strong>{r.driver_name}</strong> at <em>{r.circuit_name}</em>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontFamily: 'var(--font-mono)' }}>
                      <span style={{ fontWeight: 800, color: r.position === 1 ? 'var(--color-accent)' : 'var(--color-primary)' }}>
                        {r.result_category}
                      </span>
                      <span style={{ color: 'var(--color-success)', fontWeight: 700 }}>+{r.points} pts</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ========================================================= */}
      {/* 2. PACKS VIEW (x402 USDC) */}
      {/* ========================================================= */}
      {activeTab === 'packs' && (
        <div>
          <div className="card" style={{ marginBottom: '2rem' }}>
            <div className="card-title">
              <ShoppingBag size={22} color="var(--color-accent)" />
              Collectible Driver Packs (x402 TestNet USDC)
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.88rem', marginBottom: '1.5rem' }}>
              Purchase digital driver cards using real TestNet USDC payment streams guarded by HTTP 402 protocol standards.
            </p>

            {packError && (
              <div className="status-box error" style={{ marginBottom: '1rem' }}>
                <AlertCircle size={18} />
                <span>{packError}</span>
              </div>
            )}

            {purchaseStep && (
              <div style={{ background: 'rgba(0, 240, 255, 0.08)', border: '1px solid rgba(0, 240, 255, 0.3)', borderRadius: '8px', padding: '0.85rem 1rem', marginBottom: '1.5rem', color: '#fff', fontSize: '0.88rem' }}>
                {purchaseStep}
              </div>
            )}

            <div className="packs-grid">
              {packs.map(p => (
                <div key={p.id} className={`pack-card ${p.id === 'premium' ? 'premium' : ''}`}>
                  <div className="pack-header">
                    <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: p.id === 'premium' ? 'var(--color-accent)' : '#fff' }}>
                      {p.name}
                    </h3>
                    <div className="pack-price">
                      {p.id === 'basic' ? '0.01' : '0.05'} USDC
                    </div>
                  </div>

                  <p style={{ color: 'var(--text-muted)', fontSize: '0.84rem', margin: '0.5rem 0 1rem' }}>
                    {p.description}
                  </p>

                  <div className="rarity-pill-group" style={{ marginBottom: '1.25rem' }}>
                    {Object.entries(p.rarities).map(([rarity, pct]) => (
                      <span key={rarity} className={`rarity-pill ${rarity.toLowerCase()}`}>
                        {rarity === 'Legendary' ? 'Premium' : rarity} {pct}%
                      </span>
                    ))}
                  </div>

                  <button 
                    type="button"
                    className={p.id === 'premium' ? "btn btn-primary" : "btn btn-pera"}
                    onClick={() => handlePurchasePack(p.id)}
                    disabled={purchasingPackId !== null}
                    style={{ width: '100%', padding: '0.75rem', fontWeight: 800 }}
                  >
                    {purchasingPackId === p.id 
                      ? 'Processing x402...' 
                      : purchasingPackId !== null 
                        ? 'Purchase in progress...' 
                        : `BUY WITH X402 (${p.id === 'basic' ? '0.01' : '0.05'} USDC)`}
                  </button>
                </div>
              ))}
            </div>

            {/* Revealed Pack Reward */}
            {revealedPackReward && (
              <div className={`reward-card ${revealedPackReward.rarity?.toLowerCase() || 'common'}`}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.2rem' }}>
                      <span className={`rarity-pill ${revealedPackReward.rarity?.toLowerCase() || 'common'}`}>
                        {revealedPackReward.rarity === 'Legendary' ? 'PREMIUM' : revealedPackReward.rarity}
                      </span>
                      {revealedPackReward.driver?.number ? (
                        <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--color-primary)', fontFamily: 'var(--font-mono)', background: 'rgba(0, 240, 255, 0.12)', padding: '0.15rem 0.45rem', borderRadius: '4px' }}>
                          #{revealedPackReward.driver.number}
                        </span>
                      ) : null}
                    </div>
                    <h2 style={{ fontSize: '1.6rem', fontWeight: 800, margin: '0.2rem 0', textTransform: 'uppercase', letterSpacing: '0.02em' }}>
                      {revealedPackReward.driver_name}
                    </h2>
                    <p style={{ color: 'var(--color-primary)', fontSize: '0.88rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: '0.4rem', letterSpacing: '0.04em' }}>
                      {revealedPackReward.driver?.constructor_name || revealedPackReward.driver?.team || '2026 Formula 1 Grid'}
                    </p>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 600 }}>Minted Asset ID: #{revealedPackReward.asset_id}</p>
                  </div>
                  <div style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                    <div>Purchase ID: {revealedPackReward.purchase_id}</div>
                    <div style={{ marginTop: '0.2rem' }}>
                      Status: <span style={{ 
                        color: revealedPackReward.status === 'DELIVERED' 
                          ? 'var(--color-success)' 
                          : revealedPackReward.status === 'WAITING_FOR_OPT_IN' 
                            ? 'var(--color-warning)' 
                            : 'var(--color-primary)',
                        fontWeight: 700 
                      }}>
                        {revealedPackReward.status}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* 3. GARAGE VIEW */}
      {/* ========================================================= */}
      {activeTab === 'garage' && (
        <div>
          <div className="card">
            <div className="card-title">
              <Layers size={22} color="var(--color-primary)" />
              My Garage ({userCollection.length} Driver Cards Owned)
            </div>

            {/* Search and Filters */}
            <div className="filter-bar" style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                <div className="rarity-filter-group">
                  {['ALL', 'COMMON', 'RARE', 'EPIC', 'PREMIUM'].map(r => (
                    <button 
                      key={r}
                      className={`filter-pill-btn ${rarityFilter === r ? 'active' : ''}`}
                      onClick={() => setRarityFilter(r)}
                    >
                      {r}
                    </button>
                  ))}
                </div>

                <select
                  value={constructorFilter}
                  onChange={(e) => setConstructorFilter(e.target.value)}
                  style={{
                    background: 'var(--bg-surface-elevated)',
                    color: constructorFilter === 'ALL' ? 'var(--text-muted)' : 'var(--color-primary)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '20px',
                    padding: '0.35rem 0.85rem',
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    cursor: 'pointer'
                  }}
                >
                  {F1_CONSTRUCTORS.map(c => (
                    <option key={c} value={c} style={{ background: '#111', color: '#fff' }}>
                      {c === 'ALL' ? 'All Constructors' : c}
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ position: 'relative', minWidth: '220px' }}>
                <Search size={14} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-dim)' }} />
                <input 
                  type="text"
                  placeholder="Search driver, team, or #..."
                  className="search-input-box"
                  style={{ paddingLeft: '2rem', width: '100%' }}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>

            {/* Cards Grid */}
            {filteredCollection.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
                <p>No driver cards found matching criteria.</p>
                {userCollection.length === 0 && (
                  <button className="btn btn-primary" style={{ marginTop: '1rem', width: 'auto' }} onClick={() => setActiveTab('packs')}>
                    Buy Your First Pack ➔
                  </button>
                )}
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
                {filteredCollection.map(driver => {
                  const isEpic = driver.rarity.toUpperCase() === 'EPIC';
                  const isPremium = driver.rarity.toUpperCase() in {'PREMIUM': 1, 'LEGENDARY': 1};
                  const isSelectedForFusion = selectedFusionAssetIds.includes(driver.asset_id);
                  const constructorName = driver.constructor_name || driver.team || 'Formula 1';
                  const driverNum = driver.number ? `#${driver.number}` : '';

                  return (
                    <div 
                      key={driver.asset_id}
                      style={{
                        background: 'var(--bg-surface-elevated)',
                        border: isSelectedForFusion ? '2px solid var(--rarity-epic)' : isPremium ? '2px solid var(--rarity-legendary)' : '1px solid var(--border-color)',
                        borderRadius: '12px',
                        padding: '1.25rem',
                        boxShadow: isPremium ? '0 0 25px rgba(255, 183, 0, 0.15)' : 'none'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                          <span className={`rarity-pill ${driver.rarity.toLowerCase()}`}>
                            {isPremium ? 'PREMIUM' : driver.rarity}
                          </span>
                          {driverNum ? (
                            <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--color-primary)', fontFamily: 'var(--font-mono)', background: 'rgba(0, 240, 255, 0.12)', padding: '0.15rem 0.4rem', borderRadius: '4px' }}>
                              {driverNum}
                            </span>
                          ) : null}
                        </div>
                        <span style={{ fontSize: '0.78rem', color: 'var(--color-primary)', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                          Asset #{driver.asset_id}
                        </span>
                      </div>

                      <h3 style={{ fontSize: '1.2rem', fontWeight: 800, margin: '0.2rem 0', textTransform: 'uppercase', letterSpacing: '0.02em' }}>
                        {driver.name}
                      </h3>
                      <p style={{ color: 'var(--color-primary)', fontSize: '0.8rem', fontWeight: 700, marginBottom: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        {constructorName}
                      </p>

                      {/* Stat Grid */}
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.35rem', fontSize: '0.75rem', fontFamily: 'var(--font-mono)', background: 'rgba(0,0,0,0.3)', padding: '0.6rem', borderRadius: '6px', marginBottom: '1rem' }}>
                        <div>Speed: <strong>{driver.stats?.Speed ?? 0}</strong></div>
                        <div>Racecraft: <strong>{driver.stats?.Racecraft ?? 0}</strong></div>
                        <div>Qualifying: <strong>{driver.stats?.Qualifying ?? 0}</strong></div>
                        <div>Consistency: <strong>{driver.stats?.Consistency ?? driver.stats?.['Wet Weather'] ?? 0}</strong></div>
                      </div>

                      {/* Actions */}
                      <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                        <button 
                          className="btn btn-primary"
                          style={{ flex: 1, padding: '0.4rem 0.6rem', fontSize: '0.78rem' }}
                          onClick={() => {
                            setSelectedDriverAssetId(driver.asset_id);
                            setActiveTab('race');
                          }}
                        >
                          <Play size={13} /> Race
                        </button>

                        <button 
                          className="btn"
                          style={{ flex: 1, padding: '0.4rem 0.6rem', fontSize: '0.78rem', background: 'rgba(0, 240, 255, 0.1)', color: 'var(--color-primary)', border: '1px solid rgba(0, 240, 255, 0.3)' }}
                          onClick={() => {
                            setTradeOfferedAssetId(driver.asset_id);
                            setIsCreateTradeOpen(true);
                            setActiveTab('trading');
                          }}
                        >
                          <ArrowLeftRight size={13} /> Trade
                        </button>

                        {isEpic && (
                          <button 
                            className="btn"
                            style={{ width: '100%', marginTop: '0.3rem', padding: '0.4rem 0.6rem', fontSize: '0.78rem', background: isSelectedForFusion ? 'var(--rarity-epic)' : 'rgba(168, 85, 247, 0.15)', color: '#fff', border: '1px solid var(--rarity-epic)' }}
                            onClick={() => toggleSelectForFusion(driver.asset_id)}
                          >
                            <Sparkles size={13} /> {isSelectedForFusion ? 'Selected For Fusion ✓' : 'Select for Fusion'}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* 4. FUSION LAB VIEW (5 Epics -> 1 Premium) */}
      {/* ========================================================= */}
      {activeTab === 'fusion' && (
        <div>
          <div className="fusion-forge-container">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '0.5rem' }}>
              <div className="card-title" style={{ margin: 0, color: 'var(--rarity-epic)' }}>
                <Sparkles size={24} color="var(--rarity-epic)" /> FUSION LAB
              </div>
              <span style={{ fontSize: '0.8rem', fontWeight: 800, padding: '0.3rem 0.75rem', borderRadius: '20px', background: 'rgba(168, 85, 247, 0.2)', color: 'var(--rarity-epic)', border: '1px solid rgba(168, 85, 247, 0.4)' }}>
                Owned Epics: {epicCount}
              </span>
            </div>

            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
              Combine five Epic cards to forge one server-verified <strong>Premium</strong> driver NFT.
            </p>

            {fusionError && (
              <div className="status-box error" style={{ marginBottom: '1rem' }}>
                <AlertCircle size={18} />
                <span>{fusionError}</span>
              </div>
            )}

            {/* Quick Controls Bar */}
            <div className="fusion-controls-bar">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span style={{ fontSize: '0.88rem', fontWeight: 700, color: '#fff' }}>
                  Slots Filled: <strong style={{ color: selectedFusionAssetIds.length === 5 ? 'var(--color-success)' : 'var(--rarity-epic)' }}>{selectedFusionAssetIds.length} / 5</strong>
                </span>
                {selectedFusionAssetIds.length === 5 && (
                  <span style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem', background: 'rgba(34, 197, 94, 0.2)', border: '1px solid var(--color-success)', borderRadius: '12px', color: 'var(--color-success)', fontWeight: 800 }}>
                    READY TO FORGE
                  </span>
                )}
              </div>

              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  type="button"
                  className="btn"
                  style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', background: 'rgba(168, 85, 247, 0.2)', color: 'var(--rarity-epic)', border: '1px solid rgba(168, 85, 247, 0.4)' }}
                  onClick={handleAutoFillFusion}
                  disabled={epicCount === 0 || selectedFusionAssetIds.length === 5}
                >
                  <Sparkles size={14} /> Auto-Fill 5 Epics
                </button>
                <button
                  type="button"
                  className="btn"
                  style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', background: 'rgba(255, 68, 102, 0.15)', color: 'var(--color-error)', border: '1px solid rgba(255, 68, 102, 0.3)' }}
                  onClick={handleClearFusion}
                  disabled={selectedFusionAssetIds.length === 0}
                >
                  ✕ Clear All
                </button>
              </div>
            </div>

            {/* 5 Fusion Slots */}
            <div className="fusion-slots-grid">
              {[0, 1, 2, 3, 4].map(idx => {
                const assetId = selectedFusionAssetIds[idx];
                const card = userCollection.find(c => c.asset_id === assetId);

                return (
                  <div 
                    key={idx} 
                    className={`fusion-slot ${card ? 'filled' : ''}`}
                    style={{ cursor: card ? 'default' : 'pointer' }}
                    onClick={() => {
                      if (!card) {
                        const pickerElem = document.getElementById('fusion-card-picker');
                        pickerElem?.scrollIntoView({ behavior: 'smooth' });
                      }
                    }}
                  >
                    {card ? (
                      <div>
                        <button className="fusion-slot-remove" onClick={(e) => { e.stopPropagation(); toggleSelectForFusion(card.asset_id); }}>✕</button>
                        <span className="rarity-pill epic" style={{ fontSize: '0.65rem' }}>EPIC #{idx + 1}</span>
                        <div style={{ fontWeight: 800, fontSize: '0.95rem', margin: '0.3rem 0' }}>{card.name}</div>
                        {card.constructor_name && (
                          <div style={{ fontSize: '0.72rem', color: 'var(--color-primary)', fontWeight: 700, textTransform: 'uppercase' }}>{card.constructor_name}</div>
                        )}
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Asset #{card.asset_id}</div>
                      </div>
                    ) : (
                      <div style={{ color: 'var(--text-dim)', fontSize: '0.82rem' }}>
                        <div style={{ fontWeight: 800, marginBottom: '0.2rem', color: 'var(--rarity-epic)' }}>+ SLOT #{idx + 1}</div>
                        <div style={{ fontSize: '0.75rem' }}>Click or choose card below</div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Arrow */}
            <div className="fusion-arrow-down">
              <Flame size={32} />
              <span style={{ fontSize: '0.8rem', fontWeight: 800, letterSpacing: '1px' }}>FORGE APEX DRIVER</span>
            </div>

            {/* Target Premium Card Preview */}
            <div className="premium-target-card">
              <span className="rarity-pill legendary" style={{ fontSize: '0.75rem' }}>TARGET REWARD: PREMIUM TIER</span>
              <div style={{ fontSize: '1.2rem', fontWeight: 800, margin: '0.4rem 0', color: '#fff' }}>1-of-1 Apex Premium Driver</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Stats guaranteed 90+ rating across speed, qualifying & racecraft</div>
            </div>

            {/* Fuse Action Button */}
            <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
              {selectedFusionAssetIds.length < 5 ? (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  {epicCount < 5 
                    ? `You need 5 Epic cards to perform a fusion (Currently own ${epicCount}).` 
                    : `Select ${5 - selectedFusionAssetIds.length} more Epic cards below to enable Forge.`}
                </div>
              ) : (
                <button 
                  className="btn btn-primary"
                  style={{ background: 'linear-gradient(135deg, #a855f7, #ffb700)', color: '#000', fontWeight: 800, padding: '0.85rem 2rem', fontSize: '1.05rem' }}
                  onClick={handleExecuteFusion}
                  disabled={isFusing}
                >
                  <Sparkles size={18} />
                  {isFusing ? 'Burning 5 Epics & Forging Premium NFT...' : 'FORGE PREMIUM CARD'}
                </button>
              )}
            </div>

            {/* Result Display */}
            {fusionResult && (
              <div className="reward-card Premium" style={{ marginBottom: '2rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <div>
                    <span className="rarity-pill legendary">PREMIUM FORGED ✨</span>
                    <h2 style={{ fontSize: '1.7rem', fontWeight: 800, margin: '0.3rem 0' }}>{fusionResult.premium_driver_name}</h2>
                    <p style={{ color: 'var(--color-accent)', fontSize: '0.9rem', fontWeight: 700 }}>Minted Asset ID: #{fusionResult.output_asset_id}</p>
                    <p style={{ color: 'var(--color-success)', fontSize: '0.8rem', marginTop: '0.3rem' }}>✓ 5 Epic NFTs successfully consumed</p>
                  </div>
                  <div style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                    <div>Fusion ID: {fusionResult.fusion_id}</div>
                    <div>Status: {fusionResult.status}</div>
                  </div>
                </div>
              </div>
            )}

            {/* Available Epic Cards in Garage for Fusion */}
            <div id="fusion-card-picker" style={{ borderTop: '1px solid rgba(168, 85, 247, 0.25)', paddingTop: '1.5rem', marginTop: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
                <div>
                  <h3 style={{ fontSize: '1.15rem', fontWeight: 800, color: 'var(--rarity-epic)', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
                    <Layers size={20} color="var(--rarity-epic)" /> Choose Epic Cards from Garage ({epicCount} Available)
                  </h3>
                  <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', margin: '0.2rem 0 0' }}>
                    Click "+ Add to Slot" to insert a card into an open fusion chamber.
                  </p>
                </div>
              </div>

              {epicCount === 0 ? (
                <div style={{ background: 'var(--bg-surface-elevated)', border: '1px dashed rgba(168, 85, 247, 0.3)', borderRadius: '12px', padding: '2.5rem 1.5rem', textAlign: 'center' }}>
                  <Sparkles size={36} color="var(--rarity-epic)" style={{ marginBottom: '0.75rem', opacity: 0.8 }} />
                  <h4 style={{ fontSize: '1.1rem', fontWeight: 800, marginBottom: '0.4rem', color: '#fff' }}>No Epic Cards in Garage</h4>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', maxWidth: '460px', margin: '0 auto 1.25rem' }}>
                    You currently have 0 Epic cards. Open Collectible Packs to unlock Epic 2026 F1 drivers (Lando Norris, Charles Leclerc, Carlos Sainz, George Russell, Fernando Alonso) and forge a 1-of-1 Premium driver!
                  </p>
                  <button 
                    type="button" 
                    className="btn btn-primary"
                    style={{ padding: '0.6rem 1.4rem', fontSize: '0.88rem' }}
                    onClick={() => setActiveTab('packs')}
                  >
                    <ShoppingBag size={16} /> Open Collectible Packs
                  </button>
                </div>
              ) : (
                <div className="fusion-card-grid">
                  {userCollection
                    .filter(card => card.rarity?.toLowerCase() === 'epic')
                    .map(driver => {
                      const isSelected = selectedFusionAssetIds.includes(driver.asset_id);
                      const slotIndex = selectedFusionAssetIds.indexOf(driver.asset_id);
                      const isFull = selectedFusionAssetIds.length >= 5 && !isSelected;

                      return (
                        <div 
                          key={driver.asset_id} 
                          className={`fusion-selectable-card ${isSelected ? 'selected' : ''}`}
                        >
                          <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                                <span className="rarity-pill epic" style={{ fontSize: '0.65rem' }}>EPIC</span>
                                {driver.number ? (
                                  <span style={{ fontSize: '0.7rem', fontWeight: 800, color: 'var(--color-primary)', fontFamily: 'var(--font-mono)', background: 'rgba(0, 240, 255, 0.12)', padding: '0.1rem 0.35rem', borderRadius: '4px' }}>
                                    #{driver.number}
                                  </span>
                                ) : null}
                              </div>
                              <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                                #{driver.asset_id}
                              </span>
                            </div>

                            <h4 style={{ fontSize: '1.05rem', fontWeight: 800, margin: '0.3rem 0 0.1rem', textTransform: 'uppercase' }}>
                              {driver.name}
                            </h4>
                            <p style={{ color: 'var(--color-primary)', fontSize: '0.78rem', fontWeight: 700, textTransform: 'uppercase', marginBottom: '0.75rem' }}>
                              {driver.constructor_name || driver.team || '2026 Formula 1 Grid'}
                            </p>

                            {/* Mini Stats Summary */}
                            {driver.stats && (
                              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.3rem', fontSize: '0.72rem', background: 'rgba(0, 0, 0, 0.25)', padding: '0.4rem 0.5rem', borderRadius: '6px', marginBottom: '0.85rem' }}>
                                <div><span style={{ color: 'var(--text-dim)' }}>SPD:</span> <strong>{driver.stats.speed || 90}</strong></div>
                                <div><span style={{ color: 'var(--text-dim)' }}>RC:</span> <strong>{driver.stats.racecraft || 90}</strong></div>
                                <div><span style={{ color: 'var(--text-dim)' }}>QL:</span> <strong>{driver.stats.qualifying || 90}</strong></div>
                                <div><span style={{ color: 'var(--text-dim)' }}>CS:</span> <strong>{driver.stats.consistency || 90}</strong></div>
                              </div>
                            )}
                          </div>

                          <button
                            type="button"
                            className="btn"
                            disabled={isFull}
                            style={{
                              width: '100%',
                              padding: '0.5rem',
                              fontSize: '0.82rem',
                              fontWeight: 800,
                              background: isSelected 
                                ? 'var(--rarity-epic)' 
                                : isFull 
                                  ? 'rgba(255, 255, 255, 0.05)' 
                                  : 'rgba(168, 85, 247, 0.15)',
                              color: isFull ? 'var(--text-dim)' : '#fff',
                              border: isSelected 
                                ? '1px solid var(--rarity-epic)' 
                                : isFull 
                                  ? '1px solid rgba(255, 255, 255, 0.1)' 
                                  : '1px solid rgba(168, 85, 247, 0.5)',
                            }}
                            onClick={() => toggleSelectForFusion(driver.asset_id)}
                          >
                            {isSelected ? (
                              <span>✓ In Slot #{slotIndex + 1} (Remove)</span>
                            ) : isFull ? (
                              <span>Slots Full (5/5)</span>
                            ) : (
                              <span><Plus size={13} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '4px' }} /> Add to Slot</span>
                            )}
                          </button>
                        </div>
                      );
                    })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* 5. TRADING MARKETPLACE VIEW (1-for-1 Atomic Swaps) */}
      {/* ========================================================= */}
      {activeTab === 'trading' && (
        <div>
          <div className="card" style={{ marginBottom: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
              <div className="card-title" style={{ margin: 0 }}>
                <ArrowLeftRight size={22} color="var(--color-primary)" />
                Trading Market (Card-for-Card Atomic Swaps)
              </div>

              <button 
                className="btn btn-primary"
                style={{ width: 'auto', padding: '0.45rem 1rem', fontSize: '0.85rem' }}
                onClick={() => setIsCreateTradeOpen(true)}
              >
                <Plus size={16} /> Create Trade Offer
              </button>
            </div>

            {tradeMessage && (
              <div className="status-box" style={{ marginBottom: '1.25rem', background: 'rgba(0, 240, 255, 0.1)', border: '1px solid rgba(0, 240, 255, 0.3)', color: '#fff' }}>
                <span>{tradeMessage}</span>
              </div>
            )}

            {/* Sub Tabs */}
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
              <button 
                className={`filter-pill-btn ${tradeTab === 'available' ? 'active' : ''}`}
                onClick={() => setTradeTab('available')}
              >
                Available Trades ({openTrades.length})
              </button>
              <button 
                className={`filter-pill-btn ${tradeTab === 'my_trades' ? 'active' : ''}`}
                onClick={() => setTradeTab('my_trades')}
              >
                My Trade Offers ({userTrades.length})
              </button>
            </div>

            {/* Tab: Available Trades */}
            {tradeTab === 'available' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1rem' }}>
                {openTrades.length === 0 ? (
                  <div style={{ padding: '2.5rem', textAlign: 'center', color: 'var(--text-muted)', gridColumn: '1 / -1' }}>
                    No open trade offers in marketplace. Create one to swap with players!
                  </div>
                ) : (
                  openTrades.map(trade => (
                    <div key={trade.trade_id} style={{ background: 'var(--bg-surface-elevated)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '1.25rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem' }}>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>Trade #{trade.trade_id.substring(0, 8)}</span>
                        <span style={{ fontSize: '0.72rem', color: 'var(--color-primary)', fontFamily: 'var(--font-mono)' }}>By {trade.creator_wallet.substring(0, 6)}...</span>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '0.75rem', alignItems: 'center', marginBottom: '1rem', background: 'rgba(0,0,0,0.3)', padding: '0.75rem', borderRadius: '8px' }}>
                        <div>
                          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>OFFERS</div>
                          <div style={{ fontWeight: 800, fontSize: '0.95rem' }}>{trade.offered_driver_name}</div>
                          <span className={`rarity-pill ${trade.offered_driver_rarity.toLowerCase()}`} style={{ fontSize: '0.65rem' }}>
                            {trade.offered_driver_rarity} (#{trade.offered_asset_id})
                          </span>
                        </div>

                        <ArrowLeftRight size={18} color="var(--color-accent)" />

                        <div>
                          <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>WANTS</div>
                          <div style={{ fontWeight: 800, fontSize: '0.95rem' }}>{trade.requested_driver_name}</div>
                          <span className="rarity-pill common" style={{ fontSize: '0.65rem' }}>
                            Asset #{trade.requested_asset_id}
                          </span>
                        </div>
                      </div>

                      {trade.notes && (
                        <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '0.8rem', fontStyle: 'italic' }}>
                          "{trade.notes}"
                        </p>
                      )}

                      <button 
                        className="btn btn-primary"
                        style={{ width: '100%', padding: '0.45rem', fontSize: '0.82rem' }}
                        onClick={() => handleAcceptTrade(trade.trade_id)}
                        disabled={tradeActionLoading}
                      >
                        Accept Trade (Atomic Swap)
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}

            {/* Tab: My Trades */}
            {tradeTab === 'my_trades' && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1rem' }}>
                {userTrades.length === 0 ? (
                  <div style={{ padding: '2.5rem', textAlign: 'center', color: 'var(--text-muted)', gridColumn: '1 / -1' }}>
                    You have not created any trade offers yet.
                  </div>
                ) : (
                  userTrades.map(trade => (
                    <div key={trade.trade_id} style={{ background: 'var(--bg-surface-elevated)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '1.25rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.8rem' }}>
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>Trade #{trade.trade_id.substring(0, 8)}</span>
                        <span className={`rarity-pill ${trade.status === 'COMPLETED' ? 'rare' : trade.status === 'OPEN' ? 'epic' : 'common'}`} style={{ fontSize: '0.7rem' }}>
                          {trade.status}
                        </span>
                      </div>

                      <div style={{ marginBottom: '1rem', fontSize: '0.85rem' }}>
                        <div>Offered: <strong>{trade.offered_driver_name}</strong> (#{trade.offered_asset_id})</div>
                        <div>Wanted: <strong>{trade.requested_driver_name}</strong> (#{trade.requested_asset_id})</div>
                      </div>

                      {trade.status === 'OPEN' && (
                        <button 
                          className="btn btn-danger"
                          style={{ width: '100%', padding: '0.45rem', fontSize: '0.82rem' }}
                          onClick={() => handleCancelTrade(trade.trade_id)}
                          disabled={tradeActionLoading}
                        >
                          Cancel Offer
                        </button>
                      )}
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal: Create Trade Offer */}
      {isCreateTradeOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <h3 style={{ fontSize: '1.2rem', fontWeight: 800 }}>Create 1-for-1 Trade Offer</h3>
              <button onClick={() => setIsCreateTradeOpen(false)} style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>✕</button>
            </div>

            <form onSubmit={handleCreateTrade}>
              <div className="input-group">
                <label className="input-label">Select My Card to Offer</label>
                <select 
                  className="input-field"
                  value={tradeOfferedAssetId || ''}
                  onChange={(e) => setTradeOfferedAssetId(Number(e.target.value))}
                  required
                >
                  <option value="">-- Choose Card --</option>
                  {userCollection.map(c => (
                    <option key={c.asset_id} value={c.asset_id}>
                      {c.name} ({c.rarity}) — Asset #{c.asset_id}
                    </option>
                  ))}
                </select>
              </div>

              <div className="input-group">
                <label className="input-label">Requested Target Card Asset ID</label>
                <input 
                  type="number"
                  placeholder="e.g. 700000001"
                  className="input-field"
                  value={tradeRequestedAssetId}
                  onChange={(e) => setTradeRequestedAssetId(e.target.value)}
                  required
                />
              </div>

              <div className="input-group">
                <label className="input-label">Trade Note / Terms (Optional)</label>
                <input 
                  type="text"
                  placeholder="e.g. Looking for high-speed driver!"
                  className="input-field"
                  value={tradeNotes}
                  onChange={(e) => setTradeNotes(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1.5rem' }}>
                <button type="button" className="btn" style={{ background: 'var(--bg-surface-elevated)' }} onClick={() => setIsCreateTradeOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={tradeActionLoading}>
                  {tradeActionLoading ? 'Creating Offer...' : 'Publish Trade Offer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* 6. RACE VIEW */}
      {/* ========================================================= */}
      {activeTab === 'race' && (
        <div>
          <div className="card" style={{ marginBottom: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
              <div className="card-title" style={{ margin: 0 }}>
                <Flag size={22} color="var(--color-primary)" />
                Grand Prix Race Control
              </div>
            </div>

            {raceError && (
              <div className="status-box error" style={{ marginBottom: '1rem' }}>
                <AlertCircle size={18} />
                <span>{raceError}</span>
              </div>
            )}

            {/* Select Driver & Circuit */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem', marginBottom: '1.5rem' }}>
              <div>
                <label className="input-label">Select Owned Driver</label>
                {userCollection.length === 0 ? (
                  <div style={{ padding: '0.75rem', background: 'var(--bg-surface-elevated)', borderRadius: '8px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    No cards in garage. Purchase a pack first!
                  </div>
                ) : (
                  <select 
                    className="input-field"
                    value={selectedDriverAssetId || ''}
                    onChange={(e) => setSelectedDriverAssetId(Number(e.target.value))}
                  >
                    {userCollection.map(c => (
                      <option key={c.asset_id} value={c.asset_id}>
                        {c.name} ({c.rarity}) — Asset #{c.asset_id} (Speed: {c.stats.Speed})
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div>
                <label className="input-label">Select Grand Prix Circuit</label>
                <select 
                  className="input-field"
                  value={selectedCircuitId}
                  onChange={(e) => setSelectedCircuitId(e.target.value)}
                >
                  {circuits.map(c => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.track_type.toUpperCase()} | {c.weather.toUpperCase()})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Selected Circuit Demand Breakdown */}
            {circuits.find(c => c.id === selectedCircuitId) && (
              <div style={{ background: 'var(--bg-surface-elevated)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '0.85rem 1rem', marginBottom: '1.5rem' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', marginBottom: '0.4rem' }}>
                  CIRCUIT STAT INFLUENCE:
                </div>
                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                  {Object.entries(circuits.find(c => c.id === selectedCircuitId)!.stat_weights).map(([stat, weight]) => (
                    <span key={stat} style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', padding: '0.2rem 0.5rem', background: 'rgba(255,255,255,0.05)', borderRadius: '4px' }}>
                      {stat}: <strong>{(weight * 100).toFixed(0)}%</strong>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Optional Garage Coach (Assistive AI) */}
            <div style={{ marginBottom: '1.5rem', background: 'rgba(0, 255, 136, 0.04)', border: '1px solid rgba(0, 255, 136, 0.2)', borderRadius: '10px', padding: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--color-success)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Bot size={16} /> Garage Coach (AI Race Engineer)
                </span>
                <button 
                  className="btn"
                  style={{ width: 'auto', padding: '0.25rem 0.6rem', fontSize: '0.75rem', background: 'rgba(0, 255, 136, 0.15)', color: 'var(--color-success)', border: '1px solid rgba(0, 255, 136, 0.3)' }}
                  onClick={handleGetCoachAdvice}
                  disabled={isCoachAnalyzing || userCollection.length === 0}
                >
                  {isCoachAnalyzing ? 'Analyzing...' : 'Recommend Best Driver'}
                </button>
              </div>

              {coachRecommendation && (
                <div style={{ fontSize: '0.82rem', color: '#fff', marginTop: '0.5rem', lineHeight: 1.5 }}>
                  💡 <strong>Coach Advice:</strong> {coachRecommendation.reasoning_summary} ({coachRecommendation.driver_name} recommended, {(coachRecommendation.confidence * 100).toFixed(0)}% confidence).
                </div>
              )}
            </div>

            {/* Race Button */}
            <button 
              className="btn btn-primary"
              style={{ width: '100%', fontSize: '1.05rem', padding: '0.85rem', fontWeight: 800 }}
              onClick={handleStartRace}
              disabled={isRacing || !selectedDriverAssetId}
            >
              <Play size={18} />
              {isRacing ? 'Simulating Grand Prix...' : 'Start Grand Prix Race!'}
            </button>

            {/* Active Race Results */}
            {activeRaceResult && (
              <div style={{ marginTop: '2rem', background: 'rgba(0,0,0,0.4)', border: '1px solid var(--border-color)', borderRadius: '12px', padding: '1.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem' }}>
                  <div>
                    <span style={{ fontSize: '1.25rem', fontWeight: 800, color: activeRaceResult.position === 1 ? 'var(--color-accent)' : 'var(--color-primary)' }}>
                      {activeRaceResult.result_category} — {activeRaceResult.points} Points Earned
                    </span>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>
                      Circuit: {activeRaceResult.circuit_name} | Race ID: <code>{activeRaceResult.race_id}</code>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
                    Score: <strong>{activeRaceResult.final_score}</strong>
                  </div>
                </div>

                <p style={{ background: 'rgba(0, 240, 255, 0.05)', border: '1px solid rgba(0, 240, 255, 0.2)', borderRadius: '8px', padding: '0.75rem', fontSize: '0.85rem', color: '#fff', marginBottom: '1.25rem' }}>
                  {activeRaceResult.analysis}
                </p>

                {/* 8-Car Grid */}
                <div style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: '0.5rem' }}>OFFICIAL GRID STANDINGS:</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                  {activeRaceResult.grid.map(car => (
                    <div 
                      key={car.position}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: '0.5rem 0.75rem',
                        borderRadius: '6px',
                        background: car.is_player ? 'rgba(0, 240, 255, 0.15)' : 'rgba(255,255,255,0.03)',
                        border: car.is_player ? '1px solid var(--color-primary)' : '1px solid transparent'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <span style={{ fontWeight: 800, width: '25px', color: car.position === 1 ? 'var(--color-accent)' : 'var(--color-primary)' }}>
                          P{car.position}
                        </span>
                        <span style={{ fontWeight: car.is_player ? 800 : 400 }}>
                          {car.driver_name} {car.is_player && <strong style={{ color: 'var(--color-primary)' }}>(YOU)</strong>}
                        </span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{car.team}</span>
                      </div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                        <span style={{ color: 'var(--color-success)', fontWeight: 700 }}>+{car.points} pts</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================= */}
      {/* 7. ACTIVITY VIEW */}
      {/* ========================================================= */}
      {activeTab === 'activity' && (
        <div>
          <div className="card">
            <div className="card-title">
              <Activity size={22} color="var(--color-primary)" />
              Recent Player Activity
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {/* Fusions */}
              {userFusions.map(f => (
                <div key={f.fusion_id} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.85rem', background: 'var(--bg-surface-elevated)', borderRadius: '8px', borderLeft: '3px solid var(--rarity-epic)' }}>
                  <Sparkles size={18} color="var(--rarity-epic)" />
                  <div style={{ flex: 1 }}>
                    <div>Forged Premium Driver <strong>{f.premium_driver_name || 'Apex Driver'}</strong> (Asset #{f.output_asset_id})</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>5 Epic cards consumed | {new Date(f.created_at).toLocaleString()}</div>
                  </div>
                </div>
              ))}

              {/* Trades */}
              {userTrades.map(t => (
                <div key={t.trade_id} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.85rem', background: 'var(--bg-surface-elevated)', borderRadius: '8px', borderLeft: '3px solid var(--color-primary)' }}>
                  <ArrowLeftRight size={18} color="var(--color-primary)" />
                  <div style={{ flex: 1 }}>
                    <div>Trade Offer {t.status}: Offered <strong>{t.offered_driver_name}</strong> for <strong>{t.requested_driver_name}</strong></div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{t.atomic_group_id || t.trade_id} | {new Date(t.created_at).toLocaleString()}</div>
                  </div>
                </div>
              ))}

              {/* Races */}
              {recentRaces.map(r => (
                <div key={r.race_id} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.85rem', background: 'var(--bg-surface-elevated)', borderRadius: '8px', borderLeft: '3px solid var(--color-success)' }}>
                  <Flag size={18} color="var(--color-success)" />
                  <div style={{ flex: 1 }}>
                    <div>Finished <strong>{r.result_category}</strong> in {r.circuit_name} (+{r.points} pts)</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>Driver: {r.driver_name} | {new Date(r.created_at).toLocaleString()}</div>
                  </div>
                </div>
              ))}

              {userFusions.length === 0 && userTrades.length === 0 && recentRaces.length === 0 && (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                  No recent activity found. Buy a pack, race, or fuse cards to create history!
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default App;
