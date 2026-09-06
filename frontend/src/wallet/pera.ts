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

export interface AccountBalanceInfo {
  address: string;
  amountMicroAlgos: number;
  amountAlgos: number;
  minBalanceMicroAlgos: number;
  spendableMicroAlgos: number;
  assetsCount: number;
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
 * Queries real-time account ledger state from Algod.
 */
export async function getAccountInfo(address: string): Promise<AccountBalanceInfo> {
  const accountInfo: any = await algodClient.accountInformation(address).do();
  const amount = Number(accountInfo.amount || 0);
  const minBalance = Number(accountInfo.minBalance ?? accountInfo["min-balance"] ?? 100000);
  const spendable = Math.max(0, amount - minBalance);
  const assets = accountInfo.assets || [];

  return {
    address,
    amountMicroAlgos: amount,
    amountAlgos: amount / 1_000_000,
    minBalanceMicroAlgos: minBalance,
    spendableMicroAlgos: spendable,
    assetsCount: assets.length
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
 * Prompts Pera Wallet to sign the unsigned transaction.
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
