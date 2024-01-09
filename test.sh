#!/bin/bash

venv="/tmp/venv-kcbot"
if ! test -d "$venv" ; then
	echo "Creating venv"
	virtualenv "$venv"
fi

source "$venv/bin/activate"
echo "Installing venv"
pip install -r requirements.txt 1>/dev/null
pip install -r test-requirements.txt 1>/dev/null
pip install -e . 1>/dev/null

flake8 . || exit 1

black --check . || exit 1

isort --check . || exit 1

mypy --ignore-missing-imports . || exit 1

./.pylint.sh || exit 1

pytest || exit 1

coverage run -m pytest
coverage report
coverage html
