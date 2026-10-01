// Server-rendered sign-up form: state transitions, validation and HTML rendering.

export const FIELDS = ['name', 'email', 'password', 'confirm', 'terms'];

export const LABELS = {
  name: 'Full name',
  email: 'Email',
  password: 'Password',
  confirm: 'Confirm password',
  terms: 'Accept the terms',
};

export function initialState() {
  return {
    values: { name: '', email: '', password: '', confirm: '', terms: false },
    touched: {},
    submitAttempted: false,
    status: 'idle',
    serverError: null,
    focus: null,
  };
}

const EMAIL = /^[a-z0-9.]+@[a-z]+\.[a-z]+$/;

export function validate(values) {
  const errors = {};
  if (!values.name.trim()) errors.name = 'Required';
  else if (values.name.trim().length > 80) errors.name = 'Too long';
  if (!EMAIL.test(values.email)) errors.email = 'Invalid';
  if (values.password.length < 8) errors.password = 'Too short';
  if (values.confirm !== values.password) errors.confirm = 'Passwords do not match';
  if (!values.terms) errors.terms = 'Required';
  return errors;
}

export function update(state, action) {
  switch (action.type) {
    case 'input':
      state.values[action.field] = action.value;
      return state;
    case 'blur':
      state.touched[action.field] = true;
      return state;
    case 'submit': {
      state.submitAttempted = true;
      const errors = validate(state.values);
      state.status = Object.keys(errors).length ? 'invalid' : 'submitting';
      return state;
    }
    case 'failure':
      state.status = 'error';
      state.serverError = action.message;
      state.values = initialState().values;
      return state;
    default:
      return state;
  }
}

export function render(state) {
  const errors = validate(state.values);
  const v = state.values;
  let html = '<form class="signup">';
  if (state.status === 'invalid') html += '<div class="errors">Please fix the errors below.</div>';
  for (const field of ['name', 'email', 'password', 'confirm']) {
    const type = field === 'password' || field === 'confirm' ? 'password' : 'text';
    html += `<input type="${type}" name="${field}" placeholder="${LABELS[field]}" value="${v[field]}">`;
    if (errors[field]) html += `<span class="error">${errors[field]}</span>`;
  }
  html += `<input type="checkbox" name="terms"> ${LABELS.terms}`;
  if (errors.terms) html += `<span class="error">${errors.terms}</span>`;
  html += '<div class="button" onclick="submitSignup()">Sign up</div>';
  html += '</form>';
  return html;
}
