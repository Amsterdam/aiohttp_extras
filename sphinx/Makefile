RM            = rm -rf
SPHINXOPTS    = -d .doctrees
SPHINXBUILD   = sphinx-build
AUTOBUILD     = sphinx-autobuild
SOURCEDIR     = .
BUILDDIR      = ../docs


html:
	$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS)
	touch $(BUILDDIR)/.nojekyll


server: clean
	@$(AUTOBUILD) "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) --watch ../src


clean:
	@$(RM) $(BUILDDIR) .doctrees


invclean:
	@$(RM) *.inv *.inv.txt
