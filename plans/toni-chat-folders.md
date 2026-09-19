# Toni Sidebar Folders

Replaces Toni's "New Chat" button with a "New Folder" button and groups her chats into
collapsible folders. Anne's page is untouched. Today Toni and Anne share one `App.tsx` /
`Sidebar.tsx` component tree, parameterized entirely by `ChatPageConfig`, with a single flat
`<ul>` of conversations and lazy chat creation (a chat isn't written to `localStorage` until
its first message is sent). This feature keeps that shared-tree architecture and lazy-creation
behavior, and extends both to understand folders — gated so only Toni's config turns it on.

## Specs

### Toni-only scoping
- Add `foldersEnabled?: boolean` to `ChatPageConfig`. `VcChat.tsx` (Toni) sets it `true`;
  `CompanyChat.tsx` (Anne) leaves it unset/`false`. `App.tsx` and `Sidebar.tsx` branch their
  rendering on this flag rather than forking into separate components. Reason: least
  duplication, and matches the existing config-driven pattern already used for accent colors,
  storage keys, and copy — Anne's render path is unaffected when the flag is off.

### Top-level button
- The sidebar's top button becomes "New Folder" (replacing "New Chat") whenever
  `foldersEnabled` is true, in the same position/styling slot the old button occupied. It opens
  an inline naming input (see below) rather than immediately creating anything.

### Folder creation & naming
- Naming uses an inline input row, not `window.prompt()` or a modal — matches the app's plain
  CSS, no-modal aesthetic. Clicking "New Folder" inserts a temporary editable row at the top of
  the folder list (folders sort newest-created-first); Enter or blur-with-text commits, Escape
  or blur-with-empty-text cancels and no folder is created.
- Duplicate folder names are allowed (folders are distinguished by internal `id`, not name
  uniqueness) — no validation needed beyond "non-empty after trim."
- **Every** folder creation (not just the first ever) immediately: (1) creates and persists the
  `Folder` record, (2) opens a draft chat scoped to that folder (mirrors today's "New Chat"
  behavior: `activeConversationId` goes to `null`, main panel shows `EmptyState`), tracked
  against the new folder's id so the first sent message lands in it. The draft chat itself is
  *not* written to `localStorage`/the sidebar until the user sends its first message — this is
  the existing lazy-creation rule, just now also stamping `folderId` onto the created
  `Conversation`.

### Folder contents & the "new chat" button
- Each folder renders: header (name + collapse chevron) → its chats, sorted the same way the
  existing flat list is (most-recently-updated first) → a "new chat" button underneath the
  chat list. Clicking that button behaves exactly like the top-level "New Chat" button used to
  (opens a draft scoped to that folder), just addressable per-folder now.
- Starting a new draft (via "New Folder" or any folder's "new chat" button) while another
  unsent draft is already pending elsewhere silently replaces it — same single-active-draft
  behavior the app already has today; no confirmation prompt.

### Collapsing
- Folders are collapsible via the header chevron. Collapsed state is a `collapsed: boolean`
  field persisted on the `Folder` record itself, so it survives page reloads. New folders
  default to `collapsed: false` (expanded).

### Active state
- The active folder (containing the active conversation or active draft) gets the same accent
  highlight style the active conversation item already uses, applied to the folder header too,
  so it's visible even when that folder is collapsed.

### Legacy conversation migration
- Toni conversations that exist in `localStorage` from before this feature ships have no
  `folderId`. On first load after upgrade, if any such folderless conversations exist, run a
  one-time migration: create a `Folder` named **"General"** and set `folderId` on every
  folderless conversation to point at it. This is a persisted write (both the new `Folder`
  record and the updated `Conversation` records are saved back to `localStorage`), not a
  view-time computation — so afterward `folderId` always reflects true state and no
  recompute-on-render join is needed.
- If a Toni user has zero conversations (or all their conversations already have a `folderId`,
  i.e. migration already ran), no "General" folder is created. A brand-new Toni user sees zero
  folders and just the "New Folder" button.
- The "General" folder looks exactly like any user-created folder — no badge, icon, or special
  styling marking it as auto-created.

### Explicitly out of scope
- No renaming or deleting folders.
- No renaming, deleting, or moving chats between folders.
- No manual reordering of folders or chats — folders sort newest-created-first; chats within a
  folder sort most-recently-updated-first (same convention the flat list uses today).
- No nested folders (single flat level only).
- No changes to Anne's page, `Sidebar.tsx`'s Anne-rendering branch, or the `anne:conversations`
  data.

## Data model

```ts
interface Folder {
  id: string
  name: string
  createdAt: number
  collapsed: boolean
}
```

Stored under a new `localStorage` key, `toni:folders` (parallel to the existing
`toni:conversations` key), read/written via new functions in `conversationStore.ts` following
its existing idiom (plain exported functions taking the storage key as first arg, try/catch
JSON read/write).

`Conversation` gains one new optional field:

```ts
interface Conversation {
  id: string
  title: string
  messages: ChatMessage[]
  createdAt: number
  updatedAt: number
  folderId?: string // undefined for Anne's conversations, and for any not-yet-migrated Toni chat mid-migration
}
```

`ChatPageConfig` gains:

```ts
interface ChatPageConfig {
  // ...existing fields
  foldersEnabled?: boolean
}
```

## Implementation tasks

1. **Extend types** — add `Folder` interface, `folderId?: string` on `Conversation`,
   `foldersEnabled?: boolean` on `ChatPageConfig` in `src/types.ts`.
2. **Folder storage functions** — in `conversationStore.ts`, add `listFolders`,
   `createFolder(storageKey, name)`, `setFolderCollapsed(storageKey, folderId, collapsed)`,
   using a derived key (e.g. `` `${storageKey.split(':')[0]}:folders` `` or a second
   `folderStorageKey` field on config — pick whichever keeps the existing `storageKey` param
   pattern simplest) and the same read/write try/catch idiom as conversations.
3. **Legacy migration function** — a `migrateFolderlessConversations(storageKey)` run once on
   `App` mount (only when `config.foldersEnabled` is true): finds conversations with no
   `folderId`, and if any exist, creates the "General" `Folder` and persists `folderId` onto
   each of them.
4. **Thread folder state through `App.tsx`** — new state for `folders`, and a way to track
   which folder a pending (unsent) draft belongs to (e.g. `pendingFolderId` alongside the
   existing `activeConversationId === null` draft state). `handleSend` stamps `folderId` onto
   the conversation it creates using `pendingFolderId`. Call `migrateFolderlessConversations`
   once on mount when folders are enabled, then load `folders`/`conversations` as today.
5. **Sidebar folder UI** — in `Sidebar.tsx`, when `foldersEnabled`, replace the flat
   `<ul>`/"New Chat" button with: "New Folder" button (opens inline naming input, inserted at
   top of folder list) → per-folder sections (collapse chevron + name header, nested `<ul>` of
   that folder's chats, "new chat" button under the list). Keep the existing flat rendering
   path intact and unchanged for Anne (`foldersEnabled` falsy).
6. **Styling** — extend `Sidebar.css` with folder header, chevron, collapse transition, nested
   chat list indentation, and active-folder accent highlight (reusing the existing
   `--accent`/`--accent-border` tokens already threaded per-persona).
7. **Verify end-to-end** — fresh Toni load with legacy conversations migrates them into
   "General"; fresh Toni load with zero conversations shows no folders; creating a folder
   prompts for a name, opens a draft, and the chat appears under that folder only after the
   first message is sent; collapse state survives a reload; Anne's page (`/submit-statements`)
   is visually and behaviorally identical to before this change.

## Out of scope (deliberately)

- Renaming, deleting, or reordering folders.
- Renaming, deleting, or moving chats between folders.
- Nested folders.
- Any change to Anne's page or data.
- Any visual distinction for the auto-created "General" folder.
- A confirmation prompt when switching away from an unsent draft.
