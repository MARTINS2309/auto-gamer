/**
 * ESLint rule to prevent border radius classes in Tailwind.
 * Brutalist theme requires sharp corners everywhere.
 */

// All rounded-* classes that should be forbidden
const FORBIDDEN_RADIUS_PATTERN = /^rounded(-[a-z]+)?(-[a-z0-9]+)?$/

/** @type {import('eslint').Rule.RuleModule} */
export default {
  meta: {
    type: 'problem',
    docs: {
      description: 'Disallow border radius classes - brutalist theme requires sharp corners',
      category: 'Stylistic Issues',
      recommended: true,
    },
    messages: {
      noBorderRadius: 'Border radius class "{{className}}" is not allowed. Brutalist theme requires sharp corners (--radius: 0).',
    },
    schema: [],
  },
  create(context) {
    function checkClassName(value, node) {
      if (typeof value !== 'string') return

      const classes = value.split(/\s+/)

      for (const cls of classes) {
        // Check for any rounded-* class
        if (FORBIDDEN_RADIUS_PATTERN.test(cls)) {
          context.report({
            node,
            messageId: 'noBorderRadius',
            data: { className: cls },
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
