# Plan — {{Title}}

**Parent**: [../README.md](../README.md)

Companion to [README.md](./README.md) (decisions + scope boundary) and [tasks.md](./tasks.md) (checkbox execution).

---

## 1. Repo facts (verified)

| Area | Current state (verified) | Source |
|---|---|---|
| {{subsystem / endpoint}} | {{what exists today}} | `bounds describe` / file:line |
| {{...}} | {{...}} | {{...}} |

---

## 2. Execution order (phased, low-risk first)

1. **Phase 0 — Setup** — branch + this mini-SDD doc set + baseline (test count, `bounds validate --quick`).
2. **Phase 1 — {{first slice}}** *(gate: lint + tests + bounds preflight)*.
3. **Phase 2 — {{next}}** — {{...}}
4. **Phase N-1 — Verify** — full suite, lint, bounds preflight, docs checks.
5. **Phase N — Cleanup (END)** — DRY consolidation + doc sync.

---

## 3. Architecture / contracts

### 3.1 {{Data model / new types}}
{{type definitions, constraints, rationale}}

### 3.2 {{API / CLI}}
{{method + path, request schema, response schema}}

### 3.3 {{Decision matrix}}
{{table}}

---

## 4. Exact changes per area

### 4.1 {{Area}}
- {{exact change, file path}}
- **KEEP:** {{what must not change}}

### 4.2 {{...}}

---

## 5. Risk register

| Risk | Mitigation |
|---|---|
| {{risk}} | {{which phase/gate contains it}} |
| {{...}} | {{...}} |

---

## 6. End-phase cleanup (DRY + docs)

- **DRY sweep:** {{duplication this change may introduce + how consolidated}}.
- **Docs sync (same change, not follow-up):** mini-SDD task checkboxes, affected architecture docs, bounds manifest updates.
- **Architecture re-baseline:** `bounds calibrate --dump-baseline` if public surface changed.
