"""FRED adapter skeleton
"""

def fetch_since(timestamp: str) -> list:
    """Fetch new FRED observations since `timestamp`.

    This is a placeholder: implement the FRED HTTP client and parsing later.
    Return a list of simple dict records with `timestamp`, `series_id`, and `value`.
    """
    # TODO: implement with `fredapi` or requests to the FRED endpoints
    return []
