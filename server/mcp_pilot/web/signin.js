// Last updated: 2026-11-16 · Codex · Managed Neon OTP and OAuth consent.
import { createAuthClient } from '@neon/auth';

const $ = id => document.getElementById(id);
let auth, config, invitedEmail = '';
const query = new URLSearchParams(window.location.search);
const oauth = query.has('client_id');
const message = (text, error = false) => { $('status').textContent = text; $('status').classList.toggle('error', error); };
const show = id => { for (const name of ['email-form', 'code-form', 'consent', 'ready']) $(name).hidden = name !== id; };
const busy = value => { for (const button of document.querySelectorAll('button')) button.disabled = value; };
const check = result => { if (result?.error) throw new Error(result.error.message || 'Sign-in could not be completed. Please try again.'); return result?.data; };
async function invited(email) {
  const response = await fetch('/api/invitation', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email }) });
  if (!response.ok) throw new Error('We could not check your invitation. Please try again.');
  return (await response.json()).invited === true;
}
function ready() {
  $('card-title').textContent = 'Your connection is ready';
  $('description').textContent = 'Add this address to your own ChatGPT account. You’ll approve the connection there.';
  $('mcp-url').value = config.resource;
  message('Signed in with your invited email.'); show('ready');
}
async function resume() {
  const data = check(await auth.getSession());
  if (!data?.user) { message(''); show('email-form'); return; }
  if (!await invited(data.user.email) || data.user.emailVerified !== true) {
    await auth.signOut(); message('This email needs a verified invitation. Use the address on your invitation.', true); show('email-form'); return;
  }
  if (!oauth) { ready(); return; }
  if (query.get('resource') !== config.resource) throw new Error('This connection requested an unexpected resource. Return to ChatGPT and add the MeatCODE address again.');
  if (window.location.pathname !== '/auth/consent') {
    message('Continuing your secure connection…');
    check(await auth.oauth2.continue({ selected: true }));
    return;
  }
  const client = check(await auth.oauth2.publicClient({ query: { client_id: query.get('client_id') } }));
  $('card-title').textContent = 'Allow this connection?';
  $('description').textContent = 'You are connecting your invited account to the application below.';
  $('client-name').textContent = client?.client_name || 'MCP application';
  try { $('return-host').textContent = new URL(query.get('redirect_uri')).host; }
  catch { $('return-host').textContent = 'Return address provided by the application'; }
  $('permissions').textContent = (query.get('scope') || '').split(' ').filter(Boolean).join(', ');
  message('Signed in. Review the application before continuing.'); show('consent');
}
$('email-form').addEventListener('submit', async event => {
  event.preventDefault(); busy(true);
  try {
    invitedEmail = $('email').value.trim().toLowerCase();
    if (!await invited(invitedEmail)) throw new Error('This email is not on the invitation list. Please contact Lior for access.');
    check(await auth.emailOtp.sendVerificationOtp({ email: invitedEmail, type: 'sign-in' }));
    show('code-form'); $('code').focus(); message('Check your inbox for a sign-in code. It may also arrive in spam.');
  } catch (error) { message(error.message, true); } finally { busy(false); }
});
$('code-form').addEventListener('submit', async event => {
  event.preventDefault(); busy(true);
  try {
    const data = check(await auth.signIn.emailOtp({ email: invitedEmail, otp: $('code').value.trim() }));
    $('code').value = '';
    if (!data?.redirect) await resume();
  } catch (error) { message(error.message, true); } finally { busy(false); }
});
$('change-email').addEventListener('click', () => { $('code').value = ''; show('email-form'); message(''); });
for (const [id, accept] of [['allow', true], ['deny', false]]) $(id).addEventListener('click', async () => {
  busy(true);
  try { check(await auth.oauth2.consent({ accept })); }
  catch (error) { message(error.message, true); busy(false); }
});
$('copy').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText(config.resource); message('Connection address copied.'); }
  catch { $('mcp-url').select(); message('Select and copy the address above.'); }
});
try {
  const response = await fetch('/api/config');
  if (!response.ok) throw new Error('The connection is not ready. Please try again shortly.');
  config = await response.json(); auth = createAuthClient(config.issuer);
  await resume();
} catch (error) { message(error.message || 'Secure sign-in is temporarily unavailable.', true); }
