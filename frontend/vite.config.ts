/**
 * Configuration Vite pour CareLink Frontend
 * - Plugin Vue 3 pour le support .vue
 * - Plugin PWA pour le fonctionnement offline (Service Worker)
 * - Alias @ pour simplifier les imports
 */
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

export default defineConfig({
  plugins: [
    // Support des Single File Components Vue
    vue(),

    // Configuration PWA pour le mode offline
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'masked-icon.svg'],

      // Manifest PWA - identité de l'app installable
      manifest: {
        name: 'CareLink - Coordination des Soins',
        short_name: 'CareLink',
        description: 'Plateforme de coordination des soins pour personnes âgées',
        theme_color: '#3B82F6',
        background_color: '#ffffff',
        display: 'standalone',
        orientation: 'portrait-primary',
        categories: ['medical', 'health', 'productivity'],
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable',
          },
        ],
      },

      // Configuration Workbox pour le cache offline
      workbox: {
        // Fichiers statiques à mettre en cache
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],

        // Stratégies de cache pour l'API
        runtimeCaching: [
          {
            // API CareLink - NetworkFirst avec fallback cache
            urlPattern: /^https:\/\/api\.carelink\.fr\/api\/v1\/.*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'carelink-api-cache',
              expiration: {
                maxEntries: 200,
                maxAgeSeconds: 60 * 60 * 24, // 24 heures
              },
              cacheableResponse: {
                statuses: [0, 200],
              },
            },
          },
          {
            // Images - CacheFirst pour performance
            urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp)$/,
            handler: 'CacheFirst',
            options: {
              cacheName: 'carelink-images-cache',
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 60 * 60 * 24 * 30, // 30 jours
              },
            },
          },
        ],
      },
    }),
  ],

  // Alias pour simplifier les imports : @/components au lieu de ../../src/components
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },

  // Configuration serveur de développement
  server: {
    port: 3000,
    proxy: {
      // Proxy vers le backend FastAPI en dev
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },

  // Optimisations build
  build: {
    target: 'esnext',
    minify: 'esbuild',
    sourcemap: true,
  },
})
