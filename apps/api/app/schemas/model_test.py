from uuid import UUID

from app.schemas.common import DomainSchema, NonEmptyString


class ModelTestRequest(DomainSchema):
    target_model_id: UUID
    user_message: NonEmptyString
    system_message: NonEmptyString | None = None

