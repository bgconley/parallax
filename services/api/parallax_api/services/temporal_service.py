from __future__ import annotations

import re
from uuid import UUID

from fastapi import HTTPException

from ..repositories.unit_of_work import UnitOfWork, UnitOfWorkFactory
from ..schemas.activity import Activity
from ..schemas.temporal import (
    CreatePredictionRequest,
    JobAcceptedResponse,
    PredictionOutcome,
    RecomputeFeatureVectorsRequest,
    RecordPredictionOutcomeRequest,
    TemporalPrediction,
    TemporalQueryAnswer,
    TemporalQueryRequest,
)
from .mutations import MutationReplayService


class TemporalService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    def create_prediction(
        self,
        user_id: UUID,
        request: CreatePredictionRequest,
    ) -> TemporalPrediction:
        with self._uow_factory() as uow:
            return create_prediction_in_uow(uow, user_id, request)

    def record_prediction_outcome(
        self,
        user_id: UUID,
        prediction_id: UUID,
        request: RecordPredictionOutcomeRequest,
    ) -> PredictionOutcome:
        with self._uow_factory() as uow:
            return record_prediction_outcome_in_uow(uow, user_id, prediction_id, request)

    def create_query_answer(
        self,
        user_id: UUID,
        request: TemporalQueryRequest,
    ) -> TemporalQueryAnswer:
        with self._uow_factory() as uow:
            return create_query_answer_in_uow(uow, user_id, request)

    def get_query_answer(self, user_id: UUID, answer_id: UUID) -> TemporalQueryAnswer:
        with self._uow_factory() as uow:
            answer = uow.temporal.get_query_answer(user_id, answer_id)
        if answer is None:
            raise HTTPException(status_code=404, detail="temporal query answer not found")
        return answer

    def request_feature_vector_recompute(
        self,
        user_id: UUID,
        request: RecomputeFeatureVectorsRequest,
    ) -> JobAcceptedResponse:
        with self._uow_factory() as uow:
            return request_feature_vector_recompute_in_uow(uow, user_id, request)


def create_prediction_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    request: CreatePredictionRequest,
) -> TemporalPrediction:
    if uow.activities.get(user_id, request.activity_id) is None:
        raise HTTPException(status_code=404, detail="activity not found")
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, TemporalPrediction]:
        prediction = uow.temporal.create_prediction(user_id, request)
        return prediction.id, prediction

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="create_temporal_prediction",
        entity_type="temporal_prediction",
        result_type=TemporalPrediction,
        apply=apply,
    )


def record_prediction_outcome_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    prediction_id: UUID,
    request: RecordPredictionOutcomeRequest,
) -> PredictionOutcome:
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, PredictionOutcome]:
        try:
            outcome = uow.temporal.record_prediction_outcome(user_id, prediction_id, request)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="temporal prediction not found") from exc
        return outcome.id, outcome

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="record_prediction_outcome",
        entity_type="prediction_outcome",
        result_type=PredictionOutcome,
        apply=apply,
    )


def create_query_answer_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    request: TemporalQueryRequest,
) -> TemporalQueryAnswer:
    request = _resolve_query_activity(uow, user_id, request)
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, TemporalQueryAnswer]:
        answer = uow.temporal.create_query_answer(user_id, request)
        return answer.id, answer

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="create_temporal_query",
        entity_type="temporal_query_answer",
        result_type=TemporalQueryAnswer,
        apply=apply,
    )


def _resolve_query_activity(
    uow: UnitOfWork,
    user_id: UUID,
    request: TemporalQueryRequest,
) -> TemporalQueryRequest:
    if request.activity_id is not None:
        if uow.activities.get(user_id, request.activity_id) is None:
            raise HTTPException(status_code=404, detail="activity not found")
        return request

    activity = _activity_mentioned_in_question(
        uow.activities.list_activities(user_id, query=None, limit=100),
        request.question,
    )
    if activity is None:
        return request
    return request.model_copy(update={"activity_id": activity.id})


def _activity_mentioned_in_question(
    activities: list[Activity],
    question: str,
) -> Activity | None:
    question_tokens = set(_query_tokens(question))
    if not question_tokens:
        return None
    candidates: list[tuple[int, Activity]] = []
    for activity in activities:
        tokens = set(_query_tokens(activity.display_name))
        if tokens and tokens.issubset(question_tokens):
            candidates.append((len(tokens), activity))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], item[1].display_name.casefold()))
    return candidates[0][1]


def _query_tokens(value: str) -> list[str]:
    tokens: list[str] = []
    for token in re.findall(r"[a-z0-9]+", value.casefold().replace("&", " and ")):
        tokens.append(token)
        if token.endswith("ing") and len(token) > 5:
            tokens.append(token[:-3])
    return tokens


def request_feature_vector_recompute_in_uow(
    uow: UnitOfWork,
    user_id: UUID,
    request: RecomputeFeatureVectorsRequest,
) -> JobAcceptedResponse:
    mutations = MutationReplayService(uow.mutations)

    def apply() -> tuple[UUID, JobAcceptedResponse]:
        workflow = uow.workflows.enqueue(
            request.user_id or user_id,
            "GenerateTemporalFeatureVectorWorkflow",
            {
                "activity_id": str(request.activity_id) if request.activity_id else None,
                "session_id": str(request.session_id) if request.session_id else None,
                "feature_families": request.feature_families,
                "reason": request.reason,
            },
        )
        response = JobAcceptedResponse(workflow_run_id=workflow.id, status="accepted")
        return workflow.id, response

    return mutations.replay_or_apply(
        user_id=user_id,
        mutation=request.mutation,
        mutation_type="recompute_feature_vectors",
        entity_type="workflow_run",
        result_type=JobAcceptedResponse,
        apply=apply,
    )
