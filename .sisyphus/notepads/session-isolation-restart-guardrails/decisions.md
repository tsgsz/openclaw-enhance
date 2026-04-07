## Documentation Strategy Decisions

1. **Consolidated Guardrail Section**: Instead of scattering guardrail details across multiple existing sections, a new dedicated section "会话隔离与安全护栏" (Session Isolation & Safety Guardrails) will be added to `PLAYBOOK.md`. This ensures high visibility for this critical safety feature.
2. **Operations Deep Dive**: `docs/operations.md` will receive a corresponding deep-dive section to explain the lifecycle of session bindings and the "Fail-Closed" philosophy.
3. **Feature-Class Addition**: A new feature class `session-isolation` will be added to `docs/testing-playbook.md` to formalize the validation requirements for this and future isolation-related changes.
4. **Sanitization Boundary**: Documentation will explicitly state that sanitization is limited to enhance-controlled outward paths to avoid overclaiming protection for core-only output.
