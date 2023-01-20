#
# Copyright (c) 2016-2023, Smart Engines Service LLC
# All rights reserved
#

import asyncio
import argparse
import base64
import sys
import os
import pickle
import struct

sys.path.append(os.path.join(sys.path[0], './bindings/python/'))
sys.path.append(os.path.join(sys.path[0], './bin/'))

import pyidengine  # noqa  / # noqa to exclude that line from checking/sorting:/fieldsf_ir

"""
    This script listens for connections and wait for settings object.
"""

parser = argparse.ArgumentParser()

parser.add_argument('-b', '--bundle_dir', type=str,
                    required=True, help="bundle dir path")
parser.add_argument('-l', '--lazy', default=False,
                    action='store_true', help="Lazy init")
parser.add_argument('-c', '--concur', type=int, default=0,
                    help="CPU cores. Default max")
parser.add_argument('-p', '--port', type=int, default=53000,
                    help="CPU cores. Default max")


args = parser.parse_args()

global_engine = None
global_engine_exception = None


def initEngine():
    """
      Initialization is the longest process in recognition.
      We must init idengine only once on start.

      bundle_dir_path - Path to the *.se bundle file. Required.
      lazy_init       - Disable cache warming. Must be disabled for the server configurations.
                        Optimizes load time for idengine, but increases for recognition on new documents.
      concurrency     - How much CPU will be used for recognition. All CPU used by default.
    """

    bundle_dir_path = args.bundle_dir
    lazy_init = args.lazy
    concurrency = args.concur

    files = os.listdir(bundle_dir_path)

    bundle_path = ''
    for filepath in files:
        if '.se' in filepath:
            bundle_path = bundle_dir_path + '/' + filepath
        break
    # Init IdEngine
    try:
        global global_engine
        global_engine = pyidengine.IdEngine.Create(
            bundle_path, lazy_init, concurrency)

        print("idengine:", global_engine.GetVersion())
    except Exception as e:
        global global_engine_exception
        global_engine_exception = e
        print(e)


def RecognitionResult(recog_result):
    """
        Convert recognition result object to dict:

        {
          "docType":"",
          "fields":{},
          "images":{},
          "forensics":{}
        }

    """

    result = {}
    result['docType'] = recog_result.GetDocumentType()

    fields = {}
    forensics = {}
    images = {}

    # Text fields
    tf = recog_result.TextFieldsBegin()
    while(tf != recog_result.TextFieldsEnd()):

        info = tf.GetValue().GetBaseFieldInfo()

        # attr
        attr = {}
        mi = info.AttributesBegin()
        while(mi != info.AttributesEnd()):
            attr.update({mi.GetKey(): mi.GetValue()})
            mi.Advance()

        field = {
            'name': tf.GetKey(),
            'value': tf.GetValue().GetValue().GetFirstString().GetCStr(),
            'isAccepted': info.GetIsAccepted(),
        }

        if len(attr) != 0:
            field.update({'attr': attr})

        fields.update({tf.GetKey(): field})
        tf.Advance()

    # Image fields
    imf = recog_result.ImageFieldsBegin()
    while(imf != recog_result.ImageFieldsEnd()):

        info = imf.GetValue().GetBaseFieldInfo()

        # attr
        attr = {}
        mi = info.AttributesBegin()
        while(mi != info.AttributesEnd()):
            attr.update({mi.GetKey(): mi.GetValue()})
            mi.Advance()

        field = {
            'name': imf.GetKey(),
            'value': imf.GetValue().GetValue().GetBase64String().GetCStr(),
        }

        if len(attr) != 0:
            field.update({'attr': attr})

        images.update({
            imf.GetKey(): field
        })
        imf.Advance()

    # Forensics
    ff = recog_result.ForensicCheckFieldsBegin()
    while(ff != recog_result.ForensicCheckFieldsEnd()):

        info = ff.GetValue().GetBaseFieldInfo()

        status = 'undefined'
        if (ff.GetValue().GetValue() == pyidengine.IdCheckStatus_Passed):
            status = 'passed'
        elif (ff.GetValue() == pyidengine.IdCheckStatus_Failed):
            status = 'failed'

        field = {
            'name': ff.GetKey(),
            'value': status,
            'isAccepted': info.GetIsAccepted()
        }

        forensics.update({ff.GetKey(): field})
        ff.Advance()

    result['fields'] = fields
    if len(forensics) != 0:
        result['forensics'] = forensics

    return result


async def startRecognition(inputData):
    """
        1. Parse input settings object.
        2. Create session settings for idEngine.
        3. Put image data and start recognition.
    """

    signature = inputData.get("signature", "")
    mode = inputData.get("mode", "default")
    mask = inputData.get("mask", [])
    is_forensics = inputData.get("forensics", False)
    options = inputData.get("options", [])

    buffer = inputData.get("input", [])

    global global_engine

    try:
        session_settings = global_engine.CreateSessionSettings()

        session_settings.SetCurrentMode(mode)

        if is_forensics:
            # Do not forget to set currentDate in options!
            session_settings.EnableForensics()

        for docmask in mask:
            session_settings.AddEnabledDocumentTypes(docmask)

        for key, value in options.items():
            session_settings.SetOption(key, value)

        session = global_engine.SpawnSession(session_settings, signature)

        image = None

        file = base64.b64encode(buffer).decode("utf-8")
        image = pyidengine.Image.FromBase64Buffer(file)

        session.Process(image)

        # Obtaining the recognition result
        current_result = session.GetCurrentResult()
        result = RecognitionResult(current_result)

        #  Document is found if result has a doc type.
        if len(result.get('docType')) != 0:
            return {"error": False, "response": result}
        else:
            return {"error": True, "desc": "Not found"}

    except Exception as e:
        raise Exception(e)


async def send_result(result, writer):
    """ Response object """
    serialized_data = pickle.dumps(result)
    writer.write(struct.pack('<L', len(serialized_data)))
    writer.write(serialized_data)
    await writer.drain()
    writer.close()


async def handle_echo(reader, writer):
    """
        Wait for input settigs object and return recognition result.
    """
    request_size = struct.unpack('<L', await reader.readexactly(4))[0]
    request_body = await reader.readexactly(request_size)
    message = pickle.loads(request_body)

    try:
        if global_engine is None:
            global global_engine_exception
            print(global_engine_exception)
            raise Exception(global_engine_exception)
        else:
            result = None
            result = await startRecognition(message)
        await send_result(result, writer)
    except Exception as e:
        await send_result({"error": True, "desc": str(e)}, writer)


async def main():
    """ Create async sockets. Encode data for transmission """
    server = await asyncio.start_server(
        handle_echo, '0.0.0.0', args.port)

    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'Serving on {addrs}')

    async with server:
        await server.serve_forever()

initEngine()
asyncio.run(main())
