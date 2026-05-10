'use client'

/* ──── REAL PROVIDER SVG ICONS ──── */
/* Shared across Models page and Landing page */

export function AnthropicIcon({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M17.304 3.5L12.5 20.5H9.696L14.5 3.5H17.304Z" fill="#d4a574"/>
      <path d="M9.304 3.5L4.5 20.5H7.304L12.108 3.5H9.304Z" fill="#d4a574"/>
      <path d="M22.304 3.5L17.5 20.5H14.696L19.5 3.5H22.304Z" fill="#d4a574"/>
      <path d="M4.304 3.5L0 17.5H2.804L7.108 3.5H4.304Z" fill="#d4a574"/>
    </svg>
  )
}

export function OpenAIIcon({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872zm16.597 3.855l-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z" fill="#10a37f"/>
    </svg>
  )
}

export function GoogleIcon({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    </svg>
  )
}

export function XAIIcon({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" fill="#ff6b35"/>
    </svg>
  )
}

export function MetaIcon({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M6.915 4.012C5.437 4.012 4.297 4.602 3.364 5.445C2.445 6.275 1.794 7.376 1.2 8.567C0.412 10.138 0 11.814 0 13.247C0 14.958 0.567 16.089 1.427 16.787C2.267 17.469 3.343 17.735 4.313 17.735C5.353 17.735 6.242 17.409 7.03 16.797C7.803 16.198 8.457 15.346 9.078 14.245L9.626 13.231L10.137 14.272C10.713 15.419 11.33 16.281 12.069 16.866C12.797 17.443 13.678 17.735 14.787 17.735C15.757 17.735 16.833 17.469 17.673 16.787C18.533 16.089 19.1 14.958 19.1 13.247C19.1 11.814 18.688 10.138 17.9 8.567C17.306 7.376 16.655 6.275 15.736 5.445C14.803 4.602 13.663 4.012 12.185 4.012C11.115 4.012 10.26 4.322 9.55 4.825C8.964 5.24 8.47 5.786 7.995 6.394C7.492 5.786 6.998 5.24 6.412 4.825C5.702 4.322 4.847 4.012 3.777 4.012H6.915ZM3.777 6.012C4.457 6.012 4.978 6.213 5.467 6.559C5.983 6.924 6.477 7.495 7.052 8.268L7.995 9.563L8.938 8.268C9.513 7.495 10.007 6.924 10.523 6.559C11.012 6.213 11.533 6.012 12.213 6.012C13.117 6.012 13.822 6.368 14.458 6.945C15.13 7.553 15.685 8.425 16.212 9.481C16.86 10.785 17.1 12.12 17.1 13.247C17.1 14.405 16.767 14.981 16.363 15.312C15.94 15.658 15.34 15.735 14.787 15.735C14.073 15.735 13.577 15.561 13.161 15.227C12.73 14.88 12.316 14.326 11.849 13.48L9.55 9.563L7.251 13.48C6.784 14.326 6.37 14.88 5.939 15.227C5.523 15.561 5.027 15.735 4.313 15.735C3.76 15.735 3.16 15.658 2.737 15.312C2.333 14.981 2 14.405 2 13.247C2 12.12 2.24 10.785 2.888 9.481C3.415 8.425 3.97 7.553 4.642 6.945C5.278 6.368 5.983 6.012 6.887 6.012H3.777Z" fill="#0668E1"/>
    </svg>
  )
}

export function DeepSeekIcon({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M23.748 6.638c-.27-.27-.6-.41-.99-.41h-5.13c-.06 0-.12-.04-.14-.09a7.497 7.497 0 0 0-6.97-4.76c-3.21 0-6 2.04-7.04 4.93-.03.08-.1.14-.19.14H1.24c-.39 0-.72.14-.99.41-.27.27-.41.6-.41.99v3.18c0 .39.14.72.41.99.27.27.6.41.99.41h1.62c.11 0 .2.09.2.2v5.23c0 1.62 1.32 2.94 2.94 2.94h.39c.11 0 .2-.09.2-.2v-2.42c0-.11-.09-.2-.2-.2h-.02a.83.83 0 0 1-.83-.83V12.42c0-.11.09-.2.2-.2h2.61c.11 0 .2.09.2.2v5.43c0 .11.09.2.2.2h2.57c.11 0 .2-.09.2-.2v-5.43c0-.11.09-.2.2-.2h2.61c.11 0 .2.09.2.2v3.79a.83.83 0 0 1-.83.83h-.02c-.11 0-.2.09-.2.2v2.42c0 .11.09.2.2.2h.39c1.62 0 2.94-1.32 2.94-2.94v-5.23c0-.11.09-.2.2-.2h1.62c.39 0 .72-.14.99-.41.27-.27.41-.6.41-.99V7.628c0-.39-.14-.72-.41-.99zM10.518 8.8a3 3 0 1 1 0 2.4H8.148c-.11 0-.2-.09-.2-.2V9c0-.11.09-.2.2-.2h2.37z" fill="#4d6bfe"/>
    </svg>
  )
}

export function AlibabaIcon({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="24" height="24" rx="4" fill="#ff6a00"/>
      <path d="M4.5 17.5c.6-3.2 2.4-5.8 4.5-7.2.3-.2.5-.1.4.2-.1.5-.3 1.2-.3 1.8 0 1.5 1 2.7 2.5 2.7 1.8 0 3.2-1.8 3.2-4.2 0-2-1.2-3.6-3.2-3.6-1.2 0-2.3.6-3 1.5-.2.2-.5.2-.6-.1C7.2 6.3 8.5 4 11 4c3 0 5 2.5 5 5.8 0 4-2.8 7.2-6.5 7.2-1.8 0-3.2-.8-4-2-.1-.2-.4-.2-.5 0-.4.7-.7 1.6-.8 2.5H4.5z" fill="white"/>
    </svg>
  )
}

export function MistralIcon({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="2" width="4.8" height="4.8" rx="0.8" fill="#f70000"/>
      <rect x="7.6" y="2" width="4.8" height="4.8" rx="0.8" fill="#f70000"/>
      <rect x="13.2" y="2" width="4.8" height="4.8" rx="0.8" fill="#f70000"/>
      <rect x="2" y="7.6" width="4.8" height="4.8" rx="0.8" fill="#f70000"/>
      <rect x="13.2" y="7.6" width="4.8" height="4.8" rx="0.8" fill="#f70000"/>
      <rect x="2" y="13.2" width="4.8" height="4.8" rx="0.8" fill="#f70000"/>
      <rect x="7.6" y="13.2" width="4.8" height="4.8" rx="0.8" fill="#f70000"/>
      <rect x="13.2" y="13.2" width="4.8" height="4.8" rx="0.8" fill="#f70000"/>
      <rect x="7.6" y="18.8" width="4.8" height="3.2" rx="0.8" fill="#f70000"/>
    </svg>
  )
}

export function GroqIcon({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="12" r="10" fill="#f55036" fillOpacity="0.15"/>
      <path d="M7.5 8L12 4.5L16.5 8V10.5L12 7L7.5 10.5V8Z" fill="#f55036"/>
      <path d="M7.5 13.5L12 10L16.5 13.5V16L12 12.5L7.5 16V13.5Z" fill="#f55036"/>
      <path d="M7.5 19L12 15.5L16.5 19V19.5C16.5 20.05 16.05 20.5 15.5 20.5H8.5C7.95 20.5 7.5 20.05 7.5 19.5V19Z" fill="#f55036"/>
    </svg>
  )
}

export function CohereIcon({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="24" height="24" rx="6" fill="#39594d"/>
      <path d="M6 8C6 6.89543 6.89543 6 8 6H10C11.1046 6 12 6.89543 12 8V10C12 11.1046 11.1046 12 10 12H8C6.89543 12 6 11.1046 6 10V8Z" fill="white"/>
      <path d="M12 14C12 12.8954 12.8954 12 14 12H16C17.1046 12 18 12.8954 18 14V16C18 17.1046 17.1046 18 16 18H14C12.8954 18 12 17.1046 12 16V14Z" fill="white"/>
      <path d="M12 8C12 6.89543 12.8954 6 14 6H16C17.1046 6 18 6.89543 18 8V10C18 11.1046 17.1046 12 16 12H14C12.8954 12 12 11.1046 12 10V8Z" fill="white" fillOpacity="0.5"/>
    </svg>
  )
}

export function OllamaIcon({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="12" cy="12" r="10" fill="#00ff88" fillOpacity="0.15" stroke="#00ff88" strokeWidth="1"/>
      <path d="M9 7C9 7 8 5 7 5.5C6 6 7 8 7 8" stroke="#00ff88" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M15 7C15 7 16 5 17 5.5C18 6 17 8 17 8" stroke="#00ff88" strokeWidth="1.5" strokeLinecap="round"/>
      <ellipse cx="12" cy="13" rx="5" ry="5.5" fill="#00ff88" fillOpacity="0.3" stroke="#00ff88" strokeWidth="1"/>
      <circle cx="10" cy="12" r="1" fill="#00ff88"/>
      <circle cx="14" cy="12" r="1" fill="#00ff88"/>
      <ellipse cx="12" cy="14.5" rx="1.5" ry="1" fill="#00ff88" fillOpacity="0.5" stroke="#00ff88" strokeWidth="0.5"/>
    </svg>
  )
}

/* ──── Provider Icon Map ──── */
export const PROVIDER_ICONS: Record<string, React.FC<{ size?: number }>> = {
  anthropic: AnthropicIcon,
  openai: OpenAIIcon,
  google: GoogleIcon,
  xai: XAIIcon,
  meta: MetaIcon,
  deepseek: DeepSeekIcon,
  alibaba: AlibabaIcon,
  mistral: MistralIcon,
  groq: GroqIcon,
  cohere: CohereIcon,
  local: OllamaIcon,
}

export const PROVIDER_LIST = [
  { name: 'Anthropic', iconKey: 'anthropic', color: '#d4a574' },
  { name: 'OpenAI', iconKey: 'openai', color: '#10a37f' },
  { name: 'Google', iconKey: 'google', color: '#4285f4' },
  { name: 'xAI', iconKey: 'xai', color: '#ff6b35' },
  { name: 'Meta', iconKey: 'meta', color: '#0668E1' },
  { name: 'DeepSeek', iconKey: 'deepseek', color: '#4d6bfe' },
  { name: 'Alibaba', iconKey: 'alibaba', color: '#ff6a00' },
  { name: 'Mistral', iconKey: 'mistral', color: '#f70000' },
  { name: 'Groq', iconKey: 'groq', color: '#f55036' },
  { name: 'Cohere', iconKey: 'cohere', color: '#39594d' },
  { name: 'Local', iconKey: 'local', color: '#00ff88' },
]
