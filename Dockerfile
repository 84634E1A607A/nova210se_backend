FROM python:3.12

ENV HOME=/opt/app

WORKDIR $HOME

COPY . $HOME

RUN pip install -r requirements.txt

EXPOSE 80

CMD [ "./start.sh" ]
