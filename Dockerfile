FROM python:3.9-alpine3.15

# LABEL MAINTAINER="FirstName LastName <example@domain.com>"

ENV GROUP_ID=1000 \
    USER_ID=1000

WORKDIR /mcd

ADD . /mcd
RUN pip install -r requirements.txt
# RUN pip install gunicorn

RUN addgroup -g $GROUP_ID mcd
RUN adduser -D -u $USER_ID -G mcd mcd -s /bin/sh

USER mcd

EXPOSE 5000

CMD [ "python", "app.py"]
# CMD [ "gunicorn", "-w", "4", "--bind", "0.0.0.0:5000", "wsgi"]