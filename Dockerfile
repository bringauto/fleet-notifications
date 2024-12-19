FROM bringauto/python-environment:latest

WORKDIR /home/bringauto

COPY ./requirements.txt /home/bringauto
RUN "$PYTHON_ENVIRONMENT_PYTHON3" -m pip install --no-cache-dir -r requirements.txt

COPY config /home/bringauto/config
COPY fleet_notifications /home/bringauto/fleet_notifications

EXPOSE 8080

RUN mkdir /home/bringauto/log

ENTRYPOINT ["bash", "-c", "$PYTHON_ENVIRONMENT_PYTHON3 -m fleet_notifications $0 $@"]
CMD ["config/config.json"]