# /submit-statements Page (Company Chat)

A second, reskinned entry point into the same chat app for the product's other audience: a
portfolio company invited by its VC fund manager to talk to a bot ("Anne") and eventually
upload financial statements. Today it's a visual fork the user can view privately at
`/submit-statements`; the underlying App is made config-driven now precisely so this and the
existing VC page ("Toni," at `/`) can keep diverging cleanly later without duplicating the
component tree.

## Specs

### Routing & code sharing
- Add `react-router-dom` and wire `<BrowserRouter>` in `main.tsx` with two routes: `/` and
  `/submit-statements`. Reason: this is the real branch point future pages/links will need,
  not a throwaway copy.
- `App` becomes config-driven: it accepts a small config object (name, accent colors, storage
  key, empty-state greeting, mock reply text) and renders the existing shared component tree
  (`Sidebar`, `EmptyState`, `MessageList`, `InputArea`) unchanged, just parameterized.
- Two thin page wrapper components own each persona's config and render `<App config={...} />`:
  - `src/pages/VcChat.tsx` — today's "Toni" config, mounted at `/`.
  - `src/pages/CompanyChat.tsx` — new "Anne" config, mounted at `/submit-statements`.
- Any future behavioral divergence between the two audiences (e.g. real upload handling,
  restricted file types, a different backend) should be added as new config fields or
  conditional branches inside the shared tree — not by copy-pasting components.

### Visual & copy differences on /submit-statements
- Wordmark in the sidebar: "Anne" instead of "Toni".
- Input placeholder: "Message Anne…" instead of "Message Toni…".
- Empty-state greeting: "Upload your financial statements to get started" (VC page keeps
  "What can I help you with?").
- Mock assistant reply text: "No backend is connected yet — this is a simulated reply from
  Anne's mock response service. Once a real backend is wired up, you'll be able to upload
  financial statements and get real answers here."
- Browser tab title: set via `document.title` in each page wrapper on mount ("Anne" vs
  "Toni"), since one static `index.html` serves both routes.
- Accent color: pink `#f472b6` replaces lavender `#c084fc`, with matching
  `--accent-bg`/`--accent-border` tints derived from the same pink (mirroring how the existing
  lavender tokens are derived) — used for the send button, active sidebar item, and inline
  code highlighting exactly as the lavender accent is today.

### What stays identical
- Sidebar layout/behavior (New Chat button, conversation list, mobile drawer), Markdown
  rendering, the streamed mock-reply mechanism, and the attach-file button (still accepts any
  file type — no financial-statement-specific restriction yet).
- Fonts, spacing, dark theme, and every other design token besides the accent trio.

### Persistence
- Separate `localStorage` keys per page so conversations don't bleed between personas: keep
  `toni:conversations` for the VC page, add `anne:conversations` for `/submit-statements`.
  The storage key becomes part of each page's config and is passed into the conversation
  store functions (which currently hardcode the key).

## Data model

No changes to `ChatMessage`/`Conversation`/`Attachment` shapes. New shape for the App config:

```ts
interface ChatPageConfig {
  name: string // "Toni" | "Anne" — wordmark, placeholder, mock reply text
  storageKey: string // localStorage key for this page's conversations
  accent: string // e.g. "#c084fc" | "#f472b6"
  accentBg: string // rgba tint derived from accent
  accentBorder: string // rgba tint derived from accent
  emptyStateGreeting: string
  mockReplyText: string
}
```

`conversationStore.ts`'s functions (`listConversations`, `createConversation`,
`appendMessage`, etc.) take the storage key as a parameter instead of the hardcoded
`STORAGE_KEY` constant.

## Implementation tasks

1. **Add react-router-dom** — install the dependency; wrap the app in `<BrowserRouter>` in
   `main.tsx` with routes for `/` → `VcChat` and `/submit-statements` → `CompanyChat`.
2. **Parameterize the conversation store** — change `conversationStore.ts` to accept a storage
   key argument instead of the hardcoded `toni:conversations` constant.
3. **Make `App` config-driven** — add the `ChatPageConfig` prop; thread `name` into the
   `Sidebar` wordmark and `InputArea` placeholder; thread `storageKey` into the conversation
   store calls; thread `emptyStateGreeting` into `EmptyState`; thread `accent`/`accentBg`/
   `accentBorder` down to wherever the CSS custom properties are set (e.g. an inline style on
   the root element, or a small per-page CSS class) so the shared stylesheets pick up the
   right accent without duplicating them; set `document.title` from `name` in a `useEffect`.
4. **Update `sendMessage`** — accept the mock reply text (or the two pieces needed to build
   it) as a parameter instead of hardcoding "Toni's mock response service" text, so each
   page's config supplies its own copy.
5. **Build page wrappers** — `src/pages/VcChat.tsx` with today's Toni/lavender config, and
   `src/pages/CompanyChat.tsx` with the new Anne/pink/statements config; both just render
   `<App config={...} />`.
6. **Verify end-to-end** — `/` still behaves exactly as before (lavender, "Toni", existing
   `toni:conversations` data intact); `/submit-statements` shows the pink "Anne" branding,
   the statements-focused empty state and mock reply, and persists to its own
   `anne:conversations` key without affecting the VC page's conversations.

## Out of scope (deliberately)

- Any real financial-statement upload handling, file-type restrictions, or backend
  distinction between the two personas — the attach button stays generic on both pages.
- Auth, access control, or a real "fund manager sends this page to a company" flow — for now
  `/submit-statements` is reachable by anyone who navigates to it, for the user's own viewing.
- A light theme, model selector, or any other feature not already in scope for the base chat
  app (see `plans/frontend-outline.md`).
- Navigation UI linking the two pages together (e.g. a link from `/` to
  `/submit-statements`) — out of scope until the "fund manager creates a page to send"
  feature is actually built.
