"""Test script to debug cloud mode status query."""

import os

# Set cloud mode
os.environ["DATABASE_URL"] = "kurt"

from kurt.db import managed_session
from kurt.status.queries import get_status_data

print("Testing cloud mode status query...")

try:
    with managed_session() as session:
        print(f"Session type: {type(session)}")
        print(f"Has _client: {hasattr(session, '_client')}")

        result = get_status_data(session)
        print(f"Result: {result}")
        print("SUCCESS!")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()
