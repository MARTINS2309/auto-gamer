/**
 * ESLint rule to prevent direct color overrides in Tailwind classes.
 * Only semantic colors from shadcn theme are allowed (bg-primary, text-muted-foreground, etc.)
 */

// Tailwind color palette names that should NOT be used directly
const FORBIDDEN_COLOR_PALETTES = [
  'slate', 'gray', 'zinc', 'neutral', 'stone',
  'red', 'orange', 'amber', 'yellow', 'lime',
  'green', 'emerald', 'teal', 'cyan', 'sky',
  'blue', 'indigo', 'violet', 'purple', 'fuchsia',
  'pink', 'rose', 'black', 'white'
]

// Allowed semantic color names from shadcn
const ALLOWED_SEMANTIC_COLORS = [
  'background', 'foreground',
  'card', 'card-foreground',
  'popover', 'popover-foreground',
  'primary', 'primary-foreground',
  'secondary', 'secondary-foreground',
  'muted', 'muted-foreground',
  'accent', 'accent-foreground',
  'destructive', 'destructive-foreground',
  'border', 'input', 'ring',
  'sidebar', 'sidebar-foreground',
  'sidebar-primary', 'sidebar-primary-foreground',
  'sidebar-accent', 'sidebar-accent-foreground',
  'sidebar-border', 'sidebar-ring',
  'chart-1', 'chart-2', 'chart-3', 'chart-4', 'chart-5',
  'inherit', 'current', 'transparent'
]

// Build regex patterns
const colorPalettePattern = FORBIDDEN_COLOR_PALETTES.join('|')
const arbitraryColorPattern = /\[#[0-9a-fA-F]{3,8}\]|\[rgb\(|\[rgba\(|\[hsl\(|\[hsla\(|\[oklch\(/

// Pattern for color utility classes with forbidden palettes
// Matches: bg-red-500, text-blue-200, border-gray-100, etc.
const forbiddenColorClassPattern = new RegExp(
  `(bg|text|border|ring|outline|shadow|from|via|to|fill|stroke|decoration|placeholder|caret|accent)-(${colorPalettePattern})(-\\d+)?(/\\d+)?`
)

/** @type {import('eslint').Rule.RuleModule} */
export default {
  meta: {
    type: 'problem',
    docs: {
      description: 'Disallow direct color overrides - use shadcn semantic colors only',
      category: 'Stylistic Issues',
      recommended: true,
    },
    messages: {
      noArbitraryColor: 'Arbitrary color values are not allowed. Use semantic colors from the shadcn theme (e.g., bg-primary, text-muted-foreground).',
      noColorPalette: 'Direct Tailwind color palette "{{color}}" is not allowed. Use semantic colors from the shadcn theme (e.g., bg-primary, text-muted-foreground).',
    },
    schema: [],
  },
  create(context) {
    function checkClassName(value, node) {
      if (typeof value !== 'string') return

      const classes = value.split(/\s+/)

      for (const cls of classes) {
        // Check for arbitrary color values
        if (arbitraryColorPattern.test(cls)) {
          context.report({
            node,
            messageId: 'noArbitraryColor',
          })
          return
        }

        // Check for forbidden color palette classes
        const match = cls.match(forbiddenColorClassPattern)
        if (match) {
          context.report({
            node,
            messageId: 'noColorPalette',
            data: { color: match[2] },
          })
          return
        }
      }
    }

    return {
      // Check className="..." attributes
      JSXAttribute(node) {
        if (node.name.name !== 'className') return

        if (node.value?.type === 'Literal') {
          checkClassName(node.value.value, node)
        }

        // Check template literals: className={`...`}
        if (node.value?.type === 'JSXExpressionContainer') {
          const expr = node.value.expression

          if (expr.type === 'TemplateLiteral') {
            expr.quasis.forEach(quasi => {
              checkClassName(quasi.value.raw, node)
            })
          }

          // Check string literals: className={"..."}
          if (expr.type === 'Literal') {
            checkClassName(expr.value, node)
          }
        }
      },

      // Check cn() and clsx() calls
      CallExpression(node) {
        const callee = node.callee
        if (callee.type !== 'Identifier') return
        if (!['cn', 'clsx', 'cva', 'twMerge'].includes(callee.name)) return

        node.arguments.forEach(arg => {
          if (arg.type === 'Literal' && typeof arg.value === 'string') {
            checkClassName(arg.value, arg)
          }
          if (arg.type === 'TemplateLiteral') {
            arg.quasis.forEach(quasi => {
              checkClassName(quasi.value.raw, arg)
            })
          }
        })
      },
    }
  },
}
