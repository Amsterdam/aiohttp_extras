.PHONY: test testcov release dist clean

PYTHON = python3
RM = rm -rf

# `pytest` and `python -m pytest` are equivalent, except that the latter will
# add the current working directory to sys.path. We don't want that; we want
# to test against the _installed_ package(s), not against any python sources
# that are (accidentally) in our CWD.
PYTEST = pytest
SETUPTEST = $(PYTHON) setup.py test


# The ?= operator below assigns only if the variable isn't defined yet. This
# allows the caller to override them:
#
#     TESTS=other_tests make test
#
#PYTEST_OPTS    ?= --verbose -p no:cacheprovider --exitfirst --capture=no
PYTEST_OPTS     ?= --verbose -p no:cacheprovider --exitfirst
PYTEST_OPTS_COV ?= --verbose -p no:cacheprovider --exitfirst --cov=src --cov-report=term --no-cov-on-fail
TESTS ?= tests


dist: test clean
	$(PYTHON) setup.py sdist


release: test clean
	$(PYTHON) setup.py sdist upload


test:
	$(SETUPTEST) --addopts "$(PYTEST_OPTS)     $(TESTS)"


testcov:
	$(SETUPTEST) --addopts "$(PYTEST_OPTS_COV) $(TESTS)"


pytest:
	$(PYTEST) $(PYTEST_OPTS)     $(TESTS)


pytestcov:
	$(PYTEST) $(PYTEST_OPTS_COV) $(TESTS)


clean:
	@$(RM) .eggs src/datapunt_config_loader.egg-info dist .coverage
	@find . \( \
		    -iname "*~" \
		-or -iname "__pycache__" \
	\) -delete
