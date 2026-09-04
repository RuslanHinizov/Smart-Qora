from collections import defaultdict, deque


class CenterSmoother:
    def __init__(self, history_size: int = 5):
        self.history = defaultdict(lambda: deque(maxlen=history_size))

    def update(self, tracking_id: int, center: tuple[int, int]) -> tuple[int, int]:
        values = self.history[tracking_id]
        values.append(center)
        return (round(sum(x for x, _ in values) / len(values)), round(sum(y for _, y in values) / len(values)))
