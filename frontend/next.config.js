/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
    output: 'standalone', // Required for Docker/Dokploy deployment

    async rewrites() {
        // In production, use NEXT_PUBLIC_API_URL env variable
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        return [
            {
                source: '/api/:path*',
                destination: `${apiUrl}/api/:path*`,
            },
        ]
    },
}

module.exports = nextConfig
