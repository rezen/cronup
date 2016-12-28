FROM centos
RUN yum install -y vim cronie
RUN mkdir -p /var/log/cronup/
WORKDIR /root
RUN echo -e "set nocp\nset term=builtin_ansi\n" > /root/.vimrc
ADD . /data/cronup
