# State Rules and Fallbacks

Every major surface must support the following states without inventing new visual language.

## Empty
Use a calm empty state with:
- one illustration or soft icon
- one sentence of orientation
- one simple action
- optional small supportive link

## Loading / thinking
Use skeleton rows or soft placeholder shapes.
Do not use aggressive spinners as the main event.
A helper card can explain the delay in plain language.

## Offline but safe
The message is not “failure.” It is “your work is safe; we’ll sync later.”

## Sync pending
Show that the system is catching up, but preserve usability.

## AI unavailable
The fallback should keep the user moving.
Allowed fallback surfaces:
- quick capture
- today
- inbox
- saved
- ideas
Do not dead-end the user because enrichment is unavailable.

## Error / couldn’t save
Use one clear recovery action and one cancel/back action.
Never make the user decipher raw error language.

## Successful save / updated
Use a small success surface or inline confirmation. Avoid celebratory excess.

## Long-text capture
The field should expand gracefully. The system may acknowledge that the detail is useful, but should not overwhelm the user with extra prompts.

## Accessibility / large type
Cards and footer actions must reflow without clipping. Chips may wrap, but the row should remain readable.
