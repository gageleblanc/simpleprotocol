import json
from clilib.builders.app import EasyCLI
from simpleprotocol.v2.client import PupClient
from simpleprotocol.v2.tools import print_out, print_in, strfdelta
from simpleprotocol.v2.tx import ClientRequest
from urllib.parse import urlparse


def pup_client(url: str, authentication_type: str = None, token: str = None, files: list = None, skip_ssl_validation: bool = False, verbose: bool = False):
    """
    Command line pup client, similar to curl.
    :param url: The URL to request
    :param authentication_type: The authentication type to use. Defaults to "token".
    :param token: Optional token to use for authentication, added to request parameters.
    :param files: Files to upload, passed as list of paths.
    :param ssl_enabled: Whether or not to enable SSL.
    :param skip_ssl_validation: Whether or not to skip SSL validation. Defaults to False.
    :param verbose: Whether to print additional information about the request and response.
    """
    if not url.startswith("pup://") and not url.startswith("pups://"):
        url = "pup://" + url
    url = urlparse(url)
    if url.scheme == "pups":
        ssl_enabled = True
    else:
        ssl_enabled = False
    parameters = {}
    if url.query:
        for parameter in url.query.split("&"):
            key, value = parameter.split("=")
            parameters[key] = value
    if token:
        if authentication_type is None:
            authentication_type = "Token"
        parameters["Authorization"] = f"{authentication_type} {token}"
    client = PupClient(url.hostname, url.port, ssl_enabled=ssl_enabled, validate_ssl=not skip_ssl_validation)
    body = None
    if files is not None:
        parameters["Files"] = files
    request = ClientRequest(url.path, parameters=parameters, body=body)
    try:
        response = client.send_request(request)
    except Exception as e:
        print(e)
        return
    if response is None:
        print("No response received.")
        return
    if verbose:
        print(f">>> Preprocessing time: {strfdelta(response.timings['preprocessing'], '{milliseconds}ms {microseconds}μs')}")
        print(f">>> Connection time: {strfdelta(response.timings['connection'], '{milliseconds}ms {microseconds}μs')}")
        print(f">>> Data transfer time: {strfdelta(response.timings['data'], '{milliseconds}ms {microseconds}μs')}")
        print(f">>> File upload time: {strfdelta(response.timings['file_upload'], '{milliseconds}ms {microseconds}μs')}")
        print(f">>> Total time: {strfdelta(response.timings['overall'], '{milliseconds}ms {microseconds}μs')}\r\n")
        print(print_out(request.build()))
        print("----------------")
        print(print_in(response.raw_response))
    else:
        if response.json_body:
            print(json.dumps(response.body, indent=4))
        else:
            print(response.body)

def main():
    EasyCLI(pup_client)

if __name__ == "__main__":
    main()