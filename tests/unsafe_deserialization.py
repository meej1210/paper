import pickle
import yaml


def load_cache(blob: bytes):
    return pickle.loads(blob)


def load_config(text: str):
    return yaml.load(text, Loader=yaml.Loader)


def parse_payload(path: str):
    with open(path, "rb") as handle:
        return pickle.load(handle)
