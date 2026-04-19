import type {
  ControversialItem,
  MemberOpinion,
  MemberProfile,
  MemberProfileEnvelope,
  MemberStats,
  MemberSummary,
  MemberVote,
  VotePrediction,
  VotingNetwork,
} from './types';

const API_BASE = '/api';

export class ApiError extends Error {
  constructor(public status: number, public payload: unknown, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  });
  const text = await res.text();
  const body = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const msg = (body && (body.error || body.details)) || `HTTP ${res.status}`;
    throw new ApiError(res.status, body, typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  return body as T;
}

const enc = encodeURIComponent;

export const api = {
  listMembers: () => request<MemberSummary[]>('/members'),
  getMemberVotes: (name: string) => request<MemberVote[]>(`/members/${enc(name)}/votes`),
  getMemberOpinions: (name: string) => request<MemberOpinion[]>(`/members/${enc(name)}/opinions`),
  getMemberStats: (name: string) => request<MemberStats>(`/members/${enc(name)}/stats`),
  getMemberProfile: (name: string) =>
    request<MemberProfileEnvelope>(`/members/${enc(name)}/profile`),
  buildMemberProfile: (name: string) =>
    request<MemberProfile>(`/members/${enc(name)}/build-profile`, { method: 'POST' }),
  predictVote: (issue: string, memberName: string) =>
    request<VotePrediction>('/predict-vote', {
      method: 'POST',
      body: JSON.stringify({ issue, member_name: memberName }),
    }),
  votingNetwork: (params: { k?: number; minN?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.k !== undefined) qs.set('k', String(params.k));
    if (params.minN !== undefined) qs.set('min_n', String(params.minN));
    const q = qs.toString();
    return request<VotingNetwork>(`/voting-network${q ? `?${q}` : ''}`);
  },
  controversialItems: (limit = 10) =>
    request<ControversialItem[]>(`/controversial-items?limit=${limit}`),
};
