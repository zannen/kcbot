#!/usr/bin/env bash

# Run pylint, collect output as json
pylint --exit-zero --persistent=no -f json kcbot/ tests/ *.py >.pylint.json

jqcmd='[.[]|select(.type==$x)]|length'
fatals="$(jq --arg x fatal "$jqcmd" .pylint.json)"
errors="$(jq --arg x error "$jqcmd" .pylint.json)"
warnings="$(jq --arg x warning "$jqcmd" .pylint.json)"
refactors="$(jq --arg x refactor "$jqcmd" .pylint.json)"
conventions="$(jq --arg x convention "$jqcmd" .pylint.json)"
usages="$(jq --arg x usage "$jqcmd" .pylint.json)"

max_fatal=0
max_error=0
max_warning=10
max_refactor=10
max_convention=10
max_usage=0

pylint --exit-zero --persistent=no kcbot/ tests/ *.py
echo
echo "Fatal: $fatals (max $max_fatal)"
echo "Error: $errors (max $max_error)"
echo "Warning: $warnings (max $max_warning)"
echo "Refactor: $refactors (max $max_refactor)"
echo "Convention: $conventions (max $max_convention)"
echo "Usage: $usages (max $max_usage)"

if [[ "$fatals" -gt "$max_fatal" || "$fatals" -gt "$max_fatal" || "$errors" -gt "$max_error" || "$warnings" -gt "$max_warning" || "$refactor" -gt "$max_refactor" || "$conventions" -gt "$max_convention" ]] ; then
	exit 1
fi
