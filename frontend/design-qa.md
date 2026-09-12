# Design QA

- Source visual truth: `design-reference.png`
- Implementation screenshot: `artifacts/implementation-1440x1024.png`
- Comparison composite: `artifacts/design-comparison-pass2.png` (source left, implementation right)
- Viewport: 1440 × 1024 CSS pixels
- Source pixels: 1487 × 1058, normalized to 1440 × 1024
- Implementation pixels: 1440 × 1024 at device scale factor 1
- State: initial desktop, editor and Control Graph Inspector open, Events tab selected

## Full-view comparison evidence

The normalized side-by-side comparison confirms the same primary composition: four desktop icons at upper left, slate editor at x≈212/y≈116, narrow inspector at x≈988/y≈116, a 42px dark bottom panel, and a full-bleed green aurora landscape. Window proportions, overlap, title bars, content density, panel grouping, shadows, and the muted green accent hierarchy are materially aligned.

## Focused-region comparison evidence

- Editor: title/menu/toolbar/tab/editor/status layers match; the document now has the same 26-line density and footer position.
- Inspector: four tabs, 15 visible events, focused-node readout, invoke control, and listener footer now match the source hierarchy.
- Panel: left launcher/pinned/task grouping and right network/audio/battery/date grouping occupy the same visual bands.
- Desktop assets: real themed SVG icons are used at the same approximate scale; no placeholder or code-drawn icon assets remain.

## Comparison history

### Pass 1 — blocked

- P1: Inspector was missing Settings, Current Focused Node, and the source event density.
- P2: symbolic icons were rendered too dark because already-light assets were inverted.
- P2: editor stopped at line 22 instead of the source's 26-line document.

Fixes: added the fourth inspector mode and settings state, restored the focused-node surface, expanded the seeded event history, matched the document copy/line count, and corrected icon filters. Post-fix evidence is `artifacts/design-comparison-pass2.png`.

### Pass 2 — passed

No actionable P0/P1/P2 differences remain at the target viewport.

## Required fidelity surfaces

- Fonts and typography: Cantarell variable is bundled for native desktop UI; a restrained system monospace stack is used in research/editor surfaces. Size, weight, line height, truncation, and hierarchy match the target closely.
- Spacing and layout rhythm: window positions, panel height, tab/tool/status bands, radii, border weight, and shadow depth align with the source.
- Colors and visual tokens: slate surfaces, near-black borders, muted foregrounds, and apple-green success/accent tokens are consistent throughout.
- Image quality and asset fidelity: the reconstructed aurora is a sharp full-resolution raster asset. Desktop, application, action, window, and tray icons use real open desktop-theme SVG assets.
- Copy and content: the editor research notes, event names, focused-node label, node invocation control, date, and status copy reproduce the selected concept.

## Primary interactions tested

- Initial editor and inspector render
- Network panel open
- Network selection and connected state
- Application menu open
- Search input filtering
- Files launch
- Remote `POST /api/control` command delivery over SSE
- Browser console checked: no errors

## Follow-up polish

- P3: the reconstructed wallpaper has slightly stronger lake reflections than the original generated composite.
- P3: native font rasterization varies subtly by browser and operating system.

final result: passed
