export type Party = 'Democrat' | 'Republican' | 'Independent' | 'Green' | 'Libertarian';
export type Role = 'President' | 'Vice President' | 'Senator' | 'Representative' | 'Governor' | 'Secretary' | 'Mayor' | 'Ambassador';

export interface Stances {
  healthcare: number;   // 0=universal, 100=private market
  economy: number;      // 0=regulated, 100=free market
  climate: number;      // 0=aggressive action, 100=skeptical
  immigration: number;  // 0=open, 100=strict enforcement
  education: number;    // 0=public/free, 100=school choice
  defense: number;      // 0=reduce spending, 100=increase spending
}

export interface ActivityItem {
  date: string;
  title: string;
  type: 'vote' | 'statement' | 'bill' | 'event';
  description?: string;
}

export interface Politician {
  id: string;
  name: string;
  party: Party;
  role: Role;
  state: string;
  stateCode: string;
  district?: string;
  lat: number;
  lng: number;
  age: number;
  yearsInOffice: number;
  bio: string;
  twitter?: string;
  stances: Stances;
  allies: string[];
  opponents: string[];
  tags: string[];
  recentActivity: ActivityItem[];
}

export interface NetworkEdge {
  source: string;
  target: string;
  type: 'ally' | 'opponent';
  strength: number; // 1–3
}

export const PARTY_COLORS: Record<Party, string> = {
  Democrat: '#3b82f6',
  Republican: '#ef4444',
  Independent: '#f59e0b',
  Green: '#22c55e',
  Libertarian: '#a855f7',
};

export const PARTY_BG: Record<Party, string> = {
  Democrat: 'bg-blue-500',
  Republican: 'bg-red-500',
  Independent: 'bg-amber-500',
  Green: 'bg-green-500',
  Libertarian: 'bg-purple-500',
};
