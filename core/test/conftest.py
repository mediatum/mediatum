from pytest import yield_fixture


@yield_fixture(autouse=True)
def session(session):
    yield session
