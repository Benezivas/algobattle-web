docker run --rm \
    -v algobattle-web_db-data:/db_data \
    -v algobattle-web_db-files:/db_files \
    -v $1:/backup \
    -e TZ=$TZ \
    busybox \
    tar -zcvf /backup/`date +"%Y-%m-%d_%H-%M-%S"`.tar.gz /db_data /db_files