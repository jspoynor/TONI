# Toni Chatbot Frontend

A Claude-like chat interface for "Toni," built frontend-only against a mock reply
service. Every product decision below was chosen so a real backend can be dropped in
later behind a single swappable seam, without reworking the UI.

## Specs

### Layout & sidebar
- Sidebar + main chat panel layout. On narrow viewports the sidebar collapses into an
  off-canvas drawer opened by a hamburger toggle. Reason: matches Claude's own
  responsive pattern without inventing a new one.
- Sidebar, top to bottom: "Toni" wordmark header (no icon/logo beside it) → "New Chat"
  button → scrollable list of past conversations → a static, non-interactive
  placeholder user/settings row pinned at the bottom (avatar + name only, no click
  behavior). Reason: full Claude-parity chrome without building account/settings
  features that have nothing to back them yet.

### Visual system
- Dark theme only — gray base, lavender accent. Reason: keeps scope tight; the
  existing scaffold's dark-mode accent (`#c084fc`) already reads as lavender.
- Cormorant Garamond for headers, branding, and UI chrome; system-ui sans-serif stack
  for message body text and dense UI. Reason: keeps Cormorant as "the main font" for
  identity while keeping actual conversations easy to read.
- Plain CSS using custom properties and native nesting, no framework. Reason: matches
  what's already scaffolded in `index.css`/`App.css`; zero new styling dependencies.
- `lucide-react` for all functional icons (new chat, send, attach, mobile menu, etc.).
  No icon or logo is placed next to the "Toni" wordmark itself.

### Chat behavior
- Single model — no model selector in v1.
- Messages render Markdown, including fenced code blocks.
- The attachment button accepts any file type. Pending attachments show as removable
  chips above the input (thumbnail for images, filename otherwise) and are passed to
  the send call as `{name, type, size, file}` descriptors.
- No per-message actions (copy/edit/regenerate) and no stop-generating button in v1.
- No backend exists yet: sending a message simulates a streamed reply through the same
  seam a real backend will use. The placeholder text explicitly says no backend is
  connected, so the app's real state is obvious during development.

### Backend integration seam
- One swappable async service module exposes the send operation as an async generator
  (`AsyncIterable<string>` of text chunks). The mock implementation satisfies this
  contract now; a real fetch/SSE implementation can replace it later without changing
  any caller.

### Conversations & persistence
- Conversations and their messages persist to `localStorage`.
- A conversation's sidebar title is auto-derived from the first few words of the
  user's first message, matching Claude's own convention.
- Clicking "New Chat" does not create a sidebar entry until the first message is
  actually sent — avoids accumulating empty conversation clutter.
- No rename or delete in v1 — create and switch only.

### Tooling
- Convert the project from plain `.jsx` to TypeScript (`.tsx`/`.ts`), adding a
  `tsconfig.json`. `@types/react`/`@types/react-dom` are already installed as unused
  devDependencies, and TypeScript was chosen now rather than deferred.
- The existing Vite demo scaffold (the counter/demo markup in `App.jsx`, the hero/
  react/vite assets, the vite-scaffold `icons.svg`) is replaced by the real Toni UI.

## Data model

Frontend-only for now (backed by `localStorage`), shaped so it maps cleanly onto a
future backend response.

```ts
interface Attachment {
  name: string
  type: string
  size: number
  file: File
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  attachments?: Attachment[]
  createdAt: number
}

interface Conversation {
  id: string
  title: string // derived from the first user message
  messages: ChatMessage[]
  createdAt: number
  updatedAt: number
}
```

Send service seam:

```ts
function sendMessage(
  messages: ChatMessage[],
  attachments: Attachment[]
): AsyncIterable<string>
```

## Implementation tasks

1. **Project setup** — add TypeScript + `tsconfig.json`, rename existing files to
   `.tsx`/`.ts`, add the `lucide-react` dependency, remove the Vite demo scaffold
   content (demo markup, hero/react/vite logos, vite-scaffold `icons.svg`), and load
   Cormorant Garamond (Google Fonts) into `index.css`.
2. **Design tokens** — rewrite `index.css` custom properties for the dark-only
   gray/lavender palette; define `--heading` (Cormorant Garamond) and `--sans`
   (system-ui) font vars; remove the light-mode media query block.
3. **Data layer** — define the `Attachment`/`ChatMessage`/`Conversation` types; build a
   `localStorage`-backed conversation store (create, list, get, append message, derive
   title from the first message).
4. **Mock backend seam** — implement `sendMessage()` as an async generator yielding a
   "no backend connected" placeholder message in simulated streamed chunks.
5. **Sidebar component** — "Toni" header (no icon), New Chat button, conversation list
   (reads from the store, click to switch, active-state styling), and the static
   placeholder user row pinned at the bottom.
6. **Mobile responsive shell** — off-canvas drawer behavior for the sidebar, with a
   hamburger toggle (lucide-react `Menu` icon) shown below a breakpoint.
7. **Main panel — empty state** — centered greeting ("What can I help you with?") shown
   when the active conversation has no messages yet.
8. **Main panel — message list** — render the `ChatMessage` list with Markdown and
   code-block support, with distinct user vs. assistant styling.
9. **Input area** — text input, attach-file button (lucide-react), a removable
   pending-attachment chip row (thumbnail for images), and a send button. Wire submit
   to append the user message, create/persist the conversation on first send, and
   stream the mock assistant reply into the message list.
10. **Wire it end-to-end** — new conversation → first message sent → conversation
    appears in the sidebar with a derived title → switching conversations loads the
    right message list → reloading the page preserves state via `localStorage`.

## Out of scope (deliberately)

- Light theme / theme toggle — dark only for v1.
- Model selector — single model only.
- Per-message actions (copy, edit, regenerate).
- Stop-generating button.
- Conversation rename/delete.
- Any real backend call, auth, or functional user/settings panel — placeholder UI
  only.
- Icon or logo mark next to the "Toni" wordmark.
