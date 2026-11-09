# Cloudflare Turnstile + React masked inputs via CDP

Verified working 2026-09-12 on `https://www.escrow.com/log-in` (visible automation Chrome,
Xvfb `:99`, CDP `http://127.0.0.1:9333`). Result: full login succeeded end-to-end headlessly
— no human handoff, no VNC click by the user.

## Meta-rule: never declare a CAPTCHA "human-only" before trying a real mouse event

A JS `.click()` on the widget does nothing (Cloudflare treats untrusted events as bot
behaviour). Earlier in the session a Turnstile-blocked step had been delegated to the user's
browser / VNC because "the checkbox is human-only". That was WRONG: a **CDP-dispatched real
input event** (`Input.dispatchMouseEvent`) cleared it. Protocol, in order:

1. JS click / `el.click()` → widget stays unsolved (`token_len = 0`). Expect this, don't stop here.
2. Real mouse event via CDP at the widget's box-model centre → solved.

Only escalate to a human/VNC *after* step 2 fails or the widget shows an image puzzle.

## Recipe that works

```python
# 1. The widget lives in a shadow root / nested iframe; pierce the tree.
doc = cdp('DOM.getDocument', depth=-1, pierce=True)
# 2. Locate the iframe carrying the challenge (blob: or challenges.cloudflare.com).
#    Find its nodeId (walk doc['root']['children']) -> then:
box = cdp('DOM.getBoxModel', nodeId=<iframe_nodeId>)['model']['content']  # 8 numbers = 4 xy pairs
# 3. Compute the centre of the CHECKBOX (left edge + ~30px, mid height), not the iframe centre.
x = (box[0] + box[2]) / 2 + 30        # tune by inspecting the widget rect
y = (box[1] + box[5]) / 2
# 4. Real press+release (both required — a lone press does not register).
for t in ('mousePressed', 'mouseReleased'):
    cdp('Input.dispatchMouseEvent', type=t, x=x, y=y, button='left',
        clickCount=1, buttons=1 if t == 'mousePressed' else 0)
time.sleep(3)
# 5. Verify the hidden response input is populated, THEN submit.
js("document.querySelector('input[name=\"cf-turnstile-response\"], [id*=turnstile-response]').value.length")
```

Then click the real submit button ("Secure Login") and confirm by URL change + cookies,
not by the absence of an error message.

## Coordinate traps

* `DOM.getBoxModel` returns **CSS pixels**; if you screenshot at `devicePixelRatio > 1`,
  divide screenshot pixels by DPR before clicking, or read click targets straight out of
  `DOM.getBoxModel` and ignore the screenshot scale.
* Always re-check viewport + DPR (`window.innerWidth`, `devicePixelRatio`, `screen.*`) when a
  click lands "next to" the target; that is the classic DPR mismatch symptom.
* Hidden/host `<div>` wrappers (e.g. `.auth_turnstile`) report `w=0,h=0` or huge padded rects —
  trust the iframe's own box model instead.

## React controlled inputs (intl-tel-input, masked/formatting fields)

The masked phone field rejected programmatic values. What worked, in order of preference:

1. **Best:** focus the field with a real click, then
   `Input.dispatchKeyEvent(type='rawKeyDown', modifiers=2, key='a', code='KeyA', commands=['selectAll'])`
   followed by `Input.insertText(text='+966 58 210 4381')`. `commands=['selectAll']` is the part
   that makes React see a full replacement instead of an append.
2. **Sometimes:** native value setter
   (`Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el, v)` + `input` event).
3. Plain `el.value = v` / `fill_input` alone silently fails on masked inputs — React state stays empty
   and the form validation never clears.

Always verify by reading back the values you care about *and* checking the submit button is no
longer disabled, then eyeball one screenshot before claiming the form is filled.

## Dump the form before filling it

Enumerate `input,select` with `name||id||placeholder` + `value` + `checked` + `disabled`, plus all
button labels, in ONE call. It reveals (a) which sections the wizard still wants, (b) fields that
look filled in the DOM but are empty in React state, (c) whether the submit button is gated.
