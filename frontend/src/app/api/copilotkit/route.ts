import {
  CopilotRuntime,
  OpenAIAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from '@copilotkit/runtime';
import OpenAI from 'openai';

// Use copilot-api as OpenAI-compatible endpoint
const COPILOT_API_URL = process.env.COPILOT_API_URL || 'http://localhost:4141/v1';

// Create OpenAI client pointing to copilot-api
const openai = new OpenAI({
  baseURL: COPILOT_API_URL,
  apiKey: 'dummy-key', // copilot-api doesn't require a real key
});

// Create the service adapter
const serviceAdapter = new OpenAIAdapter({ openai });

// Create CopilotRuntime with the adapter
const runtime = new CopilotRuntime();

export const POST = async (req: Request) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: '/api/copilotkit',
  });

  return handleRequest(req);
};
