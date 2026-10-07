/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Palette principale — alignée sur Nassira
        green: {
          DEFAULT: '#3B6D11',
          light:   '#EAF3DE',
          mid:     '#C0DD97',
          dark:    '#2d5409',
          text:    '#27500A',
        },
        surface: {
          DEFAULT: '#f5f4f0',
          white:   '#ffffff',
          hover:   '#f0f4eb',
        },
        border: {
          DEFAULT: '#e8ede3',
          dark:    '#d0d8c8',
        },
        text: {
          primary:   '#111827',
          secondary: '#6b7280',
          muted:     '#9ca3af',
        },
        // Statuts impact
        impact: {
          low:     '#3B6D11',
          medium:  '#d97706',
          high:    '#dc2626',
          massive: '#7c3aed',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        xl:  '0.75rem',
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
    },
  },
  plugins: [],
}
