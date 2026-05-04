# Figma Generation Brief

## 1. Goal

Generate a native iOS mockup system for [APP_NAME] based on the v0.8 design language. The design should be ready to guide SwiftUI implementation and user acceptance testing after engineering builds the first vertical slice.

## 2. Artboard assumptions

Primary frame size:

- iPhone 15/16 Pro logical size, 393 x 852 pt.

Also create variants for:

- Small iPhone width.
- Large text stress frame.
- Dark mode.
- High contrast / reduced transparency.

## 3. File organization

Suggested Figma pages:

1. Cover / Design Thesis
2. Tokens
3. Components
4. Core Flow Prototype
5. Home and Lists
6. Capture and Inbox
7. Today
8. Task Detail and Plan Builder
9. Now and Stuck
10. Timing and Review
11. Settings and Privacy
12. Empty / Offline / Error States
13. Accessibility Stress Tests

## 4. Prototype flow

Create this clickable flow:

Home → Quick Capture → Saved with inferred chips → Plan Builder → Today Fit → Now Card → Timing Session → Checkpoint → Stuck → Smaller Step → Done → Review.

Also create partial workflows:

- Quick reminder only.
- Capture only.
- Tiny start.
- Routine run.
- Timing session without full plan.
- Offline capture and later AI refinement.

## 5. Component requirements

Build these as reusable components with variants:

- App shell / tab bar.
- Capture field.
- Inference chip.
- List card.
- Task row.
- Estimate chip.
- Route badge.
- Now Card.
- Stuck option button.
- Timing instrument.
- Checkpoint row.
- Routine step.
- Sync/offline indicator.
- Empty state card.
- Settings row.

## 6. Visual acceptance bar

The mockups should feel native, modern, and refined. They should not look like a generic SaaS dashboard. The app should feel usable in one hand. It should be comfortable for someone who opens it during stress, distraction, or transition.

## 7. Copy conventions

Use realistic examples:

- “Clean kitchen”
- “Return package”
- “Reply to Alex about the quote”
- “Pack for weekend trip”
- “Pay insurance bill”
- “Take trash out before pickup”

Avoid lorem ipsum in functional screens.

## 8. What not to generate

Do not generate a mascot. Do not generate an AI chat home screen. Do not use heavy neon gradients. Do not create a dashboard of productivity scores. Do not create task cards that look like Jira tickets. Do not use OmniFocus-like dense metadata by default.
