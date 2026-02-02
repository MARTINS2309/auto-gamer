/**
 * Custom ESLint rules for shadcn/presentational component patterns
 */

import noColorOverrides from './no-color-overrides.js'
import noBorderRadius from './no-border-radius.js'

/** @type {import('eslint').ESLint.Plugin} */
export default {
  meta: {
    name: 'eslint-plugin-shadcn-rules',
    version: '1.0.0',
  },
  rules: {
    'no-color-overrides': noColorOverrides,
    'no-border-radius': noBorderRadius,
  },
}
