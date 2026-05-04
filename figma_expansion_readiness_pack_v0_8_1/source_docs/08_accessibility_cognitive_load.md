# Accessibility and Cognitive Load Design

## 1. Accessibility stance

Accessibility is not a later compliance pass. It is central to the product because the app is designed around executive-function support, time awareness, low-friction capture, and recovery.

## 2. Visual accessibility

Requirements:

- Support Dynamic Type.
- Preserve layout at large text sizes.
- Use sufficient contrast in light and dark mode.
- Support Increase Contrast.
- Do not rely on color alone.
- Provide meaningful VoiceOver labels.
- Ensure touch targets are comfortably sized.
- Avoid text embedded in images.

## 3. Cognitive accessibility

Requirements:

- One primary action per screen.
- Avoid forced multi-step setup before first capture.
- Use progressive disclosure.
- Keep reminders user-controlled.
- Avoid unwanted interruptions.
- Preserve raw captured input so the user does not lose intent.
- Provide recovery paths when tasks are late, stuck, or deferred.
- Support personalization of density, reminders, tone, and granularity.

## 4. Reminder accessibility

Reminders should be easy to set and personalize. The app may suggest reminders for time-sensitive tasks, but reminders must be accepted by the user and adjustable.

Reminder settings should include:

- Default reminder lead time.
- Start-by reminders.
- Quiet hours.
- Notification privacy mode.
- Reminder intensity.
- Repeat nagging disabled by default.

## 5. Motion and sensory load

Support:

- Reduce Motion.
- Reduced transparency.
- Disable sounds.
- Disable celebratory feedback.
- Calm mode with fewer visual effects.

## 6. ADHD/executive-function specific UI safeguards

- Do not punish overdue tasks visually.
- Avoid red as default overdue alarm; use calm urgency.
- Avoid large “failed” sections.
- Make deferral intentional and easy.
- Offer minimum viable options.
- Make estimates ranges, not exact promises.
- Show “done enough” criteria.
- Let users hide analytics if they increase anxiety.

## 7. Accessibility acceptance gates

A screen is not ready if:

- It breaks at large text.
- The primary action is unclear.
- A user cannot capture without classification.
- Completion/stuck/recovery rely on gesture-only controls.
- Color is the only state signal.
- Offline states are alarming or blocking.
