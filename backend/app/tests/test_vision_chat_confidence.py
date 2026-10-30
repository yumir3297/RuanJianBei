import pytest
from pydantic import ValidationError
from app.schemas.chat import VisionContext

@pytest.mark.parametrize('value', [-0.01, 1.01, float('nan'), float('inf')])
def test_invalid_vision_confidence_is_rejected(value):
    with pytest.raises(ValidationError):
        VisionContext(confidence=value)

@pytest.mark.parametrize('value', [0.0, 0.5, 1.0])
def test_valid_vision_confidence_is_accepted(value):
    assert VisionContext(confidence=value).confidence == value
