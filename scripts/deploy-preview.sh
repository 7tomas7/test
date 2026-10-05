#!/usr/bin/env bash
# Publikacja PODGLĄDU na GitHub Pages (https://7tomas7.github.io/test/).
#   set -e  = przerwij przy pierwszym błędzie (nie publikuj połowicznie zbudowanej strony)
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/build.py --preview          # buduje dist/ z noindex
cd dist
git init -q -b gh-pages
git add -A
git commit -qm "Publikacja podglądu $(date '+%Y-%m-%d %H:%M')"
# -f: gałąź gh-pages to tylko wynik budowania, więc nadpisujemy ją w całości
git push -qf git@github.com:7tomas7/test.git gh-pages
echo "Wysłane. Strona odświeży się za ok. 1 minutę: https://7tomas7.github.io/test/"
