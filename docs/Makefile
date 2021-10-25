# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    		?=
SPHINXBUILD   		?= sphinx-build
BUILDDIR			= build
export PROJECTNAME 	= creepy
export SOURCEDIR	= source
export AUTOAPIDIR	= $(SOURCEDIR)/autoapi
export CODEDIR		= ../$(PROJECTNAME)
READMEFILES = $(shell realpath --relative-to $(CODEDIR) $(wildcard $(CODEDIR)/*/README.md))

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile copy_readme clean

# Copy all README.md files to autoapi dir.
# TODO(Roman Bilyi): Make it Makefile way.
copy_readme:
	for file in $(READMEFILES);\
	do \
		from_path=$(CODEDIR)/$${file};\
		to_path=$(AUTOAPIDIR)/$(PROJECTNAME)/$${file};\
		mkdir -p $$(dirname $${to_path});\
		cp $${from_path} $${to_path};\
	done;

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile copy_readme
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

clean:
	rm -r build
