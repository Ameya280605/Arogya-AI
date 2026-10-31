# Arogya AI — Frontend Application

This directory contains the Next.js web application for the Arogya AI clinical decision-support and healthcare intelligence research prototype.

> **Status:** Module 6 (Patient Intelligence) Complete.<br/>
> Implemented complete database-backed Patient Intelligence interface across all seven canonical phases: 6.1 Patient List (search, biological sex and cohort stratification, pagination, empty states), 6.2 Patient CRUD (schema-validated registration, profile viewing, and demographic editing), 6.3 Patient Profile (tabs for Overview, Encounters, Observations, Analysis Runs, and Longitudinal Timeline), 6.4 Encounters (creation, status lifecycle, cross-entity observation/analysis linkage), 6.5 Data Quality (completeness scoring and unit/physiological bound consistency checks), 6.6 API Integration (FastAPI REST endpoints and typed client), and 6.7 End-to-End Testing (138 automated frontend unit tests across 33 test suites, zero TypeScript errors, zero ESLint warnings, and verified production static build).



---

## 1. Environment & Prerequisites

* **Node.js:** Node.js `v20.x` LTS or higher (tested on Node.js `v24.18.0`).
* **Package Manager:** `npm` (tested on npm `11.16.0`) with committed `package-lock.json`.
* **Framework Stack:**
  * Next.js: `16.4.3` (App Router with Turbopack)
  * React: `19.3.0`
  * TypeScript: `5.x` (Strict type checking enabled)
  * ESLint: `9.x` with `eslint-config-next`
  * Test Runner: Node.js native `node:test` executed via `tsx` with custom ESM CSS loader

---

## 2. Getting Started & Installation

From the repository root or the `frontend/` directory:

```bash
# Navigate to frontend directory
cd frontend

# Install exact pinned dependencies from package-lock.json
npm ci
```

---

## 3. Operational Commands

All commands are executed from the `frontend/` directory:

| Command | Action | Description |
| :--- | :--- | :--- |
| `npm run dev` | Local Dev Server | Starts Next.js development server at `http://localhost:3000` with fast refresh. |
| `npm run build` | Production Build | Compiles TypeScript, runs route optimization, and generates static production output for all 19 routes. |
| `npm run start` | Production Server | Runs the compiled production server on port 3000. |
| `npm run lint` | ESLint | Executes ESLint against all source files using Next.js core web vitals and TypeScript rules. |
| `npm run type-check` | TypeScript Check | Runs `tsc --noEmit` to verify type safety without emitting build artifacts. |
| `npm run test` | Automated Tests | Executes 138 component, state, dashboard, filter, visualization, patient intelligence, API client, and end-to-end workflow unit tests across 33 suites using `node:test` and `tsx`. |

---

## 4. UI Component Library (Phase 4.4)

All shared UI primitives are located in [`frontend/components/ui/`](components/ui/) and exported via a central barrel [`index.ts`](components/ui/index.ts).

### Component Summary

| Component | Primitives & Variants | Key Features |
| :--- | :--- | :--- |
| **Button** | `primary`, `secondary`, `outline`, `ghost`, `danger`<br/>Sizes: `sm`, `md`, `lg` | Semantic `<button>`, native types (`button`, `submit`, `reset`), `asChild` composition, leading/trailing icons, disabled state with `aria-disabled`. |
| **Card** | `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter` | Composable structure, polymorphic `as` prop (`article`, `section`, `div`), subtle clinical elevation. |
| **Badge** | `neutral`, `info`, `success`, `warning`, `danger`<br/>Sizes: `sm`, `md` | Explicit text labels, optional indicator dot (`withDot`), high-contrast clinical status tokens. |
| **Table** | `Table`, `TableHeader`, `TableBody`, `TableFooter`, `TableRow`, `TableHead`, `TableCell`, `TableCaption` | Responsive horizontal scroll wrapper, semantic `scope="col"`, dense row token support, accessible caption. |
| **Form** | `Label`, `Input`, `Textarea`, `Select`, `Checkbox`, `FormField` | Programmatic label association, clear `aria-invalid` error states with `role="alert"`, helper text, custom accessible checkbox. |
| **Dialog** | `Dialog`, `DialogTrigger`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription`, `DialogBody`, `DialogFooter`, `DialogClose` | Accessible modal (`role="dialog"`, `aria-modal="true"`, `aria-labelledby`), Escape key listener, backdrop dismiss, Tab focus containment, focus restoration on unmount, `asChild` composition. |
| **Tabs** | `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` | W3C WAI-ARIA tab pattern (`role="tablist"`, `role="tab"`, `aria-selected`, `aria-controls`, `role="tabpanel"`). |
| **Skeleton** | `rectangular`, `circular`, `text` | Decorative loading placeholder (`aria-hidden="true"`), pulse animation respecting `prefers-reduced-motion`. |
| **Toast** | `neutral`, `info`, `success`, `warning`, `danger` | Accessible notification presentation (`role="status"`, `role="alert"`, `aria-live="polite"`), dismissible button. |

---

## 5. Reusable Application State Primitives (Phase 4.5)

All reusable application state components are located in [`frontend/components/states/`](components/states/) and exported via [`index.ts`](components/states/index.ts):

| Component | Target Scenarios | Accessibility & Privacy Features |
| :--- | :--- | :--- |
| **`LoadingState`** | Page, section, card, or inline loading placeholders. | `role="status"`, `aria-live="polite"`, decorative skeletons marked `aria-hidden="true"`, respectful of `prefers-reduced-motion`. Avoids simulating false backend progress percentages. |
| **`EmptyState`** | No records available, no search matches, no research runs queued. | Semantic heading hierarchy, `role="region"`, optional primary action button, clear non-diagnostic context notice preventing false claims that queries occurred. |
| **`ErrorState`** | Unexpected exceptions, failed service attempts. | `role="alert"`, clear nontechnical summary, safe diagnostic ID (no stack traces, tokens, or PHI exposed), recovery retry button rendered only when parent supplies `onRetry`. |
| **`InlineError`** | Compact inline error presentation for form fields and table rows. | `role="alert"`, accessible warning icon, text label. |
| **`AccessDeniedState`** | Administrative route boundary notice. | Clear statement that access is restricted without leaking sensitive protected resource details; optional return action; explicit boundary disclaimer stating frontend views are not security boundaries. |
| **`PlannedFeatureState`** | Unimplemented roadmap pages (`/patients`, `/analysis`, `/research`, `/admin`). | Honest language ("Planned for a future module", "Not implemented yet"), lists verified architecture foundations from earlier modules (e.g., Module 3 database models and seed data), and preserves research prototype notices. |

### Route-Level Error Boundaries & 404 Handlers

* **`frontend/app/error.tsx`:** Next.js App Router client error boundary wrapping unhandled rendering exceptions with an accessible `ErrorState`, sanitized diagnostic reference, and meaningful `reset()` retry action.
* **`frontend/app/not-found.tsx`:** Clean, accessible 404 presentation using `EmptyState` with a navigation action returning clinicians safely to the Overview route.

### State Usage Examples

```tsx
import {
  LoadingState,
  EmptyState,
  ErrorState,
  AccessDeniedState,
  PlannedFeatureState,
} from "@/components/states";

// 1. Loading State
<LoadingState
  variant="section"
  label="Retrieving Longitudinal Laboratory Metrics..."
  description="Accessing Module 3 observations repository."
  lines={3}
/>

// 2. Empty State
<EmptyState
  preset="runs"
  title="No Active Research Runs In Progress"
  description="There are currently no inference pipelines or multi-agent evaluations executing against this synthetic cohort."
  action={{
    label: "Initiate Exploratory Run",
    onClick: handleInitiate,
    variant: "primary",
  }}
  notice="Illustrative empty state demonstration — does not imply backend query execution."
/>

// 3. Error State with Working Retry Action
<ErrorState
  title="Pipeline Disconnection"
  message="A communication interruption occurred while contacting the synthetic evaluation runner."
  errorCode="ERR-SYNTH-EVAL-404"
  onRetry={handleRetry}
  retryLabel="Retry Connection"
/>

// 4. Access-Denied State
<AccessDeniedState
  title="Administrative Access Restricted"
  message="This view requires designated platform oversight roles."
  requiredRole="Platform Administrator"
/>

// 5. Planned Feature State for Roadmap Routes
<PlannedFeatureState
  moduleName="Module 6: Patient Intelligence"
  targetBlock="Block 2: Clinical Domain Foundation"
  statusText="Planned for a future module"
  description="Patient Intelligence is scheduled for full implementation in Module 6."
  verifiedFoundations={[
    "SQLAlchemy Models: Patient, Encounter, Observation (Module 3)",
    "Repositories: PatientRepository, EncounterRepository",
  ]}
/>
```

### Usage Examples

```tsx
import {
  Button,
  Badge,
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
  FormField,
  Input,
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "@/components/ui";

// Card & Table Usage
export function SpecCard() {
  return (
    <Card as="article">
      <CardHeader>
        <CardTitle as="h3">Platform Specifications</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Service</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>FastAPI Gateway</TableCell>
              <TableCell><Badge variant="success">Verified</Badge></TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

// Dialog with Form Fields
export function ConfirmModal() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline">Open Review</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogTitle>Confirm Review Parameters</DialogTitle>
        <DialogDescription>Review synthetic analysis parameters before proceeding.</DialogDescription>
        <FormField label="Reviewer Notes" htmlFor="notes" helperText="Optional internal audit note">
          <Input id="notes" placeholder="Enter notes..." />
        </FormField>
        <DialogClose asChild>
          <Button variant="primary">Accept</Button>
        </DialogClose>
      </DialogContent>
    </Dialog>
  );
}
```

### Accessibility Guidelines

1. **Semantic Elements:** All primitives use native HTML elements (`<button>`, `<table>`, `<dialog>` / `role="dialog"`, `<label>`, `<input>`).
2. **Accessible Contrast:** Colors adhere to WCAG AAA/AA contrast tokens on both light and dark backgrounds.
3. **Keyboard Focus:** Every interactive element has visible `:focus-visible` styling (`--color-focus-ring` with 2px offset).
4. **Motion Safety:** All animations (Skeleton pulse, Dialog scale, Toast fade) are suppressed under `@media (prefers-reduced-motion: reduce)`.
5. **No Color-Only State:** Badges and alerts always include descriptive text labels; colors never serve as the sole communication medium.

### Explicitly Deferred Functionality

* **Data Grid Engine:** Complex sorting, multi-column filtering, pagination, and virtual scrolling are deferred until real patient/cohort data requires them (Module 6).
* **Clinical Intake Forms:** Live medical file uploads, DICOM previewers, and EHR patient intake validation are deferred to Modules 7 & 8.
* **Global Notification Bus:** Standalone global toast queue and push notification systems are deferred to later application integration phases.

---

## 5. Application Shell & Navigation

* **`AppShell` ([`components/layout/AppShell.tsx`](components/layout/AppShell.tsx)):** Master client shell managing layout geometry, mobile navigation drawer state, backdrop overlay, route synchronization, and `Escape` key listeners.
* **`Sidebar` ([`components/layout/Sidebar.tsx`](components/layout/Sidebar.tsx)):** Primary navigation sidebar featuring semantic `<nav>` markup, active route highlighting (`aria-current="page"`), roadmap stage badges, and prototype version/safety footer.
* **`Header` ([`components/layout/Header.tsx`](components/layout/Header.tsx)):** Clinical header providing mobile drawer toggling (`aria-expanded`, `aria-controls`), dynamic route context title, and prominent "Research Prototype — Human Review Only" safety indicator.
* **`Breadcrumbs` ([`components/layout/Breadcrumbs.tsx`](components/layout/Breadcrumbs.tsx)):** W3C WAI-ARIA compliant breadcrumb trail reflecting true hierarchical routing.
* **`PageContainer` ([`components/layout/PageContainer.tsx`](components/layout/PageContainer.tsx)):** Reusable page scaffold providing standardized heading, description, breadcrumb integration, and responsive content margins.

### Canonical Roadmap Destinations

All navigation links resolve to valid, statically prerendered routes inside the shell:

| Navigation Item | Route | Roadmap Module | Purpose | Status in Shell |
| :--- | :--- | :--- | :--- | :--- |
| **Overview** | `/` | Module 5 | Clinical intelligence overview, summary cards & recent activity | Active Overview UI (Phase 5.2) |
| **Patient Intelligence** | `/patients` | Module 6 | Longitudinal timelines, encounter history, vitals | Planned Roadmap Preview |
| **Clinical Workspace** | `/analysis` | Module 8 | Multimodal case intake, triage, and review | Planned Roadmap Preview |
| **AI Research Lab** | `/research` | Module 18 / M9–14 | Model evaluation, SHAP, and Grad-CAM benches | Planned Roadmap Preview |
| **Administration** | `/admin` | Module 19 | Role-based access control & audit trail | Planned Roadmap Preview |

---

## 6. Design Tokens & Visual Foundation

The design system communicates clinical clarity, scientific credibility, precision, and trust. Tokens are implemented entirely as standard CSS custom properties in [`frontend/app/globals.css`](app/globals.css) and consumed via CSS Modules.

### Semantic Token Categories

| Category | Token Prefix | Examples | Purpose |
| :--- | :--- | :--- | :--- |
| **Colors (Brand)** | `--color-brand-` | `--color-brand-primary`, `--color-brand-subtle`, `--color-brand-border` | Clinical deep teal/cyan identity and interactive states. |
| **Colors (Accent)** | `--color-accent-` | `--color-accent-primary`, `--color-accent-subtle` | Secondary medical blue/slate accent. |
| **Colors (Surfaces)** | `--color-bg-` | `--color-bg-canvas`, `--color-bg-surface`, `--color-bg-surface-elevated` | Layered canvas, card, and modal surfaces. |
| **Colors (Text)** | `--color-text-` | `--color-text-primary`, `--color-text-secondary`, `--color-text-muted` | High-contrast WCAG AAA/AA text hierarchy. |
| **Colors (Status)** | `--color-{status}-` | `--color-success-fg`, `--color-warning-bg`, `--color-danger-border` | Status indicators (Success, Warning, Danger, Info). |
| **Typography** | `--font-`, `--font-size-` | `--font-sans`, `--font-size-display`, `--font-size-body`, `--font-weight-bold` | Scalable type scale with fluid clamp headings. |
| **Spacing** | `--space-` | `--space-1` (4px) to `--space-20` (80px), `--space-table-cell-y` | 4pt/8pt systematic grid for cards, forms, and dense data tables. |
| **Borders & Radii** | `--border-`, `--radius-` | `--border-width-sm`, `--radius-sm` (6px), `--radius-lg` (12px), `--radius-full` | Restrained radii and border widths. |
| **Elevation** | `--shadow-` | `--shadow-sm`, `--shadow-md`, `--shadow-lg` | Clean, subtle shadows without glowing artifacts. |
| **Layout & Sizing** | `--layout-`, `--control-` | `--layout-max-width` (1120px), `--control-height-md` (40px) | Layout constraints, gutters, and dense row tokens. |
| **Motion** | `--motion-` | `--motion-duration-fast`, `--motion-easing-default` | Respects `prefers-reduced-motion` unconditionally. |

---

## 7. Environment Variables

Frontend configuration is driven by environment variables using Next.js conventions:

* Template file: [`frontend/.env.example`](.env.example)
* Local configuration file: `frontend/.env.local` (excluded from version control in `.gitignore`).

### Key Variables

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | URL | `http://127.0.0.1:8000/api/v1` | Base endpoint URL for the backend FastAPI service. |
| `NEXT_PUBLIC_APP_ENV` | String | `development` | Active environment profile (`development`, `staging`, `production`). |

---

## 8. Directory Structure

```text
frontend/
├── .env.example                # Environment variable template
├── .gitignore                  # Frontend-specific ignores (.next, node_modules)
├── eslint.config.mjs           # ESLint 9 flat configuration
├── next.config.ts              # Next.js configuration (Turbopack, cache components)
├── next-env.d.ts               # Next.js TypeScript type declarations
├── package.json                # Pinned frontend dependencies and scripts
├── package-lock.json           # Deterministic npm lockfile
├── tsconfig.json               # TypeScript strict configuration
├── README.md                   # Frontend architecture & component documentation
├── app/
│   ├── favicon.ico             # Application favicon
│   ├── globals.css             # Vanilla CSS design tokens system & accessible reset
│   ├── layout.tsx              # Root layout wrapping AppShell & fonts
│   ├── page.tsx                # Overview landing page & component showcase
│   ├── page.module.css         # Scoped CSS module for landing page content
│   ├── error.tsx               # Next.js App Router route-level error boundary
│   ├── not-found.tsx           # Next.js App Router 404 handler
│   ├── admin/page.tsx          # M19: Platform Administration & Governance
│   ├── agents/page.tsx         # M11: Multi-Agent Orchestration & State Graph
│   ├── analysis/page.tsx       # M8: Clinical Workspace & Case Analysis
│   ├── explainability/page.tsx # M14: Explainability & Evidence Presentation (XAI)
│   ├── imaging/page.tsx        # M10: Chest X-ray Imaging & Research Pipeline
│   ├── knowledge/page.tsx      # M12: Medical Knowledge Hub & RAG Retrieval
│   ├── monitoring/page.tsx     # M20: System Deployment & Telemetry Health
│   ├── operations/page.tsx     # M17: Hospital Intelligence & Resource Simulation
│   ├── patients/page.tsx       # M6: Patient Intelligence & Cohort Profiles
│   ├── readiness/page.tsx      # M21: Research Documentation & Readiness Review
│   ├── research/page.tsx       # M18: AI Research Lab & Model Evaluation
│   ├── reviews/page.tsx        # M15: Clinician Review, Critique & Reports
│   ├── safety/page.tsx         # M13: Critic, Consensus & Uncertainty Safety
│   ├── security/page.tsx       # M7: Security Safeguards & Identity Management
│   └── timeline/page.tsx       # M16: Longitudinal Patient Trajectory & Follow-up
├── components/
│   ├── layout/
│   │   ├── AppShell.tsx        # Master responsive layout container
│   │   ├── AppShell.module.css # Scoped styles for shell, sidebar, and header
│   │   ├── Breadcrumbs.tsx     # Semantic accessible breadcrumbs component
│   │   ├── Header.tsx          # Top bar with page context & status indicator
│   │   ├── PageContainer.tsx   # Reusable page scaffold
│   │   ├── PageContainer.module.css # Scoped styles for PageContainer
│   │   └── Sidebar.tsx         # Primary grouped navigation sidebar & mobile drawer
│   ├── dashboard/
│   │   ├── index.ts            # Central barrel export for dashboard components
│   │   ├── SummaryCard.tsx     # Generic metric card primitive & specialized domain cards
│   │   ├── SummaryCard.module.css
│   │   ├── RecentActivityFeed.tsx # Sanitized operational audit event feed
│   │   ├── RecentActivityFeed.module.css
│   │   ├── AnalysisStatusIndicator.tsx # Accessible lifecycle status badge
│   │   ├── PendingReviewTable.tsx # Candidate review queue table
│   │   ├── PendingReviewTable.module.css
│   │   ├── DashboardFilterBar.tsx # Accessible UTC date and status filter controls
│   │   ├── DashboardFilterBar.module.css
│   │   ├── DashboardVisualizations.tsx # Status & model distribution charts with tables
│   │   └── DashboardVisualizations.module.css
│   ├── states/
│   │   ├── index.ts            # Central barrel export for all state primitives
│   │   ├── LoadingState.tsx    # Page/section/card skeleton loading state
│   │   ├── LoadingState.module.css
│   │   ├── EmptyState.tsx      # Semantic non-diagnostic empty results state
│   │   ├── EmptyState.module.css
│   │   ├── ErrorState.tsx      # Clear error state & InlineError component
│   │   ├── ErrorState.module.css
│   │   ├── AccessDeniedState.tsx # Presentation-only access boundary state
│   │   ├── AccessDeniedState.module.css
│   │   ├── PlannedFeatureState.tsx # Honest roadmap status callout component
│   │   └── PlannedFeatureState.module.css
│   └── ui/
│       ├── index.ts            # Central barrel export for all UI primitives
│       ├── Badge.tsx           # Semantic status badge component
│       ├── Badge.module.css    # Scoped styles for Badge
│       ├── Button.tsx          # Polymorphic button primitive
│       ├── Button.module.css   # Scoped styles for Button
│       ├── Card.tsx            # Composable Card primitives
│       ├── Card.module.css     # Scoped styles for Card
│       ├── Dialog.tsx          # Accessible modal dialog primitive
│       ├── Dialog.module.css   # Scoped styles for Dialog
│       ├── Form.tsx            # Accessible form controls & wrappers
│       ├── Form.module.css     # Scoped styles for Form controls
│       ├── Skeleton.tsx        # Loading placeholder primitive
│       ├── Skeleton.module.css # Scoped styles for Skeleton
│       ├── Table.tsx           # Semantic table primitives & wrapper
│       ├── Table.module.css    # Scoped styles for Table
│       ├── Tabs.tsx            # W3C WAI-ARIA tab navigation
│       ├── Tabs.module.css     # Scoped styles for Tabs
│       ├── Toast.tsx           # Accessible notification toast
│       └── Toast.module.css    # Scoped styles for Toast
│   ├── services/
│   │   └── dashboard.ts        # Typed API client for /api/v1/dashboard/overview
│   ├── types/
│   │   └── dashboard.ts        # Typed TypeScript contracts matching Phase 5.1
├── docs/
│   └── ROUTES.md               # Canonical 21-module route inventory & architecture
├── tests/
│   ├── css-loader.mjs          # Node ESM loader for mocking CSS module imports
│   ├── register-css.mjs        # Node loader registration hook
│   ├── components.test.tsx     # 24 unit tests covering UI primitives
│   ├── dialog.test.tsx         # 6 focused unit tests for dialog keyboard & accessibility
│   ├── states.test.tsx         # 13 unit tests covering all application states & 404
│   ├── routes.test.tsx         # 26 unit tests verifying 21-module route coverage, sidebar, drawer, and header
│   └── dashboard.test.tsx      # 60 unit tests covering dashboard cards, review table, filters, charts, API client & e2e workflow
└── public/                     # Static public assets (SVG icons, logos)
```

---

## 9. Current Implementation Limitations & Roadmap

* **Clinical Workflow Disconnection:** In Phase 4.7, the frontend provides the full verified application route architecture, grouped sidebar navigation, responsive off-canvas drawer, reusable UI primitives, and application states for all 21 roadmap modules. Destination routes and component previews are direct-loadable and styled, but **not yet connected** to live backend REST endpoints, patient cohort data, or clinical inference pipelines.
* **Authentication & Authorization:** Client-side route guards, user session state, and JWT token refresh are deferred to Module 7. Frontend `AccessDeniedState` is strictly a presentation layer pattern and does not represent an enforced security boundary.
* **Automated Browser Automation Environment:** In this environment, headless browser context initialization encountered a CDP port resolution limitation during subagent execution (`failed to create browser context: failed to resolve CDP URLs: failed to parse CDP port:`). Component rendering, static optimization, responsive layouts, and unit testing were verified via Next.js Turbopack build (all 19 routes statically prerendered) and Node.js test runner suites (69 tests passed across 19 suites).
* **Research Disclaimer:** Arogya AI is an investigative research prototype. It does not provide certified medical diagnosis or autonomous clinical decision-making.
