import { NextResponse } from 'next/server'

type CopilotKitProxyError = {
  error: string
  details?: unknown
}

function getBackendUrl(): string {
  // Prefer INTERNAL_API_URL for server-side (Docker network), fallback to public/local.
  return (
    process.env.INTERNAL_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    'http://localhost:8000'
  )
}

export async function POST(req: Request) {
  const backendBaseUrl = getBackendUrl().replace(/\/+$/, '')
  const targetUrl = `${backendBaseUrl}/copilotkit`

  try {
    const contentType = req.headers.get('content-type') || ''

    // CopilotKit typically sends JSON, but we proxy whatever bytes we receive.
    const body = await req.arrayBuffer()

    const upstreamRes = await fetch(targetUrl, {
      method: 'POST',
      // Forward content-type and auth headers if present.
      headers: {
        ...(contentType ? { 'content-type': contentType } : {}),
        ...(req.headers.get('authorization')
          ? { authorization: req.headers.get('authorization') as string }
          : {}),
      },
      body,
      // Prevent Next.js from caching API proxy requests.
      cache: 'no-store',
    })

    const upstreamContentType =
      upstreamRes.headers.get('content-type') || 'application/json'

    // Return upstream response as-is (status + body), preserving content-type.
    const responseBody = await upstreamRes.arrayBuffer()

    return new NextResponse(responseBody, {
      status: upstreamRes.status,
      headers: {
        'content-type': upstreamContentType,
      },
    })
  } catch (err) {
    const payload: CopilotKitProxyError = {
      error: 'Failed to proxy CopilotKit request to backend',
      details: err instanceof Error ? err.message : err,
    }

    return NextResponse.json(payload, { status: 502 })
  }
}
