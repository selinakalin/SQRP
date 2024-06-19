## SQRP (Simple Query and Response Protocol)

SQRP is a simple client-server protocol designed for querying information about directories and files on a server. This guide provides instructions on how to run the SQRP client and server, introduces the dependencies required, and explains their purposes.

### IP Address and Port

By default, the client is configured to connect to `127.0.0.1` (localhost) on port `31369`. You can modify these values in the `client.py` file if needed.

### Dependencies

The SQRP client and server are implemented in Python and require the following dependencies:

1. **Python 3.x:** The programming language used to develop the client and server applications.
2. **enum:** Used for defining enumeration classes in Python.
3. **socket:** Provides access to the BSD socket interface, allowing communication between the client and server over a network.
4. **struct:** Used for packing and unpacking binary data, essential for constructing and parsing protocol headers.
5. **datetime:** Provides classes for manipulating dates and times, necessary for handling timestamps.
6. **os:** Provides a portable way to interact with the operating system, used for file and directory operations.
7. **threading:** Used for handling multiple client connections concurrently on the server side.

### Running the Server

To run the SQRP server:

1. Ensure you have Python installed on your system.
2. Navigate to the directory containing the `server.py` file in your terminal or command prompt.
3. Run the following command:

    ```
    python server.py
    ```

   The server will start listening for incoming connections on port `31369`. You can modify the port number in the `SQRPServer` instantiation if needed.

### Running the Client

To run the SQRP client:

1. Ensure you have Python installed on your system.
2. Navigate to the directory containing the `client.py` file in your terminal or command prompt.
3. Run the following command:

    ```
    python client.py
    ```

   Follow the prompts on the command line to input the query type, directory path, file name (if applicable), file extension (if applicable), and file modification datetime (if applicable).

### How to Use

1. **Query Types:**

   Enter a query type (`0/1/2/3`) to perform the following operations:
   
   - `0`: Verify directory existence.
   - `1`: Check file existence.
   - `2`: Determine if a file has been modified after a specific timestamp.
   - `3`: Identify files with a specific extension modified after a timestamp.

2. **Directory Path:**

   Enter the path of the directory you want to query.

3. **File Name:**

   Enter the name of the file you want to check for existence or modification.

4. **File Extension and Modification Datetime:**

   - Enter the extension of the files you want to query.
   - Enter the modification datetime in the format `YYYY-MM-DD HH:MM:SS`.

5. **Response:**

   The client will display the response message ID, message type, query type, status name, response body (if applicable), and response timestamp.

### Note

- Ensure the server is running before executing the client.
- Both the client and server should be running on the same network for communication to occur successfully.