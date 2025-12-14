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
                // UI colors
                'primary': '#6366f1',
                'surface': '#1e1e2e',
                'surface-light': '#2a2a3e',
                'accent': '#a78bfa',
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
