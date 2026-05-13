// Mock for SvelteKit's $app/environment in vitest / standalone Vite builds.
// We're a Tauri desktop app — always running in a browser webview.
export const browser = typeof window !== 'undefined'
export const dev = false
export const building = false
export const version = '0.0.0'
