# Production knowledge model

pack-preflight is not intended to be only a PDF syntax checker. The project records practical print-production knowledge so a PDF finding can be connected to what may happen later on press or in finishing.

Each production rule or investigation should be described with the following backbone.

## Rule backbone

1. **Production problem**  
   What real shop-floor problem are we trying to prevent?

2. **Origin stage**  
   Where does the problem usually begin: artwork/prepress, imposition, plate/press setup, printing, coating, cutting, folding, binding, gluing, or another stage?

3. **PDF / job evidence**  
   What objective evidence can the software inspect? Examples: color operators, image resolution, TrimBox/BleedBox geometry, text size, spot colors, page orientation, imposed-sheet identifiers, or operator-supplied job metadata.

4. **Trigger conditions**  
   Under what conditions does the evidence become risky? Include thresholds, combinations, substrate/process dependencies, and whether the rule applies to all jobs or only certain production methods.

5. **Press mechanism**  
   Why can the condition become a problem on press? Record the physical or process mechanism where it is known: registration sensitivity, paper movement, ink load, water/ink interaction, gamut conversion, trapping, plate/form confusion, etc.

6. **Finishing / converting consequence**  
   What can happen later during trimming, folding, stitching, coating, die-cutting, gluing, or assembly?

7. **Valid exceptions**  
   When is the same PDF construction intentional and acceptable? The project should avoid turning a production practice into a blind universal prohibition.

8. **Detection method**  
   How can pack-preflight detect the condition: direct PDF-object inspection, content-stream analysis, rendered edge analysis, geometry comparison, operator metadata, or a hybrid method?

9. **Confidence level**  
   Classify the result as:
   - **confirmed condition** — objective evidence is sufficient;
   - **production-risk warning** — evidence suggests risk but outcome depends on the workflow;
   - **ambiguous / operator review** — the file does not contain enough information for a safe automatic decision.

10. **Operator message**  
    What should the report actually tell the operator? Prefer a concrete production statement over a generic "PDF error" message.

11. **Suggested operator action**  
    What should be checked next: separation preview, RIP result, imposition proof, customer correction, plate identity, trim preview, etc. The tool should assist the operator rather than silently rewrite customer artwork.

12. **Regression tests**  
    Add at least one synthetic case that must trigger the rule and, where possible, one valid case that must not trigger it.

13. **Evidence provenance**  
    Record whether the rule came from:
    - maintainer field experience,
    - independent tester feedback,
    - published technical literature or standards,
    - vendor/OEM documentation,
    - or a combination.

14. **Implementation status**  
    Track whether the idea is only a field note, an open issue, under development, merged, or included in a downloadable beta.

## Example: false bleed

- **Production problem:** artwork stops at the trim line and a white edge appears after trimming.
- **Origin stage:** artwork/prepress.
- **PDF / job evidence:** a BleedBox may exist, but page-edge artwork may not extend beyond the TrimBox.
- **Trigger conditions:** an edge intended to bleed has insufficient artwork extension.
- **Press mechanism:** not primarily a press fault; normal print/cut register tolerances expose the missing extension.
- **Finishing consequence:** white hairline or unprinted edge after trimming.
- **Valid exceptions:** an intentionally white/non-bleeding page edge.
- **Detection method:** investigate rendered edge sampling plus vector/image geometry.
- **Confidence:** risk warning unless intent can be established reliably.
- **Operator message:** identify the affected page and edge, not merely "bleed error".
- **Suggested action:** inspect trim preview or request corrected artwork.
- **Regression tests:** true 3 mm artwork bleed; nominal BleedBox with artwork stopping at TrimBox; intentionally white edge.
- **Evidence provenance:** maintainer field experience plus external technical validation where available.
- **Implementation status:** tracked in the relevant GitHub issue.

## Example: composite/rich-black text

- **Production problem:** small black text is built from multiple process colors, increasing sensitivity to plate/register variation.
- **Origin stage:** artwork/prepress.
- **PDF / job evidence:** painted text uses a CMYK construction in which K is dominant but one or more C/M/Y components are also present.
- **Trigger conditions:** the construction becomes more production-sensitive as declared text size gets smaller. The current diagnostic uses 12 pt as a conservative prominence boundary, not as a universal printing law.
- **Press mechanism:** multiple process plates must fit accurately on the same glyph; small type makes visible color fringes or loss of crispness more likely when register varies.
- **Finishing consequence:** normally none directly; the defect is primarily a printed-image/readability issue.
- **Valid exceptions:** large display text or large headlines may intentionally use a controlled rich-black recipe such as C40 K100.
- **Detection method:** inspect text painting operations, text rendering mode, declared font size, and resolvable CMYK operands.
- **Confidence:** confirmed PDF construction; production severity remains workflow-dependent.
- **Operator message:** report page, CMYK recipe, declared text size, paint mode, and occurrence count.
- **Suggested action:** review separations and job intent rather than automatically rewriting the text.
- **Regression tests:** K-only small text; C40 K100 small text; C40 K100 large display text.
- **Evidence provenance:** maintainer field experience translated into a conservative diagnostic rule.
- **Implementation status:** implemented in source; public binary availability depends on the current release.

## Design principle

A PDF construction should not be labelled wrong merely because it differs from a default rule. The project should connect **file evidence -> production mechanism -> possible downstream consequence**, while preserving legitimate production choices and surfacing uncertainty to the operator.
