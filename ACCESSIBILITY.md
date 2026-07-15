# Accessibility

This project treats accessibility as a non-negotiable quality attribute, equal to
security and correctness. Target: **WCAG 2.2 Level AA**.

## Commitments

- **Keyboard-first.** Every interactive control is reachable and operable without a
  mouse, with a visible focus indicator (3px high-contrast outline).
- **Semantic markup.** Native `<button>`, `<label>`, `<table>` with `<th scope>`,
  `<nav>`, and a logical heading hierarchy. ARIA only where native semantics fall short.
- **No color as the sole indicator.** Status is conveyed in text (`role="status"`,
  `aria-live="polite"`), not color alone.
- **Contrast.** Foreground/background pairs meet 4.5:1 (text) and 3:1 (UI); verified
  in both light and dark themes via `prefers-color-scheme`.
- **Reduced motion.** `prefers-reduced-motion` disables all animation/transition.
  There is no autoplay or flashing content.
- **Touch targets** are at least 44x44 CSS px.
- **Document language** is declared (`lang="en"`).
- **Skip link** to main content is the first focusable element.

## The public filter UI

Search is intentionally limited to **date** and **location** (city / block-level
text). There is no name search. Labels are visibly associated with every control,
help text is linked via `aria-describedby`, and results are announced live.

## Release checklist (manual)

- [ ] Keyboard-only pass end to end
- [ ] VoiceOver spot-check (macOS)
- [ ] 200% zoom and narrow viewport
- [ ] Dark mode + high-contrast
- [ ] Focus order matches visual order; no traps

## Automated

CI runs the pytest suite. Add axe-core to the Pages build before public launch;
the pipeline should fail on accessibility violations. Accessibility bugs are
**severity-critical by default** and are never suppressed.
