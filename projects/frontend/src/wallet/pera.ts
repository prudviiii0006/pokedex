import { PeraWalletConnect } from "@perawallet/connect";
import algosdk from "algosdk";

// Algorand TestNet Chain ID (416002 for TestNet, 416001 for MainNet)
export const TESTNET_CHAIN_ID = 416002;

// Public Algonode TestNet Node
export const ALGOD_SERVER = "https://testnet-api.algonode.cloud";
export const ALGOD_PORT = "";
export const ALGOD_TOKEN = "";

// 1. Initialize Algod Client for querying balances and submitting raw signed transactions
export const algodClient = new algosdk.Algodv2(ALGOD_TOKEN, ALGOD_SERVER, ALGOD_PORT);

// 2. Initialize PeraWalletConnect singleton instance
export const peraWallet = new PeraWalletConnect({
  chainId: TESTNET_CHAIN_ID,
  shouldShowSignTxnToast: true
});

// Algorand TestNet USDC Asset ID
export const TESTNET_USDC_ASSET_ID = 10458941;

export interface AccountBalanceInfo {
  address: string;
  amountMicroAlgos: number;
  amountAlgos: number;
  minBalanceMicroAlgos: number;
  spendableMicroAlgos: number;
  assetsCount: number;
  usdcBalance: number;
  isUsdcOptedIn: boolean;
}

/**
 * Connects to Pera Wallet via mobile QR code or browser extension.
 * Returns the array of approved public addresses.
 */
export async function connectPeraWallet(): Promise<string[]> {
  try {
    const newAccounts = await peraWallet.connect();
    // Setup disconnect event listener
    peraWallet.connector?.on("disconnect", () => {
      console.log("Pera Wallet disconnected by user or session expired");
    });
    return newAccounts;
  } catch (error: any) {
    if (error?.data?.type === "CONNECT_MODAL_CLOSED") {
      throw new Error("Connection modal closed by user");
    }
    throw error;
  }
}

/**
 * Reconnects an existing active session on page reload.
 */
export async function reconnectPeraSession(): Promise<string[]> {
  try {
    const accounts = await peraWallet.reconnectSession();
    return accounts;
  } catch (error) {
    console.warn("No active Pera Wallet session to resume", error);
    return [];
  }
}

/**
 * Disconnects the active Pera Wallet session.
 */
export async function disconnectPeraWallet(): Promise<void> {
  await peraWallet.disconnect();
}

/**
 * Queries real-time account ledger state and USDC balance from Algod.
 */
export async function getAccountInfo(address: string): Promise<AccountBalanceInfo> {
  const accountInfo: any = await algodClient.accountInformation(address).do();
  const amount = Number(accountInfo.amount || 0);
  const minBalance = Number(accountInfo.minBalance ?? accountInfo["min-balance"] ?? 100000);
  const spendable = Math.max(0, amount - minBalance);
  const assets = accountInfo.assets || [];

  const usdcAsset = assets.find((a: any) => (a["asset-id"] ?? a.assetId) === TESTNET_USDC_ASSET_ID);
  const usdcMicroUnits = usdcAsset ? Number(usdcAsset.amount || 0) : 0;
  const usdcBalance = usdcMicroUnits / 1_000_000;
  const isUsdcOptedIn = Boolean(usdcAsset);

  return {
    address,
    amountMicroAlgos: amount,
    amountAlgos: amount / 1_000_000,
    minBalanceMicroAlgos: minBalance,
    spendableMicroAlgos: spendable,
    assetsCount: assets.length,
    usdcBalance,
    isUsdcOptedIn
  };
}

/**
 * Constructs an unsigned TestNet PaymentTxn.
 * Note: The frontend NEVER needs the private key to construct this transaction!
 */
export async function createUnsignedPaymentTxn(
  senderAddress: string,
  receiverAddress: string,
  amountMicroAlgos: number,
  noteText: string = "AlgoRacers: Session 4 Test Payment"
): Promise<algosdk.Transaction> {
  const suggestedParams = await algodClient.getTransactionParams().do();
  
  const enc = new TextEncoder();
  const noteBytes = enc.encode(noteText);

  const txn = algosdk.makePaymentTxnWithSuggestedParamsFromObject({
    sender: senderAddress,
    receiver: receiverAddress,
    amount: amountMicroAlgos,
    note: noteBytes,
    suggestedParams
  });

  return txn;
}

/**
 * Checks whether an account has opted into a specific ASA asset.
 */
export async function checkAssetOptIn(address: string, assetId: number): Promise<boolean> {
  try {
    const accountInfo: any = await algodClient.accountInformation(address).do();
    const assets = accountInfo.assets || [];
    return assets.some((a: any) => (a["asset-id"] ?? a.assetId) === assetId);
  } catch (error) {
    console.warn(`Failed to check asset opt-in for ${assetId}:`, error);
    return false;
  }
}

/**
 * Constructs an unsigned Asset Opt-In transaction (0-amount transfer to self).
 */
export async function createAssetOptInTxn(
  address: string,
  assetId: number
): Promise<algosdk.Transaction> {
  const suggestedParams = await algodClient.getTransactionParams().do();
  return algosdk.makeAssetTransferTxnWithSuggestedParamsFromObject({
    sender: address,
    receiver: address,
    assetIndex: assetId,
    amount: 0,
    suggestedParams
  });
}

/**
 * Constructs an unsigned TestNet USDC Asset Transfer transaction (ASA ID: 10458941).
 */
export async function createUnsignedAssetTransferTxn(
  senderAddress: string,
  receiverAddress: string,
  assetId: number,
  amountMicroUnits: number,
  noteText: string = "AlgoRacers: Pack Payment"
): Promise<algosdk.Transaction> {
  const suggestedParams = await algodClient.getTransactionParams().do();
  const enc = new TextEncoder();
  const noteBytes = enc.encode(noteText);

  return algosdk.makeAssetTransferTxnWithSuggestedParamsFromObject({
    sender: senderAddress,
    receiver: receiverAddress,
    assetIndex: assetId,
    amount: amountMicroUnits,
    note: noteBytes,
    suggestedParams
  });
}

export function isPeraConnected(): boolean {
  return Boolean(peraWallet.isConnected);
}

/**
 * Prompts Pera Wallet to sign a transaction and returns the signed bytes as Base64.
 * Does NOT submit the transaction directly to Algod.
 */
export async function signTransactionOnly(
  unsignedTxn: algosdk.Transaction,
  senderAddress: string
): Promise<{ signedBytes: Uint8Array; signedB64: string; txId: string }> {
  if (!peraWallet.isConnected) {
    throw new Error("Pera Wallet is not connected via mobile session.");
  }
  const singleTxnGroup = [{ txn: unsignedTxn, signers: [senderAddress] }];
  
  const signPromise = peraWallet.signTransaction([singleTxnGroup]);
  const timeoutPromise = new Promise<never>((_, reject) => {
    setTimeout(() => reject(new Error("Pera Wallet signing timed out or was dismissed")), 4000);
  });

  const signedTxnBytesArray = await Promise.race([signPromise, timeoutPromise]);
  const signedBytes = signedTxnBytesArray[0];
  
  // Convert binary Uint8Array to Base64
  let binary = "";
  for (let i = 0; i < signedBytes.byteLength; i++) {
    binary += String.fromCharCode(signedBytes[i]);
  }
  const signedB64 = btoa(binary);
  const txId = unsignedTxn.txID();

  return { signedBytes, signedB64, txId };
}

/**
 * Prompts Pera Wallet to sign the unsigned transaction and submits it to Algod.
 * The private key stays strictly inside Pera Wallet.
 */
export async function signAndSubmitTxn(
  unsignedTxn: algosdk.Transaction,
  senderAddress: string
): Promise<{ txId: string; confirmedRound: number }> {
  // Pera expects an array of transaction groups
  const singleTxnGroup = [{ txn: unsignedTxn, signers: [senderAddress] }];

  // 1. Request signature from Pera Wallet
  const signedTxnBytes = await peraWallet.signTransaction([singleTxnGroup]);

  // 2. Submit signed bytes to Algorand TestNet node (Algod)
  const res: any = await algodClient.sendRawTransaction(signedTxnBytes).do();
  const txId = res.txid ?? res.txId;

  // 3. Await round finality (~2.9s)
  const confirmedTxn: any = await algosdk.waitForConfirmation(algodClient, txId, 4);
  const confirmedRound = Number(confirmedTxn.confirmedRound ?? confirmedTxn["confirmed-round"] ?? 0);

  return { txId, confirmedRound };
}
