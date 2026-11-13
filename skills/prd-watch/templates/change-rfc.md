# {{feature_title}} — Change RFC {{change_no}}

> Change RFC for **{{base_rfc_title}}** (base RFC, v{{base_rfc_version}}): {{base_rfc_url}}
> Covers only PRD changes made after the base RFC. Everything else stays as specified in the base RFC.
> Change requests: {{cr_ids}} · PRD versions: {{prd_versions}} · Drafted by prd-watch on {{date}}
> Flags: {{flags_summary}}

# Engineering Specification

## 1. Overview

### Feature Summary

- Problem statement: {{problem_statement}}
- Current flow (base RFC): {{current_flow}}
- Proposed flow: {{proposed_flow}}

### Business Objective

{{objectives}}

### Success Criteria

- Feature works as expected.
- Required workflows are completed successfully.
- Audit logs are generated.
- No regression in existing functionality.
- Performance requirements are met.

---

# 2. Scope

## In Scope

{{in_scope}}

## Out of Scope

- Everything already specified in {{base_rfc_title}} v{{base_rfc_version}} and earlier change RFCs, unless listed above.

---

# 3. Solution

## High-Level Approach

{{approach}}

## Key Design Decisions

{{decisions_and_open_points}}

---

# 4. Technical Changes

## Backend

{{backend}}

## Mobile

{{mobile}}

## Web / Back Office

{{web}}

## Third Party / Integrations

{{integrations}}

---

# 5. API Contract

## Endpoints

| API | Method | Purpose |
| --- | --- | --- |
{{endpoint_rows}}

## Request / Response

{{request_response}}

## Error Handling

{{error_handling}}

---

# 6. Dependencies

| Team | Responsibility |
| --- | --- |
| Product | Requirement clarification |
| FE | UI implementation |
| BE | API & business logic |
| IAM | Permission management |
| QE | Testing |

---

# 7. Risks & Mitigation

| Risk | Mitigation |
| --- | --- |
{{risk_rows}}

---

# 8. Testing

{{testing}}

---

# 9. Change Requests in this RFC

| CR | Type | PRD › section | PRD versions | Flags |
| --- | --- | --- | --- | --- |
{{cr_rows}}
