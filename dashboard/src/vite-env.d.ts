/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** e.g. `https://example.com/p/{article_id}` — placeholders URL-encoded */
  readonly VITE_SHOP_PRODUCT_URL_TEMPLATE?: string;
}
