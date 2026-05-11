**Art Direction System**

- Working name: `Structured Abstraction`
- Purpose: turn textbook diagrams into quiet, intelligent illustrations that explain structure, flow, constraint, and scale without becoming decorative noise.
- Core rule: every figure must clarify one idea first, then add atmosphere second.
- Visual stance: abstract, geometric, editorial, restrained, transparent on the page, never boxed like a slide deck.

**1. Color System**
- Use neutrals for 70–75% of the page, semantic colors for 20–25%, accent color for 5% or less.
- Limit any single figure to `1 neutral + 2 semantic colors + 1 accent`.
- Use `#1E2124` for nearly all text and small labels; do not rely on colored text for meaning.

- `Problem / Friction` — `#9A4E44`; WCAG vs white `5.92:1`; grayscale `#646464`; use for blockers, failure states, risk surfaces, constraint pressure.
- `Proposal / Direction` — `#264E86`; WCAG vs white `8.35:1`; grayscale `#484848`; use for intended flow, candidate solutions, forward motion.
- `Research / Analysis` — `#2E6A5E`; WCAG vs white `6.29:1`; grayscale `#575757`; use for evidence, tracing, investigation, grounding.
- `Values / Principles` — `#6A737D`; WCAG vs white `4.82:1`; grayscale `#717171`; use for philosophy, invariants, policies, guardrails.
- `Alignment / Decision` — `#7A6A2F`; WCAG vs white `5.34:1`; grayscale `#686868`; use for gates, tradeoffs, synthesis, resolution.
- `Accent / Signal` — `#A85E1C`; WCAG vs white `4.90:1`; grayscale `#6D6D6D`; use sparingly for pivots, highlights, figure focal points.

- `Ink` — `#1E2124`; WCAG vs white `16.18:1`; grayscale `#202020`; use for headings, captions, thin outlines, core labels.
- `Warm Background` — `#F5EEE9`; WCAG vs white `1.15:1`; grayscale `#F0F0F0`; use behind problem-centered figures.
- `Cool Background` — `#EEF2F7`; WCAG vs white `1.12:1`; grayscale `#F1F1F1`; use behind proposal/research figures.
- `Neutral Background` — `#F3F3F1`; WCAG vs white `1.11:1`; grayscale `#F3F3F3`; default figure field.
- `Paper` — `#FFFFFF`; default body background.

- Grayscale rule: never encode semantics with color alone.
- In grayscale, pair each semantic role with a form cue:
- `Problem` = angular breaks, truncated paths, sharper junctions.
- `Proposal` = clean continuous arcs or straight directional bands.
- `Research` = fine dotted or grid micro-texture.
- `Values` = steady horizontal rule or quiet enclosing field.
- `Alignment` = bracket, ring, or gate-like circular closure.

**2. Illustration Style**
- Primary mode: flat editorial geometry with subtle depth, not isometric and not literal scene drawing.
- Secondary mode: shallow layered perspective only when hierarchy or stack depth matters.
- Best reference family: “diagrammatic editorial illustration,” not “infographic UI.”

- Geometry vocabulary:
- Circles, arcs, rings, capsules, wedges, thin bands, stepped planes, clustered nodes.
- Avoid default rectangles unless they are clearly transformed: cropped, open, offset, or partially implied.
- Prefer paths, fields, and grouped shapes over outlined boxes.

- Surface treatment:
- Flat fills with 1–2% paper grain or ultra-light noise.
- No glossy gradients, glassmorphism, bevels, or fake 3D chrome.
- Gradients, when used, should be broad and atmospheric: one soft radial or linear wash only.

- Line system:
- Primary strokes: `1.75px` on screen / `0.5pt` in print.
- Secondary strokes: `1.0–1.25px` / `0.35pt`.
- Emphasis strokes: `2.5px` / `0.75pt` only for main flow or decisive closure.
- Arrowheads should be rare; use directional taper, path curvature, or sequencing dots first.

- Corner radius:
- Standard radius `10–14px` for capsules and soft blocks.
- Small modules `6–8px`.
- Avoid fully squared corners except for deliberate tension or blockage.

- Shadow treatment:
- Minimal and diffuse.
- One soft shadow layer only: `0 8px 24px rgba(30,33,36,.06)` for screen.
- In print, replace shadows with faint edge tint or tonal underlay.

- Human figures:
- Not in inline technical figures.
- Allowed only in chapter openers, cover details, or occasional concept spreads.
- If used, they should be ultra-abstract: 2–4 contour curves, no face detail, no clothing detail, no literal environment.
- The “hunched note-taking figure” works only as a symbolic silhouette nested into geometric structure, never as a character illustration.

- How to represent common concepts:
- `Processes / Workflows` — a winding path, segmented ribbon, or stepped track with circular stops; use pacing, scale change, and interruptions instead of box-arrow chains.
- `Relationships / Dependencies` — weighted nodes floating in a shared field, connected by thin tension lines, arcs, or proximity halos; show dependency strength by spacing and line density.
- `Convergence` — multiple thin paths joining one thicker, calmer spine.
- `Explosion` — one ordered cluster splitting into many smaller, tighter fragments; density increases while shape scale decreases.
- `Feedback loops` — incomplete ring plus one weighted return arc; the loop should feel active, not decorative.
- `Compounding` — repeated modules that increase in size, opacity, or count along a curve.
- `Hierarchies / Layers` — terraced bands, stacked planes, or nested fields; use vertical spacing and inset depth, not folder-tree diagrams.

- Standard metaphor set:
- `Path` = temporal progression.
- `Station` = checkpoint, decision, or artifact.
- `Field` = shared context or system boundary.
- `Ring` = closure, alignment, or review loop.
- `Wedge` = narrowing constraint or priority funnel.
- `Fragment cloud` = branching risk or combinatorial growth.

**3. Figure Container Treatment**
- No full rectangle around the figure.
- Figures should feel placed into the page, not inserted into a card.

- Use one of these container modes:
- `Halo Field` — a soft asymmetrical underlay behind the figure, usually offset toward one corner.
- `Edge Brace` — 1–2 partial rules at opposing corners, suggesting a frame without enclosing it.
- `Shelf` — a faint baseline or ground plane under the figure, useful for workflows and hierarchies.
- `Margin Band` — a colored strip or faded geometric intrusion from the outer margin.
- `Open Plate` — transparent figure with only caption, one small anchor mark, and negative space.

- Spacing rules:
- Inline figures: top margin `1.5×` body leading, bottom margin `1.75×`.
- Full-width figures: allow the halo to bleed `4–8mm` into the outer margin.
- Internal breathing room: minimum `12%` of figure width as quiet space around the main geometry.
- Keep the densest visual activity in the central `60–70%` of the figure area.

- Caption rules:
- Always below figure.
- Left-align caption with the image body, not necessarily with the page column.
- `Figure 3.2` in small caps or semibold sans; caption text in regular roman.
- Caption color: `Ink` at `85–90%` opacity.
- Caption width: equal to figure width or slightly narrower; never wider than the text column.

- Differentiating figure types:
- `Workflow figures` — directional underlay and path-based composition.
- `Network figures` — constellation layout, no baseline.
- `Concept figures` — centralized focal structure with more negative space.
- `Hierarchy figures` — stepped shelf or layered bands.
- `Chapter dividers` — one dominant motif plus large quiet field.

**4. Cover and Front Matter**
- Overall cover stance: scholarly, architectural, quiet confidence.
- Avoid startup aesthetics: no glossy gradients, no bold neon tech, no stock-isometric cityscapes.

- Cover composition:
- Background: off-white or soft neutral paper tone.
- Right side: vertical rectangles occupying `22–28%` of the cover width.
- Use `7–10` bars of varied widths and lengths, aligned to a strict vertical grid but staggered in start/end points.
- Bars should descend top-to-bottom like a measured cascade, not a barcode.
- Interrupt 2–3 bars with circular cut-ins, arcs, or small stations to echo the “problem-first” path motif.
- Add one subtle cross-axis element: a long arc or diagonal band passing behind the bar system.

- Title treatment:
- Do not rely on AI-generated text.
- Typeset the real title in layout software as a designed object.
- Make the title part of the composition by masking it into the geometric field, aligning it to the bar grid, or letting one bar intrude into the title block.
- Title should feel “constructed,” not merely placed on top.
- Best treatment: stacked title on left two-thirds, large line breaks, tight tracking, with one word partially intersected by a vertical element.

- Front page / title page:
- Repeat a quieter version of the cover language.
- Use 3–5 thin vertical bars or cropped circular stations in one corner.
- Add one faint path fragment or ring behind the title block.
- Keep plenty of negative space; the title page should feel calmer than the cover.

- Half-title:
- One small geometric motif only, centered low or in outer margin.
- Good option: a single ring with one offset station in `Proposal` blue and `Problem` rust.

- Chapter openers:
- Use a large abstract motif aligned to the chapter theme.
- One dominant gesture only: path, ring, branching fan, or stepped terrace.
- Optional note-taking silhouette can appear here as a ghosted contour integrated into geometry, not as an illustrated scene.

**5. Seedream Prompt Engineering**
- Global prompt scaffold:
- Start with: `abstract editorial geometric illustration for a technical textbook`
- Add: `minimal, sophisticated, vector-like, flat layered shapes, subtle paper grain, off-white background, strong negative space`
- Add palette guidance by name and hex.
- End with: `no photorealism, no literal objects, no stock corporate infographic, no heavy box frame, no glossy 3D, no UI screenshot, no text`

- Workflow diagram prompt:
```text
Abstract editorial geometric illustration for a technical textbook, showing a problem-first AI engineering workflow as a winding path across an off-white field, 6 circular stops of varying size, one interruption zone in rust (#9A4E44), main directional flow in deep indigo (#264E86), supporting analysis elements in deep green (#2E6A5E), quiet neutral slate (#6A737D), flat layered shapes, thin precise lines, asymmetrical composition, subtle shelf underlay, transparent page feel, sophisticated minimalism, vector-like clarity, strong negative space, no boxes, no chunky arrows, no photorealism, no people, no UI, no text
```

- Concept illustration prompt: `combinatorial explosion`
```text
Abstract conceptual illustration of combinatorial explosion for a technical book, one ordered geometric cluster on the left splitting into many smaller fragments and branching arcs toward the right, increasing density and complexity while preserving elegance, deep indigo, rust, olive, and slate on off-white, flat editorial vector style, subtle paper grain, restrained but intellectually tense, large negative space, no literal explosion, no particles, no sci-fi, no boxes, no photorealism, no text
```

- Relationship/dependency prompt:
```text
Abstract network illustration for a textbook, weighted nodes floating in a shared field with thin tension lines and soft halos showing dependencies and coupling, no central box, clustered geometry, quiet asymmetry, deep indigo for primary dependencies, green for research links, slate for stable principles, one rust stress point, minimal vector-like style, elegant negative space, no dashboard look, no icons, no photorealism, no text
```

- Feedback loop prompt:
```text
Minimal abstract illustration of a feedback loop in AI engineering, an incomplete ring with one decisive return arc, three stations around the loop, one gate marker in olive (#7A6A2F), calm neutral field, crisp thin lines, flat layered geometry, editorial sophistication, slightly offset composition, subtle gradient wash only, no arrows unless extremely minimal, no business infographic style, no photorealism, no text
```

- Abstract geometric background / pattern prompt:
```text
Quiet abstract geometric pattern for a technical book, staggered vertical rectangles, partial rings, fine line intersections, sparse composition, off-white ground with very subtle cool and warm tints, restrained palette of indigo, slate, olive, and rust, print-friendly, editorial, minimal, refined, suitable for chapter backgrounds or endpapers, no central focal object, no text, no photorealism
```

- Cover element prompt:
```text
Create a professional abstract cover element for a technical textbook: a right-side system of descending vertical rectangles with varied widths and cropped lengths, intersected by one long soft arc and a few circular stations, conservative palette of deep indigo, rust, olive, slate, and warm off-white, architectural precision, flat layered vector-like forms, subtle grain, elegant negative space, serious and intelligent, not corporate, no title text, no logos, no photorealism
```

- Chapter divider prompt:
```text
Minimal chapter divider illustration for a technical book, one long curved path with 4 circular stops moving across a large quiet field, one abstract note-taking silhouette built from only a few contour lines nested into the geometry, deep indigo and slate with one rust accent, transparent page feel, editorial vector style, very restrained, sophisticated and human without becoming literal, no scenery, no detailed person, no text
```

- Hierarchy / layers prompt:
```text
Abstract layered hierarchy illustration, terraced planes and nested bands descending from top left to bottom right, showing structure, dependency, and containment without using boxes, muted indigo, olive, slate, and off-white, crisp edges, soft underlay, calm but rigorous composition, vector-like editorial graphic, no diagrams with labels, no corporate infographic style, no photorealism, no text
```

**6. Image Evaluation Rubric**
- Score each image out of `100`.
- Reject immediately if it is literal, photorealistic, noisy, or reads like generic startup marketing.

- `Concept communication` — `25 points`
- Does the image clarify the concept at a glance?
- Does the metaphor map to the chapter’s idea, or is it merely atmospheric?
- Would a reader remember the structure after seeing it?

- `Geometric style fit` — `20 points`
- Is it abstract and shape-driven?
- Does it avoid literal scenes, objects, faux-3D, and cliché infographic tropes?
- Does it feel like the same book as the other figures?

- `Compositional restraint` — `15 points`
- Is there enough negative space?
- Is there one dominant idea rather than five competing ones?
- Does the eye know where to enter and exit?

- `Palette discipline` — `10 points`
- Does it stay within the system palette?
- Are semantic colors used deliberately rather than decoratively?
- Does it still read if desaturated?

- `Page behavior` — `10 points`
- Can it sit on the page without a box?
- Does it leave room for caption, nearby text, and margin breathing?
- Does it feel embedded in editorial layout rather than pasted on?

- `Accessibility / print robustness` — `10 points`
- Are forms distinguishable in grayscale?
- Are key edges and structures readable at textbook print size?
- Does reduced contrast still preserve meaning?

- `Complexity match` — `10 points`
- Is the image too busy for a simple concept?
- Is it too sparse for a complex concept?
- Does the visual density match the intellectual density?

- Interpretation bands:
- `90–100` = publish as-is.
- `80–89` = strong; light cleanup only.
- `70–79` = usable conceptually; tighten prompt or simplify composition.
- `60–69` = regenerate with stricter constraints.
- `<60` = reject.

- Quick red flags:
- Too busy: more than 3 focal areas, texture everywhere, tangled lines, unclear hierarchy.
- Too sparse: one lonely icon-like object with no structural relationship.
- Too decorative: pleasing pattern but concept could be swapped without changing the image.
- Too corporate: glossy gradients, device-like cards, icon packs, “innovation” art language.
- Too literal: brains, robots, people at laptops, puzzle pieces, lightbulbs, city skylines.

**7. CSS For Figure Containers**
```css
:root {
  --pf-ink: #1E2124;
  --pf-paper: #FFFFFF;
  --pf-bg-warm: #F5EEE9;
  --pf-bg-cool: #EEF2F7;
  --pf-bg-neutral: #F3F3F1;
  --pf-problem: #9A4E44;
  --pf-proposal: #264E86;
  --pf-research: #2E6A5E;
  --pf-values: #6A737D;
  --pf-alignment: #7A6A2F;
  --pf-accent: #A85E1C;
  --pf-shadow: 0 8px 24px rgba(30, 33, 36, 0.06);
  --pf-radius-lg: 28px;
  --pf-radius-sm: 12px;
  --pf-figure-max: 980px;
  --pf-caption-max: 72ch;
}

.figure {
  position: relative;
  margin: clamp(1.75rem, 4vw, 3.5rem) 0;
  padding: clamp(1rem, 2vw, 1.5rem) clamp(1rem, 2.8vw, 2rem) 0.75rem;
  color: var(--pf-ink);
  break-inside: avoid;
}

.figure__media {
  position: relative;
  z-index: 1;
  max-width: var(--pf-figure-max);
}

.figure__media > img,
.figure__media > svg,
.figure__media > picture,
.figure__media > canvas {
  display: block;
  width: 100%;
  height: auto;
  background: transparent;
  filter: drop-shadow(var(--pf-shadow));
}

.figure__caption {
  position: relative;
  z-index: 1;
  max-width: min(100%, var(--pf-caption-max));
  margin-top: 0.85rem;
  font-size: 0.95rem;
  line-height: 1.45;
  color: rgba(30, 33, 36, 0.88);
}

.figure__caption strong {
  color: var(--pf-ink);
  font-weight: 600;
  letter-spacing: 0.02em;
}

.figure::before {
  content: "";
  position: absolute;
  inset: 0.35rem 0 2.25rem 0;
  border-radius: var(--pf-radius-lg) var(--pf-radius-sm) var(--pf-radius-lg) var(--pf-radius-sm);
  pointer-events: none;
  z-index: 0;
  opacity: 0.95;
}

.figure::after {
  content: "";
  position: absolute;
  left: 0;
  top: 0.65rem;
  width: clamp(3rem, 8vw, 6rem);
  height: 1px;
  background: rgba(30, 33, 36, 0.18);
  z-index: 1;
}

.figure--halo::before {
  background:
    radial-gradient(110% 90% at 12% 8%, rgba(38, 78, 134, 0.08), transparent 48%),
    linear-gradient(180deg, rgba(30, 33, 36, 0.03), rgba(30, 33, 36, 0));
}

.figure--workflow::before {
  background:
    radial-gradient(120% 100% at 0% 0%, rgba(38, 78, 134, 0.10), transparent 52%),
    linear-gradient(90deg, rgba(46, 106, 94, 0.05), rgba(46, 106, 94, 0));
}

.figure--network::before {
  background:
    radial-gradient(60% 60% at 18% 24%, rgba(38, 78, 134, 0.08), transparent 60%),
    radial-gradient(45% 45% at 82% 30%, rgba(46, 106, 94, 0.06), transparent 65%),
    radial-gradient(70% 70% at 50% 100%, rgba(106, 115, 125, 0.05), transparent 65%);
}

.figure--concept::before {
  background:
    radial-gradient(75% 75% at 50% 35%, rgba(122, 106, 47, 0.08), transparent 62%),
    linear-gradient(180deg, rgba(243, 243, 241, 0.9), rgba(255, 255, 255, 0));
}

.figure--hierarchy::before {
  background:
    linear-gradient(180deg, rgba(106, 115, 125, 0.06), rgba(106, 115, 125, 0)),
    radial-gradient(90% 100% at 0% 100%, rgba(38, 78, 134, 0.05), transparent 58%);
}

.figure--divider {
  padding-top: clamp(1.5rem, 4vw, 3rem);
  padding-bottom: 1rem;
}

.figure--divider::before {
  inset: 0 0 1.75rem 12%;
  border-radius: 64px 0 0 64px;
  background:
    linear-gradient(90deg, rgba(38, 78, 134, 0.08), rgba(38, 78, 134, 0)),
    radial-gradient(50% 100% at 100% 50%, rgba(154, 78, 68, 0.06), transparent 70%);
}

.figure--edge-brace .figure__media {
  padding-top: 0.25rem;
  padding-left: 0.5rem;
}

.figure--edge-brace .figure__media::before,
.figure--edge-brace .figure__media::after {
  content: "";
  position: absolute;
  pointer-events: none;
  z-index: 2;
}

.figure--edge-brace .figure__media::before {
  left: -0.15rem;
  top: -0.15rem;
  width: 18%;
  height: 24%;
  border-left: 1.5px solid rgba(30, 33, 36, 0.22);
  border-top: 1.5px solid rgba(30, 33, 36, 0.22);
  border-top-left-radius: 12px;
}

.figure--edge-brace .figure__media::after {
  right: 1%;
  bottom: 1%;
  width: 14%;
  height: 18%;
  border-right: 1.5px solid rgba(30, 33, 36, 0.16);
  border-bottom: 1.5px solid rgba(30, 33, 36, 0.16);
  border-bottom-right-radius: 12px;
}

.figure--problem::after {
  background: rgba(154, 78, 68, 0.45);
}

.figure--proposal::after {
  background: rgba(38, 78, 134, 0.45);
}

.figure--research::after {
  background: rgba(46, 106, 94, 0.45);
}

.figure--values::after {
  background: rgba(106, 115, 125, 0.45);
}

.figure--alignment::after {
  background: rgba(122, 106, 47, 0.45);
}

.figure--open {
  padding-left: 0;
  padding-right: 0;
}

.figure--open::before,
.figure--open::after {
  display: none;
}

.figure--open .figure__media > img,
.figure--open .figure__media > svg,
.figure--open .figure__media > picture,
.figure--open .figure__media > canvas {
  filter: none;
}

@media (max-width: 720px) {
  .figure {
    margin: 1.5rem 0 2rem;
    padding: 0.75rem 0.75rem 0.5rem;
  }

  .figure__caption {
    font-size: 0.92rem;
  }

  .figure--divider::before {
    inset: 0 0 1.5rem 0;
    border-radius: 32px 0 0 32px;
  }
}

@media print {
  :root {
    --pf-shadow: none;
  }

  .figure {
    margin: 10mm 0 12mm;
    padding: 4mm 5mm 3mm;
  }

  .figure::before {
    opacity: 1;
    background:
      linear-gradient(180deg, rgba(0, 0, 0, 0.035), rgba(0, 0, 0, 0)),
      radial-gradient(80% 80% at 0% 0%, rgba(0, 0, 0, 0.04), transparent 60%);
  }

  .figure::after {
    background: rgba(0, 0, 0, 0.28);
  }

  .figure__media > img,
  .figure__media > svg,
  .figure__media > picture,
  .figure__media > canvas {
    filter: none;
  }

  .figure__caption {
    color: rgba(0, 0, 0, 0.9);
  }
}
```

**Recommended Markup**
```html
<figure class="figure figure--workflow figure--proposal figure--edge-brace">
  <div class="figure__media">
    <img src="workflow-01.svg" alt="Problem-first workflow shown as a winding path with checkpoints">
  </div>
  <figcaption class="figure__caption">
    <strong>Figure 3.2</strong> The workflow moves forward through checkpoints, not boxed stages.
  </figcaption>
</figure>
```

**Operating Rules**
- Replace most box-arrow diagrams with paths, stations, fields, terraces, and rings.
- Keep one dominant metaphor per figure.
- Use human silhouettes only in chapter-level art, not technical inline diagrams.
- Build the final cover title with real typography, then integrate it into the generated geometry.

If you want, I can turn this into a production-ready `art-direction.md` plus a prompt library organized by figure type.
