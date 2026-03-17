from pathlib import Path


class WorkspaceManager:

    BASE_PATH = Path("data/users")

    def __init__(self, user_id):

        self.user_id = str(user_id)

        self.user_path = self.BASE_PATH / self.user_id

        self.raw_path = self.user_path / "raw"
        self.processed_path = self.user_path / "processed"
        self.vector_path = self.user_path / "vector_store"

        self.create_workspace()

    def create_workspace(self):

        self.raw_path.mkdir(parents=True, exist_ok=True)
        self.processed_path.mkdir(parents=True, exist_ok=True)
        self.vector_path.mkdir(parents=True, exist_ok=True)

    def raw(self):
        return str(self.raw_path)

    def processed(self):
        return str(self.processed_path)

    def vector(self):
        return str(self.vector_path)