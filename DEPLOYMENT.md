# Deployment Guide

This guide walks you through deploying the HarvyAI Data Room to production using **Render** (backend + database) and **Vercel** (frontend).

## Prerequisites

- GitHub account (connected to both Render and Vercel)
- Google Cloud Console project with OAuth 2.0 credentials
- Code pushed to a GitHub repository

---

## Part 1: Deploy Backend to Render

### Step 1: Create OAuth Credentials for Production

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create new OAuth 2.0 Client ID (or edit existing):
   - **Application type**: Web application
   - **Authorized redirect URIs**: Add your future Render URL:
     ```
     https://harvyai-dataroom-api.onrender.com/auth/google/callback
     ```
     *(Replace with your actual Render service name)*
3. Save the **Client ID** and **Client Secret**

### Step 2: Deploy to Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New"** → **"Blueprint"**
3. Connect your GitHub repository
4. Render will detect `render.yaml` automatically
5. Click **"Apply"**

### Step 3: Configure Environment Variables

After the services are created, go to the **API service** settings and set:

| Variable | Value | Notes |
|----------|-------|-------|
| `GOOGLE_CLIENT_ID` | `your-client-id.apps.googleusercontent.com` | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | `GOCSPX-xxx...` | From Google Cloud Console |
| `GOOGLE_REDIRECT_URI` | `https://your-api.onrender.com/auth/google/callback` | Must match OAuth config |
| `WEB_BASE_URL` | `https://your-app.vercel.app` | Your Vercel URL (add after Step 4) |

**Note:** `DATABASE_URL`, `SECRET_KEY`, and other vars are auto-configured by `render.yaml`.

### Step 4: Verify Backend is Running

Visit: `https://your-api.onrender.com/healthz`

You should see: `{"status":"ok"}`

---

## Part 2: Deploy Frontend to Vercel

### Step 1: Deploy to Vercel

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click **"Add New"** → **"Project"**
3. Import your GitHub repository
4. Configure project:
   - **Framework Preset**: Next.js
   - **Root Directory**: `apps/web`
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `.next` (default)

### Step 2: Set Environment Variables

In Vercel project settings → **Environment Variables**, add:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_BASE_URL` | `https://your-api.onrender.com` |

### Step 3: Deploy

Click **"Deploy"**

Vercel will build and deploy your app. You'll get a URL like:
```
https://your-app.vercel.app
```

### Step 4: Update Backend CORS

Go back to **Render** → API service → Environment Variables:

Update `WEB_BASE_URL` to your Vercel URL:
```
WEB_BASE_URL=https://your-app.vercel.app
```

Click **"Save Changes"** (this will redeploy the API)

---

## Part 3: Update Google OAuth Redirect URI

1. Go back to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Edit your OAuth 2.0 Client
3. Confirm **Authorized redirect URIs** includes:
   ```
   https://your-api.onrender.com/auth/google/callback
   ```
4. Add your **production frontend domain** to **Authorized JavaScript origins**:
   ```
   https://your-app.vercel.app
   ```

---

## Testing the Deployment

1. Visit your Vercel URL: `https://your-app.vercel.app`
2. You should see the "Demo Room" (public, seeded data)
3. Click "Sign in with Google"
4. Authorize the app
5. Create your own room and import files

---

## Troubleshooting

### CORS Errors
- Ensure `WEB_BASE_URL` in Render matches your Vercel URL exactly
- Check browser console for specific error messages

### OAuth Errors
- Verify `GOOGLE_REDIRECT_URI` matches Google Cloud Console exactly
- Ensure "Testing" mode in Google Cloud Console has you added as a test user
  - OR publish the app to "Production" mode

### Database Connection Issues
- Check Render logs: Dashboard → API service → Logs
- Verify `DATABASE_URL` is set correctly (auto-configured via `render.yaml`)

### Files Not Persisting
- Render free tier uses ephemeral storage (`/tmp/`)
- Files uploaded will be lost on service restart
- For production persistence, implement S3/GCS storage (see `apps/api/app/storage.py`)

---

## Production Checklist

- [ ] Google OAuth credentials configured for production URLs
- [ ] Render backend deployed and healthy
- [ ] Vercel frontend deployed and loading
- [ ] CORS configured correctly (`WEB_BASE_URL`)
- [ ] Demo room visible when logged out
- [ ] Sign-in flow works end-to-end
- [ ] File import from Google Drive works
- [ ] Room creation and member management works

---

## Cost

Both services offer **free tiers**:
- **Render**: Free tier includes PostgreSQL + 1 web service
- **Vercel**: Free tier includes unlimited Next.js deployments

**Note:** Render free services sleep after 15 minutes of inactivity. First request after sleep takes ~30 seconds to wake up.

---

## Next Steps (Optional)

- **Custom Domain**: Configure in Vercel/Render settings
- **Persistent Storage**: Implement S3/GCS backend (see `ARCHITECTURE_DECISIONS.md`)
- **Monitoring**: Add Sentry or LogRocket for error tracking
- **CI/CD**: Auto-deploy on git push (already works with Render/Vercel GitHub integration)

