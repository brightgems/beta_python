FROM postgres:9.5

RUN apt-get update -y &&\
    apt-get install -y vim less &&\
    apt-get clean &&\
    rm -rf /var/lib/apt/lists/*

ADD /dev.sh /docker-entrypoint-initdb.d/dev.sh
ADD /demo.sh /docker-entrypoint-initdb.d/demo.sh
ADD /demostaging.sh /docker-entrypoint-initdb.d/demostaging.sh
ADD /ipdemostaging.sh /docker-entrypoint-initdb.d/ipdemostaging.sh
ADD /ipdemostaging.sh /docker-entrypoint-initdb.d/ipdemo.sh
ADD /ipdev.sh /docker-entrypoint-initdb.d/ipdev.sh
ADD /ipdev.sh /docker-entrypoint-initdb.d/ip.sh
ADD /prod.sh /docker-entrypoint-initdb.d/prod.sh
ADD /aus.sh /docker-entrypoint-initdb.d/aus.sh
ADD /beta.sh /docker-entrypoint-initdb.d/beta.sh
ADD /betastaging.sh /docker-entrypoint-initdb.d/betastaging.sh
ADD /staging.sh /docker-entrypoint-initdb.d/staging.sh
ADD /production.sh /docker-entrypoint-initdb.d/production.sh
ADD /local.sh /docker-entrypoint-initdb.d/local.sh


#COPY ./docker-entrypoint.sh /

RUN chmod +x /docker-entrypoint-initdb.d/dev.sh
RUN chmod +x /docker-entrypoint-initdb.d/demo.sh
RUN chmod +x /docker-entrypoint-initdb.d/demostaging.sh
RUN chmod +x /docker-entrypoint-initdb.d/ipdemostaging.sh
RUN chmod +x /docker-entrypoint-initdb.d/ipdemo.sh
RUN chmod +x /docker-entrypoint-initdb.d/ipdev.sh
RUN chmod +x /docker-entrypoint-initdb.d/ip.sh
RUN chmod +x /docker-entrypoint-initdb.d/prod.sh
RUN chmod +x /docker-entrypoint-initdb.d/aus.sh
RUN chmod +x /docker-entrypoint-initdb.d/beta.sh
RUN chmod +x /docker-entrypoint-initdb.d/betastaging.sh
RUN chmod +x /docker-entrypoint-initdb.d/staging.sh
RUN chmod +x /docker-entrypoint-initdb.d/production.sh
RUN chmod +x /docker-entrypoint-initdb.d/local.sh

#CMD ["/docker-entrypoint.sh"]
