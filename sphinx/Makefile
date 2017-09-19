RM            = rm -rf
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
AUTOBUILD     = sphinx-autobuild
SOURCEDIR     = .
BUILDDIR      = _build


html:
	$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)


server:
	@$(AUTOBUILD) "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) --watch ../src


clean:
	@$(RM) $(BUILDDIR)


invclean:
	@$(RM) *.inv *.inv.txt


publish: html
	cd gh-pages && $(RM) *
	cd _build/html && cp -a * ../../gh-pages/
