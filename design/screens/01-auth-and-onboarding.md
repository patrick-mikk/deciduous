# Screens — Auth & Onboarding

## Landing (`/`)
Editorial treatment (the one marketing page). Hero uses `serif-title`/`display`.
```
┌──────────────────────────────────────────────────────────┐
│  Deciduous            Features  ·  Sign in  ▸   │
│                                                          │
│   Plan your whole degree —            [ hero visual:     │
│   requirements, courses, and          a faint degree-    │
│   a conflict-free timetable.          audit ledger +     │
│   (Source Serif 4, large)             breadth spectrum)  │
│                                                          │
│   [ Get started ]  [ See how it works ]                  │
│   Unofficial · not affiliated with the University of T.  │
├──────────────────────────────────────────────────────────┤
│  3 value props (StatTile-ish): Import in seconds ·        │
│  See what's left · Optimize your timetable                │
└──────────────────────────────────────────────────────────┘
```
Components: TopBar (public), Button, serif hero, feature cards. Single hero only.

## Sign in (`/signin`) · Sign up (`/signup`) · Reset (`/reset-password`)
Centered **AuthCard** on a calm blue-tinted canvas.
```
            ┌──────────────────────────────┐
            │      Deciduous      │
            │   Sign in to your planner     │  (h2)
            │                              │
            │  Email    [______________]   │
            │  Password [__________] 👁     │
            │           Forgot password?    │
            │        [   Sign in   ]        │  (primary, fullWidth)
            │  ─────────  or  ─────────      │
            │  New here?  Create an account │
            └──────────────────────────────┘
```
- Sign up adds: PasswordField + StrengthMeter, terms checkbox, and a one-line note
  that academic data is encrypted.
- Reset: request screen (email) → confirmation → set-new-password (token) with a
  **Callout** warning that reset needs the recovery code (data re-encryption).
- Errors inline (Input error state); rate-limit message after repeated failures.

## Onboarding wizard (`/onboarding`)
Full-width **Stepper**, 3 steps, single card body.

**Step 1 — Import your record** (ImportPanel)
```
 ①Import ──②Programs ──③Term
┌───────────────────────────────────────────────┐
│  Bring in your record                          │
│  [ Upload PDF ] [ Bookmarklet ] [ Start blank ]│  ← tabs
│  ┌ Dropzone ─────────────────────────────────┐ │
│  │  Drop your Degree Explorer PDF here        │ │
│  │  or browse.  We parse it locally & encrypt.│ │
│  └────────────────────────────────────────────┘ │
│  ⟳ Parsing… → ImportPreview:                    │
│    Programs found: [Major PUBLIC POLICY]…       │
│    Transcript: 25 courses · CGPA 2.70           │
│                        [ Looks right → Next ]   │
└───────────────────────────────────────────────┘
```
- Bookmarklet tab: numbered steps + "Copy bookmarklet" + a paste box for the
  `<degree-explorer-capture>…</degree-explorer-capture>` JSON, then ImportPreview.

**Step 2 — Confirm programs** — detected **ProgramCard**s (add/remove) + SearchTypeahead
to add more; POStCombinationValidator shows if the combo is valid.

**Step 3 — Set your term** — current session Select (e.g. Fall 2026), expected
graduation, then **[ Finish → Dashboard ]**.

Data: `POST /api/import/pdf` or `/api/import/capture` → StudentRecord (see 06);
`GET /api/programs?q=`; `POST /api/me/programs`.
```
