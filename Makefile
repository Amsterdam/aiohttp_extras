.PHONY: run test jenkinstest cov testclean distclean clean

RM = rm -rf

# `pytest` and `python -m pytest` are equivalent, except that the latter will
# add the current working directory to sys.path. We don't want that; we want
# to test against the _installed_ package(s), not against any python sources
# that are (accidentally) in our CWD.
PYTEST = pytest

# The ?= operator below assigns only if the variable isn't defined yet. This
# allows the caller to override them::
#
#     TESTS=other_tests make test
#
#PYTEST_OPTS ?= --loop uvloop -p no:cacheprovider --verbose --exitfirst --capture=no --cov=src --cov-report=term --no-cov-on-fail
PYTEST_OPTS ?= --loop uvloop -p no:cacheprovider --verbose --exitfirst
PYTEST_COV_OPTS ?= --loop uvloop -p no:cacheprovider --verbose --cov=src --cov-report=term --no-cov-on-fail
TESTS ?= tests


run:
	cp -af src/authz_admin/openapi-$(DATAPUNT_ENVIRONMENT).json \
	       swagger-ui/dist/openapi.json && \
	authz_admin


schema schema_jenkins schema_acc:
	$(MAKE) -C alembic $@


test: schema
	$(PYTEST) $(PYTEST_OPTS) $(TESTS)


jenkinstest: schema_jenkins
	$(PYTEST) $(PYTEST_OPTS) $(TESTS)


cov:
	$(PYTEST) $(PYTEST_COV_OPTS) $(TESTS)


testclean:
	@$(RM) .cache .coverage


# @evert waar komt dit eigenlijk vandaan? [--PvB]
distclean:
	@$(RM) \
		dist/ \
		bin/ \
		develop-eggs/ \
		eggs/ \
		parts/ \
		MANIFEST \
		htmlcov/ \
		.installed.cfg

clean: testclean distclean
	@$(RM) build *.egg-info .eggs dist
	@find . -not -path "./.venv/*" -and \( \
		-name "*.pyc" -or \
		-name "__pycache__" -or \
		-name "*.pyo" -or \
		-name "*.so" -or \
		-name "*.o" -or \
		-name "*~" -or \
		-name "._*" -or \
		-name "*.swp" -or \
		-name "Desktop.ini" -or \
		-name "Thumbs.db" -or \
		-name "__MACOSX__" -or \
		-name ".DS_Store" \
	\) -delete
