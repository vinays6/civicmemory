from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TopicSummary(StrictBaseModel):
    issue: str
    stance: str
    sentiment: Literal["positive", "negative", "neutral", "mixed"]
    timestamps: List[str]


class MemberMeetingSummary(StrictBaseModel):
    member_name: str
    topics: List[TopicSummary]


class MeetingAnalysisResult(StrictBaseModel):
    meeting_date: str
    member_summaries: List[MemberMeetingSummary]


class IssuePosition(StrictBaseModel):
    stance: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_meetings: List[str]


class MemberProfile(StrictBaseModel):
    member_name: str
    recurring_issues: List[str]
    issue_positions: Dict[str, IssuePosition]
    themes: List[str]
    commitment_history: List[str]
    commitment_reliability: float = Field(ge=0.0, le=1.0)
    ideology_dimensions: List[str]


class BuildProfileResponse(StrictBaseModel):
    profile: MemberProfile


class PredictVoteRequest(StrictBaseModel):
    issue: str = Field(min_length=1)


class MemberVotePrediction(StrictBaseModel):
    member_name: str
    predicted_vote: Literal["yes", "no", "abstain", "unclear"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    evidence_meetings: List[str]


class VotePredictionResult(StrictBaseModel):
    predictions: List[MemberVotePrediction]
