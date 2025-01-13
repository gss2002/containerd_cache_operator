# Use the official Rocky Linux 9 base image
FROM rockylinux:9

# Update system packages and install necessary tools for Python
RUN dnf update -y && \
    dnf install -y \
    python3 \
    python3-pip \
    && \
    dnf clean all

# Set Python 3 as the default python
#RUN alternatives --set python /usr/bin/python3

# Upgrade pip to the latest version
RUN pip3 install --upgrade pip

# Install Python modules required by the application
RUN pip3 install toml

# Switch to the non-root user


# Run the Python script when the container launches

COPY containerd_config.py /
CMD ["python3", "/containerd_config.py"]
