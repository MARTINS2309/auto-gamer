import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'
import shadcnRules from './eslint-rules/index.js'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    plugins: {
      'shadcn-rules': shadcnRules,
    },
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      // Allow _-prefixed unused vars (standard destructure convention)
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      // Enforce semantic colors only - no direct Tailwind palette or arbitrary colors
      'shadcn-rules/no-color-overrides': 'error',
      // Enforce sharp corners - brutalist theme
      'shadcn-rules/no-border-radius': 'error',
    },
  },
  // Exclude shadcn ui components from custom rules + react-refresh (they export variants + components)
  {
    files: ['src/components/ui/**/*.{ts,tsx}'],
    rules: {
      'shadcn-rules/no-color-overrides': 'off',
      'shadcn-rules/no-border-radius': 'off',
      'react-refresh/only-export-components': 'off',
    },
  },
])
