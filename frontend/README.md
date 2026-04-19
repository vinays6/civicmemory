# unbais — Frontend

React 18 + Vite + TypeScript + Tailwind CSS frontend for the unbais civic intelligence platform.

## Prerequisites

- Node.js 18+
- npm 9+

## Local development

```bash
cd frontend
npm install
npm run dev
```

App runs at `http://localhost:5173`.

## Production build

```bash
npm run build
```

Output goes to `frontend/dist/`. Serve any static file host from that folder.

---

## Deploy to Vercel (recommended)

1. Push the repo to GitHub (already done).
2. Go to [vercel.com](https://vercel.com) → **Add New Project** → import `civicmemory`.
3. Set the following in project settings:
   - **Framework Preset:** Vite
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. Click **Deploy**.

Vercel auto-deploys on every push to `main`.

---

## Deploy to Netlify

1. Go to [netlify.com](https://netlify.com) → **Add new site** → **Import from Git**.
2. Connect the `civicmemory` repo and set:
   - **Base directory:** `frontend`
   - **Build command:** `npm run build`
   - **Publish directory:** `frontend/dist`
3. Click **Deploy site**.

Add a `frontend/public/_redirects` file to handle client-side routing:

```
/*  /index.html  200
```

---

## Deploy to GitHub Pages

```bash
# Install gh-pages helper
npm install --save-dev gh-pages

# Add to frontend/package.json scripts:
# "deploy": "gh-pages -d dist"

npm run build
npm run deploy
```

Set GitHub Pages source to the `gh-pages` branch in repo Settings → Pages.

> **Note:** Set the `base` option in `vite.config.ts` to match your repo name:
> ```ts
> export default defineConfig({ base: '/civicmemory/', ... })
> ```

---

## Environment variables

No environment variables are required for the current mock-data build. When connecting to a live backend, create `frontend/.env.local`:

```
VITE_API_URL=https://your-api.example.com
```

Access in code via `import.meta.env.VITE_API_URL`.
