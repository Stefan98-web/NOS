FROM ros:humble

ENV DEBIAN_FRONTEND=noninteractive

# Minimal tools for build
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# rosdep init/update (safe pattern)
RUN rosdep update || true

# workspace
WORKDIR /ros2_ws

# Copy requirements first (for caching)
COPY requirements.txt /ros2_ws/requirements.txt

# Install python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# auto-source ROS
RUN echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc

CMD ["bash"]