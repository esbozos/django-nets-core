# BASH SCRIPT to commit changes to git and build the project
# Author: Norman Torres
# Date: 2023-09-17
# Version: 1.0
# Description: This script will commit changes to git and build the project
# Usage: ./sync_and_build.sh

# Enter folder nets_core and commit and push changes to git
# cd nets_core
# git add *
# git commit -m "Syncing changes to git from local to deploy django-nets-core"
# git push origin master

# # Enter to django-nets-core/nets_core and pull changes from git
# cd ../../django-nets-core/nets_core
# git pull origin master --rebase

# # Enter to django-nets-core and build the project
# cd ..

# increase version number in setup.cfg
# get current version number from setup.cfg is in form 0.1.29
version=$(grep -oP '(?<=version = ).*' setup.cfg)
# increase version number
version=$(echo $version | awk -F. '{$NF = $NF + 1;} 1' | sed 's/ /./g')

# replace version number in setup.cfg
sed -i "s/version = .*/version = $version/" setup.cfg

# build the project
python3 setup.py sdist 


