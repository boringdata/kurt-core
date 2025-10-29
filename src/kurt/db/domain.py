from typing import Optional

from pydantic import BaseModel, Field


class ProductFeature(BaseModel):
    """Product feature entity."""

    feature_id: Optional[str] = Field(None, description="Unique feature identifier")
    feature_name: Optional[str] = Field(None, description="Name of the feature")
    description: Optional[str] = Field(None, description="Description of the feature")

    model_config = {"extra": "forbid"}  # Override EntityNode config for OpenAI compatibility


class Topic(BaseModel):
    """Topic entity."""

    topic_id: Optional[str] = Field(None, description="Unique topic identifier")
    topic_name: Optional[str] = Field(None, description="Name of the topic")
    description: Optional[str] = Field(None, description="Description of the topic")

    model_config = {"extra": "forbid"}  # Override EntityNode config for OpenAI compatibility


entity_types = {
    "ProductFeature": ProductFeature,
    "Topic": Topic,
}
