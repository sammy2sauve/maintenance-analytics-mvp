# TrueSignal — Claude Instructions

## Design Context

### Users
Three overlapping user types, all needing signal over noise at different depths:

- **Plant/Facility Manager** — Reviews dashboards in the morning. Makes budget and prioritization calls. Needs at-a-glance status and KPIs. Cannot afford to parse noise.
- **Maintenance Technician** — On the floor, checking what to act on next. Needs clear urgency signals and task direction. Speed and clarity are everything.
- **Reliability Engineer** — Deep-analysis user. Validates predictions, reviews trends, exports data. Needs power, depth, and trustworthy numbers.

All three need the same thing: **confidence that the signal they're seeing is real and actionable**.

### Brand Personality
**Precise. Alert. Trustworthy.**

TrueSignal is a predictive intelligence tool. The brand should feel like a sharp instrument: expert, calibrated, always telling you what matters. Emotional goals: **Clarity** (no noise, just signal) + **Confidence** (I trust what I'm seeing).

### Aesthetic Direction
- **Dark, always.** Background slate-950 (`#0f172a`), never white or light gray.
- **Indigo + emerald duopoly.** Primary brand actions in indigo (`#6366f1`), success/safe in emerald (`#34d399`). Risk colors follow a strict semantic system: red → orange → amber → emerald.
- **Eye-catching, not flashy.** Custom SVG visualizations (gauges, EKG logo, progress rings), glassmorphism cards, glow accents — used purposefully, not decoratively.
- **Not vibecoded.** Every element must feel intentional and brand-aligned. Avoid AI-generated-feeling randomness: mismatched spacing, overused gradients, inconsistent border radii, or components that feel copy-pasted from different design systems.
- **Not a template.** No generic Tailwind UI cards, no startup-style hero sections, no BI tool dashboard explosion.
- **Not legacy CMMS.** No gray tables, no cluttered toolbars, no 2010-era software feel.

### Design Principles

1. **Signal over noise.** Every element must earn its place. If it doesn't communicate health, risk, or action — remove or de-emphasize it.

2. **Urgency has visual weight.** CRITICAL must feel critical. The hierarchy red → orange → amber → green must be visceral. Size, color intensity, and placement should all reinforce risk level.

3. **Serve all three users in one view.** High-level summary at top (manager), specific actionable items in sidebars (technician), detailed data below the fold (engineer).

4. **Consistency builds trust.** Spacing, border radius, typography scale, and color use must be consistent across every page and component. Inconsistency signals a cobbled-together tool.

5. **Dark, intentional, non-generic.** The UI should feel custom-built for industrial predictive maintenance — not a starter template with the color changed.

### Color Quick Reference

| Token | Hex | Use |
|---|---|---|
| Page background | `#0f172a` | All page backgrounds (slate-950) |
| Card background | `#1e293b` | Cards, panels, inputs (slate-800/900) |
| Primary brand | `#6366f1` | Actions, focus, links (indigo-500/600) |
| Safe/Success | `#34d399` | Low risk, success states (emerald-400) |
| CRITICAL | `#f87171` | Critical risk (red-400) |
| HIGH | `#fb923c` | High risk (orange-400) |
| MEDIUM | `#fbbf24` | Medium risk (yellow-400) |
| LOW | `#34d399` | Low/safe (emerald-400) |
| White text | `#ffffff` | Headings, primary labels |
| Muted text | `#94a3b8` | Secondary labels (slate-400) |
| Subtle border | `#334155` | Card borders (slate-700, often `/50`) |
