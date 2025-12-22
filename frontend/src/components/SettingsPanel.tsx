
'use client'

import { useState, useEffect } from 'react'
import { Save, RefreshCw, Key, Server, Database, Moon, Sun } from 'lucide-react'

interface SettingItem {
    key: string
    label: string
    type: string
    value: string | number
    description: string
    options?: string[]
    min?: number
    max?: number
    step?: number
}

interface SettingCategory {
    category: string
    settings: SettingItem[]
}

export default function SettingsPanel() {
    const [settings, setSettings] = useState<SettingCategory[]>([])
    const [fetchedModels, setFetchedModels] = useState<string[]>([])
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState<string | null>(null)
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

    useEffect(() => {
        fetchSettings()
        fetchModels()
    }, [])

    const fetchModels = async () => {
        try {
            const res = await fetch('/api/ai/models')
            if (res.ok) {
                const data = await res.json()
                setFetchedModels(data)
            }
        } catch (error) {
            console.error('Failed to fetch models:', error)
        }
    }

    const fetchSettings = async () => {
        try {
            const res = await fetch('/api/settings')
            if (res.ok) {
                const data = await res.json()
                // Inject fetched models if available
                setSettings(data)
            }
        } catch (error) {
            console.error('Failed to fetch settings:', error)
        } finally {
            setLoading(false)
        }
    }

    const handleSave = async (key: string, value: string) => {
        setSaving(key)
        setMessage(null)

        try {
            const formData = new FormData()
            formData.append('key', key)
            formData.append('value', value)

            const res = await fetch('/api/settings', {
                method: 'POST',
                body: formData
            })

            if (res.ok) {
                setMessage({ type: 'success', text: 'Setting updated successfully!' })
                // Refresh settings to confirm save
                fetchSettings()
            } else {
                setMessage({ type: 'error', text: 'Failed to update setting.' })
            }
        } catch (error) {
            setMessage({ type: 'error', text: 'An error occurred.' })
        } finally {
            setSaving(null)
            // Clear message after 3 seconds
            setTimeout(() => setMessage(null), 3000)
        }
    }

    if (loading) {
        return <div className="p-8 text-center text-zinc-500">Loading settings...</div>
    }

    return (
        <div className="max-w-4xl mx-auto space-y-8 p-4">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-white">System Settings</h2>
                    <p className="text-zinc-400">Configure environment variables and system behavior</p>
                </div>
                {message && (
                    <div className={`px-4 py-2 rounded-lg ${message.type === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                        }`}>
                        {message.text}
                    </div>
                )}
            </div>

            {settings.map((category, idx) => (
                <div key={idx} className="glass rounded-xl p-6 space-y-6">
                    <h3 className="text-xl font-semibold text-white border-b border-white/10 pb-2">
                        {category.category}
                    </h3>

                    <div className="grid gap-6">
                        {category.settings.map((setting) => {
                            // Use fetched models if available for AI Model setting
                            const options = (setting.key === 'AI_MODEL_NAME' && fetchedModels.length > 0)
                                ? fetchedModels
                                : setting.options

                            return (
                                <div key={setting.key} className="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
                                    <div>
                                        <label className="block text-sm font-medium text-zinc-200 mb-1">
                                            {setting.label}
                                        </label>
                                        <p className="text-xs text-zinc-500">{setting.description}</p>
                                        <code className="text-[10px] text-zinc-600 mt-1 block">{setting.key}</code>
                                    </div>

                                    <div className="md:col-span-2 flex gap-2">
                                        {setting.type === 'select' ? (
                                            <select
                                                className="flex-1 bg-surface-light border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary"
                                                defaultValue={setting.value}
                                                onChange={(e) => handleSave(setting.key, e.target.value)}
                                                disabled={saving === setting.key}
                                            >
                                                {options?.map(opt => (
                                                    <option key={opt} value={opt}>{opt}</option>
                                                ))}
                                            </select>
                                        ) : (
                                            <input
                                                type={setting.type}
                                                className="flex-1 bg-surface-light border border-white/10 rounded-lg px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                                                defaultValue={setting.value}
                                                min={setting.min}
                                                max={setting.max}
                                                step={setting.step}
                                                onBlur={(e) => {
                                                    if (e.target.value !== String(setting.value)) {
                                                        handleSave(setting.key, e.target.value)
                                                    }
                                                }}
                                                disabled={saving === setting.key}
                                            />
                                        )}

                                        {saving === setting.key && (
                                            <div className="flex items-center justify-center px-3">
                                                <RefreshCw className="w-4 h-4 text-zinc-400 animate-spin" />
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>
            ))}

            <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/20">
                <div className="flex gap-3">
                    <Server className="w-5 h-5 text-blue-400 flex-shrink-0" />
                    <div>
                        <h4 className="font-medium text-blue-400">System Logs</h4>
                        <p className="text-sm text-blue-200/70 mt-1">
                            Backend logs are being written to <code>backend/logs/app.log</code>.
                            Check this file to debug C engine loading or AI errors.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    )
}
