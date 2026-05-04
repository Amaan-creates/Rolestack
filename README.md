# Rolestack — AI Job Search OS

> The only job search platform with live multi-source job search, real-time UK visa sponsor verification, and a dual AI assistant built in.

**Live:** [amaan-creates.github.io/Rolestack](https://amaan-creates.github.io/Rolestack)

---

## What is Rolestack?

Rolestack is a single-file web application that replaces the 12+ tools most job seekers use during an active search. It combines a live job aggregator, a Kanban pipeline, an AI assistant, a CV studio, a connections CRM, and the complete UK Home Office sponsor register — all in one interface.

Built by [Amaan Aslam](https://linkedin.com/in/amaan-aslam-078b33176) — enterprise sales professional, LSE MSc AI (Distinction), Swizio SaaS founder (exited 2024).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Rolestack v5                          │
│                    Single HTML file (197KB)                  │
│                  GitHub Pages (free hosting)                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐
│   Supabase   │  │  Job APIs    │  │   AI Providers       │
│              │  │              │  │                      │
│ • Auth       │  │ • Adzuna     │  │ BYOK (free):         │
│ • Roles DB   │  │ • Reed       │  │ • Claude (Anthropic) │
│ • Connections│  │ • Himalayas  │  │ • ChatGPT (OpenAI)   │
│ • Interviews │  │ • Arbeitnow  │  │ • Gemini (Google)    │
│ • Profiles   │  │ • Remotive   │  │                      │
│ • uk_sponsors│  │              │  │ Hosted (paid):       │
│   (100k rows)│  │              │  │ • rs-chat Edge Fn    │
└──────────────┘  └──────────────┘  │   (Anthropic API)    │
                                    └──────────────────────┘
```

---

## Feature Map

### 1. Live Multi-Source Job Search
Search across 5 job boards simultaneously — no tab switching.

| Source | Coverage | Auth |
|--------|----------|------|
| Adzuna | UK + UAE, 10M+ listings | API key (free) |
| Reed | UK, 300k+ listings | API key (free) |
| Himalayas | Remote-first, global | No key required |
| Arbeitnow | Europe/UK, ATS-powered | No key required |
| Remotive | Remote tech + sales | No key required |

Results are deduplicated, sorted, and filtered. UK Skilled Worker sponsor status is checked live against the Home Office register on every result card.

### 2. UK Sponsor Register
- 100,000+ licensed UK sponsors loaded into Supabase
- Source: UK Home Office register (updated daily via Edge Function + pg_cron)
- Checked on every job card, pipeline card, and search result
- Searchable directory with filter by company, city, and route type

```
Gov.uk CSV → sync-uk-sponsors Edge Function → uk_sponsors table
                      ↑
              pg_cron (3am UTC daily)
```

### 3. Dual AI Assistant — Role + Stack

Two modes, one chat panel:

- **Role** — job search mode. Finds roles, scores fit, suggests companies, maps market intelligence
- **Stack** — execution mode. Drafts outreach messages, tailors CVs, writes cover letters, runs interview prep

**AI routing:**
```
User message
     │
     ├── BYOK key present? → Direct to Anthropic/OpenAI/Gemini API
     │
     └── No key → Credits > 0? → rs-chat Edge Function (hosted key, server-side)
                                        │
                                        └── Credits = 0 → Prompt to buy or add key
```

### 4. Kanban Pipeline

Stages: `Wishlist → Applied → Active → Awaiting Reply → Interviewing → Offered → Rejected`

- Drag and drop between stages
- Stale role detection (7-day amber, 14-day red warnings)
- Per-market boards (UK + Dubai default, custom markets addable)
- Right panel: AI ghostwriter, interview prep, company research brief

### 5. CV Studio

```
Job Description + Your CV
         │
         ▼ Claude AI
         │
         ├── ATS keyword match score
         ├── Formatted CV preview (Times New Roman, configurable)
         ├── Missing keywords highlighted
         └── Download as DOCX or PDF
```

### 6. Connections CRM

- 5-step LinkedIn outreach sequence tracker
- Status: Sent → Connected → Replied → Met → Converted
- Extract contacts directly from pipeline notes
- Filter and search across all connections

### 7. Billing

| Tier | Price | Credits | Route |
|------|-------|---------|-------|
| BYOK | Free | Unlimited | Your own API key |
| Starter | £1 | 50 | Hosted Anthropic key |
| Pro | £4.99 | 500 | Hosted Anthropic key |
| Power | £9.99 | 1,200 | Hosted Anthropic key |

1 credit = 1 AI action. No subscription. Credits never expire.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vanilla HTML/CSS/JS (single file) |
| Hosting | GitHub Pages |
| Database | Supabase (PostgreSQL) |
| Auth | Supabase Auth |
| Edge Functions | Supabase Edge Functions (Deno) |
| AI | Anthropic Claude (primary), OpenAI, Gemini |
| Job APIs | Adzuna, Reed, Himalayas, Arbeitnow, Remotive |
| Payments | Stripe (UK, individual) |
| Scheduling | pg_cron (daily sponsor sync) |
| CV Export | docx.js + html2pdf.js |

---

## Supabase Schema

```sql
-- User profiles with billing state
profiles (id, email, anthropic_key, profile_text, tier, credits, markets, custom_boards)

-- Job pipeline
roles (id, user_id, co, role, market, status, role_date, notes, salary)

-- Connections CRM
connections (id, user_id, name, co, title, status, note, seq)

-- UK sponsor register (100k rows)
uk_sponsors (id, organisation_name, town, county, type_and_rating, route)

-- Sync audit log
sync_log (id, table_name, row_count, synced_at)
```

---

## Edge Functions

### `sync-uk-sponsors`
- Triggered: daily at 3am UTC via pg_cron
- Downloads latest UK Home Office sponsor CSV
- Clears and reloads `uk_sponsors` table
- Logs sync to `sync_log`
- No JWT required (internal trigger)

### `rs-chat`
- Triggered: by paid users with hosted credits
- Verifies user JWT
- Checks and deducts credits from `profiles`
- Proxies request to Anthropic API (key never exposed client-side)
- Returns reply + remaining credit count

---

## Local Development

No build step required. It is a single HTML file.

```bash
git clone https://github.com/Amaan-creates/Rolestack.git
cd Rolestack
open index.html
```

To run with live Supabase data, just open `index.html` in a browser. All Supabase calls are made client-side using the public anon key.

---

## Deployment

```bash
# Any change to index.html on main branch
# auto-deploys to GitHub Pages

git add index.html
git commit -m "your message"
git push origin main

# Live at: https://amaan-creates.github.io/Rolestack
# Deploy time: ~60 seconds
```

---

## Roadmap

- [ ] Stripe webhook → auto-credit on payment (currently manual SQL)
- [ ] Reed API CORS proxy via Edge Function
- [ ] Webhook for daily sync notifications
- [ ] Mobile-responsive layout
- [ ] Innovator Founder Visa business case (pending 100+ active users)

---

## About

Built by **Amaan Aslam** during an active job search in 2026, as both a tool for the search and a demonstration of what I build.

- [LinkedIn](https://linkedin.com/in/amaan-aslam-078b33176)
- [GTM OS v3](https://amaanaslam.lovable.app) — companion sales operating system
- [Email](mailto:amaanaslam1999@gmail.com)

