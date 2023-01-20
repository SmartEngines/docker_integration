#
# Copyright (c) 2016-2023, Smart Engines Service LLC
# All rights reserved
#

import asyncio
from io import FileIO
import pathlib
import pickle
import json
import time

from datetime import date
import struct
import argparse
import uuid
from datetime import datetime, timezone


""" 
    This client send settings object to the server and return recognition result in json file.

    Example: python3 client.py  -mask "mrz.mrp" -s=YOUR_SIGNATURE_HERE --image_path="./Smart-ID-Engine/testdata/mrz_passport_2.jpg"
    Response:

    {
        "error":false,
        "response":{
            "docType":"mrz.mrp",
            "fields":{
                "full_mrz":{
                    "name":"full_mrz",
                    "value":"P<CANMARTIN<<SARAH<<<08",
                    "isAccepted":true,
                    "attr":{
                    "control_digit_check":"passed"
                    }
                },
                "mrz_birth_date":{
                    "name":"mrz_birth_date",
                    "value":"01.01.1985",
                    "isAccepted":true,
                    "attr":{
                    "control_digit_check":"passed"
                    }
                },
                "mrz_gender":{
                    "name":"mrz_gender",
                    "value":"F",
                    "isAccepted":true
                }
            }
        }
    }

    Arguments:

    --mask - Document mask. [default "*"]
    --mode - Engine mode. [default "default"]
    --signature - *required*. Licencse key.
    --image_path - *required*. Path to local image.
    --output - Output folder for result. [default "./result"]
    --forensics - If you want to check forensics data. This option must be enabled with `"common.currentDate": "DD.MM.YYYY"` in `options`forensics data. [default false]
    --endpoint - server ip adress
    --port - Port of your server endpoint. [default 53000]

"""


parser = argparse.ArgumentParser()

parser.add_argument('-mask', '--mask', default="*")
parser.add_argument('-mode', '--mode', default="default")
parser.add_argument('-s', '--signature')
parser.add_argument('-i', '--image_path')
parser.add_argument('-o', '--output', default="./result")
parser.add_argument('-f', '--forensics', action='store_true')
parser.add_argument('-e', '--endpoint', default="127.0.0.1")
parser.add_argument('-p', '--port', default=53000)
parser.add_argument('-l', '--log', action='store_true')
parser.add_argument('-t', '--stdout', action='store_true')

args = parser.parse_args()

mode = args.mode
mask = args.mask
sign = args.signature
input = args.image_path
folder_dest = args.output
is_forensics = args.forensics
is_log = args.log
endpoint = args.endpoint
port = args.port


if is_log:
    settings = {
        "log": True
    }

else:
    # Get current date for forensics
    today = date.today()
    # dd.mm.yyyy
    currentDate = today.strftime("%d.%m.%Y")

    input = FileIO(input).read()

    settings = {
        "mode": mode,
        "mask": [mask],
        "forensics": is_forensics,
        "options": {"common.currentDate": currentDate},
        "input": input,
        "signature": sign
    }


async def save_result(data):
    """  Create folder and save result as json file. """
    if (folder_dest == "stdout"):
        print(json.dumps(data, ensure_ascii=False, indent=4, sort_keys=True))
    else:
        # Create folder if not exist
        pathlib.Path(folder_dest).mkdir(parents=True, exist_ok=True)

        # get the current time
        time = datetime.now(
            timezone.utc).strftime("%Y-%m-%d_%H-%M")

        # Filename = time + random salt
        filename = time + '_' + str(uuid.uuid4().hex)[0:8] + '.json'

        full_path = folder_dest + '/' + filename

        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f,
                      ensure_ascii=False, indent=4, sort_keys=True)


async def tcp_client(settings):
    """ Connect to async sockets. Encode data for transmission and Decode for result.
        Result will be saved in a folder.
    """
    reader, writer = await asyncio.open_connection(endpoint, port)

    # send request
    serialized_data = pickle.dumps(settings)

    writer.write(struct.pack('<L', len(serialized_data)))
    writer.write(serialized_data)
    await writer.drain()

    # get response
    request_size = struct.unpack('<L', await reader.readexactly(4))[0]
    request_body = await reader.readexactly(request_size)
    message = pickle.loads(request_body)
    writer.close()

    if (message.get("error") == True):
        """ Log server exceptions """
        desc = message.get("desc")
        print(desc)

        file_object = open('error.log', 'a')
        timestr = time.strftime("%Y-%m-%d-%H%M%S")
        file_object.write("\r\n ========= " + timestr + " ========= \r\n")
        file_object.write(desc)

        file_object.close()
    else:
        await save_result(message)

asyncio.run(tcp_client(settings))
