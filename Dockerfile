FROM rabbitmq:4.0-management

# Install Python and venv (no supervisor needed)
USER root
RUN apt-get update && apt-get install -y python3 python3-pip python3-venv curl && \
    rm -rf /var/lib/apt/lists/*

# Copy files
COPY rabbitmq.conf /etc/rabbitmq/
COPY monitor.py /usr/local/bin/
COPY start-services.sh /usr/local/bin/
COPY requirements.txt /tmp/

# Create virtual environment and install Python dependencies
RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Make scripts executable
RUN chmod +x /usr/local/bin/monitor.py /usr/local/bin/start-services.sh

# Add venv to PATH so Python uses it by default
ENV PATH="/opt/venv/bin:$PATH"

ENV RABBITMQ_NODENAME=rabbit@localhost

# Enable plugins
RUN rabbitmq-plugins enable rabbitmq_management rabbitmq_prometheus

# Create .erlang.cookie with proper permissions if it doesn't exist
# Then set all permissions for RabbitMQ user
RUN touch /var/lib/rabbitmq/.erlang.cookie && \
    chmod 600 /var/lib/rabbitmq/.erlang.cookie && \
    chown -R rabbitmq:rabbitmq /etc/rabbitmq /var/lib/rabbitmq /opt/venv /usr/local/bin/monitor.py /usr/local/bin/start-services.sh

# Run as non-root rabbitmq user
USER rabbitmq:rabbitmq
EXPOSE 5672 15672 15692

CMD ["/usr/local/bin/start-services.sh"]
