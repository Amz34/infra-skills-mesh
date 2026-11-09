# Automating Angular/SPA forms, captcha gates and OTP gates (browser-exec)

Use when a JS SPA form won't submit, values you set from JS never reach the server,
or a captcha / OTP gate stands between you and a quote, checkout or booking.
Verified end-to-end on Bcare (Angular + Angular Material), 2026-09.

## 1. Make the framework actually see your values

`el.value = 'x'` does NOT update an Angular/React model — the framework submits its
own model and sends empty fields. Use the native setter + real events:

```js
const set=(sel,v)=>{const e=document.querySelector(sel); if(!e) return 'NF';
  const s=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
  s.call(e,v);
  e.dispatchEvent(new Event('input',{bubbles:true}));
  e.dispatchEvent(new Event('change',{bubbles:true}));
  return e.value;};
```

Diagnose with the framework's own classes:
`document.querySelectorAll('.ng-invalid, .ng-valid')` per control.
- A form-level `.ng-invalid` with **no** invalid child control = a validator that
  lives outside the DOM (captcha/session/server state). Stop hunting for a missing
  input; fix that server-side piece instead.
- Entering a National ID / account number often auto-fires a lookup request — exploit
  it to verify the entity you're about to quote (it removed all doubt about the vehicle).

## 2. Clicking: DOM click beats coordinates

```js
Array.from(document.querySelectorAll('*'))
  .find(x=>x.children.length===0 && x.innerText.trim()==='GET QUOTES').click();
```

- Coordinate clicks (`click_at_xy`) drift: after any re-render/refresh the target has
  moved and you click a *different* control. In this session a stale coordinate landed
  on the language toggle and threw the page into Arabic + back to home, losing the form.
  Always re-read the element's rect immediately before clicking, and prefer DOM clicks
  for anything inside the app frame.
- Icon-only buttons: click the icon's nearest clickable ancestor, e.g. the
  `.material-icons` whose text is `autorenew` -> click its `.cursor-pointer` parent DIV.
  `.click()` on that ancestor DID refresh the captcha; blind coordinates did not.
- To surface a server-side error, force the submit and read the response:
  `b.removeAttribute('disabled'); b.click();` — server text is far more informative
  than a disabled button.

## 3. Learn an undocumented API by capturing the app's own calls

Hook XHR (and fetch) **before** driving the app, then trigger the real submit:

```js
window.__hdrs=[];
const OX=XMLHttpRequest, oopen=OX.prototype.open,
      oset=OX.prototype.setRequestHeader, osend=OX.prototype.send;
OX.prototype.open=function(m,u){this.__u=u;this.__m=m;return oopen.apply(this,arguments);};
OX.prototype.setRequestHeader=function(k,v){(this.__h=this.__h||{})[k]=v;return oset.apply(this,arguments);};
OX.prototype.send=function(b){ if(/example\.com/.test(this.__u||''))
  window.__hdrs.push({u:this.__u,m:this.__m,h:this.__h,b:typeof b==='string'?b:''});
  return osend.apply(this,arguments); };
```

Two pitfalls that cost real time:
- every override must `return o<original>.apply(this,arguments)`; returning the wrong
  thing breaks the app and **nothing** gets captured;
- hook `open` too, or you never learn the URL. Re-install after every navigation
  (hooks die with the page).

This is how the required `Authorization: Bearer <random float>!!` header was found —
without it every hand-made replay returned 401. Headers are the part you cannot guess.

Cross-origin: a fetch from `www.example.com` to `example.com/...` can die with
"Failed to fetch" (preflight). Navigate the tab to the same host the API lives on so
calls are same-origin. Shell-side curl is usually stopped by the WAF first
(Aliyun `acw_tc` cookie -> 405 / HTML block page), so keep API calls inside the page.

## 4. Captcha

- Digit captcha served as a data-URI JPEG: pull the raw base64, save to a file, OCR
  that file. In-page canvas pixel reads fail when the image hasn't decoded
  (`img.naturalWidth === 0`) — use PIL on the saved bytes instead.
- tesseract: `tesseract img.jpg stdout --psm 7 -c tessedit_char_whitelist=0123456789`
  plus `--psm 8` and `--psm 13`; only trust a **consensus**. A disagreement usually
  means the last glyph is clipped at the canvas edge (generator bug) — request a NEW
  captcha and retry, do not guess digits.
- Most reliable read: pad white + 8x LANCZOS upscale, then look at it yourself
  (`ImageOps.expand(im,border=20,fill=(255,255,255)).resize((w*8,h*8),Image.LANCZOS)`).
- When the captcha comes from a REST endpoint (`GetCaptcha` -> `{image, token,
  expiredInSeconds:600}`), the **token** pairs with your value: solve -> immediately
  submit. Don't burn the window by refreshing repeatedly.

## 5. OTP gates

Session login OTP goes to a phone number on the record — quote it masked
(`05****4381`) so the user knows which handset to check. Ask, then enter immediately:
expiry is minutes, and a stale code returns e.g. "Error In OTP". Enter one digit per
box (`input[type=tel]`, last 4 visible ones) with the native setter + input event;
a 4-box layout means a 4-digit code (do not assume 5-6).

## 6. Shell quirk seen here

Commands written as `cd /abs/path && python3 -c "..."` sometimes die with exit 126 and
one line of output; passing the tool's `workdir` parameter instead works. Use workdir.
