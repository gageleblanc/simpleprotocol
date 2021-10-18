# Simple Protocol
This project was created because I got tired of making socket based protocols over and over for various projects. 
This allows for quick creation of a server and client which can send "generic" requests/responses back and forth.
These generic transfers can be customized by inheriting the GenericTxParser or GenericTxBuilder classes.

# Usage

### Server
To initialize a SimpleProtocolServer:
```python
from simpleprotocol.server import SimpleProtocolServer
server = SimpleProtocolServer(server_name="Test Server")
```
Without registering any handlers, the server won't be of much use. Registering handlers is simple:
```python
from simpleprotocol.server import SimpleProtocolServer
from simpleprotocol.tx import GenericRequestParser, GenericTxBuilder

# Initialize Server
server = SimpleProtocolServer(server_name="Test Server")

def handler_func(request: GenericRequestParser) -> GenericTxBuilder:
    return GenericTxBuilder(status=200, response=request.value)

# Register Handler and "VALUE" request header
server.register_handler("method_name", handler_func)
server.register_header("VALUE")
server.run_server()
```
As seen here, `handler_func` must return a `GenericTxBuilder` object in order for the server to send the response properly.
You also need to register any headers you'd like the server to recognize in your requests. In the above example, we are
using "VALUE" to store the information we are sending to the server, so we register "VALUE" as a valid header.

### Client
Initializing a SimpleProtocolClient is also easy, although different from the server. Typical usage for the SimpleProtocolClient
looks like this:
```python
from simpleprotocol.client import SimpleProtocolClient
from simpleprotocol.tx import GenericTxBuilder

class MyClient(SimpleProtocolClient):
    def send_message(self, message: str):
        req = GenericTxBuilder(method="method_name", value=message)
        return self._send(req) # Returns GenericResponseParser object

client = MyClient()
res = client.send_message("Hello")
print(res.response) # "Hello"
```
The `_send` method of `SimpleProtocolClient` always returns a `GenericResponseParser` object which contains the information
returned from the server. 