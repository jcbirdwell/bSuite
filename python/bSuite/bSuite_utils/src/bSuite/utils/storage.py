from typing import Optional
import os
import pickle


class Pickler:
    def __init__(self, root_dir: Optional[str] = './pickle_files'):
        self.root = self.ensure_root(root_dir)

    @staticmethod
    def ensure_root(root_path: str):
        if not os.path.exists(root_path):
            os.mkdir(root_path)
        return root_path

    def load(self, name: str):
        try:
            with open(f'{self.root}/{name}.pickle', mode='rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return None

    def save(self, obj, name: str):
        with open(f'{self.root}/{name}.pickle', mode='wb') as f:
            pickle.dump(obj, f)

