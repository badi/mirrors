
NAME=mirror
VENV=venv
PIP=$(VENV)/bin/pip

.PHONY: venv

venv: $(VENV)/bin/activate

$(VENV)/bin/activate: requirements.txt
	test -d $(VENV) || virtualenv $(VENV)
	$(PIP) install -U  pip requests[security]
	$(PIP) install -Ur requirements.txt
	touch $@
