export const FIELDS = ['name', 'email', 'password', 'confirm', 'terms'];
export const LABELS = {name: 'Full name', email: 'Email', password: 'Password', confirm: 'Confirm password', terms: 'Accept the terms'};

export function initialState() {
  return {values: {name: '', email: '', password: '', confirm: '', terms: false}, touched: {}, submitAttempted: false, status: 'idle', serverError: null, focus: null};
}

export function validate(values) {
  const errors = {};
  const name = values.name.trim();
  if (!name) errors.name = 'Enter your full name.';
  else if (name.length > 80) errors.name = 'Full name must be at most 80 characters.';
  if (!/^[^\s@]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+$/i.test(values.email.trim())) errors.email = 'Enter an email with a local part and dotted domain.';
  if (values.password.length < 10 || !/[a-z]/i.test(values.password) || !/[0-9]/.test(values.password)) errors.password = 'Password needs at least 10 characters, a letter and a digit.';
  if (values.confirm !== values.password) errors.confirm = 'Confirm password must match your password.';
  if (!values.terms) errors.terms = 'Accept the terms to continue.';
  return errors;
}

export function update(state, action) {
  switch (action.type) {
    case 'input': return {...state, values: {...state.values, [action.field]: action.value}, serverError: null, focus: null, status: state.status === 'submitting' ? 'submitting' : 'idle'};
    case 'blur': return {...state, touched: {...state.touched, [action.field]: true}};
    case 'submit': {
      if (state.status === 'submitting') return state;
      const errors = validate(state.values);
      const focus = FIELDS.find(field => errors[field]) ?? null;
      return {...state, submitAttempted: true, serverError: null, focus, status: focus ? 'invalid' : 'submitting'};
    }
    case 'failure': return {...state, status: 'error', serverError: action.message, focus: null};
    default: return state;
  }
}

function escape(value) {
  return String(value).replace(/[&<>"']/g, character => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[character]));
}

export function render(state) {
  const errors = validate(state.values);
  const visible = Object.fromEntries(Object.entries(errors).filter(([field]) => state.touched[field] || state.submitAttempted));
  let html = '<form class="signup">';
  if (state.status === 'invalid' && Object.keys(visible).length) html += `<div role="alert">${Object.values(visible).map(escape).join(' ')}</div>`;
  if (state.status === 'error' && state.serverError) html += `<div role="alert">${escape(state.serverError)}</div>`;
  for (const field of FIELDS) {
    const type = field === 'terms' ? 'checkbox' : field === 'email' ? 'email' : ['password', 'confirm'].includes(field) ? 'password' : 'text';
    const autocomplete = field === 'name' ? 'name' : field === 'email' ? 'email' : type === 'password' ? 'new-password' : null;
    const error = visible[field];
    html += `<label for="signup-${field}">${LABELS[field]}</label><input id="signup-${field}" name="${field}" type="${type}"`;
    if (autocomplete) html += ` autocomplete="${autocomplete}"`;
    if (field === 'name' || field === 'email') html += ` value="${escape(state.values[field])}"`;
    if (field === 'terms' && state.values.terms) html += ' checked';
    if (error) html += ` aria-invalid="true" aria-describedby="signup-${field}-error"`;
    html += '>';
    if (error) html += `<span id="signup-${field}-error">${escape(error)}</span>`;
  }
  html += `<button type="submit"${state.status === 'submitting' ? ' disabled' : ''}>Sign up</button></form>`;
  return html;
}
