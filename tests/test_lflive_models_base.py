from lflive.models.base import Base


def test_base_metadata_exists() -> None:
    assert Base.metadata is not None
