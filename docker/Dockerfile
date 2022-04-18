FROM ubuntu:latest
USER root

RUN apt update && apt install -y bash grep curl python3 python3-dev python3-pip

RUN mkdir -p /crawlalllinks

COPY requirements.txt /crawlalllinks/

RUN pip install -r /crawlalllinks/requirements.txt

COPY sources/* /crawlalllinks/sources/

WORKDIR /crawlalllinks/sources

#ENTRYPOINT ["/bin/bash"]
ENTRYPOINT ["python3","crawlalllinks.py"]