#
# Copyright (c) 2016-2023, Smart Engines Service LLC
# All rights reserved
#

# Image for building python wrapper 
FROM ubuntu:22.04 AS builder

# Copy SDK to image

COPY "./bin/" /home/idengine/bin/
COPY "./bindings/" /home/idengine/bindings/
COPY "./include/" /home/idengine/include/
COPY "./data-zip/" /home/idengine/data-zip/
COPY "./samples/" /home/idengine/samples/
COPY "./integration/" /home/idengine/integrations/
WORKDIR "/home/idengine/samples/idengine_sample_python/"

# remove interactive actions in console
ENV DEBIAN_FRONTEND noninteractive

RUN set -xe \
	&& apt -y update  \
	&& apt -y install tcl \
	&& apt -y install build-essential \
	&& apt -y install make \
	&& apt -y install cmake \
	&& apt -y install python3-dev

RUN bash ./build_python_wrapper.sh "/home/idengine/bin/" 3

# Image for production
FROM ubuntu:22.04
RUN set -xe \
	&& apt -y update  \
	&& apt -y install python3 \
	&& apt -y install python3-dev

# idengine libs
COPY --from=builder /home/idengine/bin/ /home/idengine/bin/
# py wrapper
COPY --from=builder /home/idengine/bindings/python/pyidengine.py /home/idengine/bindings/python/pyidengine.py
# bundle
COPY --from=builder /home/idengine/data-zip/ /home/idengine/data-zip/
# server
COPY "./integration/docker/idengine_server.py" /home/idengine/

WORKDIR "/home/idengine/"

# --bundle_dir (required) - path to bundle.
# --lazy - IdEngine lazy mode. Not recommended for server.
# --concur - Concurrency. All CPU cores enabled by default.
# --port - Server port. [default 53000]

CMD ["bash","-c","python3 idengine_server.py --bundle_dir './data-zip/' "]
