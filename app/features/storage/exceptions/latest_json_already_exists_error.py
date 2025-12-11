class LatestJsonAlreadyExistsError(Exception):
    def __init__(self, path: str, message: str = None):
        self.path = path
        self.message = message or f"latest.json already exists at path: {path}"
        super().__init__(self.message)