# Copy-claim integrity after a link swap (worked case: AZ tender wave 2)

Context: a client Pages site (`az-consultants`) was deleted and the campaign's link repointed to a
surviving sibling (`azconsultants-india.pages.dev`). The link audit passed (whole-tree grep 0 hits,
xlsx rebuilt, 41 refs updated, 0 dead) — **and the wave was still dishonest**, because the copy had
always promised the old page's *content*. A 200 on the new URL says nothing about what is on it.

## The three defects found (all after a "clean" link audit)

1. **Email body claimed the new page hosts the funnel assets.**
   Old line: "*…the tender map, the buyer groups that outsource this work and the 14-point
   compliance pass are also open here: <link>*" — true of the deleted funnel site, false of a
   brochure page.
2. **xlsx row advertised a gated document at a URL that is not gated.**
   `Gated funnel document | azconsultants-india.pages.dev/funnel` — the path 200s (so a link
   checker passes) but opens the plain brochure.
3. **The fulfilment file itself was gone.** The copy tells prospects to "reply BID" and a funnel
   file gets sent; that file had lived under the deleted tree, so disk had none (only the tar).

## Claim-vs-page check (run it, don't reason about it)

```bash
curl -sL https://<new-target>/ > /tmp/target.html
for k in 'tender map' 'buyer group' '14-point' 'compliance'; do
  printf '%s -> %s\n' "$k" "$(grep -ci "$k" /tmp/target.html)"
done        # all 0 = the copy is promising content the page does not carry
```

If the target is the old *funnel* file rather than the site, the same grep must return >0 — that is
what makes the reframed copy true:

```bash
grep -c -e 'buyer' -e 'tender map' -e '14-point' AZ_Tender_Funnel_India.html   # >0 each
grep -c 'az-consultants\.pages\.dev' AZ_Tender_Funnel_India.html                # MUST be 0 (self-contained)
grep -c 'https\?://' AZ_Tender_Funnel_India.html                                # channel count → 143
```

## The reframe that shipped (promise → reply, page → background)

> "*…send our Pan-India tender funnel file — 143 live channels (GeM, CPPP, PSU, state, defence,
> healthcare, railways), the working tender map, the buyer groups that outsource this work and the
> 14-point compliance pass, plus the projects I am tracking this month. No fee, no pitch. Background
> on the practice: `https://azconsultants-india.pages.dev`*"

Rule: every concrete noun in the pitch must be reachable by the action the pitch asks for. The site
link may only carry what a plain brochure genuinely is ("who I am / what I do").

## Attachment row relabel (source + generated artifact)

Patch the builder constant, not the workbook:

```python
# mkxlsx2.py — before
{"doc": "Gated funnel document", "link": f"{SITE}/funnel"}
# after
{"doc": 'Funnel file (on reply "BID")', "link": "emailed as attachment"}
```

Then rebuild and prove it, because the dead-link count alone cannot see a false label:

```python
import zipfile, re
blob = ''.join(zipfile.ZipFile('AZ_Tender_Outreach_List.xlsx').read(n).decode('utf8','ignore')
               for n in zipfile.ZipFile('AZ_Tender_Outreach_List.xlsx').namelist() if n.endswith('.xml'))
print('gated-label', len(re.findall('Gated funnel document', blob)),   # 0
      'funnel-file', len(re.findall('Funnel file', blob)),             # 1
      'new-link', len(re.findall('azconsultants-india', blob)),        # 41
      'dead-link', len(re.findall('az-consultants\\.pages\\.dev', blob)))  # 0
```

## Restoring the deleted fulfilment asset

```bash
tar tzf ~/backups/az_consultants_20260911_2230.tar.gz | grep -i funnel     # confirm it is in the tar
tar xzf ~/backups/az_consultants_20260911_2230.tar.gz -C /home/ubuntu \
    az_consultants/site/funnel.html
cp /home/ubuntu/az_consultants/site/funnel.html ~/az_consultants/outreach/AZ_Tender_Funnel_India.html
```

Offer a PDF of it (attach-on-reply becomes trivial). Also re-check that the file is not carrying
other deleted-domain refs, and that it is the *current* copy the email describes.

## Preview card: every number computed in the same run

The preview screenshot / user summary is a factual claim about the campaign. Build it from a script
that prints the derived values, not from memory:

```python
import importlib.util, json
spec = importlib.util.spec_from_file_location('t', 'tmpl.py'); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
leads = json.load(open('sms_send2.json'))
print('HTML', len(m.body(leads[0])),
      '| sms', [len(m.sms(l)) for l in leads][:3],
      '| max sms', max(len(m.sms(l)) for l in leads),
      '| funnel channels', open('AZ_Tender_Funnel_India.html').read().count('http'))
```

Final shipped line: `HTML 4940 | sms [144, 158, 155] | body 1469` — and the email-body tail was
`repr()`-checked to prove the reframe actually landed in the rendered bytes.

## Long-line patch pitfall (why the edits needed short anchors)

Patching a whole email paragraph as one quoted string in a shell/heredoc command can arrive
truncated → partial match → exit 1 (or worse, a silently truncated paragraph). Two workarounds used:

- patch a SHORT unique anchor inside the line (`"\n\nhttps://az-consultants.pages.dev"`), or
- bridge the tail with a regex: `re.sub(r'practice\..*?(https://<domain>[^\s]*)"', new, src, flags=re.S)`

then verify with counts + a re-render (`old 0 | new 1`, `len(body())`, tail repr). Exit 0 is not
evidence.
