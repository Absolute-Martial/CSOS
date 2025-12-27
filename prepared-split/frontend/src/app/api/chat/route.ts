import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
    try {
        const body = await request.json()
        const { message, thread_id } = body

        // Forward request to Python backend with LangGraph
        const response = await fetch(`${BACKEND_URL}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message,
                thread_id: thread_id || 'default',
            }),
        })

        if (!response.ok) {
            const error = await response.text()
            return NextResponse.json(
                { error: 'Backend error', details: error },
                { status: response.status }
            )
        }

        const data = await response.json()
        return NextResponse.json(data)
    } catch (error) {
        console.error('Chat API error:', error)
        return NextResponse.json(
            { error: 'Failed to connect to backend' },
            { status: 500 }
        )
    }
}

// Streaming endpoint for SSE
export async function GET(request: NextRequest) {
    const searchParams = request.nextUrl.searchParams
    const message = searchParams.get('message')
    const thread_id = searchParams.get('thread_id') || 'default'

    if (!message) {
        return NextResponse.json({ error: 'Message required' }, { status: 400 })
    }

    try {
        const response = await fetch(`${BACKEND_URL}/api/chat/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message, thread_id }),
        })

        if (!response.ok || !response.body) {
            return NextResponse.json({ error: 'Streaming not available' }, { status: 500 })
        }

        // Return the stream from backend
        return new Response(response.body, {
            headers: {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            },
        })
    } catch (error) {
        console.error('Stream error:', error)
        return NextResponse.json({ error: 'Stream failed' }, { status: 500 })
    }
}
