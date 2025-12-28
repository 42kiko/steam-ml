from src.utils.logging import get_logger


def test_get_logger_singleton() -> None:
    logger1 = get_logger("test")
    logger2 = get_logger("test")

    assert logger1 is logger2
