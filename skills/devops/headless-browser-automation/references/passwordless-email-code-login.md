# Passwordless email-code console login (agent-completable)

Proven end-to-end 2026-09-21 on `console.typesafe.ai` (Next.js console): email entry ->
"Our code has been sent. It expires in 15 minutes" -> code read from Gmail via himalaya ->
Verify -> logged in -> API key minted in a console dialog. No human step.

Use this class of recipe whenever a provider console offers "email me a code instead" /
magic-code login AND we already hold IMAP access to that mailbox (see the `himalaya` and
`hermes-email-access` skills for the mailbox side). It is a login into the user's OWN
account at his request -- not credential guessing. If the mailbox is unknown or the flow
demands a password/CAPTCHA/OTP to a phone we do not hold, stop and ask the user instead.

## Steps

1. Open the login page in a CDP-driven tab and enumerate it before acting:
   read the form (input names, placeholders) and the button labels. Print only labels --
   never the whole DOM, which may already contain a session token.
2. Fill the email field with a native setter, not `el.value = x`. React / server-action
   forms submit an empty value otherwise:
   ```js
   const i = document.querySelector('input[name=email]');
   const s = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
   s.call(i, '<address>');
   i.dispatchEvent(new Event('input', {bubbles:true}));
   i.dispatchEvent(new Event('change', {bubbles:true}));
   ```
3. Click the "Email me a code instead" button (exact label match on `innerText`), then
   confirm the "code has been sent" banner appears. Do not assume the click landed.
4. Wait ~10-15s, then find the message. List the mailbox and pick the message whose
   SUBJECT matches the code mail. Pitfall: product marketing/newsletter mail for the same
   product often arrives in the same minute -- selecting by date alone picks the wrong one.
5. Read the body, then extract the code defensively: strip `<style>...</style>` blocks
   FIRST (hex colours and sizes in CSS contribute 6-digit runs and poison a naive
   `\b\d{6}\b` search), unwrap quoted-printable soft line breaks (`=\r\n`), strip tags,
   then collect candidates. When more than one candidate survives, take the most frequent
   and sanity-check it sits near words like "code" / "expires".
6. Fill the code input with the same native-setter pattern, click Verify, then PROVE the
   login: read `location.href` and a logged-in-only marker (account or workspace name
   shown in the console shell). A changed URL is not proof.
7. Mint the credential from the UI: Keys page -> "Create key" -> dialog
   `input[name=name]` -> submit. Expect the key to be displayed once; capture it now.

## Secret hygiene while driving a browser (reusable, not TypeSafe-specific)

The user reads this transcript. A credential that appears in a tool result is disclosed.

* Mask inside the JS you evaluate, so the raw value never leaves the page process:
  ```js
  document.body.innerText.replace(/[A-Za-z0-9_\-]{20,}/g,
    m => m.slice(0,4) + '…[' + m.length + ']')
  ```
  This keeps the page readable for debugging while showing only a prefix and a length.
* To persist the real value: capture the CLI's stdout into a shell variable, write it to a
  `chmod 600` file, and print only a masked confirmation. Never `echo` the variable.
* Pipe any command that might echo a key through a masker:
  `... | sed -E 's/[A-Za-z0-9_-]{20,}/[REDACTED]/g'`
* Then put it in the vault (`vault set <space> KEY=value`) and verify by USING it: a live
  authenticated call returning 200 is the only acceptable proof.

## CDP driving quirks hit this session

* `PUT /json/new?url=<percent-encoded>` can create the tab yet leave it on `about:blank`;
  navigate it explicitly afterwards by tab INDEX. Do not grep the tab list for the target
  URL when the page has not settled -- match by index from `tabs` output instead.
* Keep a dedicated debug-port Chrome for this; the harness' own browser may be running
  `--no-startup-window`, in which case driving the already-running Chrome over CDP is the
  faster path than starting a second browser.
* Leave a logged-in tab alone once authenticated: session cookies persist, but the console
  UI state does not survive a re-navigation mid-flow.
