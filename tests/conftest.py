from dotenv import load_dotenv


def pytest_sessionstart(session):
    # This hook runs once at the beginning of the entire test session
    load_dotenv()
