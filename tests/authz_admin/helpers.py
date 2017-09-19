from collections import deque


def follow_path(o, *args):
    # language=rst
    """Follows a path through a nested dictionary.

    Asserts that each path element exists.

    Example usage::

        o = {
            'foo': {
                'bar': "baz"
            }
        }
        follow_path(o, 'foo', 'bar')
        >>> "baz"
        follow_path(o, 'not_existing')
        >>> raises AssertionError

    """
    seen = deque()
    cursor = o
    path = deque(args)
    while len(path) > 0:
        assert hasattr(cursor, '__getitem__'), \
            "Object at path {} is not subscriptable:\n{}".format(tuple(seen), cursor)
        path_element = path.popleft()
        seen.append(path_element)
        assert path_element in cursor, \
            "No object found at path {}:\n{}".format(tuple(seen), o)
        cursor = cursor[path_element]
    return cursor


