from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from ..auth import AuthContext, get_auth_context
from ..repositories.unit_of_work import UnitOfWorkFactory
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
from ..services.temporal_service import TemporalService

router = APIRouter(tags=["temporal"])


def get_uow_factory(request: Request) -> UnitOfWorkFactory:
    return request.app.state.uow_factory


AUTH_CONTEXT = Depends(get_auth_context)
UOW_FACTORY = Depends(get_uow_factory)


@router.post(
    "/v1/temporal/predictions",
    response_model=TemporalPrediction,
    status_code=status.HTTP_201_CREATED,
)
def create_temporal_prediction(
    payload: CreatePredictionRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> TemporalPrediction:
    return TemporalService(uow_factory).create_prediction(auth.user_id, payload)


@router.post(
    "/v1/temporal/predictions/{prediction_id}/outcome",
    response_model=PredictionOutcome,
    status_code=status.HTTP_201_CREATED,
)
def record_temporal_prediction_outcome(
    prediction_id: UUID,
    payload: RecordPredictionOutcomeRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> PredictionOutcome:
    return TemporalService(uow_factory).record_prediction_outcome(
        auth.user_id,
        prediction_id,
        payload,
    )


@router.post(
    "/v1/temporal/query",
    response_model=TemporalQueryAnswer,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_temporal_query_answer(
    payload: TemporalQueryRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> TemporalQueryAnswer:
    return TemporalService(uow_factory).create_query_answer(auth.user_id, payload)


@router.get("/v1/temporal/query/{answer_id}", response_model=TemporalQueryAnswer)
def get_temporal_query_answer(
    answer_id: UUID,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> TemporalQueryAnswer:
    return TemporalService(uow_factory).get_query_answer(auth.user_id, answer_id)


@router.post(
    "/v1/analytics/feature-vectors/recompute",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_feature_vector_recompute(
    payload: RecomputeFeatureVectorsRequest,
    auth: AuthContext = AUTH_CONTEXT,
    uow_factory: UnitOfWorkFactory = UOW_FACTORY,
) -> JobAcceptedResponse:
    return TemporalService(uow_factory).request_feature_vector_recompute(auth.user_id, payload)
