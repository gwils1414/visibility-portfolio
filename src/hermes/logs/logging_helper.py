import logging


def configure(level: int = logging.INFO) -> None:
    """Configure root logging for Hermes. Call once at process boot."""
    logging.basicConfig(
        filename='hermes_logging.log',
        filemode='a',
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )

#used as a decorator to handle logging throught the app
def log(func):
    def wrapper(*args, **kwargs):
        func_logger = logging.getLogger(func.__module__)
        func_logger.info(f"Running {func.__name__}")
        result = func(*args, **kwargs)
        return result
    return wrapper

#TODO, handler to write log file to postgres
#I could read directly from the log file, and write the to db
#but that feels like a loop, we should go directly from log writing to db
#handlers is apparently the way to do this
