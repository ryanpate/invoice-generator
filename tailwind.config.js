/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    './templates/**/*.html',
    './static/js/**/*.js',
  ],
  // Classes assembled at runtime via JS string concatenation — the content
  // scan can't see these, so they must be pinned here or styling silently
  // breaks (drag-over states on batch upload, calculator mode toggle,
  // dark-mode switching).
  safelist: [
    'dark',
    'hidden',
    'border-blue-500',
    'bg-blue-50',
    'dark:bg-blue-900/20',
    'bg-white',
    'dark:bg-gray-600',
    'text-gray-900',
    'dark:text-white',
    'shadow',
    'text-gray-600',
    'dark:text-gray-300',
    'text-green-600',
    'text-red-600',
    'dark:text-green-400',
    'dark:text-red-400',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
      },
    },
  },
  plugins: [],
};
