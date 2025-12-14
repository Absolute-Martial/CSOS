# DOKPLOY DEPLOYMENT GUIDE

## Overview

This project deploys as **3 individual services** on Dokploy:
1. PostgreSQL Database
2. FastAPI Backend
3. Next.js Frontend

---

## Step 1: Create PostgreSQL Database

1. In Dokploy, go to **Add Service** → **Database** → **PostgreSQL**
2. Configure:
   - **Name**: `engineering-os-db`
   - **Database**: `engineering_os`
   - **Username**: `postgres`
   - **Password**: (generate secure password)
3. After creation, copy the **internal connection URL**

### Initialize Schema
Connect to the database and run the contents of `database/init.sql`

---

## Step 2: Deploy Backend

1. **Add Service** → **Application**
2. Connect your GitHub repo
3. Configure:

| Setting | Value |
|---------|-------|
| Branch | `main` |
| Build Path | `.` |
| Build Type | `Dockerfile` |
| Dockerfile Path | `deploy/Dockerfile.backend` |
| Port | `8000` |

### Environment Variables
```
DATABASE_URL=postgresql://postgres:PASSWORD@engineering-os-db.internal:5432/engineering_os
COPILOT_API_URL=http://localhost:4141
UPLOAD_DIR=/app/uploads
ENGINE_PATH=/app/engine/scheduler
```

### Domain
- Set up a domain like `api.yourdomain.com`

---

## Step 3: Deploy Frontend

1. **Add Service** → **Application**
2. Connect your GitHub repo
3. Configure:

| Setting | Value |
|---------|-------|
| Branch | `main` |
| Build Path | `frontend` |
| Build Type | `Nixpacks` |
| Port | `3000` |

### Environment Variables
```
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

### Domain
- Set up a domain like `app.yourdomain.com`

---

## Step 4: Configure Webhooks (Optional)

For auto-deploy on push:
1. Go to each service → **Deployments** → **Webhooks**
2. Copy the webhook URL
3. Add to GitHub repo → **Settings** → **Webhooks**

---

## Verification

1. Check backend health: `https://api.yourdomain.com/health`
2. Open frontend: `https://app.yourdomain.com`
3. Test AI chat (requires local copilot-api)

---

## Notes

- **copilot-api** must run locally (requires GitHub OAuth)
- Backend will work without AI, falling back gracefully
- Database backups: Use Dokploy's built-in backup feature
