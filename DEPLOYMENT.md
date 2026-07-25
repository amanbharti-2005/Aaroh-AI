# Deployment Guide — Aaroh AI

Backend runs on **Render** (already exists). Frontend runs on **Vercel** (new).
Do the steps in this order — a couple of settings depend on URLs you only get
after an earlier step.

---

## 0. Push the code

The Render backend auto-deploys from the GitHub repo, so nothing goes live
until the updated code is pushed. Push all current changes to the branch
Render is watching (usually `main`).

Config files already included in the repo for you:
- `vercel.json` — SPA routing for the frontend (so `/dashboard` etc. don't 404)
- `backend/.python-version` — pins Python 3.11 on Render

---

## 1. Backend → Render (redeploy the existing service)

**Service settings** (Render dashboard → your service → Settings):

| Setting          | Value                                                                 |
|------------------|-----------------------------------------------------------------------|
| Root Directory   | `backend`                                                             |
| Build Command    | `pip install -r requirements.txt && python -m app.core.rag.engineering_rag` |
| Start Command    | `uvicorn app.main:app --host 0.0.0.0 --port $PORT`                    |

> The `python -m app.core.rag.engineering_rag` part is **new and required** —
> it rebuilds the knowledge-base search index, which is not stored in git.
> Without it, the AI Mentor loses its general-engineering knowledge.

**Environment variables** (Render dashboard → Environment):

Already set from the previous deploy — leave them as-is:
- `DATABASE_URL` — the Neon Postgres URL
- `GROQ_API_KEY`
- `TAVILY_API_KEY`
- `FIREBASE_CREDENTIALS_JSON` — the full service-account JSON on one line

**Add one new variable** (you'll fill the value in Step 3):
- `FRONTEND_ORIGINS` = `https://<your-vercel-app>.vercel.app`

Then **Manual Deploy → Deploy latest commit**. When it's up, copy the service
URL (e.g. `https://gen-ai-and-agentic-ai.onrender.com`) — you need it in Step 2.

> **Heads-up on the free plan:** this backend loads `torch` +
> `sentence-transformers` + `chromadb`, which can exceed the 512 MB free-tier
> RAM and get killed. If the service crash-loops with "out of memory", upgrade
> to the Starter instance.

---

## 2. Frontend → Vercel (new project)

1. Vercel → **Add New → Project** → import the same GitHub repo.
2. Framework preset: **Vite** (auto-detected). Build command `npm run build`
   and output directory `dist` are auto-filled — leave them.
3. **Environment Variables** → add:
   - `VITE_API_BASE_URL` = the Render backend URL from Step 1
     (e.g. `https://gen-ai-and-agentic-ai.onrender.com`, no trailing slash)
4. **Deploy.** When it finishes, copy the Vercel URL
   (e.g. `https://aaroh-ai.vercel.app`).

> `VITE_API_BASE_URL` is read at **build time**, so if you change it later you
> must redeploy the frontend for it to take effect.

---

## 3. Connect the two (CORS) — don't skip this

The browser blocks the frontend from calling the backend unless the backend
explicitly allows the frontend's origin.

1. On **Render**, set `FRONTEND_ORIGINS` to the exact Vercel URL from Step 2
   (scheme + host, no trailing slash, no path). For multiple URLs, separate
   with commas.
2. **Redeploy the backend** so it picks up the new value.

---

## 4. Firebase — allow the new domain

Login/signup uses Firebase Auth. If sign-in fails on the live site with an
`auth/unauthorized-domain` error:

- Firebase Console → **Authentication → Settings → Authorized domains → Add
  domain** → add your `*.vercel.app` domain.

Harmless to add regardless; `localhost` is already there for local dev.

---

## 5. Verify it's live

- `https://<backend>/health` → `{"status":"ok"}`
- `https://<backend>/db-check` → `{"database":"connected"}`
- Open the Vercel URL, sign up / log in.
- Upload a public GitHub repo → check Health, Roadmap, Architecture, Chat.
- In the browser Network tab, confirm requests go to your Render URL and
  return `200`/`401` (not CORS errors).

---

## Notes / limitations

- **Uploaded-repo chat is not persistent on Render's free tier.** The per-repo
  search index lives on disk, which is wiped on each restart/redeploy. Fine for
  a demo (just re-upload), but don't expect it to survive a redeploy.
- **The database is already migrated.** The `repos.full_analysis` column was
  added directly to the shared Neon database, so production already has it.
- **Groq free tier is limited.** Chat uses `llama-3.3-70b-versatile`
  (100K tokens/day); the analysis agents use `llama-3.1-8b-instant`
  (500K tokens/day), with automatic fallback between them. Heavy use can still
  hit the daily cap.
