import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import CopilotProvider from '@/providers/CopilotProvider'
import ScheduleConfirmation from '@/components/ScheduleConfirmation'
import AchievementPopup from '@/components/AchievementPopup'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
    title: 'Personal Engineering OS',
    description: 'AI-powered study management for KU Engineering students',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en" className="dark">
            <body className={`${inter.className} bg-[#0a0a0f] min-h-screen`}>
                <CopilotProvider>
                    <div className="flex flex-col min-h-screen">
                        {children}
                    </div>
                    {/* Global modals and popups */}
                    <ScheduleConfirmation />
                    <AchievementPopup />
                </CopilotProvider>
            </body>
        </html>
    )
}
