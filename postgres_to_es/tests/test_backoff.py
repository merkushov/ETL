import pytest
import backoff


def test_on_exception():

    @backoff.on_exception(border_sleep_time=1)
    def test_func(log):
        if len(log) == 0:
            e = KeyError()
        elif len(log) == 1:
            e = ValueError()
        else:
            return True
        log.append(e)
        raise e

    log = []
    test_func(log)

    assert 2 == len(log)
    assert isinstance(log[0], KeyError)
    assert isinstance(log[1], ValueError)


def test_on_exception_wait_till_exception():

    @backoff.on_exception(border_sleep_time=1)
    def test_func(log):
        e = ValueError("test_func exception")
        log.append(e)
        raise e

    log = []
    with pytest.raises(ValueError, match=r"test_func exception") as exception:
        test_func(log)

    # assert str(exception) == "test_func exception"
    assert len(log) > 4
    assert isinstance(log[0], ValueError)
