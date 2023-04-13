from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union, overload

import requests
from pydantic import BaseModel, validator
from requests.adapters import HTTPAdapter, Retry

from darwin.future.core.types.query import Query
from darwin.future.data_objects.darwin_meta import Team
from darwin.future.exceptions.client import NotFound, Unauthorized

# HTTPMethod = TypeVar("HTTPMethod", bound=Callable[..., requests.Response])
HTTPMethod = Union[Callable[[str], requests.Response], Callable[[str, dict], requests.Response]]


class Config(BaseModel):
    """Configuration object for the client

    Attributes
    ----------
    api_key: Optional[str], api key to authenticate
    base_url: pydantic.HttpUrl, base url of the API
    default_team: Optional[Team], default team to make requests to
    """

    api_key: Optional[str]
    base_url: str
    default_team: Optional[Team]

    @validator("base_url")
    def validate_base_url(cls, v: str) -> str:
        v = v.strip()
        if not v.endswith("/"):
            v += "/"
        assert v.startswith("http") or v.startswith("https"), "base_url must start with http or https"
        assert v.count("/") >= 3, "base_url must contain at least 3 slashes"
        return v

    def from_env(cls) -> Config:
        pass

    def from_file(cls, path: Path) -> Config:
        pass

    class Config:
        validate_assignment = True


class Result(BaseModel):
    """Default model for a result, to be extended by other models specific to the API"""

    def from_json(cls, json: dict) -> Result:
        pass


class PageDetail(BaseModel):
    """Page details model for managing pagination

    Attributes
    ----------
    count: int, current position
    next: Optional[str], url for the next page
    previous: Optional[str], url for the previous page
    """

    count: int
    next: Optional[str]
    previous: Optional[str]


class Page(BaseModel):
    """Page of results

    Attributes
    ----------
    results: List[Result], list of results
    detail: PageDetail, details about the page
    """

    results: List[Result]
    detail: PageDetail


class Cursor(ABC):
    """Abstract class for a cursor

    Attributes
    ----------
    url: str, url of the endpoint
    client: Client, client used to make requests
    """

    def __init__(self, url: str, client: Client):
        self.url = url
        self.client = client
        self.current_page: Optional[Page] = None

    @abstractmethod
    def execute(self, query: Query) -> Page:
        pass

    @abstractmethod
    def __iter__(self) -> Page:
        pass

    @abstractmethod
    def __next__(self) -> Page:
        pass


class Client:
    """Client Object to manage and make requests to the Darwin API
    Attributes
    ----------
    url: str, url of the endpoint
    api_key: str, api key to authenticate
    team: Team, team to make requests to
    """

    def __init__(self, config: Config, retries: Optional[Retry] = None) -> None:
        self.config = config
        self.session = requests.Session()
        if not retries:
            retries = Retry(total=3, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504])
        self._setup_session(retries)
        self._mappings = {
            "get": self.session.get,
            "put": self.session.put,
            "post": self.session.post,
            "delete": self.session.delete,
            "patch": self.session.patch,
        }

    def _setup_session(self, retries: Retry) -> None:
        self.session.headers.update(self.headers)
        self.session.mount("http://", HTTPAdapter(max_retries=retries))
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    @property
    def headers(self) -> Dict[str, str]:
        http_headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.config.api_key:
            http_headers["Authorization"] = f"ApiKey {self.config.api_key}"
        return http_headers

    @overload
    def _generic_call(self, method: Callable[[str], requests.Response], endpoint: str) -> dict:
        ...

    @overload
    def _generic_call(self, method: Callable[[str, dict], requests.Response], endpoint: str, payload: dict) -> dict:
        ...

    def _generic_call(self, method: Callable, endpoint: str, payload: Optional[dict] = None) -> dict:
        endpoint = self._validate_endpoint(endpoint)
        url = self.config.base_url + endpoint
        if payload is not None:
            response = method(url, payload)
        else:
            response = method(url)

        raise_for_darwin_exception(response)
        response.raise_for_status()

        return response.json()

    def cursor(self) -> Cursor:
        pass

    def get(self, endpoint: str) -> dict:
        return self._generic_call(self.session.get, endpoint)

    def put(self, endpoint: str, data: dict) -> dict:
        return self._generic_call(self.session.put, endpoint, data)

    def post(self, endpoint: str, data: dict) -> dict:
        return self._generic_call(self.session.post, endpoint, data)

    def delete(self, endpoint: str) -> dict:
        return self._generic_call(self.session.delete, endpoint)

    def patch(self, endpoint: str, data: dict) -> dict:
        return self._generic_call(self.session.patch, endpoint, data)

    def _validate_endpoint(self, endpoint: str) -> str:
        return endpoint.strip().strip("/")


def raise_for_darwin_exception(response: requests.Response) -> None:
    """Raises an exception if the response is not 200

    Parameters
    ----------
    response: requests.Response, response to check
    """
    if response.status_code == 200:
        return
    if response.status_code == 401:
        raise Unauthorized(response)
    if response.status_code == 404:
        raise NotFound(response)