import re
import typing as T

from .helpers import follow_path


RE_DATASET_ID = re.compile(r'\w{1,4}')
RE_SCOPE_ID = re.compile(r'\w{1,4}')


def _test_verify_datasets_and_scope_ids(aaconfig):
    datasets = follow_path(aaconfig, 'authz_admin', 'datasets')
    assert isinstance(datasets, T.Mapping)
    for dataset_id, dataset in datasets.items():
        assert RE_DATASET_ID.fullmatch(dataset_id)
        dataset_name = follow_path(dataset, 'name')
        assert len(dataset_name) > 0
        assert len(dataset_name) <= 80
        scopes = follow_path(dataset, 'scopes')
        assert isinstance(scopes, T.Mapping)
        for scope_id, scope in scopes.items():
            assert RE_SCOPE_ID.fullmatch(scope_id)
            scope_name = follow_path(scope, 'name')
            assert len(scope_name) > 0
            assert len(scope_name) <= 80
