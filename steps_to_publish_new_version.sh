#/bin/bash

echo "Don't run this script. It's used as reference for manual work only"
exit

hatch test -i py=3.8 -c  # All tests must pass
hatch env run -e py3.8 coverage report -- --format=total  # Update total into README.md

# Set new version number in pyproject.toml
git add pyproject.toml README.md
git commit -m "Release v$(hatch version)"
git push
git tag -a release-$(hatch version) -m "Release v$(hatch version)"
git push origin release-$(hatch version)

# Really build and release it
