import base64
import pickle


def dump_session(data: dict) -> str:
    return base64.b64encode(pickle.dumps(data)).decode()


def load_session(cookie: str) -> dict:
    return pickle.loads(base64.b64decode(cookie))
