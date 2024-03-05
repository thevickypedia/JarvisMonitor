#!/bin/bash
# git push origin --delete docs  # Delete remote branch
dt=$(date '+%d/%m/%Y %H:%M:%S %Z %z')
default=$(git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@')

echo -e '\n\n***************************************************************************************************'
echo "                               $dt"
echo -e '***************************************************************************************************\n'

echo -e "\nSwitching to $default branch"
git checkout "$default"
echo -e "\nRetrieving latest commit info from $default branch"
git pull --rebase
sha=$(git log --format="%H" -n 1)
msg=$(git log --oneline -1)
# msg=$(git log -1 --pretty=%B)  # Get commit message in multiple lines

echo -e "\nLatest commit on $default branch: $sha - $msg"

echo -e "\nResetting docs branch to match $default"
git branch -D docs # Delete local branch to avoid overlap errors
git checkout -b docs
git reset --hard "$sha"
# git push -f origin docs  # Instant reset

if [[ -f "venv/bin/activate" ]]; then
  echo 'Activating virtual env'
  source venv/bin/activate
fi

echo -e "\nRunning monitor script"
python main.py

echo -e "\nChecking for changes"
if [[ -n $(git status -s) ]]; then
  echo -e "\nAdding all changes to stage"
  git add --all

  echo -e "\nRunning git commit"
  git commit -m "Updated as of $dt"

  echo -e "\nPushing changes to origin"
  git push -f origin docs
  echo -e "\nCompleted task"
else
  echo -e "\nNo changes detected. Task completed."
fi
