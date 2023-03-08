from datetime import datetime, timedelta


class Domain:
    def __init__(self, nam_domain: str, time_limit_between_requests: int):
        self.time_last_access = datetime(1970, 1, 1)
        self.nam_domain = nam_domain
        self.time_limit_seconds = time_limit_between_requests

    @property
    def time_since_last_access(self) -> timedelta:
        return timedelta(seconds=(datetime.now()-self.time_last_access).total_seconds())

    def accessed_now(self) -> None:
        self.time_last_access = datetime.now()
        return None

    def is_accessible(self) -> bool:
        return self.time_since_last_access.seconds >= self.time_limit_seconds

    def __hash__(self):
        return hash(self.nam_domain)

    def __eq__(self, domain):
        return domain == self.nam_domain

    def __str__(self):
        return self.nam_domain

    def __repr__(self):
        return str(self)
