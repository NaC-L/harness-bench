Repair `src/signup.js`, the validation, immutable state transitions and HTML renderer for a server-rendered sign-up form. Do not change tests or package.json; no packages, network or services are required. Preserve the exported FIELDS and LABELS and the initialState(), validate(values), update(state, action), render(state) API.

Values always have string name/email/password/confirm and boolean terms. initialState returns fresh values, empty touched, submitAttempted=false, status='idle', serverError=null, focus=null.

Validation returns an object mapping invalid field names to nonempty actionable messages, with no entries for valid fields. Name trimmed length is 1..80. Email is checked after trimming: one @, nonempty local part without whitespace, a dotted domain with nonempty labels containing only letters/digits/hyphens. Local plus-addressing is accepted. Password is at least 10 characters and includes an ASCII letter and digit. Confirm must exactly match password. Terms must be true. Each error names its field (name, email, password, confirm or terms); password error explains the 10-character, letter and digit rules; name error explains the 80-character maximum when exceeded. Validation never mutates values.

update is pure: never mutate the input state or nested objects. Unknown actions return state unchanged. Known actions:
- input {field,value}: replace that field, clear serverError and focus, and return status to idle unless currently submitting. Keep touched and submitAttempted.
- blur {field}: mark that field touched.
- submit: ignore while submitting. Otherwise mark submitAttempted=true, clear serverError, validate, set status='invalid' and focus to the first invalid field in FIELDS order, or status='submitting' and focus=null when valid.
- failure {message}: status='error', serverError=message, focus=null, preserving ALL values and touched/submission flags.
Action fields are always members of FIELDS; input values have the correct type. Network submission, success navigation and DOM focus execution are outside this renderer's scope; focus is an instruction to its consumer.

render returns a single semantic form. Every field is an input with its field name and unique nonempty id, an associated visible label (for/id or enclosing label), and an appropriate type: text/name, email/email, password/password and confirm, checkbox/terms. Autocomplete is name, email and new-password for both password controls. Name/email values and terms checked state are preserved; password values must never be placed in HTML. Escape all user-controlled text and attribute values, including server errors.

Do not show validation messages on a pristine form. Show each error only after its field is blurred or a submission attempted. Invalid visible controls have aria-invalid='true' and aria-describedby referencing an existing nonempty error element; valid controls have no true aria-invalid or stale error description. A failed submission announces all validation messages in a role='alert' summary. A server failure announces its message in a role='alert'. Idle pristine form has no alert. Use a real button type='submit', labeled Sign up, disabled only while submitting. No inline event handlers or alert() popups.

This fixture grades rendered semantics and state behavior, not browser layout, contrast, actual keyboard/focus execution or subjective design quality.
