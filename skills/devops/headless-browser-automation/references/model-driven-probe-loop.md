# Model-driven browser probe loop (automated QA at volume)

Condensed from Jason Arbon, "I Put Jev in a Playwright Browser Testing Loop"
(jarbon.substack.com, 2026-09-20; paid post, the method below is from the free part). Found
via a LinkedIn share. This is the automated, high-volume sibling of manual exploratory
dogfooding: instead of a human clicking through flows, a controller drives Playwright and a
decision model picks the next probe and rules on each result.

## The pattern

A Node controller + Playwright + dashboard + FFmpeg. Per probe the controller makes **two
model calls**:

1. **Action choice** -- given the executable probe menu, "which action should I take next?"
   (a Choice question over the probe vocabulary).
2. **Verdict** -- given the observed result, "does this violate the stated requirement?"
   (a Noul / yes-no question returning a calibrated confidence).

Result quoted in the post: **63 browser probes in 24.3 seconds** against a deliberately
broken storefront.

## The two load-bearing design decisions

* **The model never receives screenshots.** The controller sends page TEXT plus structured
  observations (product name, quantity, price, line totals, status messages). This stays
  cheap and fast precisely because no vision model is in the loop -- keep the extractor
  structured and deterministic rather than dumping raw HTML.
* **The human supplies the probe vocabulary; the model only chooses.** Probes are concrete
  and executable (negative quantity, duplicate coupon, malformed email, missing required
  field, quantity beyond stock, currency/total mismatch...). Everything else is ordinary
  software. A model choosing among known-good actions is far more reliable than a model
  inventing actions, and the probe menu doubles as the coverage statement shown to a client.

## What a build here needs

Playwright, a structured page-text/state extractor, a declared probe menu, the requirements
written out in plain text, and a confidence threshold deciding when a verdict is trustworthy
versus escalated to a human. Verify the model's current rate card before pricing anything:
public pricing pages for these vendors have 404'd, so read the console Usage page instead of
guessing at margin.

## Where it maps for us

Sellable as an automated functional-QA sweep added to client website delivery, and as a
recurring check after each content or catalogue change. The cheapest honest demo target is a
storefront we already own -- run the loop against our own Shopify store, record the probe
report, and show that artefact instead of describing it. Do not promise coverage the probe
menu does not actually contain.
