import { NextResponse } from 'next/server'

const OWNER = 'Ggboykxz'
const REPO = 'APEX'
const BASE = `https://api.github.com/repos/${OWNER}/${REPO}`

export const dynamic = 'force-dynamic'

const headers: Record<string, string> = {
  Accept: 'application/vnd.github.v3+json',
  'User-Agent': 'APEX-Website',
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

export async function GET() {
  try {
    const repo = await fetchJSON<Record<string, unknown>>(BASE)
    const issues = await fetchJSON<Record<string, unknown>[]>(`${BASE}/issues?state=all&sort=created&direction=desc&per_page=10`)
    const prs = await fetchJSON<Record<string, unknown>[]>(`${BASE}/pulls?state=all&sort=created&direction=desc&per_page=10`)
    const releases = await fetchJSON<Record<string, unknown>[]>(`${BASE}/releases?per_page=5`)

    const pureIssues = (issues || []).filter(i => !i.pull_request)
    const latestRelease = releases && releases.length > 0 ? releases[0] : null

    return NextResponse.json({
      repo: repo ? {
        stargazers_count: repo.stargazers_count,
        forks_count: repo.forks_count,
        open_issues_count: repo.open_issues_count,
        subscribers_count: repo.subscribers_count,
        contributors: 2,
        latest_release: latestRelease ? {
          tag_name: latestRelease.tag_name,
          published_at: latestRelease.published_at,
        } : null,
      } : null,
      issues: pureIssues.map(i => ({
        number: i.number,
        title: i.title,
        state: i.state,
        created_at: i.created_at,
        user: i.user,
        labels: i.labels,
      })),
      pullRequests: (prs || []).map(p => ({
        number: p.number,
        title: p.title,
        state: p.state,
        merged_at: p.merged_at,
        created_at: p.created_at,
        user: p.user,
        labels: p.labels,
      })),
      releases: (releases || []).map(r => ({
        tag_name: r.tag_name,
        name: r.name,
        published_at: r.published_at,
        body: typeof r.body === 'string' ? r.body.substring(0, 500) : '',
      })),
    })
  } catch {
    return NextResponse.json({
      repo: null, issues: [], pullRequests: [], releases: [],
    })
  }
}
