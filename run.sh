#!/bin/bash
# git push origin --delete docs  # Delete remote branch
dt=$(date '+%d/%m/%Y %H:%M:%S %Z %z')

echo -e '\n\n***************************************************************************************************'
echo "                               $dt"
echo -e '***************************************************************************************************\n'

echo -e "Checkout and rebase to docs branch"
git checkout -b docs
git pull --rebase

if [[ -f "venv/bin/activate" ]]; then
  echo 'Activating virtual env'
  source venv/bin/activate
fi

echo -e "Running monitor script"
python main.py

if [[ -n $(git status -s) ]]; then
  echo -e "Adding all changes to stage"
  git add --all

  echo -e "Running git commit"
  git commit -m "Updated as of $dt"

  echo -e "\nPushing changes to origin"
  git push -f origin docs
  echo -e "Task completed."
else
  echo -e "No changes detected. Task completed."
fi
