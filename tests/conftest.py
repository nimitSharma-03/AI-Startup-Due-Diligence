from __future__ import annotations

import pytest

from diligence import create_app
from diligence.config import Config


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    config = Config(env="test", frontend_dist=tmp_path_factory.mktemp("dist"))
    application = create_app(config)
    application.config["TESTING"] = True
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(scope="session")
def model(app):
    return app.extensions["diligence"]["model"]


@pytest.fixture(scope="session")
def store(app):
    return app.extensions["diligence"]["store"]


GENERIC_CSV = (
    "Company Name,Founded Year,Funding,Location,Industry,Status\n"
    "Acme Robotics,2012,\"$2.5M\",San Francisco,\"Hardware, Robotics\",Operating\n"
    "Beta Health,2009,0,Boston,Health Care,Closed\n"
    "Gamma Pay,2011,750k,New York City,Finance,Acquired\n"
    "No Year Inc,,1000000,Austin,SaaS,\n"
    "=Formula Co,2013,-5,London,SaaS,\n"
)
