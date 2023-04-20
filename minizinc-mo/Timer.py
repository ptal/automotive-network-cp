from datetime import datetime, timedelta

class Timer:
  def __init__(self, time_budget_sec):
    self.time_budget_sec = time_budget_sec
    self.start_time = datetime.now()

  def time_left(self):
    time_left = self.time_budget_sec - (datetime.now() - self.start_time).total_seconds()
    if time_left <= 0:
      raise TimeoutError()
    return timedelta(seconds = time_left)
