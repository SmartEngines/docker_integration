# IdEngine docker integration

## Requirements

Python >=3.7

## Quick Start

1. Unpack SDK
2. Build image `docker build -t idengineserver -f <dockerfile> ./../../`
3. Run server  `docker run -p 53000:53000 -d idengineserver`
4. Run client.py `python3 client.py --signature=YOUR_SIGNATURE_HERE --image_path="<sdk>/testdata/mrz_passport_2.jpg"`
5. Check `result` folder for result.

---

# Docker

## 1. Building Docker image

   Run `docker build -t idengineserver -f <dockerfile> .`  
   It will compile python wrapper from SDK and create clean docker image for production.
   
   - `-t` - name of your new docker image.
   - `-f` - name of the Dockerfile.



## 2. Run it

   Run container from the image: `docker run -p 53000:53000 -d idengineserver`

   - `-p` - ports to expose
   - `-d` - name of docker image
- `cpus` - by default, each container’s access to the host machine’s CPU cycles is unlimited. If the host machine has two CPUs and you set --cpus="1.5", the container is guaranteed at most one and a half of the CPUs. <https://docs.docker.com/config/containers/resource_constraints/#configure-the-default-cfs-scheduler>

**Default endpoint:** 127.0.0.1:53000

---

# Idengine_server.py 

Dockerfilie default server command:

`python3 idengine_server.py --bundle_dir "./data-zip/bundle.so"`

### flags

`--bundle_dir` - *required* - path to bundle.
`--lazy` - IdEngine lazy mode. Not recommended for server.
`--concur` - Concurrency. All CPU cores enabled by default.
`--port` - Server port. [default 53000]

### log file

Check `error.log` for server exceptions.

# Client.py

Run `python3 client.py --signature=YOUR_SIGNATURE_HERE --image_path="sdk/testdata/mrz_passport_2.jpg" ` 

### client flags

`--mask` - Document mask. [default "*"]
`--mode` - Engine mode. [default "default"]
`--signature` - *required*. Licencse key.
`--image_path` - *required*. Path to local image.
`--output_path` - Output folder for result. [default "./result"]
`--forensics` - Available only for forensics-enabled SDK packages. This option must be enabled with `"common.currentDate": "DD.MM.YYYY"` in `options`forensics data. [default false]
`--endpoint` - server ip adress
`--port` - Port of your server endpoint. [default 53000]
`--log` - Return last 80 lines from error.log

Result will be saved in `result` folder.

----
**Response**

```json
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
```
----

**Response with exceptions**

```json
{
   "error":true,
   "desc": "exception description"
}
```
----

