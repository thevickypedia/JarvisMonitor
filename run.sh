#!/bin/bash
# git push origin --delete docs  # Delete remote branch
dt=$(date '+%d/%m/%Y %H:%M:%S %Z %z');
default=$(git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@')

echo -e '\n***************************************************************************************************'
echo "                               $dt"
echo -e '***************************************************************************************************\n'

echo 'Deleting the existing branch: docs'
git branch -D docs  # Delete local branch to avoid overlap errors

echo "Retrieving latest commit info from $default branch"
git checkout "$default"
git pull --rebase
sha=$(git log --format="%H" -n 1)
msg=$(git log --oneline -1)
# msg=$(git log -1 --pretty=%B)  # Get commit message in multiple lines
echo "Latest commit on $default branch: $sha - $msg"

echo "Resetting docs branch to match $default"
git checkout -b docs
git reset --hard "$sha"
# git push -f origin docs  # Instant reset

if [[ -f "venv/bin/activate" ]]; then
  echo 'Activating virtual env'
  source venv/bin/activate
fi

echo 'Running monitor script'
python main.py

echo 'Adding all changes to stage'
git add --all

echo 'Running git commit'
git commit -m "Updated as of $dt"

echo 'Pushing changes to origin'
git push -f origin docs
