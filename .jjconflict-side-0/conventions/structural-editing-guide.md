**Basis**
- I synthesized this from established technical-writing and editing guidance: Google Technical Writing, Microsoft Style Guide, Digital.gov plain-language guidance, technical-writing textbooks on lists and figures, accessibility guidance for figure text, and instructional-scaffolding guidance for sequencing complex concepts.
- I’ve adapted those principles for a technical book about AI agents, where overloaded terms, system diagrams, and multi-step arguments create unusually high comprehension risk.

**1. Reader Knowledge Management**
- **Principle:** Readers build a mental model in sequence; if a term arrives before its frame, they guess, and later explanation has to fight the wrong guess.
- **Detection:** Flag any acronym used before expansion: search for patterns like all-caps tokens or mixed-case abbreviations before a `full term (ACRONYM)` introduction.
- **Detection:** Flag any key term first appearing in a heading, figure, sidebar, or example before the body text defines it.
- **Detection:** Flag overloaded words used with a book-specific meaning but no cue, especially `agent`, `memory`, `tool`, `context`, `plan`, `state`, `alignment`, `reasoning`, `reflection`, `scratchpad`.
- **Detection:** Flag first-mention definitions that themselves contain 2+ undefined terms of equal or greater complexity.
- **Detection:** Flag paragraphs that introduce 3+ new technical nouns in 2-3 sentences without an anchor example or familiar category.
- **Detection:** Flag sentences that use a term causally before defining it, e.g. “`coordination drift causes rework`” before `coordination drift` exists for the reader.
- **Detection:** Flag figures whose labels, legends, or node names do not appear in the surrounding text within one paragraph before or after the figure.
- **Detection:** Flag pronouns like `this`, `it`, `they`, `that` when the referent is a just-introduced technical concept and the noun is not repeated.
- **Fix pattern:** Define on first mention with `class + purpose + boundary`: “A `tool call` is an external action an agent takes outside the model’s text output.”
- **Fix pattern:** For overloaded words, write the contrast explicitly: “In ordinary speech, `memory` means recall. In this book, `memory` means stored state outside the current prompt.”
- **Fix pattern:** Sequence concepts as `familiar problem -> minimal definition -> one concrete example -> operating rule -> edge case`, not `term -> jargon pile -> example`.
- **Fix pattern:** If a term is needed early for momentum, use a generic phrase first, then name it once the mechanism is visible.
- **Before:** `The agent writes to memory when the context window saturates.`
- **After:** `When the prompt gets too full, the system stores selected information outside the prompt. In this book, that stored information is called memory.`
- **Before:** `Coordination fails when plan shards diverge.`
- **After:** `Large tasks are often split into smaller plans. We’ll call each smaller plan a shard. Coordination fails when those shards drift out of sync.`

**2. Self-Reference and Meta-Narration**
- **Principle:** Readers want subject matter, not commentary about the document’s structure; meta-narration spends attention on the wrapper instead of the idea.
- **Detection:** Search for `this chapter`, `this section`, `this book`, `in this chapter`, `in this section`, `we will discuss`, `we now turn to`, `this chapter will`.
- **Detection:** Search for brittle positional references: `as discussed above`, `below`, `earlier`, `later`, `in the previous section`, `in section X`, `the following section`.
- **Detection:** Search for ordinal scaffolding that names position instead of concept: `the first point`, `the second failure`, `the third lesson`, `finally`.
- **Detection:** Flag openers whose grammatical subject is the document, not the topic, e.g. `This chapter explains...` instead of `Agents fail when...`.
- **Detection:** Flag filler signposts such as `it is important to note`, `note that`, `notice that`, `we can see that`, `I will show`.
- **Detection:** Flag figure references by placement, not identity: `the figure below`, `the table above`, `shown below`.
- **Detection:** Flag chapter openers that summarize the reading plan before establishing a problem, tension, or payoff.
- **Fix pattern:** Replace roadmap prose with a claim, a reader problem, or a surprising failure case.
- **Fix pattern:** Replace positional references with semantic reminders: not “as discussed in Section 2,” but “because prompts are lossy interfaces...”
- **Fix pattern:** Use headings and topic sentences to carry structure; don’t narrate the structure in prose unless the ordering itself is the point.
- **Fix pattern:** Use one short roadmap only when needed, and make it concept-based: `We’ll move from prompt-only agents to tool-using agents to multi-agent systems.`
- **Before:** `This chapter will discuss five ways AI agents fail in production.`
- **After:** `Production agent failures look diverse, but five patterns recur: hidden state, weak decomposition, prompt overload, tool misuse, and unowned recovery.`
- **Before:** `As discussed in Section 3, context windows are limited.`
- **After:** `Because context windows are limited, agents must decide what to keep active and what to store elsewhere.`
- **Before:** `The second failure is context drift.`
- **After:** `Context drift begins when the agent carries forward stale assumptions from earlier turns.`

**3. Redundancy Detection**
- **Principle:** Supplementary elements must change function, not just formatting; a box, sidebar, or callout should add a new use, not reprint the paragraph in a rectangle.
- **Detection:** Flag any definition box whose wording overlaps heavily with the adjacent paragraph, especially if the key noun-verb pair is identical.
- **Detection:** Flag boxes that answer the same question as the body text in the same order with the same example.
- **Detection:** Flag term boxes placed within 150-200 words of a full in-text definition of that same term.
- **Detection:** Flag captions or callouts that restate all the same data points the paragraph already lists, with no interpretation change.
- **Detection:** Flag pull quotes or sidebars that can be deleted with no loss of meaning, guidance, warning, or usability.
- **Detection:** Flag “note” or “tip” boxes whose content is not actually a note, tip, warning, checklist, exception, or example.
- **Detection:** Flag repetition that stays at the same abstraction level: same claim, same evidence, same wording, same span.
- **Detection:** Treat repetition as intentional only if at least one dimension changes: representation, audience, time, or function.
- **Fix pattern:** Give each supplement one explicit job: `define`, `warn`, `show example`, `give checklist`, `state exception`, `compare alternatives`, or `offer a quick test`.
- **Fix pattern:** If the box adds no new job, merge it into the body or delete it.
- **Fix pattern:** Convert duplicate definitions into worked examples, counterexamples, or editorial tests the reader can apply.
- **Fix pattern:** Keep deliberate reinforcement short, spaced, and functionally different: paragraph explains; box operationalizes.
- **Before:** Body text: `A system prompt is the persistent instruction layer that shapes all later responses.` Box: `System prompt: the persistent instruction layer that shapes all later responses.`
- **After:** Body text stays. Box becomes: `Quick test: If changing this text would alter every reply in the session, it belongs in the system prompt.`
- **Before:** Body text: `Tool calls add latency and create new failure points.` Callout: `Tool calls increase latency.`
- **After:** Callout becomes: `Latency rule: If a tool call neither changes the answer nor reduces uncertainty, cut it.`

**4. Logical Coherence**
- **Principle:** Readers need a stable causal map; if claims appear to cancel each other, they stop trusting the argument and start repairing it themselves.
- **Detection:** Flag adjacent claims of broad capability and broad incapacity without scope markers, e.g. `AI is powerful` followed by `AI cannot...`.
- **Detection:** Flag `not because X, but because Y` when `X` is not an active misconception in the reader’s mind.
- **Detection:** Flag contrast words such as `but`, `however`, `although`, `yet` when the second sentence is actually a refinement, not a contradiction.
- **Detection:** Flag absolute qualifiers near nuanced claims: `always`, `never`, `cannot`, `everything`, `nothing`, `all`, `none`.
- **Detection:** Flag level shifts where the subject silently changes from `model` to `agent`, `agent` to `system`, or `prototype` to `production`.
- **Detection:** Flag limitation statements that lack boundary conditions such as task length, tool availability, latency budget, or supervision level.
- **Detection:** Flag concession-heavy paragraphs where the “however” material is longer and more vivid than the main thesis.
- **Detection:** Flag double negatives and exception chains: `not uncommon`, `not unless`, `cannot... except when... unless...`.
- **Fix pattern:** Scope both sides of the claim explicitly: `good at X, weak at Y, under Z conditions`.
- **Fix pattern:** Rewrite negation-first claims into affirmative causality unless you are directly correcting a live misconception.
- **Fix pattern:** Separate capability claims from failure-mechanism claims: the model can generate locally; the system fails over long horizons.
- **Fix pattern:** Present the core argument first, then the limitation as a boundary, not a reversal.
- **Before:** `AI agents are capable. But they fail at long tasks.`
- **After:** `AI agents are strong at local generation. Their performance drops on long tasks when they lack durable state and reliable checkpoints.`
- **Before:** `Agents fail not because the model is weak, but because the prompt is long.`
- **After:** `Many agent failures come from prompt overload rather than from raw model capability.`
- **Before:** `The model is reliable. However, it often invents tool arguments.`
- **After:** `The model is reliable at fluent text generation, but tool selection and argument formatting remain failure-prone.`

**5. Figure Composition**
- **Principle:** A figure should answer one main reader question; once a figure tries to teach architecture, sequence, comparison, and interpretation at once, it creates cognitive load instead of reducing it.
- **Detection:** Flag captions or alt text containing multiple jobs, especially `X vs Y`, `before/after`, `from...to...`, `and`, `or`, or two independent clauses.
- **Detection:** Flag figures with 8+ labeled elements, 3+ legend variables, or several color/shape/line encodings that readers must decode at once.
- **Detection:** Flag figures that combine different structures in one image, such as taxonomy + process flow, architecture + benchmark results, or timeline + decision tree.
- **Detection:** Flag figures that need two or more paragraphs of “how to read this” before the reader can grasp the point.
- **Detection:** Flag figures whose surrounding text discusses only one corner of the graphic; that usually means the figure is carrying too much.
- **Detection:** Flag alt text that has to explain multiple takeaways rather than identify the figure and its main purpose.
- **Detection:** Flag figures placed before the first forward reference or more than one page after the paragraph that first needs them.
- **Detection:** Flag figures that introduce terms, abbreviations, or symbols not established in the body text.
- **Detection:** Flag prose that says only `see Figure 4` instead of telling the reader what Figure 4 demonstrates, compares, or explains.
- **Fix pattern:** Split by reader question: one figure for structure, one for sequence, one for comparison.
- **Fix pattern:** Use a three-part figure contract: one sentence before the figure to set the question, the figure itself, and one sentence after to state the takeaway.
- **Fix pattern:** Keep captions orienting, not overloaded; move deep interpretation into the surrounding text and long description.
- **Fix pattern:** If the visual is data-dense, pair it with a nearby table, long description, or simplified follow-on figure instead of forcing one do-everything image.
- **Before:** `Figure 4. Agent loop, memory types, escalation logic, and evaluation results across synchronous and asynchronous systems.`
- **After:** `Figure 4. One agent run from user request to tool output.` Then add `Figure 5. Where short-term and long-term memory persist.` Then add `Table 2. Sync vs. async trade-offs.`
- **Before:** Alt text: `Diagram comparing planning, memory, tool use, and monitoring across two classes of agent system.`
- **After:** Alt text: `Sequence diagram of a single tool-using agent run.` Long description nearby: the comparison details.
- **Before:** Body text: `See Figure 7.`
- **After:** `Figure 7 shows why hidden state accumulates after each tool call unless the agent writes back a stable summary.`

**6. Argument Structure**
- **Principle:** Enumeration is a support structure, not a substitute for argument; readers remember a chapter that develops a line of thought, not one that merely counts items.
- **Detection:** Flag headings or topic sentences that start with ordinals instead of concepts: `First`, `Second`, `Third`, `Finally`.
- **Detection:** Flag introductions that announce `five failure modes` but never explain the ordering principle.
- **Detection:** Flag sections that could be rearranged without changing the chapter’s logic; that signals list structure without argument structure.
- **Detection:** Flag transitions that refer only to position: `the next issue`, `another point`, `the last problem`.
- **Detection:** Flag repeated section templates where only the ordinal changes and the prose rhythm becomes mechanical.
- **Detection:** Flag sections that end without a hinge sentence explaining why the next section follows.
- **Detection:** Flag chapter summaries that merely restate all numbered items instead of showing how they interact or which matters most.
- **Detection:** Flag examples that stay isolated inside each section and never get reused to build cumulative understanding.
- **Detection:** Flag sections with equal status when the real logic is causal or hierarchical, e.g. one “failure mode” actually causes two others.
- **Fix pattern:** Choose and state an ordering principle: `chronological`, `causal`, `increasing complexity`, `increasing organizational cost`, or `from visible symptom to root cause`.
- **Fix pattern:** Name sections by concept, not by count: `Hidden state`, `Weak decomposition`, `Tool overreach`.
- **Fix pattern:** End each section with a hinge: “This limitation matters because it creates the next problem: ...”
- **Fix pattern:** Add synthesis after 2-3 sections: show interaction, dependency, or triage order, not just more items.
- **Before:** `The first failure mode is hallucination. The second failure mode is context drift.`
- **After:** `Hallucination is the visible symptom. Context drift is one upstream cause, especially in long-running tasks where stale assumptions survive across turns.`
- **Before:** `The third lesson is about memory.`
- **After:** `Memory becomes necessary once planning spans multiple turns; without a durable record, the agent starts each step with a shrinking and distorted view of prior work.`
- **Before:** `Finally, the fifth problem is recovery.`
- **After:** `Recovery matters last because it governs what the system does after the first four problems appear.`

**Practical Review Pass**
- Run one pass just for first mentions and overloaded terms.
- Run one pass just for meta-narration with searches for `this chapter`, `as discussed`, `below`, `first`, `second`, `finally`.
- Run one pass just for boxes, captions, and sidebars asking: `What new job does this element perform?`
- Run one pass just for contradiction markers: `but`, `however`, `although`, `not because`, `cannot`, `never`.
- Run one pass just for figure overload: `How many reader questions is this figure answering?`
- Run one pass just for chapter spine: `Why is this section here now, and what does it make possible next?`

If you want, I can turn this into a manuscript-ready editorial rubric with severity levels like `must fix`, `should fix`, and `watch`, or into a search-driven QA checklist for an editor using Word, Google Docs, or Markdown.
