import functools
import logging
import time

_logger = logging.getLogger('backoff')
_logger.addHandler(logging.NullHandler())


def on_exception(start_sleep_time=0.1, factor=2, border_sleep_time=10, logger=_logger):
    """
    Функция для повторного выполнения функции через некоторое время,
    если возникла ошибка. Использует наивный экспоненциальный рост времени
    повтора (factor) до граничного времени ожидания (border_sleep_time)

    Формула:
        t = start_sleep_time * 2^(n) if t < border_sleep_time
        t = border_sleep_time if t >= border_sleep_time
    :param start_sleep_time: начальное время повтора
    :param factor: во сколько раз нужно увеличить время ожидания
    :param border_sleep_time: граничное время ожидания
    :param logger Логгер
    :return: результат выполнения функции
    """
    def func_wrapper(func):

        @functools.wraps(func)
        def inner(*args, **kwargs):
            tries = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    sleep_time = start_sleep_time * (factor ** tries)
                    if sleep_time > border_sleep_time:
                        logger.warning(
                            "The exception is caught. '{}' function call limit reached".format(func.__name__))
                        raise e
                    else:
                        logger.info("The exception is caught. Repeated execution of the '{}' function"
                                    "will be backed off by {} seconds.".format(func.__name__, sleep_time))
                        time.sleep(sleep_time)

                tries += 1

        return inner
    return func_wrapper
