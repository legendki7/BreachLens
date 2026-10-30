from typing import Annotated

from fastapi import Depends

from app.evaluation.blue import BlueEvaluator
from app.evaluation.judge import RubricJudge
from app.evaluation.service import EvaluationService
from app.model_gateway.dependencies import get_model_gateway
from app.model_gateway.gateway import ModelGateway


def get_evaluation_service(
    gateway: Annotated[ModelGateway, Depends(get_model_gateway)],
) -> EvaluationService:
    return EvaluationService(BlueEvaluator(), RubricJudge(gateway))
