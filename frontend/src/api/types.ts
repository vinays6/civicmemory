export type VoteCounts = { aye: number; nay: number; absent: number };
export type Sentiment = 'positive' | 'negative' | 'neutral' | 'mixed';
export type Position = 'aye' | 'nay' | 'absent';
export type PredictedVote = 'yes' | 'no' | 'abstain' | 'unclear';

export interface MemberSummary {
  name: string;
  meeting_count: number;
  opinion_meeting_count: number;
  opinion_topic_count: number;
  vote_counts: VoteCounts;
  issues: string[];
}

export interface MemberVote {
  meeting_date: string;
  item_number: number;
  file_code: string;
  council_district: string | null;
  description: string;
  disposition: string;
  position: Position;
  member_raw: string;
}

export interface MemberOpinion {
  meeting_date: string;
  issue: string;
  stance: string;
  sentiment: Sentiment;
  youtube_links: string[];
}

export interface CodissentPartner {
  member: string;
  rate: number;
  n: number;
}

export interface MemberStats {
  member: string;
  vote_counts: VoteCounts;
  aye_rate: number;
  participation_rate: number;
  dissent_rate: number;
  lone_wolf_items: number[];
  top_codissent_partners: CodissentPartner[];
  alignment_row_contested: Record<string, number | null>;
  kingmaker: { member: string; flipped_items: number[]; score: number };
}

export interface IssuePosition {
  stance: string;
  confidence: number;
  evidence_meetings: string[];
}

export interface MemberProfile {
  member_name: string;
  recurring_issues: string[];
  issue_positions: Record<string, IssuePosition>;
  themes: string[];
  commitment_history: string[];
  commitment_reliability: number;
  ideology_dimensions: string[];
}

export interface MemberProfileEnvelope {
  member_canonical: string;
  profile: MemberProfile;
  updated_at: string | null;
}

export interface VotePrediction {
  member_name: string;
  predicted_vote: PredictedVote;
  confidence: number;
  reasoning: string;
  evidence_meetings: string[];
}

export interface VotingNetworkEdge {
  a: string;
  b: string;
  rate: number;
  n: number;
}

export interface VotingNetwork {
  members: string[];
  blocs: Record<string, number>;
  edges: VotingNetworkEdge[];
}

export interface ControversialItem {
  item_id: number;
  meeting_date: string;
  item_number: number;
  file_code: string;
  description: string;
  tally: VoteCounts;
}
