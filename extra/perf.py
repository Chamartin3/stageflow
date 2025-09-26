
class ResultPerformace(TypedDict):
    result: Any
    start_time: float
    eplapsed_time_ms: float
    end_time: float

def performance_decorator(func):
    """Decorator to measure performance of gate evaluations."""
    import time

    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        elapsed_time = (end_time - start_time) * 1000  # Convert to milliseconds
        return ResultPerformace(
            result=result,
            start_time=start_time,
            eplapsed_time_ms=elapsed_time,
            end_time=end_time
        )
    return wrapper



