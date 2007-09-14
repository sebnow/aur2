PROJECT_DIR=/home/ius/git/aur2/archlinux/
python ${PROJECT_DIR}manage.py dumpdata --format=xml --indent=4 > ${PROJECT_DIR}aur/fixtures/initial_data.xml
