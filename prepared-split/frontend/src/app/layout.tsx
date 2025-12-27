import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import CopilotProvider from '@/providers/CopilotProvider'
import KeyboardShortcutsProvider from '@/providers/KeyboardShortcutsProvider'
import ScheduleConfirmation from '@/components/ScheduleConfirmation'
import AchievementPopup from '@/components/AchievementPopup'
import ShortcutsHelp from '@/components/ShortcutsHelp'
import ServiceWorkerRegistration from '@/components/ServiceWorkerRegistration'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
    title: 'Engineering OS',
    description: 'AI-powered study management for KU Engineering students',
    manifest: '/manifest.json',
    themeColor: '#42D674',
    viewport: {
        width: 'device-width',
        initialScale: 1,
        maximumScale: 1,
    },
    appleWebApp: {
        capable: true,
        statusBarStyle: 'black-translucent',
        title: 'EngOS',
    },
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en">
            <body className={`${inter.className} bg-[#C9FDF2] min-h-screen`}>
                <CopilotProvider>
                    <KeyboardShortcutsProvider>
                        <div className="flex flex-col min-h-screen">
                            {children}
                        </div>
                        {/* Global modals and popups */}
                        <ScheduleConfirmation />
                        <AchievementPopup />
                        <ShortcutsHelp />
                        <ServiceWorkerRegistration />
                    </KeyboardShortcutsProvider>
                </CopilotProvider>
            </body>
        </html>
    )
}
