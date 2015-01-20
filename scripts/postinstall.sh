manage="${VENV}/bin/python ${INSTALLDIR}/${REPO}/django_usaid_clinicfinder/manage.py"

if [ ! -f ${INSTALLDIR}/clinicfinder-installed ]; then
    su - postgres -c "createdb django_usaid_clinicfinder"
    su - postgres -c "psql django_usaid_clinicfinder -c 'CREATE EXTENSION hstore; CREATE EXTENSION postgis; CREATE EXTENSION postgis_topology;'"

    mkdir ${INSTALLDIR}/${REPO}/django_usaid_clinicfinder/static

    chown -R ubuntu:ubuntu ${INSTALLDIR}/${REPO}/media
    chown -R ubuntu:ubuntu ${INSTALLDIR}/${REPO}/static

    $manage syncdb --noinput
    $manage collectstatic --noinput
    touch ${INSTALLDIR}/clinicfinder-installed
else
    $manage migrate --noinput
    $manage collectstatic --noinput
fi