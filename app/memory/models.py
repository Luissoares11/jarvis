from dataclasses import dataclass, asdict


@dataclass
class Fact:
    id: str
    subject: str
    relation: str
    object: str

    def to_dict(self):
        return asdict(self)


@dataclass
class Collection:
    id: str
    owner: str
    name: str
    items: list[str]

    def to_dict(self):
        return asdict(self)