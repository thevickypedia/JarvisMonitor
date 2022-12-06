#!/bin/bash
# git push origin --delete docs  # Delete remote branch
dt=$(date '+%d/%m/%Y %H:%M:%S %Z %z');
echo -e '\n***************************************************************************************************'
echo "                               $dt"
echo -e '***************************************************************************************************\n'
echo 'Deleting the existing branch: docs'
git branch -D docs  # Delete local branch to avoid overlap errors
echo 'Creating a new branch: docs'
git checkout -b docs  # Create a new branch
if [[ -f "venv/bin/activate" ]]; then
  echo 'Activating virtual env'
  source venv/bin/activate
fi
echo 'Running monitor script'
python main.py
echo 'Adding index file to staged changes'
git add "docs/index.html"
echo 'Running git commit'
git commit -m "Updated as of $dt"
echo 'Running git push'
git push -f origin docs
