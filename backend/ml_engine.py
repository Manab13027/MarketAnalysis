class MLEngine:
    cv_mape: float = 0.0
    cv_dir_accuracy: float = 0.0
    def __init__(self, db_path: str): self.db_path = db_path
    def train(self): pass
    def predict(self, *args, **kwargs): return None
