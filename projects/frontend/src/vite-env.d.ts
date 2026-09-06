/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_X402_URL?: string;
  readonly VITE_NETWORK?: string;
  readonly VITE_ALGOD_NODE?: string;
  readonly VITE_INDEXER_NODE?: string;
  readonly VITE_PAYMENT_RECEIVER_ADDRESS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
