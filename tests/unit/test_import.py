"""Skeleton unit test (step 0.1): every package module imports and stubs raise NotImplementedError."""
import importlib
import pkgutil

import pytest

import su2plaq


def _modules():
    return [m.name for m in pkgutil.walk_packages(su2plaq.__path__, "su2plaq.")]


@pytest.mark.parametrize("name", _modules())
def test_module_imports(name):
    importlib.import_module(name)


def test_stub_raises_not_implemented():
    from su2plaq.exact.physical import physical_basis

    with pytest.raises(NotImplementedError):
        physical_basis()
