#!/bin/bash

echo "Waiting for Postgres to start ..."
bash ataka/common/wait-for-it.sh postgres:5432 -t 0
echo "Postgres is running!"

echo ""
echo "Waiting for RabbitMQ to start ..."
bash ataka/common/wait-for-it.sh rabbitmq:5672 -t 0
echo "RabbitMQ is running!"

shift;  # skip shell script and first --
echo ""
echo "Starting now $@ ..."
exec $@
