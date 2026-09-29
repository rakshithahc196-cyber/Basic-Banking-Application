import { useEffect, useState, type FormEvent } from 'react'
import {
  ArrowDownLeft,
  ArrowLeftRight,
  ArrowRight,
  ArrowUpRight,
  BadgeCheck,
  Check,
  ChevronRight,
  CircleHelp,
  Clock3,
  Copy,
  CreditCard,
  Eye,
  EyeOff,
  History,
  Landmark,
  LoaderCircle,
  LogOut,
  Plus,
  ShieldCheck,
  UserRound,
  Wallet,
  X,
} from 'lucide-react'

type Account = {
  id: number
  account_number: string
  balance: string
  created_at: string
  owner_name: string
  owner_email: string
}

type Transaction = {
  id: number
  type: 'DEPOSIT' | 'WITHDRAW' | 'TRANSFER_DEBIT' | 'TRANSFER_CREDIT'
  amount: string
  status: string
  reference_id: string
  created_at: string
}

type TokenResponse = { access_token: string; token_type: string }
type Operation = 'deposit' | 'withdraw' | 'transfer'
type View = 'dashboard' | 'transactions' | 'account'

class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

const TOKEN_KEY = 'northline_access_token'
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''
const currency = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
})

async function request<T>(path: string, token?: string | null, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, headers })
  } catch {
    throw new ApiError('The banking service is unavailable. Check that the API is running.', 0)
  }

  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    const fallback = response.status === 401
      ? 'Your session has expired. Please sign in again.'
      : response.status === 409
        ? 'An account with this email already exists.'
        : response.status === 422
          ? 'Check the details and try again.'
          : response.status >= 500
            ? 'Something went wrong on our side. Please try again.'
            : 'We could not complete that request.'
    throw new ApiError(typeof body.detail === 'string' ? body.detail : fallback, response.status)
  }
  return body as T
}

function formatMoney(value: string | number) {
  return currency.format(Number(value))
}

function initials(name: string) {
  return name.split(/\s+/).map((part) => part[0]).slice(0, 2).join('').toUpperCase()
}

function transactionLabel(type: Transaction['type']) {
  return {
    DEPOSIT: 'Deposit',
    WITHDRAW: 'Withdrawal',
    TRANSFER_DEBIT: 'Transfer sent',
    TRANSFER_CREDIT: 'Transfer received',
  }[type]
}

function transactionIcon(type: Transaction['type']) {
  if (type === 'DEPOSIT' || type === 'TRANSFER_CREDIT') return <ArrowDownLeft size={18} />
  return <ArrowUpRight size={18} />
}

function isCredit(type: Transaction['type']) {
  return type === 'DEPOSIT' || type === 'TRANSFER_CREDIT'
}

function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY))
  const [account, setAccount] = useState<Account | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [view, setView] = useState<View>('dashboard')
  const [operation, setOperation] = useState<Operation | null>(null)
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const [submitting, setSubmitting] = useState(false)
  const [showBalance, setShowBalance] = useState(true)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!token) return

    const controller = new AbortController()
    Promise.all([
      request<Account>('/api/accounts/me', token, { signal: controller.signal }),
      request<{ items: Transaction[] }>('/api/accounts/transactions', token, { signal: controller.signal }),
    ]).then(([nextAccount, history]) => {
      setAccount(nextAccount)
      setTransactions(history.items)
      setError('')
    }).catch((reason: unknown) => {
      if (reason instanceof ApiError && reason.status === 401) {
        sessionStorage.removeItem(TOKEN_KEY)
        setToken(null)
        setAccount(null)
        setTransactions([])
        setError('Your session ended. Sign in to continue.')
      } else if (!(reason instanceof DOMException && reason.name === 'AbortError')) {
        setError(reason instanceof Error ? reason.message : 'Unable to load your account.')
      }
    })

    return () => controller.abort()
  }, [token])

  async function handleAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    const form = new FormData(event.currentTarget)
    const payload = {
      email: String(form.get('email') ?? '').trim(),
      password: String(form.get('password') ?? ''),
      ...(authMode === 'register' ? { name: String(form.get('name') ?? '').trim() } : {}),
    }
    try {
      if (authMode === 'register') {
        await request('/api/auth/register', null, { method: 'POST', body: JSON.stringify(payload) })
      }
      const result = await request<TokenResponse>('/api/auth/login', null, {
        method: 'POST',
        body: JSON.stringify({ email: payload.email, password: payload.password }),
      })
      sessionStorage.setItem(TOKEN_KEY, result.access_token)
      setToken(result.access_token)
      setView('dashboard')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to sign in right now.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleOperation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!operation || !token) return
    setSubmitting(true)
    setError('')
    const form = new FormData(event.currentTarget)
    const payload: Record<string, string> = { amount: String(form.get('amount') ?? '') }
    if (operation === 'transfer') payload.recipient_account_number = String(form.get('recipient') ?? '').trim()

    try {
      const result = await request<{ message: string; balance: string; transaction: Transaction }>(`/api/accounts/${operation}`, token, {
        method: 'POST',
        body: JSON.stringify(payload),
      })
      setAccount((current) => current ? { ...current, balance: result.balance } : current)
      setTransactions((current) => [result.transaction, ...current])
      setNotice(result.message)
      setOperation(null)
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 401) {
        sessionStorage.removeItem(TOKEN_KEY)
        setToken(null)
        setAccount(null)
        setTransactions([])
      }
      setError(reason instanceof Error ? reason.message : 'Unable to complete this transaction.')
    } finally {
      setSubmitting(false)
    }
  }

  async function logout() {
    if (token) {
      try {
        await request('/api/auth/logout', token, { method: 'POST' })
      } catch {
        setNotice('Signed out on this device.')
      }
    }
    sessionStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setAccount(null)
    setTransactions([])
    setOperation(null)
  }

  async function copyAccountNumber() {
    if (!account) return
    try {
      await navigator.clipboard.writeText(account.account_number)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch {
      setNotice(`Account number: ${account.account_number}`)
    }
  }

  if (!token) {
    return (
      <main className="auth-layout">
        <section className="auth-story" aria-label="Northline Banking">
          <a className="brand brand-light" href="#home" aria-label="Northline home">
            <span className="brand-mark"><Landmark size={20} /></span>
            <span>northline<span className="brand-period">.</span></span>
          </a>
          <div className="story-copy">
            <p className="eyebrow">PERSONAL BANKING, MADE CLEAR</p>
            <h1>Your money,<br />in good order.</h1>
            <p>Everyday banking with a little more breathing room.</p>
          </div>
          <div className="story-foot"><ShieldCheck size={16} /> Secure access, wherever you are</div>
          <div className="auth-lines" aria-hidden="true"><i /><i /><i /><i /><i /></div>
        </section>
        <section className="auth-panel">
          <div className="auth-mobile-brand brand">
            <span className="brand-mark"><Landmark size={20} /></span><span>northline<span className="brand-period">.</span></span>
          </div>
          <div className="auth-form-wrap">
            <p className="eyebrow">NORTHLINE BANKING</p>
            <h2>{authMode === 'login' ? 'Welcome back' : 'Open your account'}</h2>
            <p className="auth-subtitle">{authMode === 'login' ? 'Sign in to manage your money.' : 'A few details and you’re ready to go.'}</p>
            {error && <div className="alert" role="alert">{error}</div>}
            <form className="form-stack" onSubmit={handleAuth}>
              {authMode === 'register' && <label>Full name<input name="name" autoComplete="name" required minLength={2} maxLength={100} placeholder="Your name" /></label>}
              <label>Email address<input name="email" type="email" autoComplete="email" required placeholder="you@example.com" /></label>
              <label>Password<input name="password" type="password" autoComplete={authMode === 'login' ? 'current-password' : 'new-password'} minLength={8} maxLength={72} required placeholder="At least 8 characters" /></label>
              <button className="button button-primary button-wide" type="submit" disabled={submitting}>
                {submitting ? <LoaderCircle className="spin" size={18} /> : null}
                {authMode === 'login' ? 'Sign in' : 'Create account'}<ArrowRight size={17} />
              </button>
            </form>
            <p className="auth-switch">
              {authMode === 'login' ? 'New to Northline?' : 'Already have an account?'}{' '}
              <button type="button" onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setError('') }}>
                {authMode === 'login' ? 'Create an account' : 'Sign in'}
              </button>
            </p>
          </div>
          <p className="auth-legal">Your information is protected with secure, encrypted access.</p>
        </section>
      </main>
    )
  }

  if (!account) {
    return <main className="loading-screen"><LoaderCircle className="spin" size={26} /><span>{error || 'Loading your account…'}</span>{error && <button className="text-button" onClick={() => window.location.reload()}>Try again</button>}</main>
  }

  const firstName = account.owner_name.split(/\s+/)[0]
  const visibleTransactions = transactions.slice(0, view === 'dashboard' ? 5 : undefined)

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#dashboard" onClick={() => setView('dashboard')}>
          <span className="brand-mark"><Landmark size={20} /></span><span>northline<span className="brand-period">.</span></span>
        </a>
        <div className="sidebar-label">YOUR BANK</div>
        <nav className="primary-nav" aria-label="Main navigation">
          <button className={view === 'dashboard' ? 'nav-link active' : 'nav-link'} onClick={() => setView('dashboard')}><Wallet size={18} />Overview</button>
          <button className={view === 'transactions' ? 'nav-link active' : 'nav-link'} onClick={() => setView('transactions')}><History size={18} />Transactions</button>
          <button className={view === 'account' ? 'nav-link active' : 'nav-link'} onClick={() => setView('account')}><UserRound size={18} />Account details</button>
        </nav>
        <div className="sidebar-bottom">
          <div className="help-row"><CircleHelp size={17} /><span>Need a hand?</span><ChevronRight size={15} /></div>
          <div className="sidebar-profile">
            <span className="avatar">{initials(account.owner_name)}</span>
            <span className="profile-name"><strong>{account.owner_name}</strong><small>Personal account</small></span>
            <button className="icon-button logout-button" title="Sign out" aria-label="Sign out" onClick={logout}><LogOut size={17} /></button>
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumb"><span>Banking</span><ChevronRight size={14} /><strong>{view === 'dashboard' ? 'Overview' : view === 'transactions' ? 'Transactions' : 'Account details'}</strong></div>
          <div className="topbar-right"><span className="secure-status"><span /> Secure session</span><span className="avatar avatar-small">{initials(account.owner_name)}</span></div>
        </header>

        <div className="content-wrap">
          {view === 'dashboard' && <>
            <section className="welcome-row">
              <div><p className="eyebrow">YOUR ACCOUNT AT A GLANCE</p><h1>Good day, {firstName}<span className="heading-dot">.</span></h1><p className="muted">Here’s what’s happening with your account.</p></div>
              <button className="button button-outline hide-small" onClick={() => setView('transactions')}><History size={17} />Full history</button>
            </section>

            {error && <div className="alert page-alert" role="alert">{error}<button className="alert-close" onClick={() => setError('')} aria-label="Dismiss"><X size={16} /></button></div>}
            {notice && <div className="success-banner" role="status"><Check size={17} />{notice}<button className="alert-close" onClick={() => setNotice('')} aria-label="Dismiss"><X size={16} /></button></div>}

            <section className="overview-grid">
              <article className="balance-panel">
                <div className="balance-panel-top"><div><span className="balance-caption">TOTAL AVAILABLE</span><button className="balance-toggle" onClick={() => setShowBalance((value) => !value)} aria-label={showBalance ? 'Hide balance' : 'Show balance'}>{showBalance ? <Eye size={17} /> : <EyeOff size={17} />}</button></div><span className="balance-chip"><BadgeCheck size={14} />Active</span></div>
                <div className="balance-amount">{showBalance ? formatMoney(account.balance) : '₹ ••••••'}</div>
                <div className="balance-divider" />
                <div className="balance-bottom"><div><small>ACCOUNT NUMBER</small><strong>{account.account_number}</strong></div><button className="copy-button" onClick={copyAccountNumber} aria-label="Copy account number" title="Copy account number">{copied ? <Check size={16} /> : <Copy size={16} />}</button><div className="balance-orbit" aria-hidden="true" /></div>
              </article>
              <article className="account-summary">
                <div className="summary-head"><span className="summary-icon"><CreditCard size={19} /></span><span className="summary-tag">SAVINGS</span></div>
                <h2>Everyday<br />account</h2>
                <p>Account holder</p><strong>{account.owner_name}</strong>
                <button className="summary-link" onClick={() => setView('account')}>Account details <ArrowRight size={16} /></button>
              </article>
            </section>

            <section className="quick-actions" aria-label="Money actions">
              <button className="action-tile action-deposit" onClick={() => { setOperation('deposit'); setError('') }}><span><Plus size={19} /></span><strong>Deposit</strong><small>Add money</small></button>
              <button className="action-tile action-withdraw" onClick={() => { setOperation('withdraw'); setError('') }}><span><ArrowUpRight size={19} /></span><strong>Withdraw</strong><small>Take money out</small></button>
              <button className="action-tile action-transfer" onClick={() => { setOperation('transfer'); setError('') }}><span><ArrowLeftRight size={19} /></span><strong>Transfer</strong><small>Send to a person</small></button>
            </section>

            <section className="transactions-section">
              <div className="section-heading"><div><p className="eyebrow">YOUR MONEY, IN MOTION</p><h2>Recent activity</h2></div><button className="text-link" onClick={() => setView('transactions')}>See all <ArrowRight size={16} /></button></div>
              <TransactionList items={visibleTransactions} />
            </section>
          </>}

          {view === 'transactions' && <>
            <section className="welcome-row page-heading"><div><p className="eyebrow">ACCOUNT ACTIVITY</p><h1>Transactions<span className="heading-dot">.</span></h1><p className="muted">A clear record of money moving in and out.</p></div></section>
            {error && <div className="alert page-alert" role="alert">{error}</div>}
            <section className="transactions-section full-history"><div className="section-heading"><div><p className="eyebrow">ALL ACTIVITY</p><h2>{transactions.length} {transactions.length === 1 ? 'transaction' : 'transactions'}</h2></div></div><TransactionList items={visibleTransactions} /></section>
          </>}

          {view === 'account' && <>
            <section className="welcome-row page-heading"><div><p className="eyebrow">YOUR PROFILE</p><h1>Account details<span className="heading-dot">.</span></h1><p className="muted">Your account information, all in one place.</p></div></section>
            <section className="profile-layout">
              <article className="profile-card"><div className="profile-card-head"><span className="avatar avatar-large">{initials(account.owner_name)}</span><span className="balance-chip"><BadgeCheck size={14} />Verified</span></div><h2>{account.owner_name}</h2><p>{account.owner_email}</p><div className="profile-divider" /><div className="detail-line"><span>Account type</span><strong>Personal savings</strong></div><div className="detail-line"><span>Member since</span><strong>{new Date(account.created_at).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}</strong></div></article>
              <article className="details-panel"><p className="eyebrow">BANK ACCOUNT</p><h2>Account information</h2><div className="detail-line"><span>Account number</span><span className="number-copy"><strong>{account.account_number}</strong><button className="icon-button" onClick={copyAccountNumber} title="Copy account number" aria-label="Copy account number">{copied ? <Check size={16} /> : <Copy size={16} />}</button></span></div><div className="detail-line"><span>Available balance</span><strong>{formatMoney(account.balance)}</strong></div><div className="detail-line"><span>Account status</span><span className="status-text"><i />Active</span></div><div className="security-note"><ShieldCheck size={18} /><span>Your account is protected with secure, token-based access.</span></div></article>
            </section>
          </>}
          <footer className="page-footer"><span>Northline personal banking</span><span><ShieldCheck size={14} /> Your session is encrypted</span></footer>
        </div>
      </main>

      <nav className="mobile-nav" aria-label="Mobile navigation">
        <button className={view === 'dashboard' ? 'mobile-link active' : 'mobile-link'} onClick={() => setView('dashboard')}><Wallet size={19} /><span>Overview</span></button>
        <button className={view === 'transactions' ? 'mobile-link active' : 'mobile-link'} onClick={() => setView('transactions')}><History size={19} /><span>Activity</span></button>
        <button className={view === 'account' ? 'mobile-link active' : 'mobile-link'} onClick={() => setView('account')}><UserRound size={19} /><span>Account</span></button>
        <button className="mobile-link" onClick={logout}><LogOut size={19} /><span>Sign out</span></button>
      </nav>

      {operation && <OperationDialog operation={operation} balance={account.balance} submitting={submitting} error={error} onClose={() => { setOperation(null); setError('') }} onSubmit={handleOperation} />}
    </div>
  )
}

function TransactionList({ items }: { items: Transaction[] }) {
  if (items.length === 0) {
    return <div className="empty-state"><span className="empty-icon"><Clock3 size={21} /></span><strong>No transactions yet</strong><p>Your deposits, withdrawals, and transfers will show up here.</p></div>
  }
  return <div className="transaction-list">
    {items.map((item) => <div className="transaction-row" key={item.id}>
      <span className={`transaction-icon ${isCredit(item.type) ? 'credit' : 'debit'}`}>{transactionIcon(item.type)}</span>
      <span className="transaction-description"><strong>{transactionLabel(item.type)}</strong><small>{new Date(item.created_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}</small></span>
      <span className={`transaction-amount ${isCredit(item.type) ? 'positive' : ''}`}>{isCredit(item.type) ? '+' : '−'}{formatMoney(item.amount)}</span>
      <span className="transaction-state"><i />{item.status.toLowerCase()}</span>
    </div>)}
  </div>
}

function OperationDialog({
  operation,
  balance,
  submitting,
  error,
  onClose,
  onSubmit,
}: {
  operation: Operation
  balance: string
  submitting: boolean
  error: string
  onClose: () => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}) {
  const titles = { deposit: 'Add money', withdraw: 'Withdraw money', transfer: 'Send a transfer' }
  const subtitles = {
    deposit: 'Add funds to your Northline account.',
    withdraw: 'Move funds out of your account.',
    transfer: 'Send money to another Northline account.',
  }
  const submitLabels = { deposit: 'Confirm deposit', withdraw: 'Confirm withdrawal', transfer: 'Review transfer' }

  return <div className="dialog-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
    <section className="operation-dialog" role="dialog" aria-modal="true" aria-labelledby="operation-title">
      <div className="dialog-top"><span className="dialog-mark">{operation === 'deposit' ? <ArrowDownLeft size={20} /> : operation === 'withdraw' ? <ArrowUpRight size={20} /> : <ArrowLeftRight size={20} />}</span><button className="icon-button" onClick={onClose} aria-label="Close"><X size={19} /></button></div>
      <p className="eyebrow">{operation === 'transfer' ? 'MOVE MONEY' : 'ACCOUNT ACTIVITY'}</p><h2 id="operation-title">{titles[operation]}</h2><p className="dialog-subtitle">{subtitles[operation]}</p>
      <div className="available-line"><span>Available balance</span><strong>{formatMoney(balance)}</strong></div>
      {error && <div className="alert" role="alert">{error}</div>}
      <form className="form-stack" onSubmit={onSubmit}>
        {operation === 'transfer' && <label>Recipient account number<input name="recipient" inputMode="numeric" pattern="[0-9]{10}" minLength={10} maxLength={10} required placeholder="10-digit account number" /></label>}
        <label>Amount<input name="amount" type="number" min="0.01" step="0.01" max="9999999999.99" required autoFocus placeholder="0.00" /></label>
        <button className="button button-primary button-wide" type="submit" disabled={submitting}>{submitting ? <LoaderCircle className="spin" size={18} /> : null}{submitLabels[operation]}<ArrowRight size={17} /></button>
      </form>
      <p className="dialog-footnote"><ShieldCheck size={15} />Your transaction is protected and recorded.</p>
    </section>
  </div>
}

export default App