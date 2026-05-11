/**
 * GitHub API client — fetches data from GitHub's public API with
 * localStorage caching, ETag support, and stale fallback for
 * static export compatibility.
 */

const OWNER = 'Ggboykxz'
const REPO = 'APEX'
const BASE = `https://api.github.com/repos/${OWNER}/${REPO}`

const headers: Record<string, string> = {
  Accept: 'application/vnd.github.v3+json',
}

/* ──── Cache helpers ──── */
const CACHE_KEY = 'apex-github-cache'
const CACHE_TTL = 5 * 60 * 1000 // 5 minutes

interface CachedData {
  timestamp: number
  data: GitHubData
}

function readCache(): GitHubData | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    if (!raw) return null
    const cached: CachedData = JSON.parse(raw)
    if (Date.now() - cached.timestamp < CACHE_TTL) return cached.data
    return null
  } catch {
    return null
  }
}

function writeCache(data: GitHubData): void {
  try {
    const cached: CachedData = { timestamp: Date.now(), data }
    localStorage.setItem(CACHE_KEY, JSON.stringify(cached))
  } catch {
    // localStorage might be full or unavailable
  }
}

/* ──── ETag store ──── */
const ETAG_KEY = 'apex-github-etags'

function getEtag(url: string): string | null {
  try {
    const etags = JSON.parse(localStorage.getItem(ETAG_KEY) || '{}')
    return etags[url] || null
  } catch {
    return null
  }
}

function setEtag(url: string, etag: string): void {
  try {
    const etags = JSON.parse(localStorage.getItem(ETAG_KEY) || '{}')
    etags[url] = etag
    localStorage.setItem(ETAG_KEY, JSON.stringify(etags))
  } catch {
    // ignore
  }
}

/* ──── Types ──── */
export interface GitHubRepoData {
  stargazers_count: number
  forks_count: number
  open_issues_count: number
  subscribers_count: number
  contributors: number
  latest_release: { tag_name: string; published_at: string } | null
}

export interface GitHubIssue {
  number: number
  title: string
  state: 'open' | 'closed'
  created_at: string
  user: { login: string }
  labels: { name: string; color: string }[]
}

export interface GitHubPullRequest {
  number: number
  title: string
  state: 'open' | 'closed'
  merged_at: string | null
  created_at: string
  user: { login: string }
  labels: { name: string; color: string }[]
}

export interface GitHubRelease {
  tag_name: string
  name: string
  published_at: string
  body: string
}

export interface GitHubData {
  repo: GitHubRepoData | null
  issues: GitHubIssue[]
  pullRequests: GitHubPullRequest[]
  releases: GitHubRelease[]
}

const EMPTY_DATA: GitHubData = {
  repo: null,
  issues: [],
  pullRequests: [],
  releases: [],
}

async function fetchJSON<T>(url: string): Promise<{ data: T | null; notModified: boolean }> {
  try {
    const etag = getEtag(url)
    const reqHeaders = { ...headers, ...(etag ? { 'If-None-Match': etag } : {}) }

    const res = await fetch(url, { headers: reqHeaders })

    // 304 Not Modified — data hasn't changed
    if (res.status === 304) return { data: null, notModified: true }

    // Save the new ETag
    const newEtag = res.headers.get('etag')
    if (newEtag) setEtag(url, newEtag)

    if (!res.ok) return { data: null, notModified: false }
    return { data: await res.json() as T, notModified: false }
  } catch {
    return { data: null, notModified: false }
  }
}

export async function fetchGitHubData(): Promise<GitHubData> {
  // Check localStorage cache first (valid for 5 minutes)
  const cached = readCache()
  if (cached) return cached

  try {
    const [repoResult, issuesResult, prsResult, releasesResult] = await Promise.all([
      fetchJSON<Record<string, unknown>>(BASE),
      fetchJSON<Record<string, unknown>[]>(`${BASE}/issues?state=all&sort=created&direction=desc&per_page=10`),
      fetchJSON<Record<string, unknown>[]>(`${BASE}/pulls?state=all&sort=created&direction=desc&per_page=10`),
      fetchJSON<Record<string, unknown>[]>(`${BASE}/releases?per_page=5`),
    ])

    // If ALL responses are 304 (not modified), return stale cache
    if (repoResult.notModified && issuesResult.notModified && prsResult.notModified && releasesResult.notModified) {
      try {
        const raw = localStorage.getItem(CACHE_KEY)
        if (raw) return (JSON.parse(raw) as CachedData).data
      } catch { /* ignore */ }
      return EMPTY_DATA
    }

    const repo = repoResult.data
    const issues = issuesResult.data
    const prs = prsResult.data
    const releases = releasesResult.data

    // If all requests failed (not 304, just null), try stale cache
    if (!repo && !issues && !prs && !releases) {
      try {
        const raw = localStorage.getItem(CACHE_KEY)
        if (raw) return (JSON.parse(raw) as CachedData).data
      } catch { /* ignore */ }
      return EMPTY_DATA
    }

    const pureIssues = (issues || []).filter(i => !i.pull_request)
    const latestRelease = releases && releases.length > 0 ? releases[0] : null

    const data: GitHubData = {
      repo: repo ? {
        stargazers_count: repo.stargazers_count as number,
        forks_count: repo.forks_count as number,
        open_issues_count: repo.open_issues_count as number,
        subscribers_count: repo.subscribers_count as number,
        contributors: 2,
        latest_release: latestRelease ? {
          tag_name: latestRelease.tag_name as string,
          published_at: latestRelease.published_at as string,
        } : null,
      } : null,
      issues: pureIssues.map(i => ({
        number: i.number as number,
        title: i.title as string,
        state: i.state as 'open' | 'closed',
        created_at: i.created_at as string,
        user: i.user as { login: string },
        labels: i.labels as { name: string; color: string }[],
      })),
      pullRequests: (prs || []).map(p => ({
        number: p.number as number,
        title: p.title as string,
        state: p.state as 'open' | 'closed',
        merged_at: p.merged_at as string | null,
        created_at: p.created_at as string,
        user: p.user as { login: string },
        labels: p.labels as { name: string; color: string }[],
      })),
      releases: (releases || []).map(r => ({
        tag_name: r.tag_name as string,
        name: r.name as string,
        published_at: r.published_at as string,
        body: typeof r.body === 'string' ? r.body.substring(0, 500) : '',
      })),
    }

    // Cache the fresh data
    writeCache(data)

    return data
  } catch {
    // On any error, try stale cache
    try {
      const raw = localStorage.getItem(CACHE_KEY)
      if (raw) return (JSON.parse(raw) as CachedData).data
    } catch { /* ignore */ }
    return EMPTY_DATA
  }
}
