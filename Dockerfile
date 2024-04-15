FROM python:3.12

ENV HOME=/opt/app

WORKDIR $HOME

COPY . $HOME

RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

RUN pip install -r requirements.txt

EXPOSE 80

CMD [ "./start.sh" ]
