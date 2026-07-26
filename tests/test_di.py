from shakti import Config, Depends, Shakti
from shakti.testing import TestClient

app = Shakti(debug=False)


class ServiceA:
    pass


app.container.register(ServiceA)

counter = {"n": 0}


async def next_number() -> int:
    counter["n"] += 1
    return counter["n"]


@app.get("/service")
async def service_route(service: ServiceA) -> dict:
    return {"is_service": isinstance(service, ServiceA), "id": id(service)}


@app.get("/dep")
async def dep_route(a: int = Depends(next_number), b: int = Depends(next_number)) -> dict:
    return {"a": a, "b": b}


@app.get("/query")
async def query_route(limit: int = 10, active: bool = False, q: str = "") -> dict:
    return {"limit": limit, "active": active, "q": q}


@app.get("/required")
async def required_route(term: str) -> dict:
    return {"term": term}


@app.get("/config")
async def config_route(config: Config) -> dict:
    return {"is_config": isinstance(config, Config)}


client = TestClient(app)


def test_container_singleton() -> None:
    first = client.get("/service").json()
    second = client.get("/service").json()
    assert first["is_service"] is True
    assert first["id"] == second["id"]


def test_depends_request_scoped_cache() -> None:
    counter["n"] = 0
    first = client.get("/dep").json()
    assert first == {"a": 1, "b": 1}  # cached within one request
    second = client.get("/dep").json()
    assert second == {"a": 2, "b": 2}  # fresh per request


def test_query_defaults() -> None:
    assert client.get("/query").json() == {"limit": 10, "active": False, "q": ""}


def test_query_casting() -> None:
    response = client.get("/query?limit=5&active=true&q=forge")
    assert response.json() == {"limit": 5, "active": True, "q": "forge"}


def test_query_invalid_int_is_422() -> None:
    assert client.get("/query?limit=abc").status_code == 422


def test_missing_required_param_is_422() -> None:
    assert client.get("/required").status_code == 422
    assert client.get("/required?term=x").json() == {"term": "x"}


def test_config_injected_from_container() -> None:
    assert client.get("/config").json() == {"is_config": True}
