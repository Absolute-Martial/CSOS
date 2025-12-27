/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
        './src/components/**/*.{js,ts,jsx,tsx,mdx}',
        './src/app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
        extend: {
            colors: {
                // Subject colors
                'math': '#3b82f6',
                'phys': '#ef4444',
                'chem': '#22c55e',
                'engg': '#f59e0b',
                // UI colors - Light Teal Theme
                'primary': '#2A9D8F',       // Deep Teal - main actions
                'secondary': '#B6F2D1',     // Mint - secondary elements
                'accent': '#85D1DB',        // Teal - highlights
                'sage': '#B3EBF2',          // Light Teal - subtle backgrounds
                'surface': '#B3EBF2',
                'surface-light': '#85D1DB',
            },
            animation: {
                'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                'bounce-slow': 'bounce 2s infinite',
            },
        },
    },
    plugins: [],
    darkMode: 'class',
}
