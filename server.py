from datetime import datetime
import socket
import struct
import os
import threading
from enum import Enum
import time


class StatusCode(Enum):
    EXIST = '000'
    NOT_EXIST = '001'
    CHANGED = '010'
    NOT_CHANGED = '011'
    BAD_REQUEST = '100'
    ID_LEASED = '101'
    DIRECTORY_NEEDED = '110'
    SUCCESS = '111'


response = b''


class SQRPServer:
    leased_message_ids = {}

    def __init__(self, port):
        self.port = port

    def check_leasing_id(self, message_id):

        if message_id in SQRPServer.leased_message_ids:
            expire_time = SQRPServer.leased_message_ids[message_id]
            if time.time() > expire_time:
                SQRPServer.leased_message_ids[message_id] = time.time() + 300
                return StatusCode.SUCCESS
            else:
                return StatusCode.ID_LEASED
        elif message_id < 32 and message_id > -1:
            SQRPServer.leased_message_ids[message_id] = time.time() + 300
            return StatusCode.SUCCESS
        else:
            return StatusCode.BAD_REQUEST

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('0.0.0.0', self.port))
            s.listen()

            print("Server listening on port", self.port)

            while True:
                conn, addr = s.accept()
                self.handle_client(conn=conn, addr=addr)

    def handle_client(self, conn, addr):
        with conn:
            try:
                print('Connected by', addr)
                # Receiving response header
                response_header = conn.recv(8)

                # Extracting body length from the headet
                bodylength = response_header[6]

                # Receiving the body data based on the body length
                response_body = conn.recv(bodylength)

                if response_header:

                    message_type = (response_header[0] >> 7) & 0b1
                    if message_type != 0:
                        raise ValueError(StatusCode.BAD_REQUEST)

                    query_type = (response_header[0] >> 5) & 0b11
                    if query_type > 3:
                        raise ValueError(StatusCode.BAD_REQUEST)

                    message_id = response_header[0] & 0b11111
                    status = self.check_leasing_id(message_id=message_id)

                    if status != StatusCode.SUCCESS:
                        raise ValueError(status)

                    encoded_time = response_header[1:5]
                    timestamp = _decode_timestamp(
                        int.from_bytes(encoded_time, byteorder='big'))
                    time_stamp = 0

                    body = ""
                    if query_type == 0:  # Verify directory existence
                        directory = response_body.decode()
                        if directory:
                            result = self._verify_directory(directory)
                        else:
                            result = StatusCode.BAD_REQUEST
                    elif query_type == 1:  # Check file existence
                        directory, file_name = response_body.split(b",")
                        if directory and file_name:
                            result = self._check_file_existence(
                                directory.decode(), file_name.decode())
                        else:
                            result = StatusCode.BAD_REQUEST
                    elif query_type == 2:  # Determine if file has been modified
                        directory, file_name = response_body.split(b",")
                        if directory and file_name:
                            result, timeStamp = self._check_file_modified(
                                directory.decode(), file_name.decode(), timestamp)
                            if (timeStamp == 0):
                                timeStamp = datetime(2020, 1, 1, 0, 0, 0)
                            timestamp_body = _format_datetime(timeStamp)
                            time_stamp = _encode_timestamp(timeStamp)
                            f = str(file_name.decode())
                            s = timestamp_body
                            body = f + "-" + s
                        else:
                            result = StatusCode.BAD_REQUEST
                    elif query_type == 3:  # Identify files with extension modified after timestamp
                        directory, file_extension = response_body.split(b",")
                        if directory and file_extension:
                            result, modified_files = self._identify_modified_files(
                                directory.decode(), file_extension.decode(), timestamp)
                            if modified_files and len(modified_files) > 0:
                                body = ','.join(
                                    [f"{key}-{value}" for key, value in modified_files])
                        else:
                            result = StatusCode.BAD_REQUEST

                    message_type = 1

                    reserverd = 0

                    status_code = int(result.value) & 0b111
                    status_code = (status_code << 5) | reserverd

                    if time_stamp == 0:
                        time_stamp = int.from_bytes(
                            encoded_time, byteorder='big')
                    encoded_body, body_length = _encode_body(body)

                    result = struct.pack("!BIBBB", (message_type << 7) | (
                        query_type << 5) | message_id, int(time_stamp), status_code, body_length, reserverd)

                    response = result + encoded_body
                else:
                    raise ValueError(StatusCode.BAD_REQUEST)
            except ValueError as e:
                message_type = 1
                status_code = int(e.args[0].value) & 0b111
                reserverd = 0
                status_code = (status_code << 5) | reserverd
                body = e.args[0].name
                encoded_body, body_length = _encode_body(body)
                time_stamp = datetime(2020, 1, 1, 0, 0, 0)
                time_stamp = _encode_timestamp(time_stamp)
                result = struct.pack("!BIBBB", (message_type << 7) | (
                    query_type << 5) | message_id, time_stamp, status_code, body_length, reserverd)
                response = result + encoded_body
            finally:
                try:
                    print(response)
                    if response and response is not None:
                        conn.sendall(response)
                except OSError as e:
                    print("Error sending response:", e)

    def _verify_directory(self, directory):
        if os.path.exists(directory):
            return StatusCode.EXIST
        else:
            return StatusCode.NOT_EXIST

    def _check_file_existence(self, directory:str, file_name):
        if self._verify_directory(directory=directory) == StatusCode.EXIST:
            if not directory.endswith('/'):
                directory = directory + '/'
            return self._verify_directory(directory=directory + file_name)
        else:
            return StatusCode.DIRECTORY_NEEDED

    def _check_file_modified(self, directory, file_name, timestamp):
        if not directory.endswith('/'):
            directory = directory + '/'
        if self._check_file_existence(directory=directory, file_name=file_name) == StatusCode.EXIST:
            file_modified_time = os.path.getmtime(directory+file_name)
            modified_time_stamp = datetime.fromtimestamp(file_modified_time)
            if modified_time_stamp > timestamp:
                return StatusCode.CHANGED, modified_time_stamp
            else:
                return StatusCode.NOT_CHANGED, modified_time_stamp
        else:
            return StatusCode.NOT_EXIST, 0

    def _identify_modified_files(self, directory, file_extension, timestamp):
        if self._verify_directory(directory=directory) == StatusCode.EXIST:
            modified_files = []
            for file in os.listdir(directory):
                if file.endswith(file_extension):
                    file_path = os.path.join(directory, file)
                    file_modified_time = os.path.getmtime(file_path)
                    modified_time_stamp = datetime.fromtimestamp(
                        file_modified_time)
                    if modified_time_stamp > timestamp:
                        timestamp_body = _format_datetime(modified_time_stamp)
                        modified_files.append((file, timestamp_body))
            if len(modified_files) > 0:
                return StatusCode.SUCCESS, modified_files
            else:
                return StatusCode.NOT_EXIST, []
        else:
            return StatusCode.DIRECTORY_NEEDED, []


def _encode_body(body):
    if len(body) > 255:
        body = body[:255]
    # Convert string to ASCII bytes
    ascii_bytes = body.encode('ascii')

    # Get the length of the bytes
    byte_length = len(ascii_bytes)
    return ascii_bytes, byte_length


def _encode_timestamp(timeStamp):
    year, month, day, hour, minute, second = separate_datetime(timeStamp)

    if year < 2020:
        raise ValueError("Error: Input date cannot be earlier than 2020")
    elif year > 2083:
        raise ValueError("Error: Input date cannot be further than 2083")

    # To check if it's a valid datetime
    datetime(year, month, day, hour, minute, second)

    # Encode each component with specified bit lengths
    encoded_time = ((year - 2020) << 26) | (month << 22) | (day <<
                                                            17) | (hour << 11) | (minute << 5) | second
    return encoded_time


def separate_datetime(dt):
    year = dt.year
    month = dt.month
    day = dt.day
    hour = dt.hour
    minute = dt.minute
    second = dt.second
    return year, month, day, hour, minute, second


def _decode_timestamp(encoded_time):
    # Extracting each component from the encoded timestamp
    year = ((encoded_time >> 26) & 0b1111111111) + 2020
    month = (encoded_time >> 22) & 0b1111
    day = (encoded_time >> 17) & 0b11111
    hour = (encoded_time >> 11) & 0b11111
    minute = (encoded_time >> 5) & 0b111111
    second = encoded_time & 0b11111

    # Check if the components form a valid datetime
    try:
        return datetime(year, month, day, hour, minute, second)
    except ValueError as e:
        raise ValueError(StatusCode.BAD_REQUEST) from e


def _format_datetime(date_time: datetime):
    return date_time.strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    server = SQRPServer(31369)
    server.start()
