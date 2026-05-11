/**
 * GitHub API client — fetches data directly from GitHub's public API.
 * Used by both the home page and activity page for static export compatibility.
 */

const OWNER = 'Ggboykxz'
const REPO = 'APEX'
const BASE = `https://api.github.com/repos/${OWNER}/${REPO}`

const headers: Record<string, string> = {
  Accept: 'application/vnd.github.v3+json',
}

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

async function fetchJSON<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url, { headers })
    if (!res.ok) return null
    return res.json() as Promise<T>
  } catch {
    return null
  }
}

export async function fetchGitHubData(): Promise<GitHubData> {
  try {
    const [repo, issues, prs, releases] = await Promise.all([
      fetchJSON<Record<string, unknown>>(BASE),
      fetchJSON<Record<string, unknown>[]>(`${BASE}/issues?state=all&sort=created&direction=desc&per_page=10`),
      fetchJSON<Record<string, unknown>[]>(`${BASE}/pulls?state=all&sort=created&direction=desc&per_page=10`),
      fetchJSON<Record<string, unknown>[]>(`${BASE}/releases?per_page=5`),
    ])

    const pureIssues = (issues || []).filter(i => !i.pull_request)
    const latestRelease = releases && releases.length > 0 ? releases[0] : null

    return {
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
  } catch {
    return {
      repo: null,
      issues: [],
      pullRequests: [],
      releases: [],
    }
  }
}
