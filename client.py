from enum import Enum
import random
import socket
import struct
from datetime import datetime


class StatusCode(Enum):
    EXIST = '000'
    NOT_EXIST = '001'
    CHANGED = '010'
    NOT_CHANGED = '011'
    BAD_REQUEST = '100'
    ID_LEASED = '101'
    DIRECTORY_NEEDED = '110'
    SUCCESS = '111'


class SQRPClient:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port

    def send_request(self, query_type, directory="", file_name="", timestamp=0, file_extension=""):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.server_ip, self.server_port))

            # Constructing header
            message_type = 0  # QUERY

            message_id = random.randint(0, 31)
            if (timestamp == 0):
                timestamp = datetime(2020, 1, 1, 0, 0, 0)
            time_stamp = _encode_timestamp(timestamp)

            if query_type == 0:  # Verify directory existence
                body, body_length = _encode_body(directory)
            elif query_type == 1:  # Check file existence
                body = directory + "," + file_name
                body, body_length = _encode_body(body)
            elif query_type == 2:  # Determine if file has been modified
                body = directory + "," + file_name
                body, body_length = _encode_body(body)
            elif query_type == 3:  # Identify files with extension modified after timestamp
                body = directory + "," + file_extension
                body, body_length = _encode_body(body)
            else:
                raise ValueError("Error: Query Type should between 0-3.")

            # Construct the header
            reserverd = 0
            status_code = (0 << 5) | reserverd
            header = struct.pack("!BIBBB", (message_type << 7) | (
                query_type << 5) | message_id, time_stamp, status_code, body_length, reserverd)

            # header = (message_type << 63) | (query_type << 61) | (message_id << 56) | (time_stamp << 24) | (status_code << 21) | (reserverd << 16) | (body_length << 8) | reserverd
            # !: Network (big-endian) byte order.
            # I: Unsigned integer (4 bytes).
            # B: Unsigned char (1 byte).

            # Sending request
            request = header + body
            s.sendall(request)
            print("Request Message ID: ", message_id)

            # Receiving response
            response_header = s.recv(8)

            # Extracting body length from the headet
            body_length = response_header[6]

            # Receiving the body data based on the body length
            response_body = s.recv(body_length)

            # Convert byte string to binary
            binary_data = bin(int.from_bytes(response_header, byteorder='big'))

            # Remove the '0b' prefix from the binary representation
            binary_data = binary_data[2:]
            binary_data_with_space = ' '.join(
                binary_data[i:i+4] for i in range(0, len(binary_data), 4))
            print("Response Header Hex:", binary_data_with_space)

            status_code = (response_header[5] >> 5) & 0x07
            resp_encoded_time = response_header[1:5]
            message_id_res = response_header[0] & 0b11111
            query_type = (response_header[0] >> 5) & 0b11
            message_type = (response_header[0] >> 7) & 0b1
            status_name = _find_status_code(status_code=status_code)
            response_body_decoded = response_body.decode()
            resp_timestamp = _decode_timestamp(
                int.from_bytes(resp_encoded_time, byteorder='big'))

            print("Response Message ID:", message_id_res)
            print("Message Type:", message_type)
            print("Query Type:", query_type)
            print("Status Name:", status_name)
            print("Response Body:", response_body_decoded)
            print("Response Timestamp:", resp_timestamp)


def _find_status_code(status_code):
    for status in StatusCode:
        if int(status.value, 2) == status_code:
            return status.name


def _decode_timestamp(encoded_time):
    # Extracting each component from the encoded timestamp
    year = ((encoded_time >> 26) & 0b1111111111) + 2020
    month = (encoded_time >> 22) & 0b1111
    day = (encoded_time >> 17) & 0b11111
    hour = (encoded_time >> 11) & 0b11111
    minute = (encoded_time >> 5) & 0b111111
    second = encoded_time & 0b11111

    # Check if the components form a valid datetime
    return datetime(year, month, day, hour, minute, second)


def _encode_body(body):
    if any(ord(char) > 127 for char in body):
        raise ValueError("Error: Body contains non-ASCII characters.")
    if len(body) > 255:
        raise ValueError(
            "Error: Body length exceeds the maximum length representable by 1 byte.")
    else:
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


if __name__ == "__main__":
    client = SQRPClient("127.0.0.1", 31369)
    print("SQRP 1.1 Client Started!")
    print("Press Ctrl+C to exit")
    while True:
        try:
            extension = ""
            file_name = ""
            file_datetime = 0

            query_type = int(input("Enter query type (0/1/2/3): "))
            if query_type not in [0, 1, 2, 3]:
                print("Invalid query type. Please choose between 0 and 3.")
                continue
            directory = input("Enter directory path: ")
            if query_type in [1, 2]:
                file_name = input("Enter file name: ")
                if query_type == 2:
                    while True:
                        file_datetime_str = input(
                            "Enter file modification datetime (YYYY-MM-DD HH:MM:SS): ")
                        try:
                            file_datetime = datetime.strptime(
                                file_datetime_str, '%Y-%m-%d %H:%M:%S')
                            break
                        except ValueError:
                            print(
                                "Invalid datetime format. Please enter datetime in format YYYY-MM-DD HH:MM:SS")

            elif query_type == 3:
                extension = input("Enter file extension (e.g., txt): ")
                while True:
                        file_datetime_str = input(
                            "Enter file modification datetime (YYYY-MM-DD HH:MM:SS): ")
                        try:
                            file_datetime = datetime.strptime(
                                file_datetime_str, '%Y-%m-%d %H:%M:%S')
                            break
                        except ValueError:
                            print(
                                "Invalid datetime format. Please enter datetime in format YYYY-MM-DD HH:MM:SS")

            client.send_request(query_type=query_type, directory=directory,
                                file_name=file_name, file_extension=extension, timestamp=file_datetime)

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except ValueError:
            print("Invalid input. Please enter a number (0/1/2/3).")
