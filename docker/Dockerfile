FROM ubuntu:latest
USER root

RUN apt update && apt install -y bash grep curl python3 python3-dev python3-pip

# install chromium dependencies
ENV TZ=Europe/Paris
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt install -y gconf-service libasound2 libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libnspr4 libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 ca-certificates fonts-liberation libappindicator1 libnss3 lsb-release xdg-utils wget

RUN mkdir -p /crawlalllinks

COPY requirements.txt /crawlalllinks/

RUN pip install -r /crawlalllinks/requirements.txt

RUN pyppeteer-install

COPY sources/* /crawlalllinks/sources/

WORKDIR /crawlalllinks/sources



#ENTRYPOINT ["/bin/bash"]
ENTRYPOINT ["python3","crawlalllinks.py"]