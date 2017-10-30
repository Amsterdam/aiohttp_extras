from aiohttp_extras.serializers.hal_json import _parse_embed


def test_happy_path():
    embed = _parse_embed.parse_embed('foo(foo,bar(),baz(,foo,)),bar,')
    EXPECTED = {
        'foo': {
            'foo': {},
            'bar': {},
            'baz': {
                'foo': {}
            },
        },
        'bar': {}
    }
    assert embed == EXPECTED
    embed = _parse_embed.parse_embed(_parse_embed.to_string(embed))
    assert embed == EXPECTED
